"""Hardcoded server provisioning catalog used by the agent's tools."""

from __future__ import annotations

FIELD_OPTIONS: dict[str, list[str]] = {
    "os": ["Linux", "Windows"],
    "server_type": ["Physical", "Virtual"],
    "cpu_cores": ["2", "4", "8", "16", "32"],
    "memory_gb": ["4", "8", "16", "32", "64", "128"],
    "storage_gb": ["50", "100", "250", "500", "1000", "2000"],
    "region": ["us-east", "us-west", "eu-central", "ap-south"],
}

BASE_PRICE_USD: dict[tuple[str, str], float] = {
    ("Physical", "Linux"): 120.0,
    ("Physical", "Windows"): 165.0,
    ("Virtual", "Linux"): 35.0,
    ("Virtual", "Windows"): 55.0,
}

PER_CORE_USD = 6.5
PER_GB_MEMORY_USD = 1.25
PER_GB_STORAGE_USD = 0.08

REGION_MULTIPLIER: dict[str, float] = {
    "us-east": 1.0,
    "us-west": 1.05,
    "eu-central": 1.15,
    "ap-south": 0.9,
}
