from __future__ import annotations
from datetime import datetime, timedelta, date
from typing import List, Optional
import pytz
from icalendar import Calendar, Event
from dateutil.rrule import rrule, WEEKLY

from .schema import EventRow, DAY_CODE_TO_INDEX

def _first_occurrence_on_or_after(start_date: date, weekday: int) -> date:
    """Return the date of the first given weekday on/after start_date."""
    delta = (weekday - start_date.weekday()) % 7
    return start_date + timedelta(days=delta)

def _parse_hhmm(s: str) -> tuple[int, int]:
    h, m = s.split(":")
    return int(h), int(m)

def build_ics(
    events: List[EventRow],
    tz_name: str,
    start_date: date,
    end_date: date,
    calendar_name: str = "Class Schedule",
) -> bytes:
    tz = pytz.timezone(tz_name)
    cal = Calendar()
    cal.add("prodid", "-//Schedulify Class Sync//")
    cal.add("version", "2.0")
    cal.add("X-WR-CALNAME", calendar_name)
    cal.add("X-WR-TIMEZONE", tz_name)

    for row in events:
        if not row.days:
            continue

        event_start: Optional[date] = row.start_date or start_date
        event_end: Optional[date] = row.end_date or end_date

        if event_start is None or event_end is None:
            raise ValueError(f"Missing date range for {row.title}")
        if event_start > event_end:
            raise ValueError(f"start_date after end_date for {row.title}")

        sh, sm = _parse_hhmm(row.start_time)
        eh, em = _parse_hhmm(row.end_time)

        for code in row.days:
            weekday = DAY_CODE_TO_INDEX.get(code)
            if weekday is None:
                continue

            first = _first_occurrence_on_or_after(event_start, weekday)
            if first > event_end:
                continue

            dtstart = tz.localize(datetime(first.year, first.month, first.day, sh, sm))
            dtend = tz.localize(datetime(first.year, first.month, first.day, eh, em))

            ev = Event()
            ev.add("summary", row.title or "Class")
            if row.location:
                ev.add("location", row.location)
            desc = []
            if row.instructor:
                desc.append(f"Instructor: {row.instructor}")
            if row.notes:
                desc.append(row.notes)
            if row.termLabel:
                desc.append(f"Term: {row.termLabel}")
            if desc:
                ev.add("description", "\n".join(desc))
            ev.add("dtstart", dtstart)
            ev.add("dtend", dtend)
            until_dt = tz.localize(
                datetime(event_end.year, event_end.month, event_end.day, 23, 59, 59)
            ).astimezone(pytz.utc)
            ev.add("rrule", {"freq": "weekly", "until": until_dt})
            cal.add_component(ev)

    return cal.to_ical()
