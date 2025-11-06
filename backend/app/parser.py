from __future__ import annotations
from typing import List
from .schema import ClassBlock, EventRow, WEEKDAY_ALIASES
import re

COMPACT_DAY_SEQUENCES = [
    ("th", "th"),
    ("tu", "tu"),
    ("su", "su"),
    ("sa", "sa"),
    ("mo", "mo"),
]

def _expand_compact(token: str) -> List[int]:
    """Split strings like 'TuTh' or 'MWF' into weekday indices."""
    indices: List[int] = []
    s = token
    i = 0
    while i < len(s):
        matched = False
        # prioritize digraphs such as Th, Tu, Sa, Su
        for pattern, alias in COMPACT_DAY_SEQUENCES:
            if s.startswith(pattern, i):
                idx = WEEKDAY_ALIASES.get(alias)
                if idx is not None:
                    indices.append(idx)
                i += len(pattern)
                matched = True
                break
        if matched:
            continue
        ch = s[i]
        idx = WEEKDAY_ALIASES.get(ch)
        if idx is not None:
            indices.append(idx)
        i += 1
    return indices

def normalize_days(day_tokens: List[str]) -> List[int]:
    out: List[int] = []
    for token in day_tokens:
        t = token.strip().lower()
        if not t:
            continue
        if t in WEEKDAY_ALIASES:
            out.append(WEEKDAY_ALIASES[t])
            continue
        out.extend(_expand_compact(t))

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
