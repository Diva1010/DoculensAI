import { useState } from "react";
import { getSummary, type Summary } from "../api";

interface Props {
  documentId: string;
}

export default function SummaryCard({ documentId }: Props) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  async function summarize() {
    setLoading(true);
    setError("");
    try {
      setSummary(await getSummary(documentId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not summarize.");
    } finally {
      setLoading(false);
    }
  }

  async function copySummary() {
    if (!summary) return;
    const points = summary.key_points.map((p) => "- " + p).join("\n");
    const text = "Overview\n" + summary.overview + "\n\nKey points\n" + points;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setError("Could not copy to the clipboard.");
    }
  }

  return (
    <section className="card" aria-labelledby="summary-title">
      <div className="card-header">
        <h2 id="summary-title">Summary</h2>
        <div className="row">
          {summary && !loading && (
            <button className="button secondary small" onClick={copySummary}>
              {copied ? "Copied" : "Copy"}
            </button>
          )}
          <button className="button small" onClick={summarize} disabled={loading}>
            {summary ? "Regenerate" : "Summarize"}
          </button>
        </div>
      </div>

      {loading && (
        <div role="status">
          <div className="skeleton" />
          <div className="skeleton" />
          <div className="skeleton short" />
          <p className="muted">Summarizing… This can take up to a minute.</p>
        </div>
      )}

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {summary && !loading && (
        <div>
          <h3>Overview</h3>
          <p>{summary.overview}</p>
          {summary.key_points.length > 0 && (
            <>
              <h3>Key points</h3>
              <ul>
                {summary.key_points.map((point, i) => (
                  <li key={i}>{point}</li>
                ))}
              </ul>
            </>
          )}
          {summary.truncated && (
            <p className="muted">This document is long, so only the first part was summarized.</p>
          )}
        </div>
      )}

      {!summary && !loading && !error && (
        <p className="muted">Get a short overview and the key points of this document.</p>
      )}
    </section>
  );
}
