import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies the API to the backend so the browser sees one origin
// (the session cookie is httpOnly + same-origin). In prod, Caddy serves the
// built assets and proxies /api itself, so no proxy config is needed there.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
