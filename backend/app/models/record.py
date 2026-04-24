from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ApplicationCategory,
    HardeningProfile,
    InstallSource,
    LicenseTier,
    LicensingModel,
    NetworkBandwidth,
    OSFamily,
    PatchingPolicy,
    RaidLevel,
    Redundancy,
    Stage,
    Status,
    StorageType,
    WorkloadProfile,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class Hardware(_Base):
    workloadProfile: Optional[WorkloadProfile] = None
    expectedConcurrentUsers: Optional[int] = Field(None, ge=1)
    cpuCores: Optional[int] = Field(None, ge=1, le=256)
    ramGb: Optional[int] = Field(None, ge=1, le=8192)
    primaryStorageGb: Optional[int] = Field(None, ge=1, le=1_048_576)
    storageType: Optional[StorageType] = None
    raidLevel: Optional[RaidLevel] = None
    gpuRequired: Optional[bool] = None
    gpuModel: Optional[str] = None
    gpuVramGb: Optional[int] = Field(None, ge=1, le=1024)
    networkBandwidthGbps: Optional[NetworkBandwidth] = None
    redundancy: Optional[Redundancy] = None
    rackUnits: Optional[int] = Field(None, ge=1, le=20)
    powerDrawWatts: Optional[int] = Field(None, ge=0, le=20000)


class SoftwareOS(_Base):
    osFamily: Optional[OSFamily] = None
    osDistribution: Optional[str] = None
    osVersion: Optional[str] = None
    licensingModel: Optional[LicensingModel] = None
    patchingPolicy: Optional[PatchingPolicy] = None
    hardeningProfile: Optional[HardeningProfile] = None
    filesystemLayout: Optional[str] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None


class PortEndpoint(_Base):
    port: int = Field(..., ge=1, le=65535)
    protocol: str = Field(..., pattern=r"^(tcp|udp)$")


class Application(_Base):
    category: Optional[ApplicationCategory] = None
    name: Optional[str] = None
    version: Optional[str] = None
    edition: Optional[LicenseTier] = None
    expectedDataVolumeGb: Optional[int] = Field(None, ge=0)
    haConfig: Optional[str] = None
    customPorts: list[PortEndpoint] = Field(default_factory=list)
    installSource: Optional[InstallSource] = None


class LineItem(_Base):
    label: str
    amount: float


class PricingBreakdown(_Base):
    hardwareCost: float = 0.0
    softwareCost: float = 0.0
    applicationsCost: list[LineItem] = Field(default_factory=list)
    subtotal: float = 0.0
    adjustments: float = 0.0
    taxes: float = 0.0
    total: float = 0.0


class AgentContext(_Base):
    conversationId: Optional[str] = None
    mode: Optional[str] = None


class Record(_Base):
    id: Optional[str] = Field(default=None, alias="_id")
    recordName: str
    stage: Stage
    status: Status = Status.draft
    predecessorId: Optional[str] = None
    createdAt: datetime = Field(default_factory=_utcnow)
    updatedAt: datetime = Field(default_factory=_utcnow)
    hardware: Hardware = Field(default_factory=Hardware)
    softwareOS: SoftwareOS = Field(default_factory=SoftwareOS)
    applications: list[Application] = Field(default_factory=list)
    pricing: Optional[PricingBreakdown] = None
    agentContext: Optional[AgentContext] = None

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        use_enum_values=True,
    )


class RecordCreate(_Base):
    recordName: str
    stage: Stage
    hardware: Optional[Hardware] = None
    softwareOS: Optional[SoftwareOS] = None
    applications: Optional[list[Application]] = None
    agentContext: Optional[AgentContext] = None


class RecordPatch(_Base):
    recordName: Optional[str] = None
    hardware: Optional[Hardware] = None
    softwareOS: Optional[SoftwareOS] = None
    applications: Optional[list[Application]] = None
    agentContext: Optional[AgentContext] = None
