from __future__ import annotations

import io
import os
from datetime import date
from typing import List, Optional, Tuple

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from .schema import EventRow, ExtractResponse, ICSRequest
from .llm_gemini import extract_from_image
from .parser import from_gemini_json
from .build_calendar import infer_range
from .ics import build_ics

load_dotenv()  # load .env at startup

app = FastAPI(title="Schedulify Class Sync (Backend)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolve_timezone(tz_name: Optional[str]) -> str:
    return tz_name or os.environ.get("DEFAULT_TIMEZONE") or "UTC"


def _apply_global_dates(
    events: List[EventRow],
    start: Optional[date],
    end: Optional[date],
) -> List[EventRow]:
    updated: List[EventRow] = []
    for ev in events:
        updates = {}
        if start and ev.start_date is None:
            updates["start_date"] = start
        if end and ev.end_date is None:
            updates["end_date"] = end
        updated.append(ev if not updates else ev.model_copy(update=updates))
    return updated


def _resolve_date_range(
    events: List[EventRow],
    start: Optional[date],
    end: Optional[date],
) -> Tuple[date, date]:
    event_starts = [ev.start_date for ev in events if ev.start_date]
    event_ends = [ev.end_date for ev in events if ev.end_date]

    resolved_start = start or (min(event_starts) if event_starts else None)
    resolved_end = end or (max(event_ends) if event_ends else None)

    if resolved_start is None or resolved_end is None:
        raise HTTPException(
            status_code=400,
            detail="Provide start_date and end_date (either globally or per event).",
        )
    if resolved_start > resolved_end:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before end_date.",
        )
    return resolved_start, resolved_end


def _stream_ics(data: bytes, filename: str = "schedule.ics") -> StreamingResponse:
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(io.BytesIO(data), headers=headers, media_type="text/calendar")


@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/extract-gemini", response_model=ExtractResponse)
async def extract_gemini(
    file: UploadFile = File(..., description="Screenshot image"),
    start_date: Optional[date] = Form(None),
    end_date: Optional[date] = Form(None),
    timezone: Optional[str] = Form(None),
    include_heuristic_hint: Optional[bool] = Form(None),
):
    if not file.content_type or not file.content_type.startswith(("image/", "application/pdf")):
        raise HTTPException(status_code=400, detail="Please upload an image file (png/jpg/pdf).")

    image_bytes = await file.read()
    raw = extract_from_image(image_bytes)
    events = from_gemini_json(raw)
    tz = _resolve_timezone(timezone)

    events = _apply_global_dates(events, start_date, end_date)

    has_start = bool(start_date) or any(ev.start_date for ev in events)
    has_end = bool(end_date) or any(ev.end_date for ev in events)
    needs_dates = not (has_start and has_end)

    inferred_start = None
    inferred_end = None
    if start_date or end_date:
        inferred_start, inferred_end, _ = infer_range(start_date, end_date, tz)
    else:
        event_starts = [ev.start_date for ev in events if ev.start_date]
        event_ends = [ev.end_date for ev in events if ev.end_date]
        if event_starts:
            inferred_start = min(event_starts)
        if event_ends:
            inferred_end = max(event_ends)

    note = None
    if needs_dates:
        note = "Add the term's start and end dates before exporting to calendar."

    return ExtractResponse(
        events=events,
        timezone=tz,
        inferred_start=inferred_start,
        inferred_end=inferred_end,
        needs_dates=needs_dates,
        note=note,
    )

@app.post("/extract-to-ics")
async def extract_to_ics(
    file: UploadFile = File(...),
    start_date: Optional[date] = Form(None),
    end_date: Optional[date] = Form(None),
    timezone: Optional[str] = Form(None),
):
    # 1) extract
    image_bytes = await file.read()
    raw = extract_from_image(image_bytes)
    events = from_gemini_json(raw)
    events = _apply_global_dates(events, start_date, end_date)
    tz = _resolve_timezone(timezone)
    start, end = _resolve_date_range(events, start_date, end_date)
    # 3) build ICS
    try:
        ics_bytes = build_ics(events, tz, start, end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _stream_ics(ics_bytes)

@app.post("/ics")
@app.post("/make-ics")
async def make_ics(payload: ICSRequest):
    events = _apply_global_dates(payload.events, payload.start_date, payload.end_date)
    tz = _resolve_timezone(payload.timezone)
    start, end = _resolve_date_range(events, payload.start_date, payload.end_date)
    try:
        ics_bytes = build_ics(events, tz, start, end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _stream_ics(ics_bytes)
