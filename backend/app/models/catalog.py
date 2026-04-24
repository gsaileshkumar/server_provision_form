from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OSVersion(_Base):
    version: str
    label: str


class OSDistribution(_Base):
    distribution: str
    label: str
    requiresLicense: bool = False
    versions: list[OSVersion] = Field(default_factory=list)


class OSFamilyEntry(_Base):
    family: str  # "Linux" | "Windows"
    distributions: list[OSDistribution] = Field(default_factory=list)


class ApplicationOption(_Base):
    category: str
    name: str
    label: str
    availableVersions: list[str] = Field(default_factory=list)
    availableEditions: list[str] = Field(default_factory=list)


class HardwareOptions(_Base):
    storageTypes: list[str]
    raidLevels: list[str]
    networkBandwidths: list[int]
    redundancy: list[str]


class Catalog(_Base):
    osFamilies: list[OSFamilyEntry]
    applications: list[ApplicationOption]
    hardware: HardwareOptions


class CompatibilityEntry(_Base):
    appName: str
    appVersion: str
    supportedOSDistributions: list[str]  # e.g. "Ubuntu 22.04"
    notes: Optional[str] = None


class CompatibilityMatrix(_Base):
    entries: list[CompatibilityEntry]
