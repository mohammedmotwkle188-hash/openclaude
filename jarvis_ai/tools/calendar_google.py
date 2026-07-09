"""Google Calendar: read upcoming events and create new ones by voice.

Uses OAuth "installed app" flow. You provide your own OAuth client credentials (this is
free but must be set up per-user — Google doesn't allow shipping shared desktop OAuth
secrets): create a project at https://console.cloud.google.com/, enable the Google
Calendar API, make an "OAuth client ID" of type "Desktop app", download the JSON, and
save it as ~/.jarvis_ai/google_credentials.json. First use opens a browser to authorize;
the resulting token is cached at ~/.jarvis_ai/google_token.json so you only do it once.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Dict, List

from config import APP_DIR

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_FILE = APP_DIR / "google_credentials.json"
TOKEN_FILE = APP_DIR / "google_token.json"


def _service():
    # Imported lazily so the whole app doesn't hard-depend on the (heavy) Google client
    # libraries unless calendar features are actually used.
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    if not CREDENTIALS_FILE.exists():
        raise RuntimeError(
            "Google Calendar isn't set up. Save your OAuth client JSON to "
            f"{CREDENTIALS_FILE} — see tools/calendar_google.py for the one-time steps."
        )

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def list_upcoming_events(max_results: int = 10) -> List[Dict]:
    service = _service()
    now = dt.datetime.utcnow().isoformat() + "Z"
    result = (
        service.events()
        .list(calendarId="primary", timeMin=now, maxResults=max_results, singleEvents=True, orderBy="startTime")
        .execute()
    )
    events = result.get("items", [])
    out = []
    for e in events:
        start = e["start"].get("dateTime", e["start"].get("date"))
        out.append({"id": e.get("id"), "title": e.get("summary", "(no title)"), "start": start})
    return out


def create_event(title: str, start: dt.datetime, duration_minutes: int = 60) -> str:
    service = _service()
    end = start + dt.timedelta(minutes=duration_minutes)
    body = {
        "summary": title,
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
    }
    created = service.events().insert(calendarId="primary", body=body).execute()
    return f"Added \"{title}\" to your calendar for {start.strftime('%A %d %B at %H:%M')}. Link: {created.get('htmlLink', '')}"


def summarize_upcoming() -> str:
    events = list_upcoming_events(5)
    if not events:
        return "You have no upcoming events on your calendar."
    lines = [f"{e['title']} at {e['start']}" for e in events]
    return "Your next events: " + "; ".join(lines)
