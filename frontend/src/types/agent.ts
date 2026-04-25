export type QuestionKind =
  | "select"
  | "multi-select"
  | "number"
  | "text"
  | "boolean";

export interface Question {
  path: string;
  prompt: string;
  kind: QuestionKind;
  options?: string[];
  required?: boolean;
  depends_on?: string | null;
}

export interface QuestionBatch {
  batch_id: string;
  title: string;
  rationale: string;
  questions: Question[];
  submitted?: boolean;
  errors?: Record<string, string>;
}

export interface BatchAnswerPayload {
  batch_id: string;
  answers: Record<string, unknown>;
}

export const BATCH_SENTINEL = "__BATCH__";
export const BATCH_ANSWER_SENTINEL = "__BATCH_ANSWER__";

/** Parse a `__BATCH__{...}` assistant message. Returns null if not a batch. */
export function parseBatchMessage(content: unknown): QuestionBatch | null {
  if (typeof content !== "string") return null;
  const trimmed = content.trimStart();
  if (!trimmed.startsWith(BATCH_SENTINEL)) return null;
  try {
    const parsed = JSON.parse(trimmed.slice(BATCH_SENTINEL.length));
    const batch = parsed?.batch;
    if (batch && typeof batch.batch_id === "string" && Array.isArray(batch.questions)) {
      return batch as QuestionBatch;
    }
  } catch {
    // fall through
  }
  return null;
}
