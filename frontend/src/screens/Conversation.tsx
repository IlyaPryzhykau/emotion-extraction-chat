import { useParams } from "react-router-dom";

// Placeholder — the chat stream + report land in the next slices.
export function Conversation() {
  const { id } = useParams();
  return (
    <main className="page">
      <section className="frame">
        <div style={{ padding: 36 }}>
          <p className="muted">Conversation {id} — chat &amp; report coming next.</p>
        </div>
      </section>
    </main>
  );
}
