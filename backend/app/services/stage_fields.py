"""Authoritative map of which fields are visible/required at each stage.

Field paths use dot notation into the Record shape. Array fields under
``applications[]`` are evaluated per-item.

Stage visibility is cumulative: a Proposal record validates Estimate + Proposal
fields; Provisioning validates all three.
"""

from __future__ import annotations

from app.models.enums import Stage

ESTIMATE_FIELDS: list[str] = [
    "hardware.workloadProfile",
    "hardware.expectedConcurrentUsers",
    "hardware.cpuCores",
    "hardware.ramGb",
    "hardware.primaryStorageGb",
    "softwareOS.osFamily",
    "softwareOS.osDistribution",
    "softwareOS.osVersion",
    "applications[].category",
    "applications[].name",
]

PROPOSAL_FIELDS: list[str] = [
    "hardware.storageType",
    "hardware.raidLevel",
    "hardware.gpuRequired",
    "hardware.networkBandwidthGbps",
    "softwareOS.licensingModel",
    "softwareOS.patchingPolicy",
    "applications[].version",
    "applications[].edition",
    "applications[].expectedDataVolumeGb",
]

PROVISIONING_FIELDS: list[str] = [
    "hardware.redundancy",
    "hardware.rackUnits",
    "hardware.powerDrawWatts",
    "softwareOS.hardeningProfile",
    "softwareOS.filesystemLayout",
    "softwareOS.timezone",
    "softwareOS.locale",
    "applications[].haConfig",
    "applications[].installSource",
]

_STAGE_TO_FIELDS = {
    Stage.estimate: ESTIMATE_FIELDS,
    Stage.proposal: PROPOSAL_FIELDS,
    Stage.provisioning: PROVISIONING_FIELDS,
}


def required_fields_for(stage: Stage) -> list[str]:
    """Return the cumulative list of required fields for the given stage."""
    stages_up_to = {
        Stage.estimate: [Stage.estimate],
        Stage.proposal: [Stage.estimate, Stage.proposal],
        Stage.provisioning: [Stage.estimate, Stage.proposal, Stage.provisioning],
    }[Stage(stage)]
    out: list[str] = []
    for s in stages_up_to:
        out.extend(_STAGE_TO_FIELDS[s])
    return out


def visible_fields_for(stage: Stage) -> list[str]:
    """Same as required_fields_for for now; kept as a seam in case
    visibility diverges from required in the future."""
    return required_fields_for(stage)
