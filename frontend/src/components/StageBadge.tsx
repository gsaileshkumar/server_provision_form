import type { Stage, Status } from "@/schema/record";

const STAGE_COLORS: Record<Stage, string> = {
  estimate: "#6b7280",
  proposal: "#2563eb",
  provisioning: "#059669",
};
const STATUS_COLORS: Record<Status, string> = {
  draft: "#9ca3af",
  submitted: "#2563eb",
  locked: "#d97706",
};

export function StageBadge({ stage, status }: { stage: Stage; status?: Status }) {
  return (
    <span style={{ display: "inline-flex", gap: "0.5rem" }}>
      <span
        style={{
          background: STAGE_COLORS[stage],
          color: "white",
          padding: "0.15rem 0.5rem",
          borderRadius: 12,
          fontSize: "0.75rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        {stage}
      </span>
      {status ? (
        <span
          style={{
            background: STATUS_COLORS[status],
            color: "white",
            padding: "0.15rem 0.5rem",
            borderRadius: 12,
            fontSize: "0.75rem",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          {status}
        </span>
      ) : null}
    </span>
  );
}
