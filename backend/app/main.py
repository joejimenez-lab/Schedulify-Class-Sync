import os
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse
from dotenv import load_dotenv

from .schema import ExtractResponse
from .ocr import ocr_to_text
from .parser import extract_blocks, detect_term
from .llm_ollama import normalize_with_ollama
from .ics import build_ics

# Load environment (.env at repo root or backend/)
load_dotenv()

API_TITLE = "Schedule OCR Backend"
API_VERSION = "0.1.0"

app = FastAPI(title=API_TITLE, version=API_VERSION)

# CORS (dev-friendly; lock down in prod)
origins = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"

@app.post("/extract-local", response_model=ExtractResponse)
async def extract_local(
    file: UploadFile = File(...),
    timezone: str = Form("America/Los_Angeles"),
    fill_term_from_page: bool = Form(True)
):
    """
    Pure local: Tesseract OCR + heuristic parser.
    - Detects multiple classes
    - Optionally auto-fills term range from page text when present
    """
    data = await file.read()
    text = ocr_to_text(data)
    events = extract_blocks(text)

    term_sd, term_ed, term_label = detect_term(text) if fill_term_from_page else (None, None, None)
    for ev in events:
        if term_sd and not ev.get("start_date"):
            ev["start_date"] = term_sd
        if term_ed and not ev.get("end_date"):
            ev["end_date"] = term_ed
        if term_label and not ev.get("termLabel"):
            ev["termLabel"] = term_label

    return JSONResponse({"events": events, "timezone": timezone})

@app.post("/extract-ai", response_model=ExtractResponse)
async def extract_ai(
    file: UploadFile = File(...),
    timezone: str = Form("America/Los_Angeles"),
    use_heuristics_first: bool = Form(True)
):
    """
    Local LLM normalization via Ollama.
    - OCR with Tesseract
    - If use_heuristics_first, we prepend heuristic extraction text to help the LLM
    """
    data = await file.read()
    ocr_text = ocr_to_text(data)
    hint = ""

    if use_heuristics_first:
        # Create a compact hint (optional)
        rough = extract_blocks(ocr_text)
        if rough:
            hint_lines = []
            for r in rough:
                hint_lines.append(
                    f"{r['title']} | days={','.join(r['days'])} | {r['start_time']}-{r['end_time']}"
                )
            hint = "HEURISTIC PREVIEW:\n" + "\n".join(hint_lines) + "\n---\n"

    parsed = normalize_with_ollama(hint + ocr_text, timezone=timezone)
    parsed["timezone"] = parsed.get("timezone", timezone)
    return JSONResponse(parsed)

@app.post("/ics")
async def make_ics(payload: ExtractResponse):
    """
    Build and return a downloadable .ics for all valid rows.
    """
    data = build_ics(payload.model_dump())
    headers = {"Content-Disposition": "attachment; filename=schedule.ics"}
    return StreamingResponse(iter([data]), media_type="text/calendar", headers=headers)

# Optional: debug endpoint to see raw OCR text for a given upload
@app.post("/debug/ocrtext", response_class=PlainTextResponse)
async def debug_ocrtext(file: UploadFile = File(...)):
    data = await file.read()
    text = ocr_to_text(data)
    return text
