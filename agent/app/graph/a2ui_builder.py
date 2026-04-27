"""Product-policy helpers layered on top of the generic A2UI catalog.

The component schema, generation guidelines, and design guidelines are
NOT defined here — they are advertised at runtime by the React frontend
(``A2UICatalog``) via ``@copilotkit/react-core`` agent context, picked up
by ``ag_ui_langgraph`` and exposed to LangGraph nodes as
``state["ag-ui"]["a2ui_schema"]`` / ``state["ag-ui"]["context"]``.

What lives here is the *product* policy that isn't expressible in the
generic catalog: the set of components our chat is willing to render
(click-only — no free-text inputs), and the surface shape we want for a
single use-case question (one Card → Column → Text + input + submit
Button). The planner layers these rules on top of the runtime catalog
schema when it builds the secondary "designer" LLM's prompt.

Surface ops themselves are built directly via ``copilotkit.a2ui``
(``create_surface`` / ``update_components`` / ``update_data_model`` /
``render``), mirroring the dojo ``a2ui_dynamic_schema`` example.
"""

from __future__ import annotations

import json


# Click-only catalog. We deliberately omit TextField / DateTimeInput so the
# LLM cannot ask for free-text input. Slider gives us numeric input via
# clicking. ChoicePicker / CheckBox cover single- and multi-select.
ALLOWED_COMPONENTS = (
    "Card",
    "Column",
    "Row",
    "Text",
    "Divider",
    "ChoicePicker",
    "CheckBox",
    "Slider",
    "Button",
)


def click_only_rules() -> str:
    """Hard product rules layered on top of the generic catalog schema.

    These constraints are *not* expressible in the generic catalog:
    basicCatalog includes TextField, but we forbid it product-side; the
    catalog allows arbitrary surfaces, but we want exactly one Card with
    one input + one submit Button.
    """
    return (
        "PRODUCT-SPECIFIC SURFACE RULES (apply on top of the generic A2UI "
        "instructions above):\n"
        "- Render exactly ONE question as a single Card (id=\"root\") "
        "  containing one Column. Inside the Column, in order: a Text "
        "  (variant=h3) with the question, ONE input component "
        "  (ChoicePicker / CheckBox group / Slider — NEVER TextField or "
        "  DateTimeInput), and ONE Button (id=\"submit\", variant=\"primary\", "
        "  label=\"Continue\").\n"
        "- The Button's action MUST be exactly: "
        "  {\"event\": {\"name\": \"submit\", "
        "\"context\": {\"answer\": {\"path\": \"/answer\"}}}}.\n"
        "- The input's `value` MUST be path-bound to /answer (single input) "
        "  or /answer/<key> (CheckBox group). All other props are inline "
        "  literals.\n"
        "- For multi-select questions, render multiple CheckBox components "
        "  in the Column, each binding to a distinct /answer/<key> path."
    )


def fallback_component_schema() -> str:
    """Minimal schema used only when the React frontend hasn't advertised
    one — keeps the planner functional for tests / curl-driven sessions
    where there is no React client mounting ``A2UICatalog``.
    """
    schema = {
        "Card": {"props": {"id": "string"}, "children": "single component"},
        "Column": {
            "props": {"id": "string", "gap": "number", "align": "string", "justify": "string"},
            "children": "list[component]",
        },
        "Row": {
            "props": {"id": "string", "gap": "number", "align": "string", "justify": "string"},
            "children": "list[component]",
        },
        "Text": {
            "props": {"id": "string", "text": "string", "variant": "h2|h3|body|caption"},
        },
        "Divider": {"props": {"id": "string"}},
        "ChoicePicker": {
            "props": {
                "id": "string",
                "label": "string",
                "value": "{path: '/answer'}",
                "options": "list[{value, label}]",
            },
        },
        "CheckBox": {
            "props": {"id": "string", "label": "string", "value": "{path: '/answer/<key>'}"},
        },
        "Slider": {
            "props": {
                "id": "string",
                "label": "string",
                "min": "number",
                "max": "number",
                "step": "number",
                "value": "{path: '/answer'}",
            },
        },
        "Button": {
            "props": {
                "id": "string",
                "label": "string",
                "variant": "primary|borderless",
                "action": "{event: {name: 'submit', context: {...}}}",
            },
        },
    }
    return json.dumps(schema, indent=2)
