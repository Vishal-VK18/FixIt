# CampusCare

CampusCare is the FastAPI + Stitch campus maintenance application. It stores tickets, accounts, and sessions in the single authoritative `tickets.db` database.

## Setup

```powershell
py -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `OPENROUTER_API_KEY` in the server-side `.env` to enable real OpenRouter vision analysis. The model defaults to `openrouter/free` and can be changed with `OPENROUTER_MODEL`; `OPENROUTER_TIMEOUT_SECONDS` defaults to 60. Without a key, photo analysis displays a configuration error and students can still submit a ticket manually. Never place the key in browser code.

Set `SECURITY_CONTACT_NUMBER` to the campus security contact used in emergency notices. Leave it blank until the real contact is known.

Start the app:

```powershell
py app.py
```

## Accounts

Students create accounts from the Student Registration form. Passwords are stored as PBKDF2-HMAC-SHA256 hashes; sessions use expiring, HttpOnly cookies. Set `ENVIRONMENT=production` or `COOKIE_SECURE=true` when serving over HTTPS.

Create the first administrator from the application directory. The command prompts for name, email, and a password without echoing the password:

```powershell
py auth.py create-admin
```

There is no public administrator registration. Admin dashboards, ticket management, analytics, predictive maintenance, and settings are protected by backend role checks.

## Tests

```powershell
py -m pytest tests test_person1.py -q -p no:cacheprovider -p no:tmpdir
py -m compileall -q .
node --check static/app.js
```

Tests use an isolated temporary database and do not edit the local application database or `.env`.

## Legacy Streamlit files

`student_app.py`, `report_page.py`, `database.py`, `dashboard_page.py`, and the old Streamlit-only helpers are deprecated. `student_app.py` exits with a migration message so a second app cannot be started accidentally. The active FastAPI application is the only supported ticket-entry point and uses `tickets.db`. The older `fixit.db` file is not read or migrated automatically; its existing records remain untouched.
