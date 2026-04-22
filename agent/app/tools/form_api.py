from __future__ import annotations

import os
from typing import Any

import httpx


def _base_url() -> str:
    return os.environ.get("FORM_API_URL", "http://localhost:5001").rstrip("/")


class FormApiError(RuntimeError):
    def __init__(self, status: int, body: Any) -> None:
        super().__init__(f"Form API error {status}: {body}")
        self.status = status
        self.body = body


class FormApi:
    """Thin httpx wrapper around the Flask Form API. Synchronous — the graph
    nodes run in worker threads under FastAPI's run-in-threadpool by default."""

    def __init__(self, base_url: str | None = None, timeout: float = 30.0) -> None:
        self._base = (base_url or _base_url()).rstrip("/")
        self._client = httpx.Client(base_url=self._base, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "FormApi":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = self._client.request(method, path, **kwargs)
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        if resp.status_code >= 400:
            raise FormApiError(resp.status_code, body)
        return body

    def get_catalog(self, stage: str | None = None) -> dict:
        params = {"stage": stage} if stage else None
        return self._request("GET", "/api/catalog/options", params=params)

    def get_compatibility(self) -> dict:
        return self._request("GET", "/api/catalog/compatibility")

    def get_record(self, record_id: str) -> dict:
        return self._request("GET", f"/api/records/{record_id}")

    def create_record(
        self,
        record_name: str,
        stage: str,
        agent_context: dict | None = None,
        initial_fields: dict | None = None,
    ) -> dict:
        payload: dict[str, Any] = {"recordName": record_name, "stage": stage}
        if agent_context is not None:
            payload["agentContext"] = agent_context
        if initial_fields:
            payload.update(initial_fields)
        return self._request("POST", "/api/records", json=payload)

    def update_record(self, record_id: str, patch: dict) -> dict:
        return self._request("PATCH", f"/api/records/{record_id}", json=patch)

    def validate_record(self, record_id: str) -> dict:
        return self._request("POST", f"/api/records/{record_id}/validate")

    def compute_pricing(self, record_id: str) -> dict:
        return self._request("GET", f"/api/records/{record_id}/pricing")

    def submit_record(self, record_id: str) -> dict:
        return self._request("POST", f"/api/records/{record_id}/submit")

    def promote_record(self, record_id: str) -> dict:
        return self._request("POST", f"/api/records/{record_id}/promote")

    def summary(self, record_id: str) -> dict:
        return self._request("GET", f"/api/records/{record_id}/summary")
