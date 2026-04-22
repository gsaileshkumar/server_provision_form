const BASE = "/agent";

export interface AgentMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface AgentTurn {
  thread_id?: string;
  messages: AgentMessage[];
  record_id?: string | null;
  stage?: string | null;
  mode?: "A" | "B" | null;
  last_validation?: { errors: unknown[]; warnings: unknown[] } | null;
  pending_questions?: { path: string; prompt: string; options?: string[] }[];
}

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return (await r.json()) as T;
}

export const agentApi = {
  start(body: { stage: string; record_id?: string; record_name?: string }) {
    return json<AgentTurn>(`${BASE}/threads/start`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  message(threadId: string, content: string) {
    return json<AgentTurn>(`${BASE}/threads/${threadId}/message`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
  },
  get(threadId: string) {
    return json<AgentTurn>(`${BASE}/threads/${threadId}`);
  },
};
