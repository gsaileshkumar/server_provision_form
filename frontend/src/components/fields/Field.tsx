import type { ReactNode } from "react";

export function Field({
  label,
  children,
  hint,
  required,
}: {
  label: string;
  children: ReactNode;
  hint?: string | null;
  required?: boolean;
}) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
      <span style={{ fontSize: "0.85rem", color: "#555" }}>
        {label}
        {required ? <span style={{ color: "#c33" }}> *</span> : null}
      </span>
      {children}
      {hint ? (
        <span style={{ fontSize: "0.75rem", color: "#888" }}>{hint}</span>
      ) : null}
    </label>
  );
}

export function TextInput({
  value,
  onChange,
  disabled,
  placeholder,
}: {
  value: string | null | undefined;
  onChange: (v: string) => void;
  disabled?: boolean;
  placeholder?: string;
}) {
  return (
    <input
      type="text"
      value={value ?? ""}
      placeholder={placeholder}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
      style={inputStyle}
    />
  );
}

export function NumberInput({
  value,
  onChange,
  disabled,
  min,
  max,
  step,
}: {
  value: number | null | undefined;
  onChange: (v: number | null) => void;
  disabled?: boolean;
  min?: number;
  max?: number;
  step?: number;
}) {
  return (
    <input
      type="number"
      value={value ?? ""}
      disabled={disabled}
      min={min}
      max={max}
      step={step}
      onChange={(e) =>
        onChange(e.target.value === "" ? null : Number(e.target.value))
      }
      style={inputStyle}
    />
  );
}

export function Select<T extends string | number>({
  value,
  onChange,
  options,
  disabled,
  placeholder,
}: {
  value: T | null | undefined;
  onChange: (v: T | null) => void;
  options: { value: T; label: string }[];
  disabled?: boolean;
  placeholder?: string;
}) {
  return (
    <select
      value={value == null ? "" : String(value)}
      disabled={disabled}
      onChange={(e) => {
        const v = e.target.value;
        if (v === "") onChange(null);
        else {
          const match = options.find((o) => String(o.value) === v);
          onChange(match ? match.value : null);
        }
      }}
      style={inputStyle}
    >
      <option value="">{placeholder ?? "— select —"}</option>
      {options.map((o) => (
        <option key={String(o.value)} value={String(o.value)}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

export function Checkbox({
  value,
  onChange,
  label,
  disabled,
}: {
  value: boolean | null | undefined;
  onChange: (v: boolean) => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
      <input
        type="checkbox"
        checked={!!value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span style={{ fontSize: "0.9rem" }}>{label}</span>
    </label>
  );
}

const inputStyle: React.CSSProperties = {
  padding: "0.4rem 0.5rem",
  border: "1px solid #ccc",
  borderRadius: 4,
  fontSize: "0.95rem",
  background: "white",
};
