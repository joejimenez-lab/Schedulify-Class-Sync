from __future__ import annotations
import io, os, json, re
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv, find_dotenv

DEFAULT_GEMINI_MODEL = "models/gemini-2.0-flash"  # fast + vision

# ---- Prompt tuned to your parser expectations ----
# Your parser builds EventRow via ClassBlock and accepts:
#   title: str
#   days: can be a compact string like "MWF", full names "Mon/Wed/Fri",
#         or an array of tokens; parser will normalize
#   start_time/end_time: "HH:MM" or "H:MM" with AM/PM is OK; parser normalizes
#   location/instructor/notes/termLabel: optional
PROMPT = """
You are an expert at extracting university class schedules from screenshots.

Return ONLY a JSON array (no extra text). Each item is:
{
  "title": "Course title or code",
  "days": "e.g., MWF or Mon/Wed/Fri or Tu/Th",
  "start_time": "e.g., 12:00PM",
  "end_time": "e.g., 2:45PM",
  "location": "optional room/building",
  "instructor": "optional",
  "notes": "optional",
  "termLabel": "optional short label for the term"
}

Rules:
- If multiple meeting days exist, keep them in a compact or slash form (e.g., "MWF" or "Mon/Wed/Fri"); do NOT expand them to dates.
- Times MUST include AM/PM if the source uses them.
- If a field is missing, omit it rather than inventing values.
- Respond with ONLY valid JSON. Do not wrap in backticks or add prose.
"""

def _load_env_and_configure():
    # Load .env from working dir, else try parent
    env = find_dotenv(usecwd=True) or os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env):
        load_dotenv(env)
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY / GOOGLE_API_KEY not set. Add it to backend/.env")
    genai.configure(api_key=api_key)


def _model_name() -> str:
    # Allow override via env (GEMINI_MODEL) while keeping a sensible default.
    return os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL

def _image_part(image_bytes: bytes) -> Dict[str, Any]:
    # Pillow verifies bytes are a real image (and helps early error messages)
    _ = Image.open(io.BytesIO(image_bytes))
    return {"mime_type": "image/png", "data": image_bytes}

_JSON_FENCE_RE = re.compile(r"```json\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```", re.IGNORECASE)
_JSON_OBJECT_OR_ARRAY_RE = re.compile(r"(\{[\s\S]*\}|\[[\s\S]*\])")

def _try_load_json(text: str) -> Any:
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty model response")
    # 1) ```json ... ``` fences
    m = _JSON_FENCE_RE.search(text)
    if m:
        return json.loads(m.group(1))
    # 2) First JSON object/array substring
    m = _JSON_OBJECT_OR_ARRAY_RE.search(text)
    if m:
        return json.loads(m.group(1))
    # 3) Raw attempt
    return json.loads(text)

_BULLET_LINE_RE = re.compile(
    r"""
    ^\s*[-*]\s*                # bullet
    (?P<title>[^:]+?)\s*:\s*   # title up to colon
    (?P<day>\b(?:Mon|Tue|Tues|Wed|Thu|Thur|Thurs|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b)\s+
    (?P<start>[\d:]+(?:\s?[AP]M)?)\s*-\s*(?P<end>[\d:]+(?:\s?[AP]M)?)\s*,\s*
    (?P<loc>.+?)\s*$           # location to end
    """,
    re.IGNORECASE | re.VERBOSE
)

def _fallback_parse_bullets(text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Parse bullets like:
      * CS 4661-01 LEC (92211): Friday 12:00PM - 2:45PM, ASCB 132
    Returns a list of dicts matching the schema expected by from_gemini_json().
    """
    items: List[Dict[str, Any]] = []
    hit = False
    for line in text.splitlines():
        m = _BULLET_LINE_RE.match(line)
        if not m:
            continue
        hit = True
        title = m.group("title").strip()
        day = m.group("day").strip()
        start = m.group("start").strip().upper()
        end = m.group("end").strip().upper()
        loc = m.group("loc").strip()

        # Normalize day to something your parser will understand.
        # Single day is fine ("Friday"); the parser normalizes names/aliases.
        items.append({
            "title": title,
            "days": day,                 # parser.normalize_days will handle it
            "start_time": start,         # parser will normalize AM/PM → 24h as needed
            "end_time": end,
            "location": loc
        })
    return items if hit else None

def extract_from_image(image_bytes: bytes, ocr_hint: Optional[str] = None) -> List[dict]:
    """
    Returns a Python list of dicts (events), NOT Pydantic models.
    """
    _load_env_and_configure()

    model = genai.GenerativeModel(
        _model_name(),
        generation_config={
            # This strongly biases the model to return JSON (and only JSON)
            "temperature": 0,
            "response_mime_type": "application/json",
        },
    )

    parts: List[Any] = [PROMPT, _image_part(image_bytes)]
    if ocr_hint:
        parts.append(f"OCR transcription (may be noisy):\n{ocr_hint}")

    response = model.generate_content(parts)
    text = (getattr(response, "text", "") or "").strip()

    # 1) Try clean JSON paths
    try:
        data = _try_load_json(text)
        if isinstance(data, dict):
            # Some models return {"events":[...]} — accept both
            data = data.get("events", [])
        if not isinstance(data, list):
            raise ValueError("Top-level JSON must be an array of event objects.")
        return data
    except Exception:
        # 2) Fallback: try to parse bullet-style summaries like the one you posted
        bullets = _fallback_parse_bullets(text)
        if bullets:
            return bullets
        # 3) Give a helpful error with the original text for debugging
        raise RuntimeError("Could not parse JSON from model response:\n" + text)
