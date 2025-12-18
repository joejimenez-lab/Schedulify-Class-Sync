"use client";

import React, { useMemo, useState } from "react";

// If NEXT_PUBLIC_API_BASE is set (e.g., http://127.0.0.1:8001 for local dev),
// we will call that directly (no /api prefix).
// If it's empty (production on Fly), we will call same-origin with a /api prefix.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

const api = (path: string) => {
  // if API_BASE exists -> use it directly (local two-terminal dev)
  // else -> same-origin with /api prefix (Fly single URL)
  return API_BASE ? `${API_BASE}${path}` : `/api${path}`;
};


const DAY_TOKEN_MAP: Record<string, string> = {
  m: "MO",
  mon: "MO",
  monday: "MO",
  t: "TU",
  tu: "TU",
  tue: "TU",
  tues: "TU",
  tuesday: "TU",
  w: "WE",
  wed: "WE",
  wednesday: "WE",
  th: "TH",
  thu: "TH",
  thur: "TH",
  thurs: "TH",
  thursday: "TH",
  f: "FR",
  fri: "FR",
  friday: "FR",
  sa: "SA",
  sat: "SA",
  saturday: "SA",
  su: "SU",
  sun: "SU",
  sunday: "SU",
};

interface EventDraft {
  title: string;
  days: string[];
  start_time: string;
  end_time: string;
  location?: string | null;
  instructor?: string | null;
  notes?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  termLabel?: string | null;
}

interface ExtractResponse {
  events: EventDraft[];
  timezone: string;
  inferred_start?: string | null;
  inferred_end?: string | null;
  needs_dates?: boolean;
  note?: string | null;
}

const toEventDraft = (rows: EventDraft[] = []): EventDraft[] =>
  rows.map((row) => ({
    ...row,
    days: Array.isArray(row.days) ? row.days : [],
    location: row.location ?? "",
    instructor: row.instructor ?? "",
    notes: row.notes ?? "",
    start_date: row.start_date ?? "",
    end_date: row.end_date ?? "",
  }));

const normalizeDaysInput = (value: string): string[] => {
  const tokens = value.split(/[^A-Za-z]+/).filter(Boolean);
  const normalized: string[] = [];
  tokens.forEach((token) => {
    const key = token.trim().toLowerCase();
    if (!key) return;
    const mapped = DAY_TOKEN_MAP[key] || key.slice(0, 2).toUpperCase();
    if (!normalized.includes(mapped)) {
      normalized.push(mapped);
    }
  });
  return normalized;
};

const makeDownload = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
};

export default function HomePage() {
  const initialTimezone = useMemo(() => {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch (err) {
      return "America/Los_Angeles";
    }
  }, []);

  const [file, setFile] = useState<File | null>(null);
  const [events, setEvents] = useState<EventDraft[]>([]);
  const [timezone, setTimezone] = useState(initialTimezone || "America/Los_Angeles");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [includeHint, setIncludeHint] = useState(true);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [needsDates, setNeedsDates] = useState(false);
  const [inferredRange, setInferredRange] = useState<{ start?: string | null; end?: string | null }>(
    {}
  );

  const hasEvents = events.length > 0;
  const canDownload = hasEvents && Boolean(startDate.trim() && endDate.trim()) && !busy;
  const startMissing = needsDates && !startDate.trim();
  const endMissing = needsDates && !endDate.trim();

  const onFileChange = (f: File | null) => {
    setFile(f);
    setEvents([]);
    setStatus(null);
    setError(null);
    setNote(null);
    setNeedsDates(false);
    setInferredRange({});
  };

  const updateEvent = (index: number, patch: Partial<EventDraft>) => {
    setEvents((prev) =>
      prev.map((evt, idx) => (idx === index ? { ...evt, ...patch } : evt))
    );
  };

  const removeEvent = (index: number) => {
    setEvents((prev) => prev.filter((_, idx) => idx !== index));
  };

  const addEmptyEvent = () => {
    setEvents((prev) => [
      ...prev,
      {
        title: "New Class",
        days: ["MO"],
        start_time: "09:00",
        end_time: "10:00",
        location: "",
        instructor: "",
        notes: "",
      },
    ]);
  };

  const handleExtract = async () => {
    if (!file) {
      setError("Choose a screenshot or PDF first.");
      return;
    }
    setBusy(true);
    setError(null);
    setStatus("Contacting Gemini…");
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("timezone", timezone);
      if (startDate.trim()) {
        fd.append("start_date", startDate.trim());
      }
      if (endDate.trim()) {
        fd.append("end_date", endDate.trim());
      }
      fd.append("include_heuristic_hint", String(includeHint));

      const response = await fetch(api("/extract-gemini"), {
        method: "POST",
        body: fd,
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Extraction failed (${response.status}).`);
      }

      const data: ExtractResponse = await response.json();
      setEvents(toEventDraft(data.events || []));
      setNote(data.note ?? null);
      setNeedsDates(Boolean(data.needs_dates));
      setInferredRange({ start: data.inferred_start, end: data.inferred_end });
      if (!startDate.trim() && data.inferred_start) {
        setStartDate(data.inferred_start);
      }
      if (!endDate.trim() && data.inferred_end) {
        setEndDate(data.inferred_end);
      }
      if (data.timezone) {
        setTimezone(data.timezone);
      }
      setStatus(`Found ${data.events?.length || 0} classes.`);
    } catch (err: any) {
      setError(err?.message || "Extraction error");
      setStatus(null);
    } finally {
      setBusy(false);
    }
  };

  const preparedEvents = useMemo(
    () =>
      events.map((evt) => ({
        ...evt,
        days: evt.days.filter(Boolean),
        location: evt.location?.trim() || undefined,
        instructor: evt.instructor?.trim() || undefined,
        notes: evt.notes?.trim() || undefined,
        start_date: evt.start_date?.trim() || undefined,
        end_date: evt.end_date?.trim() || undefined,
      })),
    [events]
  );

  const handleDownload = async () => {
    if (!canDownload) return;
    setBusy(true);
    setError(null);
    setStatus("Building calendar…");
    try {
      const payload = {
        timezone,
        start_date: startDate.trim(),
        end_date: endDate.trim(),
        events: preparedEvents,
      };
      const response = await fetch(api("/ics"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Calendar build failed (${response.status}).`);
      }
      const blob = await response.blob();
      makeDownload(blob, "schedule.ics");
      setStatus("Downloaded schedule.ics");
    } catch (err: any) {
      setError(err?.message || "Unable to build calendar");
      setStatus(null);
    } finally {
      setBusy(false);
    }
  };

  const inferredText = useMemo(() => {
    if (!inferredRange.start && !inferredRange.end) {
      return "";
    }
    if (inferredRange.start && inferredRange.end) {
      return `Gemini spotted ${inferredRange.start} → ${inferredRange.end}`;
    }
    if (inferredRange.start) {
      return `Gemini spotted a start date: ${inferredRange.start}`;
    }
    return `Gemini spotted an end date: ${inferredRange.end}`;
  }, [inferredRange]);

  return (
    <div className="page-container">
      <header className="hero">
        <div>
          <p className="eyebrow">Schedulify Class Sync</p>
          <h1>Turn any schedule screenshot into a polished calendar.</h1>
          <p className="lead">
            Upload a PNG/JPG/PDF, we OCR + Gemini it, you fine-tune any rows,
            then download a clean .ics for Apple, Google, or Outlook.
          </p>
        </div>
      </header>

      {needsDates && (
        <div className="callout warning emphasis">
          Gemini didn’t capture the overall term dates. Enter the start and end of the term below so we can build the calendar.
        </div>
      )}

      <section className="grid">
        <div className="card">
          <div className="card-header">
            <div>
              <h2>1. Upload your schedule</h2>
              <p>Supports screenshots, photos, and portal exports (PDF).</p>
            </div>
            {file && <span className="pill">{file.name}</span>}
          </div>
          <div className="dropzone">
            <input
              id="file"
              type="file"
              accept="image/*,application/pdf"
              onChange={(e) => onFileChange(e.target.files?.[0] || null)}
            />
            <label htmlFor="file" className="dropzone-label">
              {file ? "Choose a different file" : "Click to choose or drop a file"}
            </label>
            <p className="dropzone-hint">PNG, JPG, HEIC, or PDF · up to 10 MB</p>
          </div>
          <div className="actions">
            <label className="checkbox">
              <input
                type="checkbox"
                checked={includeHint}
                onChange={(e) => setIncludeHint(e.target.checked)}
              />
              Send an OCR text hint to Gemini (helps with blurry images)
            </label>
            <button className="btn btn-primary" onClick={handleExtract} disabled={!file || busy}>
              {busy ? "Working…" : "Extract schedule"}
            </button>
          </div>
          {status && <p className="status">{status}</p>}
          {error && <p className="error">{error}</p>}
        </div>

        <aside className="card">
          <h2>2. Term + timezone</h2>
          <p className="helper">
            Your calendar needs the actual term dates. Use the inferred range if
            it looks right, or enter the start/end you prefer.
          </p>
          <label className="field">
            <span>Timezone</span>
            <input value={timezone} onChange={(e) => setTimezone(e.target.value)} />
          </label>
          <label className={`field ${startMissing ? "field-missing" : ""}`}>
            <span>Start date</span>
            <input
              type="date"
              value={startDate.trim()}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </label>
          <label className={`field ${endMissing ? "field-missing" : ""}`}>
            <span>End date</span>
            <input
              type="date"
              value={endDate.trim()}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </label>
          {inferredText && <div className="callout">{inferredText}</div>}
          {needsDates && (
            <div className="callout warning">
              Add both a start and end date before downloading the .ics file.
            </div>
          )}
          {note && <div className="callout neutral">{note}</div>}
        </aside>
      </section>

      {hasEvents && (
        <section className="card">
          <div className="card-header">
            <div>
              <h2>3. Review & tweak classes</h2>
              <p>Edit any field (title, days, time, location, notes).</p>
            </div>
            <button className="btn btn-ghost" onClick={addEmptyEvent}>+ Add class</button>
          </div>
          <div className="event-list">
            {events.map((evt, index) => (
              <div key={`evt-${index}`} className="event-row">
                <div className="event-row__header">
                  <strong>Class {index + 1}</strong>
                  <button className="link" onClick={() => removeEvent(index)}>
                    Remove
                  </button>
                </div>
                <div className="event-grid">
                  <label className="field">
                    <span>Title</span>
                    <input
                      value={evt.title}
                      onChange={(e) => updateEvent(index, { title: e.target.value })}
                    />
                  </label>
                  <label className="field">
                    <span>Days (MO,TU,WE…)</span>
                    <input
                      value={evt.days.join(", ")}
                      onChange={(e) => updateEvent(index, { days: normalizeDaysInput(e.target.value) })}
                      placeholder="MO,WE or Mon/Wed"
                    />
                  </label>
                  <label className="field">
                    <span>Start time</span>
                    <input
                      value={evt.start_time}
                      onChange={(e) => updateEvent(index, { start_time: e.target.value })}
                    />
                  </label>
                  <label className="field">
                    <span>End time</span>
                    <input
                      value={evt.end_time}
                      onChange={(e) => updateEvent(index, { end_time: e.target.value })}
                    />
                  </label>
                  <label className="field">
                    <span>Location</span>
                    <input
                      value={evt.location || ""}
                      onChange={(e) => updateEvent(index, { location: e.target.value })}
                      placeholder="Room / Zoom"
                    />
                  </label>
                  <label className="field">
                    <span>Instructor</span>
                    <input
                      value={evt.instructor || ""}
                      onChange={(e) => updateEvent(index, { instructor: e.target.value })}
                    />
                  </label>
                  <label className="field field-full">
                    <span>Notes</span>
                    <textarea
                      value={evt.notes || ""}
                      rows={2}
                      onChange={(e) => updateEvent(index, { notes: e.target.value })}
                      placeholder="Section, lab, reminders"
                    />
                  </label>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="card footer-card">
        <div>
          <h2>4. Download & import</h2>
          <p>
            When everything looks good, download a single .ics file and import it
            into Apple Calendar, Google Calendar, or Outlook.
          </p>
        </div>
        <div className="footer-actions">
          <button className="btn btn-secondary" onClick={handleDownload} disabled={!canDownload}>
            {busy ? "Preparing…" : "Download schedule.ics"}
          </button>
          {!hasEvents && <p className="helper">Run extraction first to enable download.</p>}
        </div>
      </section>
    </div>
  );
}
