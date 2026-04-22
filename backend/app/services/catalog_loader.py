from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models.catalog import Catalog, CompatibilityMatrix

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def load_catalog() -> Catalog:
    raw = json.loads((_DATA_DIR / "catalog.json").read_text())
    return Catalog.model_validate(raw)


@lru_cache(maxsize=1)
def load_compatibility() -> CompatibilityMatrix:
    raw = json.loads((_DATA_DIR / "compatibility.json").read_text())
    return CompatibilityMatrix.model_validate(raw)


@lru_cache(maxsize=1)
def load_pricing_rules() -> dict[str, Any]:
    return json.loads((_DATA_DIR / "pricing_rules.json").read_text())
