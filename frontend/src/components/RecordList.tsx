import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/api/client";
import { StageBadge } from "@/components/StageBadge";
import type { Record as ApiRecord, Stage } from "@/schema/record";

const STAGE_FILTERS: (Stage | "all")[] = ["all", "estimate", "proposal", "provisioning"];

export function RecordList() {
  const [records, setRecords] = useState<ApiRecord[]>([]);
  const [filter, setFilter] = useState<Stage | "all">("all");
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("New record");
  const [newStage, setNewStage] = useState<Stage>("estimate");
  const navigate = useNavigate();

  async function refresh() {
    const params = filter === "all" ? undefined : { stage: filter };
    setRecords(await api.listRecords(params));
  }
  useEffect(() => {
    refresh();
  }, [filter]);

  async function createNew() {
    const created = await api.createRecord({ recordName: newName, stage: newStage });
    navigate(`/records/${created._id}`);
  }

  return (
    <main style={mainStyle}>
      <header style={headerStyle}>
        <h1 style={{ margin: 0 }}>Server Provisioning Records</h1>
        <button onClick={() => setCreating((s) => !s)} style={btnPrimary}>
          {creating ? "Cancel" : "+ New record"}
        </button>
      </header>

      {creating && (
        <div style={cardStyle}>
          <label>
            Name
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              style={{ marginLeft: "0.5rem" }}
            />
          </label>
          <label>
            Stage
            <select
              value={newStage}
              onChange={(e) => setNewStage(e.target.value as Stage)}
              style={{ marginLeft: "0.5rem" }}
            >
              <option value="estimate">Estimate</option>
              <option value="proposal">Proposal</option>
              <option value="provisioning">Provisioning</option>
            </select>
          </label>
          <button onClick={createNew} style={btnPrimary}>
            Create
          </button>
        </div>
      )}

      <nav style={{ display: "flex", gap: "0.25rem" }}>
        {STAGE_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            style={{
              ...filterBtn,
              ...(filter === s ? filterBtnActive : {}),
            }}
          >
            {s}
          </button>
        ))}
      </nav>

      {records.length === 0 ? (
        <p style={{ color: "#666" }}>No records yet.</p>
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>
              <th style={th}>Name</th>
              <th style={th}>Stage / Status</th>
              <th style={th}>Updated</th>
              <th style={th}></th>
            </tr>
          </thead>
          <tbody>
            {records.map((r) => (
              <tr key={r._id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={td}>
                  <Link to={`/records/${r._id}`}>{r.recordName}</Link>
                </td>
                <td style={td}>
                  <StageBadge stage={r.stage} status={r.status} />
                </td>
                <td style={td}>{new Date(r.updatedAt).toLocaleString()}</td>
                <td style={td}>
                  <Link to={`/records/${r._id}/summary`}>summary</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
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
};
const tableStyle: React.CSSProperties = { borderCollapse: "collapse", width: "100%" };
const th: React.CSSProperties = { padding: "0.5rem", fontSize: "0.85rem", color: "#555" };
const td: React.CSSProperties = { padding: "0.5rem", fontSize: "0.9rem" };
const btnPrimary: React.CSSProperties = {
  background: "#2e5f8a",
  color: "white",
  border: "none",
  padding: "0.5rem 1rem",
  borderRadius: 4,
  cursor: "pointer",
};
const filterBtn: React.CSSProperties = {
  background: "white",
  color: "#555",
  border: "1px solid #ddd",
  padding: "0.25rem 0.75rem",
  borderRadius: 4,
  cursor: "pointer",
  textTransform: "capitalize",
};
const filterBtnActive: React.CSSProperties = {
  background: "#2e5f8a",
  color: "white",
  borderColor: "#2e5f8a",
};
const cardStyle: React.CSSProperties = {
  display: "flex",
  gap: "0.75rem",
  alignItems: "center",
  background: "white",
  border: "1px solid #ddd",
  padding: "0.75rem 1rem",
  borderRadius: 6,
};
