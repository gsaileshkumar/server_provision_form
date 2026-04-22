from enum import Enum


class Stage(str, Enum):
    estimate = "estimate"
    proposal = "proposal"
    provisioning = "provisioning"


STAGE_ORDER = [Stage.estimate, Stage.proposal, Stage.provisioning]


class Status(str, Enum):
    draft = "draft"
    submitted = "submitted"
    locked = "locked"


class WorkloadProfile(str, Enum):
    web = "web"
    database = "database"
    app = "app"
    analytics = "analytics"
    general_purpose = "general-purpose"


class StorageType(str, Enum):
    hdd = "HDD"
    ssd = "SSD"
    nvme = "NVMe"


class RaidLevel(str, Enum):
    none = "none"
    r1 = "1"
    r5 = "5"
    r10 = "10"


class NetworkBandwidth(int, Enum):
    g1 = 1
    g10 = 10
    g25 = 25
    g40 = 40


class Redundancy(str, Enum):
    none = "none"
    active_passive = "active-passive"
    active_active = "active-active"


class OSFamily(str, Enum):
    linux = "Linux"
    windows = "Windows"


class LicensingModel(str, Enum):
    byol = "BYOL"
    included = "included"
    subscription = "subscription"


class PatchingPolicy(str, Enum):
    auto = "auto"
    manual = "manual"
    scheduled = "scheduled"


class HardeningProfile(str, Enum):
    none = "none"
    cis = "CIS"
    custom = "custom"


class ApplicationCategory(str, Enum):
    database = "database"
    web_server = "web server"
    app_runtime = "app runtime"
    cache = "cache"
    message_queue = "message queue"
    monitoring = "monitoring"
    custom = "custom"


class LicenseTier(str, Enum):
    community = "Community"
    enterprise = "Enterprise"


class InstallSource(str, Enum):
    package_manager = "package manager"
    binary = "binary"
    container_image = "container image"
    custom_url = "custom URL"
