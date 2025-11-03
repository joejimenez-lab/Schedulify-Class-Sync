import os
import json
import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

SCHEMA_HINT = """
Return JSON object: {"events":[{ "title": str,
"days": ["MO","TU","WE","TH","FR","SA","SU"],
"start_time":"HH:MM","end_time":"HH:MM",
"start_date": "YYYY-MM-DD|null", "end_date":"YYYY-MM-DD|null",
"location": "str|null", "instructor":"str|null", "notes":"str|null", "termLabel":"str|null"}], "timezone": "America/Los_Angeles"}
- Use only MO,TU,WE,TH,FR,SA,SU for days.
- Times must be 24h HH:MM.
- If a course has lecture and lab, output separate event entries.
- Do not invent data not present in the text.
"""

PROMPT_TEMPLATE = """You are converting OCR text of a university class schedule into a strict JSON object for calendar import.

Rules:
- Use ONLY the keys and structure described below.
- Times must be 24h (HH:MM). If AM/PM is missing and not inferrable, skip that event.
- Day codes must be MO,TU,WE,TH,FR,SA,SU.
- If a date range for the term is present, copy it into start_date and end_date for each event; else set them to null.
- Keep titles concise if possible (course code + name), but never hallucinate.

{schema_hint}

OCR TEXT:
{ocr_text}

Reply with JSON only (no markdown, no commentary).
"""

def _extract_json_block(s: str) -> str:
    """Find the first top-level JSON object in a string."""
    start = s.find('{')
    end = s.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return "{}"
    return s[start:end+1]

def normalize_with_ollama(ocr_text: str, timezone: str = "America/Los_Angeles") -> dict:
    prompt = PROMPT_TEMPLATE.format(schema_hint=SCHEMA_HINT, ocr_text=ocr_text)
    body = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    r = requests.post(f"{OLLAMA_HOST}/api/generate", json=body, timeout=120)
    r.raise_for_status()
    raw = r.json().get("response", "{}")
    try:
        parsed = json.loads(_extract_json_block(raw))
    except Exception:
        parsed = {"events": []}
    if "events" not in parsed or not isinstance(parsed["events"], list):
        parsed = {"events": []}
    if "timezone" not in parsed:
        parsed["timezone"] = timezone
    return parsed
