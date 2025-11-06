from __future__ import annotations
from typing import List, Optional
from datetime import date
import re
from pydantic import BaseModel, Field, field_validator

WEEKDAY_ALIASES = {
    "m": 0, "mon": 0, "monday": 0,
    "t": 1, "tue": 1, "tues": 1, "tuesday": 1,
    "w": 2, "wed": 2, "wednesday": 2,
    "th": 3, "thu": 3, "thur": 3, "thurs": 3, "thursday": 3,
    "f": 4, "fri": 4, "friday": 4,
    "sa": 5, "sat": 5, "saturday": 5,
    "su": 6, "sun": 6, "sunday": 6,
}

DAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
DAY_CODE_TO_INDEX = {code: idx for idx, code in enumerate(DAY_CODES)}
INDEX_TO_DAY_CODE = {idx: code for code, idx in DAY_CODE_TO_INDEX.items()}


def normalize_time_string(value: str) -> str:
    """Normalize a fuzzy time string into HH:MM 24h format."""
    s = value.strip().lower().replace(".", ":")
    m = re.match(r"^(\d{1,2})(?::?(\d{2}))?\s*(am|pm)?$", s)
    if not m:
        raise ValueError("time must look like 9:00, 9am, 9:30pm")
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = m.group(3)
    if ampm == "pm" and hour != 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("invalid time")
    return f"{hour:02d}:{minute:02d}"


class ClassBlock(BaseModel):
    title: str = Field(..., examples=["MATH 101 - Calculus I"])
    days: List[int] = Field(..., description="0=Mon .. 6=Sun")
    start_time: str = Field(..., examples=["09:30"])
    end_time: str = Field(..., examples=["10:45"])
    location: Optional[str] = Field(default=None, examples=["Room 204", "Zoom"])
    instructor: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("start_time", "end_time")
    @classmethod
    def _hhmm(cls, v: str) -> str:
        return normalize_time_string(v)

    def to_event(self) -> "EventRow":
        return EventRow(
            title=self.title,
            days=[INDEX_TO_DAY_CODE[d] for d in self.days if d in INDEX_TO_DAY_CODE],
            start_time=self.start_time,
            end_time=self.end_time,
            location=self.location,
            instructor=self.instructor,
            notes=self.notes,
        )


class EventRow(BaseModel):
    title: str
    days: List[str]
    start_time: str
    end_time: str
    location: Optional[str] = None
    instructor: Optional[str] = None
    notes: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    termLabel: Optional[str] = Field(default=None, alias="termLabel")

    @field_validator("days", mode="before")
    @classmethod
    def _ensure_list(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return value

    @field_validator("days")
    @classmethod
    def _normalize_codes(cls, value: List[str]) -> List[str]:
        normalized: List[str] = []
        for raw in value:
            token = (raw or "").strip()
            if not token:
                continue
            upper = token.upper()
            if upper in DAY_CODE_TO_INDEX:
                normalized.append(upper)
                continue
            idx = WEEKDAY_ALIASES.get(token.lower())
            if idx is not None:
                normalized.append(INDEX_TO_DAY_CODE[idx])
        # dedupe preserving order
        seen = set()
        out: List[str] = []
        for code in normalized:
            if code not in seen:
                seen.add(code)
                out.append(code)
        return out

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def _normalize_time(cls, value: str) -> str:
        if value is None:
            raise ValueError("time is required")
        return normalize_time_string(value)


class ExtractRequest(BaseModel):
    timezone: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    include_heuristic_hint: Optional[bool] = None

class ExtractResponse(BaseModel):
    events: List[EventRow]
    timezone: str
    inferred_start: Optional[date] = None
    inferred_end: Optional[date] = None
    needs_dates: bool = False
    note: Optional[str] = None

class ICSRequest(BaseModel):
    events: List[EventRow]
    timezone: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
