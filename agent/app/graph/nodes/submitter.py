from __future__ import annotations

from langchain_core.messages import AIMessage

from app.graph.state import AgentState
from app.tools.form_api import FormApi


def _record_url(record_id: str) -> str:
    import os

    base = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return f"{base}/records/{record_id}/summary"


def submitter(state: AgentState) -> dict:
    record_id = state.get("record_id")
    if not record_id:
        return {}

    with FormApi() as api:
        try:
            locked = api.submit_record(record_id)
        except Exception as e:  # surface the error to the user turn
            return {
                "messages": [
                    AIMessage(content=f"Submission failed: {e}")
                ],
            }

    url = _record_url(record_id)
    return {
        "submitted_record": locked,
        "review_pending": False,
        "done": True,
        "messages": [
            AIMessage(
                content=(
                    f"Submitted and locked. Total ${locked.get('pricing', {}).get('total', 0):.2f}. "
                    f"View the record at {url}"
                )
            )
        ],
    }
