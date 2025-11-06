from __future__ import annotations
from datetime import date, timedelta
from typing import List, Tuple
import os
import pytz

from .schema import ClassBlock

DEFAULT_WEEKS = 5

def infer_range(start: date | None, end: date | None, tz_name: str | None) -> tuple[date, date, str]:
    tz = tz_name or os.environ.get("DEFAULT_TIMEZONE") or "UTC"
    if start and end:
        return start, end, tz
    if start and not end:
        return start, start + timedelta(weeks=DEFAULT_WEEKS, days=-1), tz
    if not start and end:
        # back-fill 5 weeks
        return end - timedelta(weeks=DEFAULT_WEEKS) + timedelta(days=1), end, tz
    # neither given: 5 weeks from "today" in tz
    from datetime import datetime
    today = datetime.now(pytz.timezone(tz)).date()
    return today, today + timedelta(weeks=DEFAULT_WEEKS, days=-1), tz
