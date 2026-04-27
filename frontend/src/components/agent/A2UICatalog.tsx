import { useLayoutEffect, useMemo } from "react";
import {
  A2UI_SCHEMA_CONTEXT_DESCRIPTION,
  basicCatalog,
  buildCatalogContextValue,
  extractCatalogComponentSchemas,
} from "@copilotkit/a2ui-renderer";
import { useAgentContext, useCopilotKit } from "@copilotkit/react-core/v2";

/**
 * Advertise the A2UI component catalog to the agent.
 *
 * Mirrors the behavior of CopilotKit's built-in A2UICatalogContext (which
 * isn't re-exported from `@copilotkit/react-core/v2`). The component
 * schema is sent as agent context tagged with the well-known
 * `A2UI_SCHEMA_CONTEXT_DESCRIPTION` description; the Python
 * `ag_ui_langgraph` adapter routes that entry into
 * `state["ag-ui"]["a2ui_schema"]` so our planner node can build its system
 * prompt from the runtime catalog rather than a hand-coded copy.
 *
 * Pass `catalog` to use a non-default catalog. Defaults to `basicCatalog`
 * from `@copilotkit/a2ui-renderer` (the click-only inputs we render via
 * A2UISurface — Card, Column, Row, Text, ChoicePicker, CheckBox, Slider,
 * Button, etc.).
 */
export function A2UICatalog({
  catalog = basicCatalog,
  includeSchema = true,
}: {
  catalog?: any;
  includeSchema?: boolean;
} = {}): null {
  const contextValue = buildCatalogContextValue(catalog);

  useAgentContext({
    description:
      "A2UI catalog capabilities: available catalog IDs and custom component definitions the client can render.",
    value: contextValue,
  });

  const { copilotkit } = useCopilotKit();
  const schemaValue = useMemo(
    () => (includeSchema ? JSON.stringify(extractCatalogComponentSchemas(catalog)) : null),
    [catalog, includeSchema],
  );

  useLayoutEffect(() => {
    if (!copilotkit || !schemaValue) return;
    const id = copilotkit.addContext({
      description: A2UI_SCHEMA_CONTEXT_DESCRIPTION,
      value: schemaValue,
    });
    return () => {
      copilotkit.removeContext(id);
    };
  }, [copilotkit, schemaValue]);

  return null;
}
