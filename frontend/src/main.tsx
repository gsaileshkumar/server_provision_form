import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";
import App from "./App";
import "./styles.css";

// Runtime bridge (frontend/runtime.mjs, port 5003) forwards to the Python
// agent's CopilotKit endpoint; vite proxies /copilotkit → 5003 in dev.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <CopilotKit runtimeUrl="/copilotkit">
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </CopilotKit>
  </React.StrictMode>,
);
