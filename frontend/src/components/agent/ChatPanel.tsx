import { useMemo } from "react";
import { useCopilotReadable } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { useRecordStore } from "@/state/recordStore";

export function ChatPanel({ mode }: { mode: "A" | "B" }) {
  const record = useRecordStore((s) => s.record);

  // Expose the current record to the agent as readable context so it knows
  // which record this conversation is about. Re-registered whenever the
  // record id/stage/name changes.
  useCopilotReadable(
    {
      description: "The server provisioning record the user is currently editing",
      value: record
        ? {
            id: record._id,
            name: record.recordName,
            stage: record.stage,
            status: record.status,
            mode,
          }
        : null,
    },
    [record?._id, record?.stage, record?.recordName, record?.status, mode],
  );

  const instructions = useMemo(
    () =>
      mode === "B"
        ? "You are in Mode B (provisioning). Answer questions about the record's current configuration. Only modify fields when the user gives an explicit edit instruction (e.g. 'set RAID to 10')."
        : "You are in Mode A (estimate/proposal). Drive the conversation by asking the user one or two focused questions at a time to build the record.",
    [mode],
  );

  const labels = useMemo(
    () => ({
      title: `Provisioning Agent · Mode ${mode}`,
      initial:
        mode === "B"
          ? "Ask about the current configuration, or say things like \"set RAID to 10\"."
          : "I'll walk you through a few questions to build this record.",
      placeholder: mode === "B" ? "Ask or instruct…" : "Your answer…",
    }),
    [mode],
  );

  return (
    <aside style={panelStyle}>
      <CopilotChat instructions={instructions} labels={labels} />
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
