import { useEffect, useMemo, useRef } from "react";
import {
  A2UIProvider,
  A2UIRenderer,
  initializeDefaultCatalog,
  injectStyles,
  useA2UIActions,
  useA2UIError,
  type A2UIClientEventMessage,
} from "@copilotkit/a2ui-renderer";

let _catalogInitialized = false;
function ensureCatalog() {
  if (_catalogInitialized) return;
  initializeDefaultCatalog();
  injectStyles();
  _catalogInitialized = true;
}

/**
 * Render an A2UI surface from a list of v0.9 ops the agent emitted.
 *
 * The agent embeds the ops in an AIMessage with the `__A2UI__` sentinel
 * (see frontend/src/types/agent.ts). ChatPanel parses the latest assistant
 * message and feeds its ops here. When the user clicks the submit button,
 * the surface dispatches an action; we forward the answer back to the
 * agent via `onSubmit` (ChatPanel constructs the `__A2UI_ACTION__` payload).
 */
export function A2UISurface({
  surfaceId,
  operations,
  onSubmit,
  disabled,
}: {
  surfaceId: string;
  operations: unknown[];
  onSubmit: (answer: unknown) => void;
  disabled?: boolean;
}) {
  ensureCatalog();

  const handleAction = useMemo(
    () => async (message: A2UIClientEventMessage) => {
      if (disabled) return;
      const action = message.userAction;
      if (!action) return;
      // Only the submit button's action is wired; ignore other action names.
      if (action.name !== "submit") return;
      const answer = action.context?.answer ?? action.context ?? null;
      onSubmit(answer);
    },
    [onSubmit, disabled],
  );

  return (
    <div
      style={{
        opacity: disabled ? 0.6 : 1,
        pointerEvents: disabled ? "none" : "auto",
      }}
    >
      <A2UIProvider onAction={handleAction} theme={{}}>
        <SurfaceMessageProcessor surfaceId={surfaceId} operations={operations} />
        <SurfaceOrError surfaceId={surfaceId} />
      </A2UIProvider>
    </div>
  );
}

function SurfaceMessageProcessor({
  surfaceId,
  operations,
}: {
  surfaceId: string;
  operations: unknown[];
}) {
  const { processMessages, getSurface } = useA2UIActions();
  const lastHashRef = useRef<string>("");
  useEffect(() => {
    const hash = JSON.stringify(operations);
    if (hash === lastHashRef.current) return;
    lastHashRef.current = hash;
    const existing = getSurface(surfaceId);
    const ops = existing
      ? (operations as { createSurface?: unknown }[]).filter(
          (op) => !op?.createSurface,
        )
      : operations;
    processMessages(ops as Parameters<typeof processMessages>[0]);
  }, [processMessages, getSurface, surfaceId, operations]);
  return null;
}

function SurfaceOrError({ surfaceId }: { surfaceId: string }) {
  const error = useA2UIError();
  if (error) {
    return (
      <div
        style={{
          padding: 8,
          border: "1px solid #f5b1b1",
          background: "#fbeaea",
          color: "#8b1a1a",
          fontSize: 12,
          borderRadius: 4,
        }}
      >
        Couldn't render the agent's question: {error}
      </div>
    );
  }
  return <A2UIRenderer surfaceId={surfaceId} />;
}
