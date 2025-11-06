"use client";

// Frontend for Schedulify — upload image/PDF, extract schedule, download .ics

import React, { useCallback, useMemo, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8001";

interface EventItem {
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
  events: EventItem[];
  timezone?: string;
  note?: string;
}

export default function Page() {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ExtractResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [timezone, setTimezone] = useState("America/Los_Angeles");
  const [includeHeuristic, setIncludeHeuristic] = useState(true);

  const hasEvents = !!result?.events?.length;

  const onSelectFile = (f: File | null) => {
    setFile(f);
    setResult(null);
    setError(null);
  };

  const doExtract = useCallback(async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("timezone", timezone);
      fd.append("include_heuristic_hint", String(includeHeuristic));

      const res = await fetch(`${API_BASE}/extract-gemini`, {
        method: "POST",
        body: fd,
      });

      if (!res.ok) {
        const t = await res.text();
        throw new Error(`Extract failed (${res.status}): ${t}`);
      }

      const data: ExtractResponse = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err?.message || "Extraction error");
    } finally {
      setBusy(false);
    }
  }, [file, timezone, includeHeuristic]);

  const downloadICS = useCallback(async () => {
    if (!result) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/ics`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(result),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(`ICS failed (${res.status}): ${t}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "schedule.ics";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err?.message || "ICS build error");
    } finally {
      setBusy(false);
    }
  }, [result]);

  const preview = useMemo(() => {
    if (!hasEvents) return null;
    return (
      <div className="mt-6">
        <h3 className="text-lg font-semibold">Parsed Classes</h3>
        <table className="mt-3 w-full text-sm border">
          <thead>
            <tr className="border-b bg-gray-50">
              <th className="py-2 px-3 text-left">Title</th>
              <th className="py-2 px-3 text-left">Days</th>
              <th className="py-2 px-3 text-left">Time</th>
              <th className="py-2 px-3 text-left">Location</th>
            </tr>
          </thead>
          <tbody>
            {result!.events.map((ev, i) => (
              <tr key={i} className="border-b">
                <td className="py-2 px-3">{ev.title}</td>
                <td className="py-2 px-3">
                  {(ev.days || []).map((d) => (
                    <span
                      key={d}
                      className="inline-block px-2 py-0.5 mr-1 rounded-full border text-xs"
                    >
                      {d}
                    </span>
                  ))}
                </td>
                <td className="py-2 px-3">
                  {ev.start_time}–{ev.end_time}
                </td>
                <td className="py-2 px-3">{ev.location || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }, [hasEvents, result]);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto p-6">
        <h1 className="text-2xl font-bold">Schedulify</h1>
        <p className="text-sm text-gray-600">
          Upload a class schedule screenshot or PDF to extract and download a
          .ics calendar file.
        </p>

        <div className="mt-6 border-2 border-dashed rounded-xl p-6 bg-white text-center">
          <input
            id="file"
            type="file"
            accept="image/*,application/pdf"
            className="hidden"
            onChange={(e) => onSelectFile(e.target.files?.[0] || null)}
          />
          <label
            htmlFor="file"
            className="cursor-pointer px-4 py-2 rounded-lg border shadow-sm"
          >
            {file ? "Choose another file" : "Choose file"}
          </label>
          {file && (
            <p className="text-sm mt-2 text-gray-700">
              Selected: <strong>{file.name}</strong>
            </p>
          )}
        </div>

        <div className="mt-4 flex flex-wrap gap-3">
          <input
            className="border px-3 py-2 rounded-lg flex-1"
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            placeholder="Timezone"
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={includeHeuristic}
              onChange={(e) => setIncludeHeuristic(e.target.checked)}
            />
            Include heuristic hint
          </label>
          <button
            onClick={doExtract}
            disabled={!file || busy}
            className="px-4 py-2 rounded-lg border shadow-sm disabled:opacity-50"
          >
            {busy ? "Working…" : "Extract"}
          </button>
        </div>

        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 text-red-800 rounded-xl p-3 text-sm">
            {error}
          </div>
        )}

        {preview}

        {hasEvents && (
          <div className="mt-6">
            <button
              onClick={downloadICS}
              disabled={busy}
              className="px-4 py-2 rounded-lg border shadow-sm"
            >
              {busy ? "Preparing…" : "Download .ics"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
