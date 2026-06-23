#!/usr/bin/env python3
"""
Application tracking agent: read Gmail for application confirmations and rejections,
update applications.csv. Run daily (e.g. via cron at end of day).
"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root for imports when run from cron
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from application_parser import parse_application_email
from csv_store import (
    add_application,
    ensure_csv,
    get_rows_with_status,
    has_application_email_id,
    update_status,
)
from gmail_client import (
    after_date_query,
    build_service,
    get_message_details,
    search_messages,
    send_email,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def _is_from_self(from_header: str) -> bool:
    """
    Return True if the email appears to be sent by the user themself.

    We check configured USER_EMAILS (from STATUSCHECK_USER_EMAILS) against the
    From header. If no USER_EMAILS are configured, we assume nothing is "self".
    """
    if not getattr(config, "USER_EMAILS", None):
        return False
    header = (from_header or "").lower()
    return any(email in header for email in config.USER_EMAILS)


def build_application_query(days_back: int) -> str:
    """Gmail q string for application confirmation emails (searches subject + body)."""
    after = after_date_query(days_back)
    # No "subject:" prefix so Gmail searches entire message (body + subject)
    parts = [
        '("application received" OR "we received your application" OR "thank you for applying")',
        after,
    ]
    return " ".join(parts)


def build_keyword_query(days_back: int, keywords: list) -> str:
    """Gmail q string matching any of the given keywords (searches subject + body)."""
    after = after_date_query(days_back)
    # Words without "subject:" search entire message (subject + body)
    terms = " OR ".join(f'"{k}"' if " " in k else k for k in keywords[:5])
    return f"({terms}) {after}"


def run_applications(service, csv_path: Path, days_back: int, dry_run: bool = False) -> list:
    """Search application emails, add new rows. Returns list of company names added
    (or that would be added, if dry_run)."""
    if not dry_run:
        ensure_csv(csv_path)
    query = build_application_query(days_back)
    message_ids = search_messages(service, query)
    added = []
    for mid in message_ids:
        if has_application_email_id(csv_path, mid):
            continue
        try:
            details = get_message_details(service, mid)
        except Exception as e:
            log.warning("Failed to fetch message %s: %s", mid, e)
            continue
        # Skip replies sent by you so we only track employer-originated emails.
        if _is_from_self(details.get("from", "")):
            continue
        company, position, confidence = parse_application_email(details["subject"], details["from"])
        applied_date = details["date"].strftime("%Y-%m-%d") if details["date"] else ""
        if not dry_run:
            add_application(
                csv_path,
                company_name=company,
                applied_date=applied_date,
                application_email_id=mid,
                subject=details["subject"],
                sender_email=details.get("from", ""),
                position=position,
                confidence=confidence,
            )
        added.append(company)
        prefix = "[DRY RUN] Would add" if dry_run else "Added"
        if confidence == "low":
            log.warning("%s application with LOW confidence company name: %s (subject: %s)", prefix, company, details["subject"])
        else:
            log.info("%s application: %s", prefix, company)
    return added


def run_status_update(
    service,
    csv_path: Path,
    days_back: int,
    keywords: list,
    new_status: str,
    from_statuses: list,
    dry_run: bool = False,
) -> list:
    """Search for emails matching keywords, match by company name against rows whose
    current status is one of from_statuses, and update them to new_status.
    Returns list of company names updated (or that would be updated, if dry_run).
    """
    candidates = get_rows_with_status(csv_path, from_statuses)
    if not candidates:
        return []
    query = build_keyword_query(days_back, keywords)
    message_ids = search_messages(service, query)
    updated_companies = []
    already_seen = set()
    prefix = "[DRY RUN] Would mark" if dry_run else "Marked"
    for mid in message_ids:
        try:
            details = get_message_details(service, mid)
        except Exception as e:
            log.warning("Failed to fetch message %s: %s", mid, e)
            continue
        text = (details["subject"] + " " + details["body"]).lower()
        # Find all candidate companies mentioned in this email
        companies_matched = set()
        for row in candidates:
            company = row.get("company_name", "")
            if company and company.lower() in text:
                companies_matched.add(company)
        for company in companies_matched:
            if company in already_seen:
                continue
            if dry_run:
                already_seen.add(company)
                updated_companies.append(company)
                log.info("%s as %s: %s", prefix, new_status, company)
                continue
            n = update_status(csv_path, company, new_status, from_statuses)
            if n > 0:
                already_seen.add(company)
                updated_companies.append(company)
                log.info("%s as %s: %s", prefix, new_status, company)
        if companies_matched and not dry_run:
            candidates = get_rows_with_status(csv_path, from_statuses)
    return updated_companies


def build_digest(added: list, interviewed: list, offered: list, rejected: list) -> str:
    """Build a plain-text summary of today's changes."""
    sections = [
        ("New applications", added),
        ("Interviews", interviewed),
        ("Offers", offered),
        ("Rejections", rejected),
    ]
    lines = []
    for title, companies in sections:
        if companies:
            lines.append(f"{title} ({len(companies)}):")
            lines.extend(f"  - {c}" for c in companies)
            lines.append("")
    return "\n".join(lines).strip()


def send_digest(service, added: list, interviewed: list, offered: list, rejected: list, dry_run: bool = False) -> None:
    """Email a summary of today's changes to STATUSCHECK_DIGEST_EMAIL, if configured."""
    if not config.DIGEST_EMAIL:
        return
    if not (added or interviewed or offered or rejected):
        log.info("No changes today; skipping digest email.")
        return
    body = build_digest(added, interviewed, offered, rejected)
    today = datetime.now().strftime("%Y-%m-%d")
    if dry_run:
        log.info("[DRY RUN] Would send digest email to %s:\n%s", config.DIGEST_EMAIL, body)
        return
    try:
        send_email(service, config.DIGEST_EMAIL, f"StatusCheck digest - {today}", body)
        log.info("Sent digest email to %s", config.DIGEST_EMAIL)
    except Exception as e:
        log.warning("Failed to send digest email: %s", e)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track job applications by reading Gmail.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing to the CSV or sending email.",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=None,
        help=f"Days of Gmail history to search (default: {config.SEARCH_DAYS_BACK}, or $STATUSCHECK_DAYS_BACK).",
    )
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=None,
        help=f"Path to the CSV file (default: {config.CSV_PATH}, or $STATUSCHECK_CSV_PATH).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    csv_path = args.csv_path or config.CSV_PATH
    days = args.days_back if args.days_back is not None else config.SEARCH_DAYS_BACK

    credentials_path = config.BASE_DIR / "credentials.json"
    token_path = config.BASE_DIR / "token.json"
    if not credentials_path.exists():
        log.error("credentials.json not found. See README for Gmail API setup.")
        return 1
    log.info(
        "Starting application tracker (CSV: %s)%s", csv_path, " [DRY RUN]" if args.dry_run else ""
    )
    try:
        service = build_service(str(credentials_path), str(token_path))
    except Exception as e:
        log.error("Gmail auth failed: %s", e)
        return 1
    added = run_applications(service, csv_path, days, dry_run=args.dry_run)
    # Order matters: check offers/interviews before rejections so a later rejection
    # email can still override an earlier interview/offer (rejection is terminal).
    offered = run_status_update(
        service, csv_path, days, config.OFFER_KEYWORDS, "Offer", ["Applied", "Interview"], dry_run=args.dry_run
    )
    interviewed = run_status_update(
        service, csv_path, days, config.INTERVIEW_KEYWORDS, "Interview", ["Applied"], dry_run=args.dry_run
    )
    rejected = run_status_update(
        service, csv_path, days, config.REJECTION_KEYWORDS, "Rejected", ["Applied", "Interview", "Offer"], dry_run=args.dry_run
    )
    log.info(
        "Done. Added %d applications, %d interviews, %d offers, %d rejected.%s",
        len(added), len(interviewed), len(offered), len(rejected),
        " [DRY RUN - nothing was written]" if args.dry_run else "",
    )
    send_digest(service, added, interviewed, offered, rejected, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
