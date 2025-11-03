"""
Optional helpers for Google Calendar integration if you decide to move
OAuth/token storage server-side. Not required for the MVP since the
frontend can call Google APIs directly after OAuth.
"""
from typing import Dict, Any

def build_google_event(ev: Dict[str, Any], timezone: str) -> Dict[str, Any]:
    """
    Convert our event row into a Google Calendar 'events.insert' payload.
    Assumes ev has start_date/end_date/start_time/end_time/days.
    """
    byday = ",".join(ev.get("days", []))
    start_dt = f"{ev['start_date']}T{ev['start_time']}:00"
    end_dt = f"{ev['start_date']}T{ev['end_time']}:00"
    until = ev['end_date'].replace("-", "") + "T235959Z"

    body = {
        "summary": ev.get("title", "Class"),
        "location": ev.get("location") or None,
        "description": ev.get("notes") or None,
        "start": {"dateTime": start_dt, "timeZone": timezone},
        "end": {"dateTime": end_dt, "timeZone": timezone},
        "recurrence": [f"RRULE:FREQ=WEEKLY;BYDAY={byday};UNTIL={until}"]
    }
    return body
