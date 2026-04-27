import { useEffect, useMemo, useRef } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  CopilotChatConfigurationProvider,
  UseAgentUpdate,
  useAgent,
  useAgentContext,
} from "@copilotkit/react-core/v2";
import {
  A2UI_ACTION_SENTINEL,
  RENDER_A2UI_TOOL_NAME,
  findLatestPendingA2UISurface,
} from "@/types/agent";
import { A2UICatalog } from "./A2UICatalog";
import { A2UISurface } from "./A2UISurface";
import {
  CopilotChat,
  CopilotChatAssistantMessage,
  CopilotChatUserMessage,
} from "@copilotkit/react-core/v2";

/**
 * Standalone agent chat page mounted at /chat.
 *
 * Cold-start: no record bound. The agent's intake node creates one on first
 * turn. After the agent submits the locked record, we navigate to the
 * record editor so the user can review or override fields manually.
 *
 * Optional query params:
 *   ?recordId=<id>  — bind to an existing record (e.g. for Mode-B from a
 *                     locked provisioning record).
 *   ?stage=<stage>  — defaults to "estimate"; pass "provisioning" to enter
 *                     Mode B with an existing record.
 */
export function ChatPage() {
  const [params] = useSearchParams();
  const recordId = params.get("recordId") ?? undefined;
  const stage = (params.get("stage") as
    | "estimate"
    | "proposal"
    | "provisioning"
    | null) ?? "estimate";
  const mode: "A" | "B" = stage === "provisioning" ? "B" : "A";

  const threadIdRef = useRef<string>();
  if (!threadIdRef.current) threadIdRef.current = cryptoRandomId();

  return (
    <main style={pageStyle}>
      <header style={headerStyle}>
        <Link to="/" style={{ fontSize: "0.9rem" }}>
          ← All records
        </Link>
        <h1 style={titleStyle}>
          {mode === "B" ? "Provisioning assistant" : "Provisioning agent"}
        </h1>
      </header>
      <CopilotChatConfigurationProvider
        agentId="provisioning_agent"
        threadId={threadIdRef.current}
      >
        <A2UICatalog />
        <ChatPageInner mode={mode} initialRecordId={recordId} stage={stage} />
      </CopilotChatConfigurationProvider>
    </main>
  );
}

function ChatPageInner({
  mode,
  initialRecordId,
  stage,
}: {
  mode: "A" | "B";
  initialRecordId?: string;
  stage: "estimate" | "proposal" | "provisioning";
}) {
  const navigate = useNavigate();

  useAgentContext({
    description:
      "Conversation context for the provisioning agent (chat-only flow).",
    value: JSON.stringify({
      mode,
      stage,
      record_id: initialRecordId ?? null,
      instructions:
        mode === "B"
          ? "Mode B (provisioning): answer questions about the current configuration; only modify fields on an explicit edit instruction."
          : "Mode A (estimate/proposal): the user will describe their use case in their first message. Ask one use-case follow-up question at a time via an A2UI surface (single Card with one click-only input + a submit Button). Never ask the user about a record field by name — infer field values internally from the use-case answers.",
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

  // Watch for completion: when the agent submits the record (state.done) we
  // know there is now a finalized record_id; redirect to the record editor.
  const submitted = (agent?.state as { submitted_record?: { _id?: string } } | undefined)
    ?.submitted_record;
  useEffect(() => {
    if (submitted?._id) {
      navigate(`/records/${submitted._id}`);
    }
  }, [submitted?._id, navigate]);

  const pendingSurface = useMemo(() => {
    if (mode !== "A" || !agent) return null;
    return findLatestPendingA2UISurface(
      agent.messages as ReadonlyArray<{ role?: string; name?: string; content?: unknown }>,
    );
  }, [mode, agent, agent?.messages]);

  const pendingQuestion = (agent?.state as
    | { pending_use_case_question?: { question_id?: string; surface_id?: string; intent?: string } }
    | undefined)?.pending_use_case_question;

  const isRunning = agent?.isRunning === true;

  function submitAnswer(answer: unknown) {
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
  }

  const labels = useMemo(
    () => ({
      chatInputPlaceholder:
        mode === "B"
          ? "Ask or instruct…"
          : pendingSurface
          ? "Use the form above to answer…"
          : "Describe what you need…",
      welcomeMessageText:
        mode === "B"
          ? 'Ask about the current configuration, or say things like "set RAID to 10".'
          : "Tell me about your use case — workload, scale, audience, constraints — and I'll figure out the rest.",
    }),
    [mode, pendingSurface],
  );

  return (
    <div style={chatWrapStyle}>
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
    </div>
  );
}

function A2UIAwareAssistantMessage(
  props: React.ComponentProps<typeof CopilotChatAssistantMessage>,
) {
  const { message } = props;
  // The render_a2ui tool call is invisible in our chat — the surface itself
  // renders separately above. Hide the assistant's empty-content message
  // that carries only the tool_calls envelope.
  const m = message as { content?: unknown; tool_calls?: { name?: string }[] };
  const calls = Array.isArray(m?.tool_calls) ? m.tool_calls : [];
  if (calls.some((c) => c?.name === RENDER_A2UI_TOOL_NAME)) {
    return null;
  }
  const content = typeof m?.content === "string" ? m.content : "";
  if (!content.trim()) return null;
  return <CopilotChatAssistantMessage {...props} />;
}

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

const pageStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  height: "100vh",
  maxWidth: 980,
  margin: "0 auto",
  padding: "1rem 1.5rem 1.5rem",
  gap: "0.75rem",
};
const headerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "1rem",
};
const titleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: "1.25rem",
};
const chatWrapStyle: React.CSSProperties = {
  flex: 1,
  minHeight: 0,
  display: "flex",
  flexDirection: "column",
  border: "1px solid #ddd",
  borderRadius: 6,
  background: "white",
  overflow: "hidden",
};
const surfaceWrapStyle: React.CSSProperties = {
  padding: 12,
  borderBottom: "1px solid #eee",
  background: "#f7faff",
};
