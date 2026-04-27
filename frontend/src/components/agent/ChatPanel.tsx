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
  A2UI_ACTION_SENTINEL,
  RENDER_A2UI_TOOL_NAME,
  findLatestPendingA2UISurface,
} from "@/types/agent";
import { A2UICatalog } from "./A2UICatalog";
import { A2UISurface } from "./A2UISurface";

export function ChatPanel({
  mode,
  threadId,
}: {
  mode: "A" | "B";
  threadId?: string;
}) {
  // Stable per-mount threadId so useAgent and CopilotChat resolve to the
  // *same* per-thread agent clone.
  const threadIdRef = useRef<string>();
  if (!threadIdRef.current) threadIdRef.current = threadId ?? cryptoRandomId();

  return (
    <CopilotChatConfigurationProvider
      agentId="provisioning_agent"
      threadId={threadIdRef.current}
    >
      <A2UICatalog />
      <ChatPanelInner mode={mode} />
    </CopilotChatConfigurationProvider>
  );
}

function ChatPanelInner({ mode }: { mode: "A" | "B" }) {
  const record = useRecordStore((s) => s.record);

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
          : "Mode A (estimate/proposal): ask one use-case question at a time via an A2UI surface (single Card with one input + a submit Button). Never ask the user about a record field by name — infer field values from the use-case answers.",
    }),
  });

  const { agent } = useAgent({
    agentId: "provisioning_agent",
    updates: [
      UseAgentUpdate.OnMessagesChanged,
      UseAgentUpdate.OnRunStatusChanged,
      UseAgentUpdate.OnStateChanged,
    ],
  });

  // Look for the latest unanswered render_a2ui ToolMessage in the
  // transcript — that's the canonical wire format from the planner.
  const pendingSurface = useMemo(() => {
    if (mode !== "A" || !agent) return null;
    return findLatestPendingA2UISurface(
      agent.messages as ReadonlyArray<{ role?: string; name?: string; content?: unknown }>,
    );
  }, [mode, agent, agent?.messages]);

  // Pull the surface_id and question_id straight from the agent state so we
  // can correlate the user's submission with the pending question.
  const pendingQuestion = (agent?.state as
    | { pending_use_case_question?: { question_id?: string; surface_id?: string; intent?: string } }
    | undefined)?.pending_use_case_question;

  const isRunning = agent?.isRunning === true;

  const submitAnswer = useCallback(
    (answer: unknown) => {
      if (!agent || !pendingQuestion?.question_id) return;
      const payload = {
        question_id: pendingQuestion.question_id,
        intent: pendingQuestion.intent,
        answer,
      };
      agent.addMessage({
        id: cryptoRandomId(),
        role: "user",
        content: `${A2UI_ACTION_SENTINEL}${JSON.stringify(payload)}`,
      });
      void agent.runAgent();
    },
    [agent, pendingQuestion?.question_id, pendingQuestion?.intent],
  );

  const labels = useMemo(
    () => ({
      chatInputPlaceholder:
        mode === "B"
          ? "Ask or instruct…"
          : pendingSurface
          ? "Use the form above to answer…"
          : "Type to start, or wait for the next question…",
      welcomeMessageText:
        mode === "B"
          ? 'Ask about the current configuration, or say things like "set RAID to 10".'
          : "Tell me about your use case — workload, scale, audience, constraints — and I'll figure out the rest.",
    }),
    [mode, pendingSurface],
  );

  return (
    <aside style={panelStyle}>
      {pendingSurface && pendingQuestion?.surface_id && (
        <div style={surfaceWrapStyle}>
          <A2UISurface
            surfaceId={pendingQuestion.surface_id}
            operations={pendingSurface.a2ui_operations}
            onSubmit={submitAnswer}
            disabled={isRunning}
          />
        </div>
      )}
      <div style={{ flex: 1, minHeight: 0, display: "flex" }}>
        <CopilotChat
          agentId="provisioning_agent"
          labels={labels}
          messageView={{
            assistantMessage:
              A2UIAwareAssistantMessage as unknown as typeof CopilotChatAssistantMessage,
            userMessage:
              A2UIAwareUserMessage as unknown as typeof CopilotChatUserMessage,
          }}
        />
      </div>
    </aside>
  );
}

// Hide the empty AIMessage that carries the render_a2ui tool_call — the
// surface itself renders separately above the chat. Also hide assistant
// messages with no visible content.
function A2UIAwareAssistantMessage(
  props: React.ComponentProps<typeof CopilotChatAssistantMessage>,
) {
  const { message } = props;
  const m = message as { content?: unknown; tool_calls?: { name?: string }[] };
  const calls = Array.isArray(m?.tool_calls) ? m.tool_calls : [];
  if (calls.some((c) => c?.name === RENDER_A2UI_TOOL_NAME)) {
    return null;
  }
  const content = typeof m?.content === "string" ? m.content : "";
  if (!content.trim()) return null;
  return <CopilotChatAssistantMessage {...props} />;
}

// Hide the raw `__A2UI_ACTION__{...}` echo from the transcript.
function A2UIAwareUserMessage(
  props: React.ComponentProps<typeof CopilotChatUserMessage>,
) {
  const { message } = props;
  const content = typeof message?.content === "string" ? message.content : "";
  if (content.startsWith(A2UI_ACTION_SENTINEL)) {
    return (
      <CopilotChatUserMessage
        {...props}
        message={{ ...message, content: "_(answer submitted)_" }}
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
  height: "100%",
  overflow: "hidden",
};

const surfaceWrapStyle: React.CSSProperties = {
  padding: 12,
  borderBottom: "1px solid #eee",
  background: "#f7faff",
};
