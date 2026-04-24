import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { CopilotKitProvider } from "@copilotkit/react-core/v2";
import { HttpAgent } from "@ag-ui/client";
import "@copilotkit/react-core/v2/styles.css";
import App from "./App";
import "./styles.css";

// CopilotKit v2 with selfManagedAgents — the React SDK talks AG-UI directly
// to the Python agent's ag_ui_langgraph endpoint via @ag-ui/client's HttpAgent.
// We use the v2 CopilotKitProvider directly (not the v1 CopilotKit wrapper),
// because the v1 wrapper renders CopilotKitInternal which calls validateProps()
// — that helper checks only runtimeUrl / publicApiKey and ignores
// selfManagedAgents, throwing ConfigurationError for self-hosted setups.
//
// The agent URL is relative; Flask reverse-proxies /agui/* to the agent
// service in production, and vite proxies /agui → :5002 in dev.
const provisioningAgent = new HttpAgent({ url: "/agui/provisioning_agent" });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <CopilotKitProvider
      selfManagedAgents={{ provisioning_agent: provisioningAgent }}
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </CopilotKitProvider>
  </React.StrictMode>,
);
