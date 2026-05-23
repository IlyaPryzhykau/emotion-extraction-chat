import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies the API to the backend so the browser sees one origin
// (the session cookie is httpOnly + same-origin). Target is env-driven: on the
// host it's localhost:8000; inside Compose it's the "app" service. In prod, Caddy
// serves the built assets and proxies /api itself — no dev server involved.
const proxyTarget = process.env.VITE_PROXY_TARGET ?? "http://localhost:8000";
const usePolling = process.env.VITE_USE_POLLING === "true";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: { "/api": proxyTarget },
    // Polling makes file-watching reliable across a Docker bind mount on Windows.
    watch: usePolling ? { usePolling: true } : undefined,
  },
});
