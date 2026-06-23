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
    "confidence",
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
    confidence: str = "high",
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
        "confidence": confidence,
    })
    save_rows(path, rows)


def get_rows_with_status(path: Path, statuses: list[str]) -> list[dict]:
    """Return rows whose status is one of the given statuses."""
    rows = load_rows(path)
    return [r for r in rows if r.get("status") in statuses]


def update_status(path: Path, company_name: str, new_status: str, from_statuses: list[str]) -> int:
    """Set status to new_status for rows with this company_name whose current status
    is one of from_statuses. Returns count updated.
    """
    rows = load_rows(path)
    updated = 0
    for r in rows:
        if r.get("company_name") == company_name and r.get("status") in from_statuses:
            r["status"] = new_status
            updated += 1
    if updated:
        save_rows(path, rows)
    return updated
