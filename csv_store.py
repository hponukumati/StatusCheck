"""CSV store for applications: add rows, list applied companies, update status to Rejected."""
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

CSV_HEADER = [
    "company_name",
    "position",
    "applied_date",
    "status",
    "application_email_id",
    "subject",
    "sender_email",
]


def ensure_csv(path: Path) -> None:
    """Create CSV with header if it does not exist."""
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)


def load_rows(path: Path) -> list[dict]:
    """Load all rows as list of dicts (keys = header). Missing columns get empty string."""
    path = Path(path)
    if not path.exists():
        return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [{k: row.get(k, "") for k in CSV_HEADER} for row in reader]


def save_rows(path: Path, rows: list[dict]) -> None:
    """Write all rows back to CSV."""
    def sort_key(r: dict):
        # applied_date is stored as YYYY-MM-DD; unknown/invalid dates go last
        s = (r.get("applied_date") or "").strip()
        try:
            dt = datetime.strptime(s, "%Y-%m-%d")
        except ValueError:
            dt = datetime.min
        # Newest first; break ties by message id for stability
        return (dt, (r.get("application_email_id") or ""))

    rows_sorted = sorted(rows, key=sort_key, reverse=True)
    path = Path(path)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows_sorted)


def has_application_email_id(path: Path, email_id: str) -> bool:
    """Return True if this message ID is already in the CSV."""
    rows = load_rows(path)
    return any(r.get("application_email_id") == email_id for r in rows)


def add_application(
    path: Path,
    company_name: str,
    applied_date: str,
    application_email_id: str,
    subject: str,
    sender_email: str = "",
    position: str = "",
) -> None:
    """Append one application row with status Applied."""
    ensure_csv(path)
    rows = load_rows(path)
    rows.append({
        "company_name": company_name,
        "position": position,
        "applied_date": applied_date,
        "status": "Applied",
        "application_email_id": application_email_id,
        "subject": subject,
        "sender_email": sender_email,
    })
    save_rows(path, rows)


def get_applied_rows(path: Path) -> list[dict]:
    """Return rows where status is Applied (for rejection matching)."""
    rows = load_rows(path)
    return [r for r in rows if r.get("status") == "Applied"]


def update_status_to_rejected(path: Path, company_name: str) -> int:
    """Set status to Rejected for all rows with this company_name and status Applied. Returns count updated."""
    rows = load_rows(path)
    updated = 0
    for r in rows:
        if r.get("company_name") == company_name and r.get("status") == "Applied":
            r["status"] = "Rejected"
            updated += 1
    if updated:
        save_rows(path, rows)
    return updated
