from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from app.models import (
    Application,
    Hardware,
    Record,
    SoftwareOS,
    Stage,
    StorageType,
    WorkloadProfile,
)
from app.services.catalog_loader import load_compatibility
from app.services.stage_fields import required_fields_for


@dataclass
class ValidationIssue:
    level: str  # "error" | "warning"
    path: str
    message: str


@dataclass
class ValidationResult:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "errors": [
                {"path": i.path, "message": i.message} for i in self.errors
            ],
            "warnings": [
                {"path": i.path, "message": i.message} for i in self.warnings
            ],
        }


def _get_by_path(record: Record, path: str) -> Any:
    """Resolve a dotted path. Array paths with ``applications[]`` are a marker
    handled by the caller; do not call this with ``[]`` in the path."""
    obj: Any = record
    for part in path.split("."):
        if obj is None:
            return None
        if isinstance(obj, dict):
            obj = obj.get(part)
        else:
            obj = getattr(obj, part, None)
    return obj


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def _check_required(record: Record, stage: Stage) -> Iterable[ValidationIssue]:
    for path in required_fields_for(stage):
        if path.startswith("applications[]"):
            sub = path.split(".", 1)[1]
            if not record.applications:
                yield ValidationIssue(
                    level="error",
                    path="applications",
                    message="At least one application is required.",
                )
                continue
            for idx, app in enumerate(record.applications):
                value = getattr(app, sub, None)
                if _is_blank(value):
                    yield ValidationIssue(
                        level="error",
                        path=f"applications[{idx}].{sub}",
                        message=f"{sub} is required at {stage.value} stage.",
                    )
        else:
            if _is_blank(_get_by_path(record, path)):
                yield ValidationIssue(
                    level="error",
                    path=path,
                    message=f"{path} is required at {stage.value} stage.",
                )


def _check_hardware_links(hw: Hardware) -> Iterable[ValidationIssue]:
    if hw.gpuRequired is True:
        if _is_blank(hw.gpuModel):
            yield ValidationIssue(
                level="error",
                path="hardware.gpuModel",
                message="gpuModel is required when gpuRequired is true.",
            )
        if _is_blank(hw.gpuVramGb):
            yield ValidationIssue(
                level="error",
                path="hardware.gpuVramGb",
                message="gpuVramGb is required when gpuRequired is true.",
            )
    if hw.gpuRequired is False and (hw.gpuModel or hw.gpuVramGb):
        yield ValidationIssue(
            level="warning",
            path="hardware.gpuModel",
            message="GPU fields set while gpuRequired is false; they will be ignored.",
        )

    if hw.raidLevel and hw.raidLevel not in ("none",) and hw.storageType is None:
        yield ValidationIssue(
            level="error",
            path="hardware.raidLevel",
            message="storageType must be set before RAID can be configured.",
        )

    if (
        hw.workloadProfile == WorkloadProfile.database.value
        and hw.storageType == StorageType.hdd.value
    ):
        yield ValidationIssue(
            level="warning",
            path="hardware.storageType",
            message="HDD storage is not recommended for database workloads.",
        )

    if hw.cpuCores and hw.ramGb:
        min_ram_per_core = {
            WorkloadProfile.database.value: 4,
            WorkloadProfile.analytics.value: 4,
            WorkloadProfile.app.value: 2,
            WorkloadProfile.web.value: 1,
            WorkloadProfile.general_purpose.value: 2,
        }.get(hw.workloadProfile)
        if min_ram_per_core and hw.ramGb < hw.cpuCores * min_ram_per_core:
            yield ValidationIssue(
                level="warning",
                path="hardware.ramGb",
                message=(
                    f"RAM below recommended {min_ram_per_core} GB/core for "
                    f"{hw.workloadProfile} workload."
                ),
            )


def _check_os_links(os: SoftwareOS) -> Iterable[ValidationIssue]:
    # Windows-specific licensing rule: the spec requires an explicit licensing
    # model at Proposal stage. The required-field check already enforces that
    # licensingModel is non-null, so no extra issue is raised here for now.
    return []


def _check_data_volume_fits(record: Record) -> Iterable[ValidationIssue]:
    total = sum(a.expectedDataVolumeGb or 0 for a in record.applications)
    primary = record.hardware.primaryStorageGb or 0
    if total and primary and total > primary:
        yield ValidationIssue(
            level="warning",
            path="hardware.primaryStorageGb",
            message=(
                f"Sum of application data volumes ({total} GB) exceeds primary "
                f"storage ({primary} GB)."
            ),
        )


def _check_compatibility(record: Record, stage: Stage) -> Iterable[ValidationIssue]:
    distribution = _resolve_os_distribution_label(record.softwareOS)
    if distribution is None:
        return
    matrix = load_compatibility()
    level = "error" if stage == Stage.provisioning else "warning"

    by_key = {(e.appName, e.appVersion): e for e in matrix.entries}
    for idx, app in enumerate(record.applications):
        if not app.name or not app.version:
            continue
        entry = by_key.get((app.name, app.version))
        if entry is None:
            yield ValidationIssue(
                level=level,
                path=f"applications[{idx}].version",
                message=(
                    f"No compatibility entry for {app.name} {app.version}; "
                    f"compatibility with {distribution} unknown."
                ),
            )
            continue
        if distribution not in entry.supportedOSDistributions:
            yield ValidationIssue(
                level=level,
                path=f"applications[{idx}].version",
                message=(
                    f"{app.name} {app.version} is not listed as compatible "
                    f"with {distribution}."
                ),
            )


def _resolve_os_distribution_label(os: SoftwareOS) -> Optional[str]:
    """Map (osDistribution, osVersion) to the label used in compatibility.json.
    Returns e.g. ``Ubuntu 22.04``, ``RHEL 9``, ``Windows Server 2022``."""
    if not os.osDistribution or not os.osVersion:
        return None
    if os.osDistribution == "WindowsServer":
        return f"Windows Server {os.osVersion}"
    return f"{os.osDistribution} {os.osVersion}"


def validate(record: Record) -> ValidationResult:
    stage = Stage(record.stage) if not isinstance(record.stage, Stage) else record.stage
    result = ValidationResult()

    for issue in _check_required(record, stage):
        (result.errors if issue.level == "error" else result.warnings).append(issue)

    for issue in _check_hardware_links(record.hardware):
        (result.errors if issue.level == "error" else result.warnings).append(issue)

    for issue in _check_os_links(record.softwareOS):
        (result.errors if issue.level == "error" else result.warnings).append(issue)

    for issue in _check_data_volume_fits(record):
        (result.errors if issue.level == "error" else result.warnings).append(issue)

    for issue in _check_compatibility(record, stage):
        (result.errors if issue.level == "error" else result.warnings).append(issue)

    return result
