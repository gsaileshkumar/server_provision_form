import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { useRecordStore } from "@/state/recordStore";
import type { PricingBreakdown, ValidationResult } from "@/schema/record";

export function ReviewTab() {
  const record = useRecordStore((s) => s.record);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [pricing, setPricing] = useState<PricingBreakdown | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!record?._id) return;
    let alive = true;
    setError(null);
    Promise.all([api.validate(record._id), api.pricing(record._id)])
      .then(([v, p]) => {
        if (!alive) return;
        setValidation(v);
        setPricing(p);
      })
      .catch((e) => alive && setError(String(e)));
    return () => {
      alive = false;
    };
  }, [record]);

  if (!record) return null;

  return (
    <section style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div>
        <h3 style={{ margin: "0 0 0.5rem" }}>Validation</h3>
        {error ? <p style={{ color: "#c33" }}>{error}</p> : null}
        {validation === null ? (
          <p>Checking…</p>
        ) : validation.errors.length === 0 && validation.warnings.length === 0 ? (
          <p style={{ color: "#2a7a2a" }}>All checks passed.</p>
        ) : (
          <>
            {validation.errors.length > 0 && (
              <IssueList title="Errors" level="error" issues={validation.errors} />
            )}
            {validation.warnings.length > 0 && (
              <IssueList title="Warnings" level="warning" issues={validation.warnings} />
            )}
          </>
        )}
      </div>
      <div>
        <h3 style={{ margin: "0 0 0.5rem" }}>Pricing</h3>
        {pricing === null ? (
          <p>Calculating…</p>
        ) : (
          <table style={tableStyle}>
            <tbody>
              <tr>
                <td>Hardware</td>
                <td style={amountCell}>${pricing.hardwareCost.toFixed(2)}</td>
              </tr>
              <tr>
                <td>Software (OS)</td>
                <td style={amountCell}>${pricing.softwareCost.toFixed(2)}</td>
              </tr>
              {pricing.applicationsCost.map((item, i) => (
                <tr key={i}>
                  <td style={{ paddingLeft: "1rem" }}>{item.label}</td>
                  <td style={amountCell}>${item.amount.toFixed(2)}</td>
                </tr>
              ))}
              <tr style={{ borderTop: "1px solid #ddd" }}>
                <td>Subtotal</td>
                <td style={amountCell}>${pricing.subtotal.toFixed(2)}</td>
              </tr>
              <tr>
                <td>Adjustments</td>
                <td style={amountCell}>${pricing.adjustments.toFixed(2)}</td>
              </tr>
              <tr>
                <td>Taxes</td>
                <td style={amountCell}>${pricing.taxes.toFixed(2)}</td>
              </tr>
              <tr style={{ fontWeight: "bold", borderTop: "2px solid #333" }}>
                <td>Total</td>
                <td style={amountCell}>${pricing.total.toFixed(2)}</td>
              </tr>
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

function IssueList({
  title,
  level,
  issues,
}: {
  title: string;
  level: "error" | "warning";
  issues: { path: string; message: string }[];
}) {
  const color = level === "error" ? "#c33" : "#c60";
  return (
    <div style={{ marginTop: "0.5rem" }}>
      <strong style={{ color }}>{title}</strong>
      <ul style={{ margin: "0.25rem 0 0 1rem" }}>
        {issues.map((i, idx) => (
          <li key={idx}>
            <code style={{ fontSize: "0.85rem", color: "#555" }}>{i.path}</code>: {i.message}
          </li>
        ))}
      </ul>
    </div>
  );
}

const tableStyle: React.CSSProperties = {
  borderCollapse: "collapse",
  width: "100%",
  maxWidth: 500,
};
const amountCell: React.CSSProperties = {
  textAlign: "right",
  padding: "0.25rem 0.5rem",
  fontVariantNumeric: "tabular-nums",
};
