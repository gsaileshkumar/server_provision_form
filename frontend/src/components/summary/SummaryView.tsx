import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "@/api/client";
import { StageBadge } from "@/components/StageBadge";
import type { PricingBreakdown, Record as ApiRecord } from "@/schema/record";

export function SummaryView() {
  const { id = "" } = useParams();
  const [data, setData] = useState<(ApiRecord & { pricing: PricingBreakdown }) | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api
      .summary(id)
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [id]);

  async function onExport() {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${data.recordName.replace(/\s+/g, "_")}_${data.stage}_summary.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (error) return <main style={mainStyle}>Error: {error}</main>;
  if (!data) return <main style={mainStyle}>Loading…</main>;

  const p = data.pricing;
  return (
    <main style={mainStyle}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <Link to={`/records/${data._id}`}>← Back to editor</Link>
          <h1 style={{ margin: "0.5rem 0" }}>{data.recordName}</h1>
          <StageBadge stage={data.stage} status={data.status} />
        </div>
        <button onClick={onExport} style={btnPrimary}>
          Export JSON
        </button>
      </header>

      <Section title="Hardware">
        <KV record={data.hardware} />
      </Section>
      <Section title="Software (OS)">
        <KV record={data.softwareOS} />
      </Section>
      <Section title="Applications">
        {data.applications.length === 0 ? (
          <p style={{ color: "#888" }}>No applications specified.</p>
        ) : (
          data.applications.map((a, i) => (
            <div key={i} style={{ marginBottom: "0.75rem" }}>
              <strong>
                {a.name ?? "(unnamed)"} {a.version ? `v${a.version}` : ""}
              </strong>
              <KV record={a} />
            </div>
          ))
        )}
      </Section>
      <Section title="Pricing">
        <table style={{ borderCollapse: "collapse", maxWidth: 500, width: "100%" }}>
          <tbody>
            <tr>
              <td>Hardware</td>
              <td style={amt}>${p.hardwareCost.toFixed(2)}</td>
            </tr>
            <tr>
              <td>Software (OS)</td>
              <td style={amt}>${p.softwareCost.toFixed(2)}</td>
            </tr>
            {p.applicationsCost.map((line, i) => (
              <tr key={i}>
                <td style={{ paddingLeft: "1rem" }}>{line.label}</td>
                <td style={amt}>${line.amount.toFixed(2)}</td>
              </tr>
            ))}
            <tr style={{ borderTop: "1px solid #ccc" }}>
              <td>Subtotal</td>
              <td style={amt}>${p.subtotal.toFixed(2)}</td>
            </tr>
            <tr>
              <td>Adjustments</td>
              <td style={amt}>${p.adjustments.toFixed(2)}</td>
            </tr>
            <tr>
              <td>Taxes</td>
              <td style={amt}>${p.taxes.toFixed(2)}</td>
            </tr>
            <tr style={{ fontWeight: "bold", borderTop: "2px solid #333" }}>
              <td>Total</td>
              <td style={amt}>${p.total.toFixed(2)}</td>
            </tr>
          </tbody>
        </table>
      </Section>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ marginTop: "1rem" }}>
      <h2 style={{ fontSize: "1.1rem", borderBottom: "1px solid #ddd", paddingBottom: "0.25rem" }}>
        {title}
      </h2>
      {children}
    </section>
  );
}

function KV({ record }: { record: object }) {
  const rows = Object.entries(record as Record<string, unknown>).filter(
    ([, v]) => v != null && !(Array.isArray(v) && v.length === 0),
  );
  if (rows.length === 0) return <p style={{ color: "#888" }}>(no fields set)</p>;
  return (
    <dl style={dlStyle}>
      {rows.map(([k, v]) => (
        <div key={k} style={{ display: "flex", gap: "0.5rem" }}>
          <dt style={{ minWidth: 200, color: "#666" }}>{k}</dt>
          <dd style={{ margin: 0 }}>
            {typeof v === "object" ? <code>{JSON.stringify(v)}</code> : String(v)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

const mainStyle: React.CSSProperties = {
  maxWidth: 900,
  margin: "0 auto",
  padding: "1.5rem",
};
const amt: React.CSSProperties = {
  textAlign: "right",
  padding: "0.25rem 0.5rem",
  fontVariantNumeric: "tabular-nums",
};
const dlStyle: React.CSSProperties = {
  margin: 0,
  display: "flex",
  flexDirection: "column",
  gap: "0.25rem",
};
const btnPrimary: React.CSSProperties = {
  background: "#2e5f8a",
  color: "white",
  border: "none",
  padding: "0.5rem 1rem",
  borderRadius: 4,
  cursor: "pointer",
};
