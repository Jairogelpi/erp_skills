import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // The demo API serves the frozen evidence; proxying keeps every fetch
  // same-origin so a stale CORS setting cannot blank the evidence panel
  // on stage. Declared for `preview` as well as `dev`: `vite preview`
  // does not inherit the dev server's proxy, so a build served without
  // this would 404 every /demo call and show "evidence unavailable".
  server: {
    port: 5173,
    proxy: { "/demo": "http://127.0.0.1:8000" },
  },
  preview: {
    port: 4173,
    proxy: { "/demo": "http://127.0.0.1:8000" },
  },
});
