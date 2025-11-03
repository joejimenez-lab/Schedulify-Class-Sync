from icalendar import Calendar, Event
from datetime import datetime
import pytz

def build_ics(payload: dict) -> bytes:
    """
    Build a single .ics with weekly recurring events for all rows.
    payload = {"events":[...], "timezone":"America/Los_Angeles"}
    """
    cal = Calendar()
    cal.add("prodid", "-//Schedule OCR//")
    cal.add("version", "2.0")

    tzname = payload.get("timezone", "America/Los_Angeles")
    tz = pytz.timezone(tzname)

    for e in payload.get("events", []):
        start_date = e.get("start_date")
        end_date = e.get("end_date")
        start_time = e.get("start_time")
        end_time = e.get("end_time")
        days = e.get("days") or []

        # Skip incomplete rows
        if not (start_date and end_date and start_time and end_time and days):
            continue

        y, m, d = [int(x) for x in start_date.split("-")]
        sh, sm = [int(x) for x in start_time.split(":")]
        eh, em = [int(x) for x in end_time.split(":")]

        dt_start = tz.localize(datetime(y, m, d, sh, sm))
        dt_end = tz.localize(datetime(y, m, d, eh, em))

        # UNTIL must be UTC datetime
        uy, um, ud = [int(x) for x in end_date.split("-")]
        until_utc = tz.localize(datetime(uy, um, ud, 23, 59, 59)).astimezone(pytz.utc)

        ev = Event()
        ev.add("summary", e.get("title", "Class"))
        if e.get("location"):
            ev.add("location", e["location"])
        if e.get("notes"):
            ev.add("description", e["notes"])

        ev.add("dtstart", dt_start)
        ev.add("dtend", dt_end)
        # rrule: weekly on specified days, until end date
        ev.add("rrule", {
            "FREQ": "WEEKLY",
            "BYDAY": days,       # list like ["MO","WE"]
            "UNTIL": until_utc
        })

        cal.add_component(ev)

    return cal.to_ical()
