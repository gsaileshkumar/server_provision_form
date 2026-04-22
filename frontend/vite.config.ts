import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:5001",
      "/agent": {
        target: "http://localhost:5002",
        rewrite: (path) => path.replace(/^\/agent/, ""),
      },
      // CopilotKit Node runtime — bridge from the React SDK to the Python agent.
      "/copilotkit": "http://localhost:5003",
    },
  },
});
