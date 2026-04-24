import { useMemo } from "react";
import { CopilotChat, useAgentContext } from "@copilotkit/react-core/v2";
import { useRecordStore } from "@/state/recordStore";

export function ChatPanel({ mode }: { mode: "A" | "B" }) {
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
          : "Mode A (estimate/proposal): drive the conversation by asking one or two focused questions at a time to build the record.",
    }),
  });

  const labels = useMemo(
    () => ({
      chatInputPlaceholder: mode === "B" ? "Ask or instruct…" : "Your answer…",
      welcomeMessageText:
        mode === "B"
          ? 'Ask about the current configuration, or say things like "set RAID to 10".'
          : "I'll walk you through a few questions to build this record.",
    }),
    [mode],
  );

  return (
    <aside style={panelStyle}>
      <CopilotChat agentId="provisioning_agent" labels={labels} />
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
  overflow: "hidden",
};
