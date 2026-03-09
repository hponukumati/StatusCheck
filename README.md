# StatusCheck – Gmail application tracker

Tracks job applications by reading Gmail: adds new application confirmations to a CSV and marks rows as **Rejected** when rejection emails (e.g. containing "unfortunately") are found. Designed to run once per day (e.g. at 11 PM via cron).

## Setup

### 1. Python and virtual environment

```bash
cd /path/to/StatusCheck
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Gmail API (one-time)

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select one) and enable **Gmail API** (APIs & Services → Enable APIs → Gmail API).
3. Configure **OAuth consent screen**: User Type “External”, add your Gmail as test user.
4. Create **OAuth 2.0 credentials**: APIs & Services → Credentials → Create Credentials → OAuth client ID → Application type **Desktop app**.
5. **Add the redirect URI**: Open your OAuth 2.0 Client ID (click its name under Credentials). Under **Authorized redirect URIs**, click **Add URI** and add:
   - `http://localhost:2001/`
   - (optional) `http://127.0.0.1:2001/`
   Save. This must match the port used in `gmail_client.py` (2001).
6. Download the JSON and save it as `credentials.json` in the project root (same folder as `run.py`).

**Do not commit `credentials.json` or `token.json` to version control.**

### 3. First run (browser login)

Run once interactively so the script can open a browser and save tokens:

```bash
python run.py
```

Sign in with your Google account and allow Gmail read access. Tokens are saved to `token.json`. After that, you can run the script from cron without a browser.

## Usage

- **Manual run**: `python run.py`
- **CSV**: By default `applications.csv` is created in the project directory. Override with:
  ```bash
  export STATUSCHECK_CSV_PATH=/path/to/applications.csv
  python run.py
  ```
- **Search window**: The script looks at the last 30 days of email. Change with:
  ```bash
  export STATUSCHECK_DAYS_BACK=14
  ```

## Running daily at end of day (cron)

1. Create a log directory (optional but recommended):
   ```bash
   mkdir -p /path/to/StatusCheck/logs
   ```

2. Edit crontab: `crontab -e`

3. Add a line to run at 11 PM every day (adjust paths to your system):
   ```
   0 23 * * * /path/to/StatusCheck/venv/bin/python /path/to/StatusCheck/run.py >> /path/to/StatusCheck/logs/cron.log 2>&1
   ```

Use your actual project path, e.g. `/Users/harshaponukumati/Projects/StatusCheck`.

## CSV format

| Column               | Description                                  |
|----------------------|----------------------------------------------|
| company_name         | Extracted from subject/sender                |
| position             | Role if detectable from subject              |
| applied_date         | Date the application email was received      |
| status               | `Applied` or `Rejected`                      |
| application_email_id | Gmail message ID (avoids duplicates)        |
| subject              | Application email subject                    |
| sender_email         | From header (e.g. sender address or name)    |

## How it works

- **New applications**: Searches Gmail (subject and body) for “application received”, “we received your application”, or “thank you for applying”. Each new message (not already in the CSV) is parsed for company name and appended with status `Applied`.
- **Rejections**: Searches for emails with “unfortunately” (and similar) in the subject. For each such email, the script checks whether any `Applied` row’s company name appears in the rejection’s subject or body; those rows are updated to `Rejected`.

## Troubleshooting

- **“Error 400: redirect_uri_mismatch”**: Add `http://localhost:2001/` to your OAuth 2.0 client in Google Cloud Console: **APIs & Services → Credentials → [your OAuth 2.0 Client ID] → Authorized redirect URIs → Add URI** → paste `http://localhost:2001/` → Save. Then try `python run.py` again.
- **“credentials.json not found”**: Place the OAuth client JSON in the project root and name it `credentials.json`.
- **Auth errors**: Delete `token.json` and run `python run.py` again to re-authorize in the browser.
- **No emails found**: Check that the date range (`STATUSCHECK_DAYS_BACK`) includes the relevant emails and that your labels/filters aren’t hiding them from the default inbox search.
