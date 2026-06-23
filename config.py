"""Configuration for the application tracking agent."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Path to the CSV file (default: same directory as this file)
CSV_PATH = Path(os.environ.get("STATUSCHECK_CSV_PATH", BASE_DIR / "applications.csv"))

# How many days back to search Gmail (avoids missing emails if a run was skipped)
SEARCH_DAYS_BACK = int(os.environ.get("STATUSCHECK_DAYS_BACK", "365"))

# Application confirmation subject keywords (Gmail search)
APPLICATION_SUBJECT_KEYWORDS = [
    "application received",
    "we received your application",
    "thank you for applying",
]

# Interview-invite keywords (searched in subject and body)
INTERVIEW_KEYWORDS = [
    "schedule an interview",
    "schedule a call",
    "schedule a phone screen",
    "phone screen",
    "would like to interview",
    "next steps in the interview process",
    "set up a time to chat",
    "set up an interview",
    "interview invitation",
    "invite you to interview",
]

# Offer keywords (searched in subject and body)
OFFER_KEYWORDS = [
    "pleased to offer",
    "happy to offer",
    "offer letter",
    "extend an offer",
    "job offer",
    "offer of employment",
    "congratulations, we",
]

# Rejection keywords (searched in subject and body)
REJECTION_KEYWORDS = [
    "unfortunately",
    "we have decided not to move forward",
    "not moving forward",
    "other candidates",
    "we will not be moving forward",
    "no longer considering",
    "not interested",
    "not pursuing",
    "not moving forward",
    "not considering",
    "we regret to inform you",
    "We are moving forward with other applicants for this position at this time.",
    "At this time we have closed or filled the job.",
    "The position has been filled.",
    "we’ve decided to pursue other candidates",
    "Thank you for your interest",
]

# Your own email addresses (used to ignore replies you send yourself).
# Comma-separated list from environment, e.g. "me@gmail.com, work@company.com".
_user_emails_raw = os.environ.get("STATUSCHECK_USER_EMAILS", "")
USER_EMAILS = [
    email.strip().lower()
    for email in _user_emails_raw.split(",")
    if email.strip()
]

# If set, a daily digest email summarizing today's changes is sent to this address
# after each run. Leave unset to disable the digest.
DIGEST_EMAIL = os.environ.get("STATUSCHECK_DIGEST_EMAIL", "").strip()

