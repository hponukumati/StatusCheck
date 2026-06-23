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

# Phrases that indicate a segment is status text, not a company name
# (e.g. "Acme - Application received" -> "Application received" is status text)
_STATUS_PHRASE_RE = re.compile(r"application|applying|received|submitted|thank you", re.IGNORECASE)


def extract_company_from_subject(subject: str) -> Optional[str]:
    """Try to extract company name from subject. Returns None if nothing clear."""
    name, _confidence = _extract_company_from_subject_with_confidence(subject)
    return name


def _extract_company_from_subject_with_confidence(subject: str) -> Tuple[Optional[str], str]:
    """Like extract_company_from_subject, but also reports confidence ("high"/"low").

    "high" means the subject matched a known, specific phrasing (a prefix like
    "thank you for applying to", an explicit "X - Application received" split, or
    "Role at Company"). "low" means we fell back to a generic dash/colon split that
    could easily grab the wrong segment.
    """
    if not subject or not subject.strip():
        return None, "low"
    subject = subject.strip()
    # Try prefixes first (e.g. "Thank you for applying to Company Name")
    for pat in APPLICATION_PREFIXES:
        m = re.search(pat, subject, re.IGNORECASE)
        if m:
            rest = subject[m.end() :].strip()
            # Rest might be "Company Name" or "Role at Company"
            name = _take_first_part(rest)
            if name and len(name) > 1:
                return name.strip(), "high"
    # "Company - Application received" style: company comes before the status phrase
    parts = re.split(r"\s*[:\-]\s*", subject, maxsplit=1)
    if len(parts) == 2:
        first, rest = parts[0].strip(), parts[1].strip()
        if (
            first
            and 1 < len(first) < 100
            and not _STATUS_PHRASE_RE.search(first)
            and _STATUS_PHRASE_RE.search(rest)
        ):
            return first, "high"
    # "Role at Company" is specific enough to trust
    m = re.search(APPLICATION_SUFFIXES[1], subject)
    if m:
        name = m.group(1).strip()
        if name and len(name) > 1 and len(name) < 120:
            return name, "high"
    # Remaining suffix patterns are generic dash/colon splits - easy to mismatch
    for pat in (APPLICATION_SUFFIXES[0], APPLICATION_SUFFIXES[2]):
        m = re.search(pat, subject)
        if m:
            name = m.group(1).strip()
            if name and len(name) > 1 and len(name) < 120:
                return name, "low"
    # Fallback: first "word" that looks like a name (e.g. "Acme - Application received")
    parts = re.split(r"\s*[:\-]\s*", subject, maxsplit=1)
    if parts:
        first = parts[0].strip()
        if first and len(first) > 1 and len(first) < 100:
            return first, "low"
    return None, "low"


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


def parse_application_email(subject: str, from_header: str) -> Tuple[str, str, str]:
    """Extract (company_name, position, confidence). company_name is required; uses
    sender if subject fails. confidence is "high" or "low" - "low" means the
    company name is a guess (sender-domain fallback, generic split, or "Unknown")
    and may be worth a manual look in the CSV.
    """
    company, confidence = _extract_company_from_subject_with_confidence(subject)
    if not company:
        company = extract_company_from_sender(from_header)
        confidence = "low"
    if not company:
        company = "Unknown"
        confidence = "low"
    position = extract_position_from_subject(subject)
    return (company, position, confidence)
