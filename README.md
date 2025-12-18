# Schedulify-Class-Sync
# Schedule OCR → Calendar

Turn class schedule screenshots into clean calendar events. Upload a PNG/JPG/PDF, let **Gemini Vision** extract the rows, tweak anything in the table, then download a single `.ics` file you can import into Google/Apple/Outlook.

---

## ✨ What it does

* Upload **PNG/JPG/PDF** schedule screenshots
* **Gemini Vision → structured classes** (multi‑class, lecture/lab supported)
* Per‑row **days, times, start/end dates** (will infer a range if it sees one)
* **Review & edit** in a simple table before exporting
* **Export `.ics`** with weekly recurrence (BYDAY, UNTIL)

---

## 🏗️ Architecture

```
frontend (Next.js/React)
   └── Upload → Show table → Download .ics
backend (FastAPI, Python)
   ├── llm_gemini.py     # Gemini Vision extraction + JSON parsing
   ├── parser.py         # normalize days/times
   ├── ics.py            # ICS generator
   └── ocr.py            # optional Tesseract hint (if installed)
```

**Data contract:**

```json
{
  "events": [
    {
      "title": "CIS 2840 - Data Structures",
      "days": ["MO","WE"],
      "start_time": "13:00",
      "end_time": "14:30",
      "start_date": "2025-01-21",
      "end_date": "2025-05-16",
      "location": "Salazar Hall 232",
      "instructor": "M. Alvarez",
      "notes": "Section 01",
      "termLabel": "Spring 2025"
    }
  ],
  "timezone": "America/Los_Angeles"
}
```

---

## 📁 Folder structure (start here)

```
schedule-ocr/
├─ README.md
├─ .env.example
├─ backend/
│  ├─ pyproject.toml
│  ├─ uvicorn.ini
│  └─ app/
│     ├─ main.py              # FastAPI app + routes
│     ├─ ocr.py               # optional Tesseract OCR hint
│     ├─ parser.py            # day/time normalization
│     ├─ llm_gemini.py        # Gemini Vision extraction
│     ├─ schema.py            # Pydantic models
│     └─ ics.py               # ICS generator
├─ frontend/
│  ├─ package.json
│  ├─ next.config.js
│  ├─ app/
│  │  └─ page.tsx            # upload + table + actions
│  └─ styles/
│     └─ globals.css
└─ docs/
   └─ samples/               # sample screenshots for testing
```

## 🔧 Prerequisites

* **Python 3.10+**
* **Node 18+** (PNPM or npm)
* **Google Generative AI API key** (Gemini 2.0 Flash or similar, with vision)
* Optional: **Tesseract OCR** if you want to experiment with OCR hints (`brew install tesseract` or `sudo apt-get install tesseract-ocr`)

---

## 🧪 Quick start (local dev)

```bash
# Backend (FastAPI + Gemini Vision)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install -e .

# backend/.env (required)
cat > .env <<'EOF'
GEMINI_API_KEY=your_key_here        # or set GOOGLE_API_KEY
DEFAULT_TIMEZONE=America/Los_Angeles
EOF

uvicorn app.main:app --reload --port 8000   # health check: http://localhost:8000/health
# (optional) Validate your key: python -m backend.tests.test_env

# Frontend (Next.js)
cd ../frontend
pnpm install   # or npm install

# frontend/.env.local
cat > .env.local <<'EOF'
NEXT_PUBLIC_API_BASE=http://localhost:8000
DEFAULT_TIMEZONE=America/Los_Angeles
EOF

pnpm dev       # or npm run dev, opens http://localhost:3000
```

Grab a sample from `docs/samples/` and drop it in. Edit any rows, set the term start/end, and download `schedule.ics`.

---

## 🔑 Environment reference

Backend (`backend/.env`):

```
GEMINI_API_KEY=sk-...        # or GOOGLE_API_KEY
DEFAULT_TIMEZONE=America/Los_Angeles
```

Frontend (`frontend/.env.local`):

```
NEXT_PUBLIC_API_BASE=http://localhost:8000   # point at your FastAPI server
DEFAULT_TIMEZONE=America/Los_Angeles
```

Notes:
- The backend picks the timezone from the request, otherwise `DEFAULT_TIMEZONE`, otherwise UTC.
- The ICS builder needs both a start and end date; if Gemini doesn’t find them, enter them manually before downloading.

---

## 🛣️ Roadmap

* Table‑grid detector (column bucketing for Mon–Fri grids)
* Visual overlays of detected blocks (confidence)
* Term presets (Fall/Spring templates)
* Idempotent Google imports (skip duplicates)

---

## 📝 License

MIT (change as you prefer).

---

## 🙌 Contributing

PRs welcome! Share sample screenshots in `docs/samples/` to improve parsers.
