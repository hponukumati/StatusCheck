#!/usr/bin/env python3
"""
Application tracking agent: read Gmail for application confirmations and rejections,
update applications.csv. Run daily (e.g. via cron at end of day).
"""
import logging
import sys
from pathlib import Path

# Add project root for imports when run from cron
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from application_parser import parse_application_email
from csv_store import (
    add_application,
    ensure_csv,
    get_applied_rows,
    has_application_email_id,
    update_status_to_rejected,
)
from gmail_client import (
    after_date_query,
    build_service,
    get_message_details,
    search_messages,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def build_application_query(days_back: int) -> str:
    """Gmail q string for application confirmation emails (searches subject + body)."""
    after = after_date_query(days_back)
    # No "subject:" prefix so Gmail searches entire message (body + subject)
    parts = [
        '("application received" OR "we received your application" OR "thank you for applying")',
        after,
    ]
    return " ".join(parts)


def build_rejection_query(days_back: int) -> str:
    """Gmail q string for rejection emails (searches full message)."""
    after = after_date_query(days_back)
    # Words without "subject:" search entire message (subject + body)
    terms = " OR ".join(f'"{k}"' if " " in k else k for k in config.REJECTION_KEYWORDS[:5])
    return f"({terms}) {after}"


def run_applications(service, csv_path: Path, days_back: int) -> int:
    """Search application emails, add new rows. Returns count added."""
    ensure_csv(csv_path)
    query = build_application_query(days_back)
    message_ids = search_messages(service, query)
    added = 0
    for mid in message_ids:
        if has_application_email_id(csv_path, mid):
            continue
        try:
            details = get_message_details(service, mid)
        except Exception as e:
            log.warning("Failed to fetch message %s: %s", mid, e)
            continue
        company, position = parse_application_email(details["subject"], details["from"])
        applied_date = details["date"].strftime("%Y-%m-%d") if details["date"] else ""
        add_application(
            csv_path,
            company_name=company,
            applied_date=applied_date,
            application_email_id=mid,
            subject=details["subject"],
            sender_email=details.get("from", ""),
            position=position,
        )
        added += 1
        log.info("Added application: %s", company)
    return added


def run_rejections(service, csv_path: Path, days_back: int) -> int:
    """Search rejection emails, match by company name, update status. Returns count updated."""
    applied = get_applied_rows(csv_path)
    if not applied:
        return 0
    query = build_rejection_query(days_back)
    message_ids = search_messages(service, query)
    total_updated = 0
    for mid in message_ids:
        try:
            details = get_message_details(service, mid)
        except Exception as e:
            log.warning("Failed to fetch rejection message %s: %s", mid, e)
            continue
        text = (details["subject"] + " " + details["body"]).lower()
        # Find all applied companies mentioned in this rejection email
        companies_to_reject = set()
        for row in applied:
            company = row.get("company_name", "")
            if company and company.lower() in text:
                companies_to_reject.add(company)
        for company in companies_to_reject:
            n = update_status_to_rejected(csv_path, company)
            if n > 0:
                total_updated += n
                log.info("Marked as rejected: %s", company)
        if companies_to_reject:
            applied = get_applied_rows(csv_path)
    return total_updated


def main() -> int:
    credentials_path = config.BASE_DIR / "credentials.json"
    token_path = config.BASE_DIR / "token.json"
    if not credentials_path.exists():
        log.error("credentials.json not found. See README for Gmail API setup.")
        return 1
    log.info("Starting application tracker (CSV: %s)", config.CSV_PATH)
    try:
        service = build_service(str(credentials_path), str(token_path))
    except Exception as e:
        log.error("Gmail auth failed: %s", e)
        return 1
    days = config.SEARCH_DAYS_BACK
    added = run_applications(service, config.CSV_PATH, days)
    updated = run_rejections(service, config.CSV_PATH, days)
    log.info("Done. Added %d applications, marked %d as rejected.", added, updated)
    return 0


if __name__ == "__main__":
    sys.exit(main())
