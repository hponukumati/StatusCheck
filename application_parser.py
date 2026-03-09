"""Extract company name and optional position from application email subject/sender."""
import re
from typing import Optional, Tuple


# Common phrases that precede or follow company name in subjects
APPLICATION_PREFIXES = [
    r"thank you for applying (?:to|at)\s*[:\-]?\s*",
    r"we received your application (?:for|at|to)\s*[:\-]?\s*",
    r"application received\s*[:\-]\s*",
    r"application (?:received|submitted)\s*[:\-]?\s*",
    r"re:\s*application\s*[:\-]?\s*",
]
# Suffixes like "... at Company Name" or "... - Company"
APPLICATION_SUFFIXES = [
    r"\s*[:\-]\s*([^\-]+?)(?:\s*[:\-]|$)",
    r"\s+at\s+([A-Za-z0-9][A-Za-z0-9\s&.,'-]+?)(?:\s*[:\-]|$)",
    r"\s+[:\-]\s*([A-Za-z0-9][A-Za-z0-9\s&.,'-]+?)$",
]


def extract_company_from_subject(subject: str) -> Optional[str]:
    """Try to extract company name from subject. Returns None if nothing clear."""
    if not subject or not subject.strip():
        return None
    subject = subject.strip()
    # Try prefixes first (e.g. "Thank you for applying to Company Name")
    for pat in APPLICATION_PREFIXES:
        m = re.search(pat, subject, re.IGNORECASE)
        if m:
            rest = subject[m.end() :].strip()
            # Rest might be "Company Name" or "Role at Company"
            name = _take_first_part(rest)
            if name and len(name) > 1:
                return name.strip()
    # Try "Role at Company" or "... - Company"
    for pat in APPLICATION_SUFFIXES:
        m = re.search(pat, subject)
        if m:
            name = m.group(1).strip()
            if name and len(name) > 1 and len(name) < 120:
                return name
    # Fallback: first "word" that looks like a name (e.g. "Acme - Application received")
    parts = re.split(r"\s*[:\-]\s*", subject, maxsplit=1)
    if parts:
        first = parts[0].strip()
        if first and len(first) > 1 and len(first) < 100:
            return first
    return None


def _take_first_part(s: str) -> str:
    """Take first segment before common separators (dash, newline, etc.)."""
    for sep in (" - ", " – ", " | ", "\n"):
        if sep in s:
            return s.split(sep)[0].strip()
    return s.strip()


def extract_position_from_subject(subject: str) -> str:
    """Optional: try to get role/position from subject. Returns empty string if not found."""
    if not subject:
        return ""
    # e.g. "Application received - Software Engineer at Acme"
    m = re.search(r"[:\-]\s*([A-Za-z0-9][A-Za-z0-9\s&.,'-]+?)\s+at\s+", subject, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def extract_company_from_sender(from_header: str) -> Optional[str]:
    """Fallback: derive a name from sender (e.g. noreply@company.com -> Company)."""
    if not from_header:
        return None
    # "Company Name <noreply@company.com>" -> try display name first
    if "<" in from_header and ">" in from_header:
        display = from_header.split("<")[0].strip().strip('"')
        if display and len(display) < 100:
            return display
    # email part: company.com -> Company
    email = from_header
    if "<" in from_header:
        email = from_header.split("<")[1].split(">")[0].strip()
    if "@" in email:
        domain = email.split("@")[1].lower()
        # remove common TLDs and take first part
        name = domain.replace(".com", "").replace(".co", "").replace(".io", "").split(".")[0]
        if name:
            return name.capitalize()
    return None


def parse_application_email(subject: str, from_header: str) -> Tuple[str, str]:
    """Extract (company_name, position). company_name is required; uses sender if subject fails."""
    company = extract_company_from_subject(subject)
    if not company:
        company = extract_company_from_sender(from_header)
    if not company:
        company = "Unknown"
    position = extract_position_from_subject(subject)
    return (company, position)
