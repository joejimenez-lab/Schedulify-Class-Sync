# Schedulify-Class-Sync
# Schedule OCR → Calendar (Local‑first)

Turn class schedule screenshots (e.g., Cal State LA portal) into clean calendar events. Users upload an image, review extracted classes, download a single `.ics`, or one‑click import to Google Calendar.

**Local‑first & low‑cost:** Uses free OCR (Tesseract) and an optional **local LLM via Ollama** for robust parsing. No cloud required.

---

## ✨ Features (MVP)

* Upload **PNG/JPG/PDF** schedule screenshots
* **OCR → structured classes** (multi‑class, lecture/lab supported)
* Per‑row **days, times, start/end dates** (term range autodetect when present)
* **Review & edit** in a simple table (highlight missing fields)
* **Export `.ics`** with recurring events (BYDAY, UNTIL)
* **Optional:** Add to **Google Calendar** via OAuth (can be toggled off)
* **Local** LLM normalization with **Ollama** (e.g., `llama3.1`, `mistral`) for messy layouts

---

## 🏗️ Architecture

```
frontend (Next.js/React/Tailwind)
   └── Upload → Show table → Download .ics → (Optional) Google import
backend (FastAPI, Python)
   ├── ocr: Tesseract (pytesseract) + OpenCV preprocessing
   ├── parse: heuristics + (optional) LLM normalize via Ollama
   ├── calendar: icalendar to build .ics
   └── google: OAuth + Calendar API (optional route)
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
│     ├─ ocr.py               # OpenCV + Tesseract OCR
│     ├─ parser.py            # regex/layout heuristics
│     ├─ llm_ollama.py        # local LLM normalization
│     ├─ schema.py            # Pydantic models
│     ├─ ics.py               # ICS generator
│     └─ google.py            # (optional) OAuth + event creation
├─ frontend/
│  ├─ package.json
│  ├─ next.config.js
│  ├─ app/
│  │  ├─ page.tsx            # upload + table + actions
│  │  └─ api/
│  │     └─ google/          # (optional) OAuth handlers
│  └─ styles/
│     └─ globals.css
├─ docs/
│  └─ samples/               # sample screenshots for testing
└─ scripts/
   └─ dev.sh                 # convenience dev runner
```

Create the folders/files above first; contents below.

---

## 🔧 Prerequisites

* **Python 3.11+**
* **Node 18+ / PNPM or NPM**
* **Tesseract OCR**

  * macOS: `brew install tesseract`
  * Ubuntu: `sudo apt-get install tesseract-ocr`
* **Ollama** (optional for AI normalization): [https://ollama.com](https://ollama.com)

  * Example models: `ollama pull llama3.1` or `ollama pull mistral`

> If skipping Google import, you don’t need any Google Cloud setup.

---

## 🧪 Quick start (dev)

```bash
# 1) Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e .            # from pyproject.toml
# Run
uvicorn app.main:app --reload --port 8000

# 2) Frontend
cd ../frontend
pnpm install  # or npm install
pnpm dev      # runs at http://localhost:3000
```

Open [http://localhost:3000](http://localhost:3000) and try a sample image from `docs/samples/`.

---

## 🔑 Environment variables

Create `.env` files from the example:

**Root `.env.example`**

```
# Frontend → Backend
NEXT_PUBLIC_API_BASE=http://localhost:8000
DEFAULT_TIMEZONE=America/Los_Angeles

# Optional Google integration (Frontend API routes)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
NEXT_PUBLIC_BASE_URL=http://localhost:3000

# Ollama (local LLM)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

Copy as needed to `frontend/.env.local` and backend uses `python-dotenv` (already handled in code skeleton).

---

## 🔒 Privacy & cost

* Processing is local; images aren’t stored by default. No per‑request cloud fees.
* LLM costs are **$0** with Ollama. (CPU works; GPU speeds up inference.)

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
