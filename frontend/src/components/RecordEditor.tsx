import { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { api } from "@/api/client";
import { HardwareTab } from "@/components/form/HardwareTab";
import { SoftwareOSTab } from "@/components/form/SoftwareOSTab";
import { ApplicationsTab } from "@/components/form/ApplicationsTab";
import { ReviewTab } from "@/components/form/ReviewTab";
import { StageBadge } from "@/components/StageBadge";
import { useLinkedDefaults } from "@/hooks/useLinkedDefaults";
import { useRecordStore } from "@/state/recordStore";

type TabKey = "hardware" | "os" | "apps" | "review";

export function RecordEditor() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const record = useRecordStore((s) => s.record);
  const loading = useRecordStore((s) => s.loading);
  const dirty = useRecordStore((s) => s.dirty);
  const error = useRecordStore((s) => s.error);
  const load = useRecordStore((s) => s.load);
  const save = useRecordStore((s) => s.save);
  const setRecordName = useRecordStore((s) => s.setRecordName);

  const [tab, setTab] = useState<TabKey>("hardware");
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  useLinkedDefaults();

  useEffect(() => {
    if (id) load(id);
  }, [id, load]);

  if (loading || !record) return <main style={mainStyle}>Loading…</main>;
  const locked = record.status === "locked";

  async function onSubmit() {
    if (!record?._id) return;
    setActionMsg(null);
    try {
      if (dirty) await save();
      const locked = await api.submit(record._id);
      await load(locked._id!);
      setActionMsg("Submitted and locked.");
    } catch (e) {
      const err = e as { body?: { errors?: { message: string }[] } };
      const msgs = err.body?.errors?.map((x) => x.message).join("; ");
      setActionMsg(`Submit failed${msgs ? `: ${msgs}` : ""}`);
    }
  }

  async function onPromote() {
    if (!record?._id) return;
    try {
      const next = await api.promote(record._id);
      navigate(`/records/${next._id}`);
    } catch (e) {
      const err = e as { body?: { message?: string } };
      setActionMsg(`Promote failed: ${err.body?.message ?? String(e)}`);
    }
  }

  async function onExport() {
    if (!record?._id) return;
    const payload = await api.summary(record._id);
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${record.recordName.replace(/\s+/g, "_")}_${record.stage}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main style={mainStyle}>
      <header style={headerStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <Link to="/" style={{ fontSize: "0.9rem" }}>
            ← All records
          </Link>
          <input
            value={record.recordName}
            disabled={locked}
            onChange={(e) => setRecordName(e.target.value)}
            style={{
              fontSize: "1.25rem",
              fontWeight: 600,
              border: "1px solid transparent",
              padding: "0.25rem 0.5rem",
              borderRadius: 4,
              background: locked ? "transparent" : "white",
            }}
          />
          <StageBadge stage={record.stage} status={record.status} />
        </div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          {!locked && (
            <button onClick={save} disabled={!dirty} style={btnSecondary}>
              Save {dirty ? "•" : ""}
            </button>
          )}
          {!locked && (
            <button onClick={onSubmit} style={btnPrimary}>
              Submit
            </button>
          )}
          {locked && record.stage !== "provisioning" && (
            <button onClick={onPromote} style={btnPrimary}>
              Promote to {record.stage === "estimate" ? "proposal" : "provisioning"}
            </button>
          )}
          <button onClick={onExport} style={btnSecondary}>
            Export JSON
          </button>
          <Link to={`/records/${record._id}/summary`} style={btnSecondaryLink}>
            Summary
          </Link>
        </div>
      </header>
      {error && <p style={{ color: "#c33" }}>{error}</p>}
      {actionMsg && <p style={{ color: "#444" }}>{actionMsg}</p>}

      <nav style={tabsStyle}>
        {(
          [
            ["hardware", "Hardware"],
            ["os", "Software (OS)"],
            ["apps", "Applications"],
            ["review", "Review"],
          ] as [TabKey, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            style={{
              ...tabStyle,
              ...(tab === key ? tabActiveStyle : {}),
            }}
          >
            {label}
          </button>
        ))}
      </nav>

      <div style={panelStyle}>
        {tab === "hardware" && <HardwareTab stage={record.stage} locked={locked} />}
        {tab === "os" && <SoftwareOSTab stage={record.stage} locked={locked} />}
        {tab === "apps" && <ApplicationsTab stage={record.stage} locked={locked} />}
        {tab === "review" && <ReviewTab />}
      </div>
    </main>
  );
}

const mainStyle: React.CSSProperties = {
  maxWidth: 1100,
  margin: "0 auto",
  padding: "1.5rem",
  display: "flex",
  flexDirection: "column",
  gap: "1rem",
};
const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  flexWrap: "wrap",
  gap: "1rem",
};
const tabsStyle: React.CSSProperties = {
  display: "flex",
  gap: "0.25rem",
  borderBottom: "1px solid #ddd",
};
const tabStyle: React.CSSProperties = {
  background: "transparent",
  border: "none",
  padding: "0.5rem 1rem",
  cursor: "pointer",
  fontSize: "0.95rem",
  color: "#555",
  borderBottom: "2px solid transparent",
};
const tabActiveStyle: React.CSSProperties = {
  color: "#222",
  borderBottomColor: "#2e5f8a",
  fontWeight: 600,
};
const panelStyle: React.CSSProperties = {
  background: "#fafafa",
  padding: "1rem",
  borderRadius: 6,
  border: "1px solid #eee",
};
const btnPrimary: React.CSSProperties = {
  background: "#2e5f8a",
  color: "white",
  border: "none",
  padding: "0.5rem 1rem",
  borderRadius: 4,
  cursor: "pointer",
};
const btnSecondary: React.CSSProperties = {
  background: "white",
  color: "#333",
  border: "1px solid #bbb",
  padding: "0.5rem 1rem",
  borderRadius: 4,
  cursor: "pointer",
};
const btnSecondaryLink: React.CSSProperties = {
  ...btnSecondary,
  textDecoration: "none",
  display: "inline-block",
};
