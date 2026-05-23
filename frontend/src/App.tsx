import type { ReactElement } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth";
import { Welcome } from "./screens/Welcome";
import { Sessions } from "./screens/Sessions";
import { Conversation } from "./screens/Conversation";

function Protected({ children }: { children: ReactElement }): ReactElement {
  const { user, loading } = useAuth();
  if (loading) return <div className="page muted">Loading…</div>;
  if (!user) return <Navigate to="/welcome" replace />;
  return children;
}

function AppRoutes(): ReactElement {
  const { user, loading } = useAuth();
  return (
    <Routes>
      <Route
        path="/welcome"
        element={!loading && user ? <Navigate to="/" replace /> : <Welcome />}
      />
      <Route path="/" element={<Protected><Sessions /></Protected>} />
      <Route path="/c/:id" element={<Protected><Conversation /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
