import express from "express";
import cors from "cors";
import {
  CopilotRuntime,
  copilotRuntimeNodeExpressEndpoint,
  copilotKitEndpoint,
} from "@copilotkit/runtime";
import { randomUUID } from "crypto";

// CopilotRuntime's default EmptyAdapter is on a blocklist that triggers
// "No default agent provided" even when we've configured a remote endpoint.
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
const PYTHON_AGENT_URL = (process.env.PYTHON_AGENT_URL ?? "http://localhost:5002/copilotkit").replace(/\/+$/, "");

const app = express();
app.use(cors());

// CopilotKit Node runtime bridges the @copilotkit/react-* frontend
// (GraphQL/REST CopilotKit protocol) to our Python FastAPI agent exposed via
// the `copilotkit` Python SDK at PYTHON_AGENT_URL.
// Note: the runtime exposes a single "default" agent to the React SDK;
// the Python-side name "provisioning_agent" lives inside that remote endpoint.
const runtime = new CopilotRuntime({
  remoteEndpoints: [copilotKitEndpoint({ url: PYTHON_AGENT_URL })],
});

// EmptyAdapter is fine here because all reasoning happens inside the Python
// LangGraph agent; the runtime just forwards traffic.
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
  console.log(`[runtime] forwarding to Python agent at ${PYTHON_AGENT_URL}`);
});
