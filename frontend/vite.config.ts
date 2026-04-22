import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:5001",
      "/agent": {
        target: "http://localhost:5002",
        rewrite: (path) => path.replace(/^\/agent/, ""),
      },
    },
  },
});
