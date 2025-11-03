import re
from typing import List, Dict, Tuple, Optional
import dateparser

DAY_ALIASES = {
    "mon": "MO", "m": "MO",
    "tue": "TU", "tu": "TU", "t": "TU",
    "wed": "WE", "w": "WE",
    "thu": "TH", "thur": "TH", "th": "TH",
    "fri": "FR", "f": "FR",
    "sat": "SA", "sa": "SA",
    "sun": "SU", "su": "SU"
}

TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([ap]m)?", re.I)
RANGE_RE = re.compile(r"(\d{1,2}(?::\d{2})?\s*[ap]m)\s*[-–—]\s*(\d{1,2}(?::\d{2})?\s*[ap]m)", re.I)

DATE_RANGE_RE = re.compile(
    r'(?P<start>(?:\d{1,2}/\d{1,2}/\d{2,4})|(?:[A-Za-z]{3,9}\s+\d{1,2},\s*\d{4}))\s*(?:-|to|through|–|—)\s*'
    r'(?P<end>(?:\d{1,2}/\d{1,2}/\d{2,4})|(?:[A-Za-z]{3,9}\s+\d{1,2},\s*\d{4}))',
    re.I
)
TERM_LABEL_RE = re.compile(r'(spring|summer|fall|autumn|winter)\s+\d{4}', re.I)

def _parse_time_token(s: str) -> Optional[str]:
    m = TIME_RE.search(s)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2) or "0")
    ampm = (m.group(3) or "").lower()
    if ampm:
        if ampm == "pm" and hh != 12:
            hh += 12
        if ampm == "am" and hh == 12:
            hh = 0
    return f"{hh:02d}:{mm:02d}"

def detect_days(text: str) -> List[str]:
    tokens = re.split(r"[^A-Za-z/]+", text.lower())
    days = set()
    for tok in tokens:
        parts = re.split(r"[\/&,-]", tok)
        for p in parts:
            if p in DAY_ALIASES:
                days.add(DAY_ALIASES[p])
            elif p in ["mw", "tuth", "mwf", "wf"]:
                if p == "mw": days.update(["MO", "WE"])
                if p == "tuth": days.update(["TU", "TH"])
                if p == "mwf": days.update(["MO", "WE", "FR"])
                if p == "wf": days.update(["WE", "FR"])
    return sorted(days)

def detect_term(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    label = None
    mlabel = TERM_LABEL_RE.search(text)
    if mlabel:
        label = mlabel.group(0).title()
    m = DATE_RANGE_RE.search(text)
    if m:
        sd = dateparser.parse(m.group("start"))
        ed = dateparser.parse(m.group("end"))
        return (
            sd.strftime("%Y-%m-%d") if sd else None,
            ed.strftime("%Y-%m-%d") if ed else None,
            label
        )
    return None, None, label

def extract_blocks(ocr_text: str) -> List[Dict]:
    """
    Heuristic multi-class extractor:
    - Walk lines and buffer until we see (days + time range)
    - Each match → an event row
    """
    lines = [ln.strip() for ln in ocr_text.splitlines() if ln.strip()]
    events: List[Dict] = []
    buf: List[str] = []

    for ln in lines:
        buf.append(ln)
        joined = " ".join(buf)
        days = detect_days(joined)
        r = RANGE_RE.search(joined)
        if days and r:
            start = _parse_time_token(r.group(1))
            end = _parse_time_token(r.group(2))
            if start and end:
                events.append({
                    "title": joined,           # user can clean this in UI
                    "days": days,
                    "start_time": start,
                    "end_time": end,
                    "start_date": None,
                    "end_date": None,
                    "location": None,
                    "instructor": None,
                    "notes": None,
                    "termLabel": None
                })
                buf = []  # reset for next block

    return events
