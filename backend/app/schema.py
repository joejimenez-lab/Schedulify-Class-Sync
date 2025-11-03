from typing import List, Optional
from pydantic import BaseModel, field_validator

class ScheduleEvent(BaseModel):
    title: str
    days: List[str]                 # e.g., ["MO","WE","FR"]
    start_time: str                 # "HH:MM" 24h
    end_time: str                   # "HH:MM" 24h
    start_date: Optional[str] = None  # "YYYY-MM-DD"
    end_date: Optional[str] = None
    location: Optional[str] = None
    instructor: Optional[str] = None
    notes: Optional[str] = None
    termLabel: Optional[str] = None

    @field_validator("days")
    @classmethod
    def valid_days(cls, v):
        valid = {"MO","TU","WE","TH","FR","SA","SU"}
        if not v:
            raise ValueError("days empty")
        for d in v:
            if d not in valid:
                raise ValueError(f"invalid day: {d}")
        return v

class ExtractResponse(BaseModel):
    events: List[ScheduleEvent]
    timezone: str = "America/Los_Angeles"
