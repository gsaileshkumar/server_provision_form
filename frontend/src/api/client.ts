import type {
  Catalog,
  CompatibilityMatrix,
  PricingBreakdown,
  Record as ApiRecord,
  Stage,
  ValidationResult,
} from "@/schema/record";

const BASE = "/api";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const err = new Error(`${resp.status} ${resp.statusText}`) as Error & {
      status?: number;
      body?: unknown;
    };
    err.status = resp.status;
    err.body = body;
    throw err;
  }
  return body as T;
}

export const api = {
  listRecords(params?: { stage?: Stage; status?: string }) {
    const qs = new URLSearchParams();
    if (params?.stage) qs.set("stage", params.stage);
    if (params?.status) qs.set("status", params.status);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return fetchJson<ApiRecord[]>(`${BASE}/records${suffix}`);
  },
  getRecord(id: string) {
    return fetchJson<ApiRecord>(`${BASE}/records/${id}`);
  },
  createRecord(payload: Partial<ApiRecord> & { recordName: string; stage: Stage }) {
    return fetchJson<ApiRecord>(`${BASE}/records`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  patchRecord(id: string, patch: Partial<ApiRecord>) {
    return fetchJson<ApiRecord>(`${BASE}/records/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
  },
  validate(id: string) {
    return fetchJson<ValidationResult>(`${BASE}/records/${id}/validate`, {
      method: "POST",
    });
  },
  pricing(id: string) {
    return fetchJson<PricingBreakdown>(`${BASE}/records/${id}/pricing`);
  },
  submit(id: string) {
    return fetchJson<ApiRecord>(`${BASE}/records/${id}/submit`, { method: "POST" });
  },
  promote(id: string) {
    return fetchJson<ApiRecord>(`${BASE}/records/${id}/promote`, { method: "POST" });
  },
  summary(id: string) {
    return fetchJson<ApiRecord & { pricing: PricingBreakdown }>(
      `${BASE}/records/${id}/summary`,
    );
  },
  catalog(stage?: Stage) {
    const suffix = stage ? `?stage=${stage}` : "";
    return fetchJson<Catalog>(`${BASE}/catalog/options${suffix}`);
  },
  compatibility() {
    return fetchJson<CompatibilityMatrix>(`${BASE}/catalog/compatibility`);
  },
};
