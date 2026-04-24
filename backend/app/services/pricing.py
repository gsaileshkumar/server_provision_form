from __future__ import annotations

from typing import Protocol

from app.models import LineItem, PricingBreakdown, Record
from app.services.catalog_loader import load_pricing_rules


class PricingEngine(Protocol):
    def compute(self, record: Record) -> PricingBreakdown: ...


class HardcodedPricingEngine:
    """Reads `data/pricing_rules.json` and computes a breakdown. The interface
    is intentionally narrow so it can be swapped with a DB-backed catalog
    later without touching call sites."""

    def __init__(self) -> None:
        self._rules = load_pricing_rules()

    def compute(self, record: Record) -> PricingBreakdown:
        hw = record.hardware
        os_ = record.softwareOS
        rules = self._rules
        hrules = rules["hardware"]

        hardware_cost = 0.0
        hardware_cost += (hw.cpuCores or 0) * hrules["cpuPerCore"]
        hardware_cost += (hw.ramGb or 0) * hrules["ramPerGb"]
        if hw.storageType and hw.primaryStorageGb:
            per_gb = hrules["storagePerGb"].get(hw.storageType, 0)
            hardware_cost += hw.primaryStorageGb * per_gb
        if hw.gpuRequired:
            hardware_cost += hrules["gpuFlat"] + (hw.gpuVramGb or 0) * hrules[
                "gpuPerVramGb"
            ]
        if hw.networkBandwidthGbps:
            hardware_cost += hw.networkBandwidthGbps * hrules[
                "networkBandwidthPerGbps"
            ]
        if hw.redundancy:
            hardware_cost += hrules["redundancySurcharge"].get(hw.redundancy, 0)
        if hw.rackUnits:
            hardware_cost += hw.rackUnits * hrules["rackUnitFlat"]

        software_cost = 0.0
        if os_.osDistribution:
            software_cost += rules["os"].get(os_.osDistribution, 0)

        app_items: list[LineItem] = []
        for app in record.applications:
            if not app.name:
                continue
            edition = app.edition or "Community"
            per_app = rules["apps"].get(app.name, {}).get(edition, 0)
            app_items.append(
                LineItem(label=f"{app.name} ({edition})", amount=float(per_app))
            )
        applications_cost_total = sum(item.amount for item in app_items)

        subtotal = hardware_cost + software_cost + applications_cost_total
        adjustments = 0.0
        taxes = round(subtotal * rules.get("taxRate", 0.0), 2)
        total = round(subtotal + adjustments + taxes, 2)

        return PricingBreakdown(
            hardwareCost=round(hardware_cost, 2),
            softwareCost=round(software_cost, 2),
            applicationsCost=app_items,
            subtotal=round(subtotal, 2),
            adjustments=adjustments,
            taxes=taxes,
            total=total,
        )


def default_engine() -> PricingEngine:
    return HardcodedPricingEngine()
