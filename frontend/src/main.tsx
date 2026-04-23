import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { CopilotKit } from "@copilotkit/react-core";
import { HttpAgent } from "@ag-ui/client";
import "@copilotkit/react-ui/styles.css";
import App from "./App";
import "./styles.css";

// Direct AG-UI wiring — no Node runtime bridge. selfManagedAgents lets the
// React SDK talk AG-UI (@ag-ui/client HttpAgent) straight to the Python
// FastAPI endpoint exposed by ag_ui_langgraph.add_langgraph_fastapi_endpoint.
// Flask reverse-proxies /agui/* to the agent service in prod; vite proxies
// /agui → :5002 in dev.
const provisioningAgent = new HttpAgent({ url: "/agui/provisioning_agent" });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <CopilotKit
      selfManagedAgents={{ provisioning_agent: provisioningAgent }}
      agent="provisioning_agent"
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </CopilotKit>
  </React.StrictMode>,
);
