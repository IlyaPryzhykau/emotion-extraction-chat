import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError, api, type ConversationListItem, type EmotionLabel } from "../api";
import { useAuth } from "../auth";

function dotClass(label: EmotionLabel): string {
  return `dot-${label.replace("/", "-")}`;
}

function formatDate(iso: string): string {
  // Fixed en-US locale — the app is English-only, so don't follow the OS locale.
  return new Date(iso).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
}

export function Sessions() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState<ConversationListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    api
      .listConversations()
      .then(setItems)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load your reflections"));
  }, []);

  const startNew = async () => {
    setStarting(true);
    setError(null);
    try {
      const conversation = await api.createConversation();
      navigate(`/c/${conversation.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not start a new conversation");
      setStarting(false);
    }
  };

  return (
    <main className="page">
      <section className="frame">
        <header className="app-header">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true" />
            Reflection
          </div>
          <button className="header-link" onClick={() => logout()}>Sign out</button>
        </header>

        <div className="sessions-body">
          <div className="sessions-top">
            <div className="sessions-heading">
              <h2>Your reflections</h2>
              <p className="muted">{user?.email}</p>
            </div>
            <button className="btn btn-primary" onClick={startNew} disabled={starting}>
              {starting ? "Starting…" : "Start new conversation"}
            </button>
          </div>

          {error && <p className="error-text">{error}</p>}

          {!items ? (
            <p className="muted">Loading…</p>
          ) : items.length === 0 ? (
            <div className="empty-state">
              <h3>Nothing here yet</h3>
              <p className="muted">Once you finish a conversation, it'll show up here so you can come back to it.</p>
              <button className="btn btn-primary" onClick={startNew} disabled={starting}>
                Start new conversation
              </button>
            </div>
          ) : (
            <ul className="session-list">
              {items.map((c) => (
                <li
                  key={c.id}
                  className="session-card"
                  onClick={() => navigate(`/c/${c.id}`)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && navigate(`/c/${c.id}`)}
                >
                  <span className="session-date">{formatDate(c.started_at)}</span>
                  <span className="session-chevron" aria-hidden="true">›</span>
                  {c.status === "active" ? (
                    <span className="session-status muted">In progress — tap to continue</span>
                  ) : c.labels.length === 0 ? (
                    <span className="session-status muted">No strong emotions came up</span>
                  ) : (
                    <div className="emotion-row">
                      {c.labels.map((label) => (
                        <span key={label} className="emotion-tag">
                          <span className={`emotion-dot ${dotClass(label)}`} aria-hidden="true" />
                          {label}
                        </span>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </main>
  );
}
