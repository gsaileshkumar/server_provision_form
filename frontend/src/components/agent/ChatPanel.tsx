import { useEffect, useRef, useState } from "react";
import { agentApi, type AgentMessage } from "@/api/agent";
import { useRecordStore } from "@/state/recordStore";

export function ChatPanel({ mode }: { mode: "A" | "B" }) {
  const record = useRecordStore((s) => s.record);
  const load = useRecordStore((s) => s.load);

  const [threadId, setThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!record?._id) return;
    let alive = true;
    setBusy(true);
    setError(null);
    agentApi
      .start({
        stage: record.stage,
        record_id: record._id,
        record_name: record.recordName,
      })
      .then((t) => {
        if (!alive) return;
        setThreadId(t.thread_id ?? null);
        setMessages(t.messages ?? []);
      })
      .catch((e) => alive && setError(String(e)))
      .finally(() => alive && setBusy(false));
    return () => {
      alive = false;
    };
  }, [record?._id, record?.stage, record?.recordName]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, busy]);

  async function send() {
    const text = input.trim();
    if (!text || !threadId) return;
    const next = [...messages, { role: "user" as const, content: text }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      const t = await agentApi.message(threadId, text);
      setMessages(t.messages ?? next);
      // Mode B edits and Mode A extractions both PATCH the record, so refetch.
      if (record?._id) await load(record._id);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside style={panelStyle}>
      <header style={headerStyle}>
        <strong>Agent</strong>
        <span style={badgeStyle}>Mode {mode}</span>
      </header>
      <div ref={scrollRef} style={scrollStyle}>
        {messages.length === 0 && !busy ? (
          <p style={hintStyle}>
            {mode === "B"
              ? "Ask questions about the current configuration or say things like \"set RAID to 10\"."
              : "The agent will walk you through a few questions to build this record."}
          </p>
        ) : null}
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              ...bubbleBase,
              ...(m.role === "user" ? bubbleUser : bubbleAssistant),
            }}
          >
            <div style={{ fontSize: "0.7rem", color: "#888", marginBottom: 2 }}>
              {m.role}
            </div>
            <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
          </div>
        ))}
        {busy ? <p style={{ color: "#888", fontSize: "0.8rem" }}>…</p> : null}
      </div>
      {error ? <div style={{ color: "#c33", padding: "0.25rem 0.5rem" }}>{error}</div> : null}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        style={formStyle}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={mode === "B" ? "Ask or instruct..." : "Your answer..."}
          disabled={busy || !threadId}
          style={inputStyle}
        />
        <button type="submit" disabled={busy || !input.trim() || !threadId} style={btnStyle}>
          Send
        </button>
      </form>
    </aside>
  );
}

const panelStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  border: "1px solid #ddd",
  borderRadius: 6,
  background: "white",
  minHeight: 400,
  maxHeight: 700,
};
const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "0.5rem 0.75rem",
  borderBottom: "1px solid #eee",
};
const badgeStyle: React.CSSProperties = {
  background: "#eef4fb",
  color: "#2e5f8a",
  padding: "0.1rem 0.5rem",
  borderRadius: 10,
  fontSize: "0.7rem",
  fontWeight: 600,
};
const scrollStyle: React.CSSProperties = {
  flex: 1,
  overflowY: "auto",
  padding: "0.75rem",
  display: "flex",
  flexDirection: "column",
  gap: "0.5rem",
};
const bubbleBase: React.CSSProperties = {
  padding: "0.5rem 0.75rem",
  borderRadius: 8,
  maxWidth: "92%",
  fontSize: "0.9rem",
};
const bubbleUser: React.CSSProperties = {
  alignSelf: "flex-end",
  background: "#2e5f8a",
  color: "white",
};
const bubbleAssistant: React.CSSProperties = {
  alignSelf: "flex-start",
  background: "#f1f3f5",
  color: "#222",
};
const hintStyle: React.CSSProperties = {
  color: "#888",
  fontSize: "0.85rem",
  fontStyle: "italic",
};
const formStyle: React.CSSProperties = {
  display: "flex",
  gap: "0.5rem",
  padding: "0.5rem 0.75rem",
  borderTop: "1px solid #eee",
};
const inputStyle: React.CSSProperties = {
  flex: 1,
  padding: "0.4rem 0.5rem",
  border: "1px solid #ccc",
  borderRadius: 4,
  fontSize: "0.9rem",
};
const btnStyle: React.CSSProperties = {
  background: "#2e5f8a",
  color: "white",
  border: "none",
  padding: "0.4rem 0.75rem",
  borderRadius: 4,
  cursor: "pointer",
};
