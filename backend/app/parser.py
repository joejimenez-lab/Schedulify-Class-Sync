from __future__ import annotations
from typing import List
from .schema import ClassBlock, EventRow, WEEKDAY_ALIASES
import re

def normalize_days(day_tokens: List[str]) -> List[int]:
    out: List[int] = []
    for token in day_tokens:
        t = token.strip().lower()
        # split "mwf" style into chars while preserving "th"
        # quick pass for compact patterns:
        if t in WEEKDAY_ALIASES:
            out.append(WEEKDAY_ALIASES[t])
            continue

        # expand compact like "mwf" or "tuth"
        # replace "th" with "X" sentinel, then iterate letters
        tt = t.replace("th", "X")
        for ch in list(tt):
            key = {"m":"m","t":"t","w":"w","f":"f","s":"sa","X":"th","u":"su"}.get(ch)
            if not key:
                continue
            idx = WEEKDAY_ALIASES.get(key)
            if idx is not None:
                out.append(idx)

    # de-duplicate, keep order
    seen = set()
    ordered = []
    for i in out:
        if i not in seen:
            seen.add(i)
            ordered.append(i)
    return ordered

def from_gemini_json(data) -> List[EventRow]:
    """
    Accepts any of:
      - [{"title":..., "days":..., "start_time":..., ...}, ...]
      - {"classes": [...]}   (legacy)
      - {"events":  [...]}   (fallback)
      - {"items":   [...]}   (fallback)
    Normalizes days and builds EventRow list.
    """
    events: List[EventRow] = []

    # Normalize the top-level container
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        raw = data.get("classes") or data.get("events") or data.get("items") or []
        if not isinstance(raw, list):
            raise TypeError("Expected list under 'classes'/'events'/'items'.")
    else:
        raise TypeError("from_gemini_json expected a list or dict.")

    for item in raw:
        if not isinstance(item, dict):
            # skip junk rows
            continue

        # Accept "days" or a single "day"
        days_field = item.get("days")
        if days_field is None and "day" in item:
            days_field = item["day"]

        if isinstance(days_field, str):
            day_tokens = [days_field]
        elif isinstance(days_field, list):
            tokens = []
            for d in days_field:
                tokens += re.split(r"[,\s/]+", str(d))
            day_tokens = [t for t in tokens if t]
        else:
            day_tokens = []

        days = normalize_days(day_tokens)
        if not days:
            # Skip entries with no parsed days (likely noise)
            continue

        block = ClassBlock(
            title=(item.get("title") or "Class").strip(),
            days=days,
            start_time=item.get("start_time") or "09:00",
            end_time=item.get("end_time") or "10:00",
            location=(item.get("location") or None) or None,
            instructor=(item.get("instructor") or None) or None,
            notes=(item.get("notes") or None) or None,
        )

        event = block.to_event().model_copy(
            update={"termLabel": item.get("termLabel") or None}
        )
        events.append(event)

    return events
