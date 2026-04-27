/**
 * Wire format the agent uses to push a dynamically generated A2UI form into
 * the chat.
 *
 * Mirrors the canonical AG-UI dojo `a2ui_dynamic_schema` example: the
 * planner runs a secondary LLM bound with a `render_a2ui` tool (forced via
 * `tool_choice="render_a2ui"`) and then emits an AIMessage(tool_calls=[...])
 * + ToolMessage(content=a2ui.render(ops)) pair. We parse the latest
 * ToolMessage with name="render_a2ui" — its content is the JSON envelope
 * `{"a2ui_operations": [...]}`.
 *
 * The user's submission of a rendered surface still rides on the message
 * channel as `__A2UI_ACTION__{...}` — the agent's extractor consumes it.
 */
export const RENDER_A2UI_TOOL_NAME = "render_a2ui";
export const A2UI_OPERATIONS_KEY = "a2ui_operations";
export const A2UI_ACTION_SENTINEL = "__A2UI_ACTION__";

export interface A2UIEnvelope {
  a2ui_operations: unknown[];
}

export interface A2UIActionPayload {
  question_id: string;
  intent?: string;
  answer: unknown;
}

/** Parse a ToolMessage's content as the `{"a2ui_operations":[...]}` envelope. */
export function parseA2UIToolMessageContent(content: unknown): A2UIEnvelope | null {
  if (!content) return null;
  // Tool content can arrive as either a JSON object (already parsed by the
  // adapter) or a JSON string (raw `a2ui.render(...)` output).
  let payload: unknown = content;
  if (typeof content === "string") {
    try {
      payload = JSON.parse(content);
    } catch {
      return null;
    }
  }
  if (
    payload &&
    typeof payload === "object" &&
    Array.isArray((payload as { a2ui_operations?: unknown[] }).a2ui_operations)
  ) {
    return payload as A2UIEnvelope;
  }
  return null;
}

/** Walk back through the message list, return the latest unanswered render_a2ui tool result. */
export function findLatestPendingA2UISurface(
  messages: ReadonlyArray<{ role?: string; name?: string; content?: unknown }> | undefined,
): A2UIEnvelope | null {
  if (!messages?.length) return null;
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    // If the user has already answered (sentinel-prefixed user message),
    // there is no pending surface.
    if (m.role === "user") {
      const c = typeof m.content === "string" ? m.content : "";
      if (c.startsWith(A2UI_ACTION_SENTINEL)) return null;
      // A free-form user message after a surface doesn't dismiss it — keep
      // walking until we hit a tool message or run out.
      continue;
    }
    if (m.role === "tool" && m.name === RENDER_A2UI_TOOL_NAME) {
      return parseA2UIToolMessageContent(m.content);
    }
  }
  return null;
}
