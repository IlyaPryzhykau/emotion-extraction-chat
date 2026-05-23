import { useAuth } from "../auth";

// Placeholder — the real history list (cards with date + emotion tags) lands in
// the history slice.
export function Sessions() {
  const { user, logout } = useAuth();
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
        <div style={{ padding: 36 }}>
          <p className="muted">Signed in as {user?.email}. History list coming next.</p>
        </div>
      </section>
    </main>
  );
}
