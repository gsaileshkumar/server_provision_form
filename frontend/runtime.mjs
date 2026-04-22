import express from "express";
import cors from "cors";
import {
  CopilotRuntime,
  copilotRuntimeNodeExpressEndpoint,
} from "@copilotkit/runtime";
import { LangGraphHttpAgent } from "@copilotkit/runtime/langgraph";
import { randomUUID } from "crypto";

// CopilotRuntime's EmptyAdapter is on a blocklist that triggers
// "No default agent provided" even when we've configured an agent.
// A minimal pass-through adapter with a distinct name is enough: all
// reasoning is delegated to the Python LangGraph agent.
class PassThroughAdapter {
  async process(request) {
    return { threadId: request.threadId || randomUUID() };
  }
  get name() {
    return "PassThroughAdapter";
  }
}

const HOST = process.env.RUNTIME_HOST ?? "0.0.0.0";
const PORT = Number(process.env.RUNTIME_PORT ?? 5003);
const PYTHON_AGENT_URL = (
  process.env.PYTHON_AGENT_URL ?? "http://localhost:5002/agui/provisioning_agent"
).replace(/\/+$/, "");

const app = express();
app.use(cors());

// The `agents` config is the supported way to register a remote LangGraph
// in @copilotkit/runtime 1.56.2. `remoteEndpoints` + `copilotKitEndpoint`
// is documented but the 1.56 runtime's assignEndpointsToAgents returns {}
// for CopilotKit endpoints, which falls back to a BuiltInAgent and crashes
// in resolveModel() with "Unknown provider undefined in undefined/undefined".
const runtime = new CopilotRuntime({
  agents: {
    provisioning_agent: new LangGraphHttpAgent({ url: PYTHON_AGENT_URL }),
  },
});

const handler = copilotRuntimeNodeExpressEndpoint({
  endpoint: "/copilotkit",
  runtime,
  serviceAdapter: new PassThroughAdapter(),
});

app.get("/health", (_req, res) => res.json({ status: "ok", service: "copilot-runtime" }));
// Mount at root so the hono router inside the handler sees the full
// /copilotkit/* path — Express would otherwise strip the mount prefix.
app.use(handler);

app.listen(PORT, HOST, () => {
  console.log(`[runtime] listening on http://${HOST}:${PORT}`);
  console.log(`[runtime] forwarding to Python AG-UI agent at ${PYTHON_AGENT_URL}`);
});
