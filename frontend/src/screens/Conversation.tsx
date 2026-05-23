import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ApiError, api, streamMessage, type ConversationDetail } from "../api";
import { Report } from "./Report";

/** Loads a conversation and shows the chat while active, the report once analyzed. */
export function Conversation() {
  const { id = "" } = useParams();
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .getConversation(id)
      .then(setDetail)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load conversation"));
  }, [id]);

  useEffect(() => load(), [load]);

  if (error) return <main className="page"><p className="error-text">{error}</p></main>;
  if (!detail) return <main className="page muted">Loading…</main>;
  if (detail.status === "analyzed") return <Report id={id} />;
  return <Chat detail={detail} onAnalyzed={load} />;
}

interface Bubble {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

function Chat({ detail, onAnalyzed }: { detail: ConversationDetail; onAnalyzed: () => void }) {
  const navigate = useNavigate();
  const [bubbles, setBubbles] = useState<Bubble[]>(
    detail.messages.map((m) => ({ role: m.role, content: m.content })),
  );
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [ending, setEnding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const streamEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    streamEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [bubbles]);

  const send = async () => {
    const content = input.trim();
    if (!content || sending) return;
    setInput("");
    setError(null);
    setSending(true);
    setBubbles((b) => [...b, { role: "user", content }, { role: "assistant", content: "", streaming: true }]);

    await streamMessage(detail.id, content, {
      onDelta: (text) =>
        setBubbles((b) => {
          const next = [...b];
          const last = next[next.length - 1];
          next[next.length - 1] = { ...last, content: last.content + text };
          return next;
        }),
      onDone: () => {
        setBubbles((b) => {
          const next = [...b];
          next[next.length - 1] = { ...next[next.length - 1], streaming: false };
          return next;
        });
        setSending(false);
      },
      onError: (msg) => {
        setError(msg);
        setBubbles((b) => b.slice(0, -1)); // drop the empty assistant bubble
        setSending(false);
      },
    });
  };

  const endSession = async () => {
    setEnding(true);
    setError(null);
    try {
      await api.analyze(detail.id);
      onAnalyzed(); // re-fetch -> status analyzed -> Report
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not analyze the conversation");
      setEnding(false);
    }
  };

  const hasUserMessage = bubbles.some((b) => b.role === "user");

  return (
    <main className="page">
      <section className="frame">
        <header className="app-header">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true" />
            Reflection
          </div>
          <button
            className="btn btn-secondary"
            onClick={endSession}
            disabled={ending || sending || !hasUserMessage}
          >
            {ending ? "Reflecting…" : "End & analyze"}
          </button>
        </header>

        <div className="chat-single">
          <div className="chat-meta">
            <span className="chat-meta-hint">
              End the session when you're ready — that's when I'll reflect back what I heard.
            </span>
          </div>

          <div className="chat-stream">
            {bubbles.map((b, i) => (
              <div
                key={i}
                className={`bubble ${b.role === "user" ? "user" : b.streaming && !b.content ? "typing" : "bot"}`}
              >
                {b.streaming && !b.content ? "…" : b.content}
              </div>
            ))}
            <div ref={streamEnd} />
          </div>

          {error && <p className="error-text" style={{ padding: "0 28px" }}>{error}</p>}

          <div className="chat-composer">
            <form
              className="composer-row"
              onSubmit={(e) => {
                e.preventDefault();
                send();
              }}
            >
              <input
                className="composer-input"
                placeholder="Type a message…"
                aria-label="Message"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={sending || ending}
              />
              <button className="send-btn" type="submit" aria-label="Send" disabled={sending || ending || !input.trim()}>
                ↑
              </button>
            </form>
          </div>
        </div>
      </section>
      <p className="muted" style={{ textAlign: "center", marginTop: 16 }}>
        <button className="link-button" onClick={() => navigate("/")}>← Back to your reflections</button>
      </p>
    </main>
  );
}
