import { useMemo, useState } from "react";
import type {
  BatchAnswerPayload,
  Question,
  QuestionBatch,
} from "@/types/agent";

type AnswerMap = Record<string, unknown>;

export function BatchedQuestionForm({
  batch,
  disabled,
  onSubmit,
}: {
  batch: QuestionBatch;
  disabled?: boolean;
  onSubmit: (payload: BatchAnswerPayload) => void;
}) {
  const [answers, setAnswers] = useState<AnswerMap>(() => initialAnswers(batch));
  const errors = batch.errors ?? {};

  const canSubmit = useMemo(
    () =>
      batch.questions.every(
        (q) => !(q.required ?? true) || hasValue(answers[q.path], q.kind),
      ),
    [answers, batch.questions],
  );

  const submit = () => {
    if (disabled || !canSubmit) return;
    onSubmit({ batch_id: batch.batch_id, answers });
  };

  return (
    <div style={wrapStyle}>
      <div style={headerStyle}>
        <div style={titleStyle}>{batch.title}</div>
        {batch.rationale && <div style={rationaleStyle}>{batch.rationale}</div>}
      </div>
      {errors.__global__ && <div style={globalErrStyle}>{errors.__global__}</div>}
      <div style={fieldsStyle}>
        {batch.questions.map((q) => (
          <FieldRow
            key={q.path}
            question={q}
            value={answers[q.path]}
            error={errors[q.path]}
            disabled={disabled}
            onChange={(v) =>
              setAnswers((prev) => ({ ...prev, [q.path]: v }))
            }
          />
        ))}
      </div>
      <button
        type="button"
        onClick={submit}
        disabled={disabled || !canSubmit}
        style={btnStyle(disabled || !canSubmit)}
      >
        Submit
      </button>
    </div>
  );
}

function FieldRow({
  question,
  value,
  error,
  disabled,
  onChange,
}: {
  question: Question;
  value: unknown;
  error?: string;
  disabled?: boolean;
  onChange: (v: unknown) => void;
}) {
  return (
    <label style={rowStyle}>
      <span style={labelStyle}>
        {question.prompt}
        {(question.required ?? true) && <span style={reqStyle}> *</span>}
      </span>
      <FieldInput
        question={question}
        value={value}
        disabled={disabled}
        onChange={onChange}
      />
      {error && <span style={errStyle}>{error}</span>}
    </label>
  );
}

function FieldInput({
  question,
  value,
  disabled,
  onChange,
}: {
  question: Question;
  value: unknown;
  disabled?: boolean;
  onChange: (v: unknown) => void;
}) {
  const options = question.options ?? [];

  if (question.kind === "select") {
    return (
      <select
        value={(value as string) ?? ""}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value || undefined)}
        style={inputStyle}
      >
        <option value="">— pick one —</option>
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    );
  }

  if (question.kind === "multi-select") {
    const current = Array.isArray(value) ? (value as string[]) : [];
    const toggle = (o: string) => {
      const next = current.includes(o)
        ? current.filter((x) => x !== o)
        : [...current, o];
      onChange(next);
    };
    return (
      <div style={checkGroupStyle}>
        {options.map((o) => (
          <label key={o} style={checkboxLabelStyle}>
            <input
              type="checkbox"
              checked={current.includes(o)}
              disabled={disabled}
              onChange={() => toggle(o)}
            />
            {o}
          </label>
        ))}
      </div>
    );
  }

  if (question.kind === "boolean") {
    return (
      <input
        type="checkbox"
        checked={value === true}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
    );
  }

  if (question.kind === "number") {
    return (
      <input
        type="number"
        value={(value as number | string) ?? ""}
        disabled={disabled}
        onChange={(e) => {
          const raw = e.target.value;
          onChange(raw === "" ? undefined : Number(raw));
        }}
        style={inputStyle}
      />
    );
  }

  return (
    <input
      type="text"
      value={(value as string) ?? ""}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value || undefined)}
      style={inputStyle}
    />
  );
}

function initialAnswers(batch: QuestionBatch): AnswerMap {
  const out: AnswerMap = {};
  for (const q of batch.questions) {
    if (q.kind === "multi-select") out[q.path] = [];
    else if (q.kind === "boolean") out[q.path] = false;
  }
  return out;
}

function hasValue(v: unknown, kind: string): boolean {
  if (kind === "multi-select") return Array.isArray(v) && v.length > 0;
  if (kind === "boolean") return typeof v === "boolean";
  if (kind === "number") return typeof v === "number" && !Number.isNaN(v);
  return v !== undefined && v !== null && String(v).trim() !== "";
}

const wrapStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 10,
  padding: 12,
  border: "1px solid #c9d4e3",
  borderRadius: 6,
  background: "#f5f8fc",
  margin: "8px 0",
};
const headerStyle: React.CSSProperties = { display: "flex", flexDirection: "column", gap: 2 };
const titleStyle: React.CSSProperties = { fontWeight: 600, fontSize: 14 };
const rationaleStyle: React.CSSProperties = { fontSize: 12, color: "#52607a" };
const fieldsStyle: React.CSSProperties = { display: "flex", flexDirection: "column", gap: 8 };
const rowStyle: React.CSSProperties = { display: "flex", flexDirection: "column", gap: 3 };
const labelStyle: React.CSSProperties = { fontSize: 12, fontWeight: 500, color: "#1f2937" };
const reqStyle: React.CSSProperties = { color: "#c1392b" };
const errStyle: React.CSSProperties = { fontSize: 11, color: "#c1392b" };
const globalErrStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#c1392b",
  background: "#fbeaea",
  padding: 6,
  borderRadius: 4,
};
const inputStyle: React.CSSProperties = {
  padding: "4px 6px",
  border: "1px solid #b7c4d6",
  borderRadius: 4,
  fontSize: 13,
};
const checkGroupStyle: React.CSSProperties = { display: "flex", flexWrap: "wrap", gap: 8 };
const checkboxLabelStyle: React.CSSProperties = { display: "flex", gap: 4, fontSize: 13 };
const btnStyle = (dis: boolean | undefined): React.CSSProperties => ({
  alignSelf: "flex-start",
  padding: "6px 14px",
  borderRadius: 4,
  border: "1px solid #1d4ed8",
  background: dis ? "#9bb0d6" : "#1d4ed8",
  color: "white",
  fontSize: 13,
  cursor: dis ? "not-allowed" : "pointer",
});
