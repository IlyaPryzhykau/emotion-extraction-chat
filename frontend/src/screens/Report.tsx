import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError, api, type Emotion, type EmotionLabel, type Intensity } from "../api";

const INTENSITY_WIDTH: Record<Intensity, string> = { low: "33%", medium: "66%", high: "100%" };

/** Map a taxonomy label to its dot CSS class (slash -> dash for the class name). */
function dotClass(label: EmotionLabel): string {
  return `dot-${label.replace("/", "-")}`;
}

export function Report({ id }: { id: string }) {
  const navigate = useNavigate();
  const [emotions, setEmotions] = useState<Emotion[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getReport(id)
      .then(setEmotions)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load the report"));
  }, [id]);

  if (error) return <main className="page"><p className="error-text">{error}</p></main>;
  if (!emotions) return <main className="page muted">Loading…</main>;

  const sorted = [...emotions].sort((a, b) => b.confidence - a.confidence);

  return (
    <main className="page">
      <section className="frame">
        <header className="app-header">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true" />
            Reflection
          </div>
          <button className="header-link" onClick={() => navigate("/")}>Back to reflections</button>
        </header>

        <div className="summary-body">
          <div className="summary-head">
            <h2>Reflection summary</h2>
          </div>
          <p className="summary-intro">
            {sorted.length === 0
              ? "Nothing negative clearly stood out in this one — sounds like an okay day."
              : "Here's what came up in our conversation. Take what's useful, leave the rest."}
          </p>

          <div className="summary-list">
            {sorted.map((e) => (
              <article key={e.id} className={`summary-card ${e.intensity === "high" ? "high" : ""}`}>
                <div className="summary-card-head">
                  <span className="summary-emotion">
                    <span className={`emotion-dot ${dotClass(e.label)}`} aria-hidden="true" />
                    {e.label}
                  </span>
                  <span className="summary-intensity">
                    <span className="summary-bar">
                      <span
                        className={`summary-bar-fill ${e.intensity === "low" ? "low" : ""}`}
                        style={{ width: INTENSITY_WIDTH[e.intensity] }}
                      />
                    </span>
                    <span className="summary-int-num">{e.intensity}</span>
                  </span>
                </div>
                <p className="summary-trigger">{e.trigger}</p>
                <ul className="summary-quotes">
                  <li>"{e.evidence}"</li>
                </ul>
                <span className="summary-confidence">confidence {e.confidence.toFixed(2)}</span>
              </article>
            ))}
          </div>

          <div className="summary-actions">
            <button className="btn btn-secondary" onClick={() => navigate("/")}>Back to my reflections</button>
          </div>
        </div>
      </section>
    </main>
  );
}
