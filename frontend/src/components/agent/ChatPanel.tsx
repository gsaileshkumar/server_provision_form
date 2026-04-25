import { useCallback, useMemo, useRef } from "react";
import {
  CopilotChat,
  CopilotChatAssistantMessage,
  CopilotChatConfigurationProvider,
  CopilotChatUserMessage,
  UseAgentUpdate,
  useAgent,
  useAgentContext,
} from "@copilotkit/react-core/v2";
import { useRecordStore } from "@/state/recordStore";
import {
  BATCH_ANSWER_SENTINEL,
  BATCH_SENTINEL,
  type BatchAnswerPayload,
  parseBatchMessage,
} from "@/types/agent";
import { BatchedQuestionForm } from "./BatchedQuestionForm";

export function ChatPanel({ mode }: { mode: "A" | "B" }) {
  // Stable per-mount threadId so useAgent (here) and the CopilotChat below
  // resolve to the *same* per-thread agent clone. Without this wrapping
  // provider, CopilotChat creates its own ad-hoc threadId internally and our
  // useAgent sees the registry agent — two different instances, so message
  // updates never re-render this component.
  const threadIdRef = useRef<string>();
  if (!threadIdRef.current) threadIdRef.current = cryptoRandomId();

  return (
    <CopilotChatConfigurationProvider
      agentId="provisioning_agent"
      threadId={threadIdRef.current}
    >
      <ChatPanelInner mode={mode} />
    </CopilotChatConfigurationProvider>
  );
}

function ChatPanelInner({ mode }: { mode: "A" | "B" }) {
  const record = useRecordStore((s) => s.record);

  // Expose the active record + mode-specific guidance to the agent as
  // context. v2 useAgentContext is the successor to v1 useCopilotReadable.
  // Pre-stringify so undefined fields are dropped (JsonSerializable forbids
  // undefined property values).
  useAgentContext({
    description:
      "The server provisioning record the user is editing, plus mode guidance.",
    value: JSON.stringify({
      record: record
        ? {
            id: record._id ?? null,
            name: record.recordName,
            stage: record.stage,
            status: record.status,
          }
        : null,
      mode,
      instructions:
        mode === "B"
          ? "Mode B (provisioning): answer questions about the current configuration; only modify fields on an explicit edit instruction (e.g. 'set RAID to 10')."
          : "Mode A (estimate/proposal): batch related unfilled fields into a single generative-UI form (pending_batch in shared state). Do not try to drive a one-question-at-a-time conversation.",
    }),
  });

  // Re-render whenever messages arrive — the planner embeds the batch payload
  // as a `__BATCH__{...}` AIMessage so the generative-UI form rides on the
  // messages channel (which is reliable) instead of AG-UI state-sync.
  const { agent } = useAgent({
    agentId: "provisioning_agent",
    updates: [UseAgentUpdate.OnMessagesChanged, UseAgentUpdate.OnRunStatusChanged, UseAgentUpdate.OnStateChanged],
  });

  // Walk back from the most recent message; show the form only if the latest
  // assistant message is a batch and no later user message has answered it.
  const pendingBatch = useMemo(() => {
    if (mode !== "A" || !agent) return null;
    const msgs = agent.messages ?? [];
    for (let i = msgs.length - 1; i >= 0; i--) {
      const m = msgs[i] as { role?: string; content?: unknown };
      if (m.role === "user") return null;
      if (m.role === "assistant") {
        const batch = parseBatchMessage(m.content);
        if (batch && !batch.submitted) return batch;
        return null;
      }
    }
    return null;
  }, [mode, agent, agent?.messages]);

  const isRunning = agent?.isRunning === true;

  console.log("agent", agent)
  console.log("pending batch", pendingBatch)
  console.log("mode", mode)
  console.log("isRunning", isRunning)

  const submitBatch = useCallback(
    (payload: BatchAnswerPayload) => {
      if (!agent) return;
      agent.addMessage({
        id: cryptoRandomId(),
        role: "user",
        content: `${BATCH_ANSWER_SENTINEL}${JSON.stringify(payload)}`,
      });
      // Fire-and-forget; subscribers will update the chat transcript.
      void agent.runAgent();
    },
    [agent],
  );

  const labels = useMemo(
    () => ({
      chatInputPlaceholder:
        mode === "B"
          ? "Ask or instruct…"
          : pendingBatch
          ? "Fill the form above, then continue…"
          : "Your answer…",
      welcomeMessageText:
        mode === "B"
          ? 'Ask about the current configuration, or say things like "set RAID to 10".'
          : "I'll group related questions into a short form so you can answer them together.",
    }),
    [mode, pendingBatch],
  );

  return (
    <aside style={panelStyle}>
      {pendingBatch && (
        <BatchedQuestionForm
          batch={pendingBatch}
          disabled={isRunning}
          onSubmit={submitBatch}
        />
      )}
      <div style={{ flex: 1, minHeight: 0, display: "flex" }}>
        <CopilotChat
          agentId="provisioning_agent"
          labels={labels}
          messageView={{
            assistantMessage:
              BatchAwareAssistantMessage as unknown as typeof CopilotChatAssistantMessage,
            userMessage:
              BatchAwareUserMessage as unknown as typeof CopilotChatUserMessage,
          }}
        />
      </div>
    </aside>
  );
}

// Rewrite `__BATCH__{...}` assistant messages into a friendly summary so the
// raw sentinel + JSON payload never appears in the chat transcript. The form
// itself is rendered separately above the chat by ChatPanel.
function BatchAwareAssistantMessage(
  props: React.ComponentProps<typeof CopilotChatAssistantMessage>,
) {
  const { message } = props;
  const content = typeof message?.content === "string" ? message.content : "";
  if (content.startsWith(BATCH_SENTINEL)) {
    const batch = parseBatchMessage(content);
    const friendly = batch
      ? `**${batch.title}** — please fill the form on the right.${
          batch.rationale ? `\n\n_${batch.rationale}_` : ""
        }`
      : "Please fill the form on the right.";
    return (
      <CopilotChatAssistantMessage
        {...props}
        message={{ ...message, content: friendly }}
      />
    );
  }
  return <CopilotChatAssistantMessage {...props} />;
}

// Hide the raw `__BATCH_ANSWER__{...}` echo from the transcript by rendering
// a short readable line in its place.
function BatchAwareUserMessage(
  props: React.ComponentProps<typeof CopilotChatUserMessage>,
) {
  const { message } = props;
  const content = typeof message?.content === "string" ? message.content : "";
  if (content.startsWith(BATCH_ANSWER_SENTINEL)) {
    return (
      <CopilotChatUserMessage
        {...props}
        message={{ ...message, content: "_(form submitted)_" }}
      />
    );
  }
  return <CopilotChatUserMessage {...props} />;
}

function cryptoRandomId(): string {
  const c =
    typeof globalThis !== "undefined"
      ? (globalThis.crypto as Crypto | undefined)
      : undefined;
  if (c?.randomUUID) return c.randomUUID();
  return `m_${Math.random().toString(36).slice(2)}_${Date.now()}`;
}

const panelStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  border: "1px solid #ddd",
  borderRadius: 6,
  background: "white",
  minHeight: 400,
  maxHeight: 700,
  overflow: "hidden",
};
