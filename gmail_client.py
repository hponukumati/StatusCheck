"""Gmail API client: authentication, search, and message fetching."""
import base64
import os
import re
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail read-only scope
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_credentials(credentials_path: str = "credentials.json", token_path: str = "token.json"):
    """Load or refresh OAuth2 credentials. First run opens browser for consent."""
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            # Port 2001: add http://localhost:2001/ to OAuth client's Authorized redirect URIs in Google Cloud Console
            creds = flow.run_local_server(port=2001)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return creds


def build_service(credentials_path: str = "credentials.json", token_path: str = "token.json"):
    """Build Gmail API service with valid credentials."""
    creds = get_credentials(credentials_path, token_path)
    return build("gmail", "v1", credentials=creds)


def search_messages(service, query: str, max_results: int = 500):
    """List message IDs matching the Gmail search query. Paginates automatically."""
    message_ids = []
    page_token = None
    while True:
        resp = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=min(100, max_results - len(message_ids)), pageToken=page_token)
            .execute()
        )
        for m in resp.get("messages", []):
            message_ids.append(m["id"])
            if len(message_ids) >= max_results:
                return message_ids
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return message_ids


def get_message(service, message_id: str):
    """Fetch full message (headers + body). Returns dict with 'payload', 'internalDate', etc."""
    return service.users().messages().get(userId="me", id=message_id, format="full").execute()


def _decode_body(payload: dict) -> str:
    """Extract plain-text body from Gmail message payload (handles multipart)."""
    if "body" in payload and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
            # Fallback: use HTML if no plain text
            raw = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
            return re.sub(r"<[^>]+>", " ", raw)
    return ""


def get_subject(headers: list) -> str:
    """Get Subject header value from Gmail headers list."""
    for h in headers:
        if h.get("name", "").lower() == "subject":
            return h.get("value", "")
    return ""


def get_from(headers: list) -> str:
    """Get From header value."""
    for h in headers:
        if h.get("name", "").lower() == "from":
            return h.get("value", "")
    return ""


def get_body(service, message_id: str) -> str:
    """Get plain-text body of a message."""
    msg = get_message(service, message_id)
    return _decode_body(msg.get("payload", {}))


def get_message_details(service, message_id: str):
    """Get subject, from, date (internalDate), and body for a message."""
    msg = get_message(service, message_id)
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])
    subject = get_subject(headers)
    from_header = get_from(headers)
    internal_date_ms = msg.get("internalDate")
    if internal_date_ms:
        try:
            date = datetime.fromtimestamp(int(internal_date_ms) / 1000.0)
        except (ValueError, OSError):
            date = None
    else:
        date = None
    body = _decode_body(payload)
    return {
        "message_id": message_id,
        "subject": subject,
        "from": from_header,
        "date": date,
        "body": body,
    }


def after_date_query(days_back: int) -> str:
    """Gmail 'after' query for the given number of days back (e.g. after:2024/01/01)."""
    d = datetime.now().date() - timedelta(days=days_back)
    return f"after:{d.year}/{d.month:02d}/{d.day:02d}"
