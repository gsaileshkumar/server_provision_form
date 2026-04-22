export type Stage = "estimate" | "proposal" | "provisioning";
export type Status = "draft" | "submitted" | "locked";
export type WorkloadProfile =
  | "web"
  | "database"
  | "app"
  | "analytics"
  | "general-purpose";
export type StorageType = "HDD" | "SSD" | "NVMe";
export type RaidLevel = "none" | "1" | "5" | "10";
export type Redundancy = "none" | "active-passive" | "active-active";
export type OSFamily = "Linux" | "Windows";
export type LicensingModel = "BYOL" | "included" | "subscription";
export type PatchingPolicy = "auto" | "manual" | "scheduled";
export type HardeningProfile = "none" | "CIS" | "custom";
export type ApplicationCategory =
  | "database"
  | "web server"
  | "app runtime"
  | "cache"
  | "message queue"
  | "monitoring"
  | "custom";
export type LicenseTier = "Community" | "Enterprise";
export type InstallSource =
  | "package manager"
  | "binary"
  | "container image"
  | "custom URL";

export interface Hardware {
  workloadProfile?: WorkloadProfile | null;
  expectedConcurrentUsers?: number | null;
  cpuCores?: number | null;
  ramGb?: number | null;
  primaryStorageGb?: number | null;
  storageType?: StorageType | null;
  raidLevel?: RaidLevel | null;
  gpuRequired?: boolean | null;
  gpuModel?: string | null;
  gpuVramGb?: number | null;
  networkBandwidthGbps?: number | null;
  redundancy?: Redundancy | null;
  rackUnits?: number | null;
  powerDrawWatts?: number | null;
}

export interface SoftwareOS {
  osFamily?: OSFamily | null;
  osDistribution?: string | null;
  osVersion?: string | null;
  licensingModel?: LicensingModel | null;
  patchingPolicy?: PatchingPolicy | null;
  hardeningProfile?: HardeningProfile | null;
  filesystemLayout?: string | null;
  timezone?: string | null;
  locale?: string | null;
}

export interface PortEndpoint {
  port: number;
  protocol: "tcp" | "udp";
}

export interface Application {
  category?: ApplicationCategory | null;
  name?: string | null;
  version?: string | null;
  edition?: LicenseTier | null;
  expectedDataVolumeGb?: number | null;
  haConfig?: string | null;
  customPorts?: PortEndpoint[];
  installSource?: InstallSource | null;
}

export interface LineItem {
  label: string;
  amount: number;
}

export interface PricingBreakdown {
  hardwareCost: number;
  softwareCost: number;
  applicationsCost: LineItem[];
  subtotal: number;
  adjustments: number;
  taxes: number;
  total: number;
}

export interface Record {
  _id?: string;
  recordName: string;
  stage: Stage;
  status: Status;
  predecessorId?: string | null;
  createdAt: string;
  updatedAt: string;
  hardware: Hardware;
  softwareOS: SoftwareOS;
  applications: Application[];
  pricing?: PricingBreakdown | null;
  agentContext?: { conversationId?: string | null; mode?: string | null } | null;
}

export interface ValidationIssue {
  path: string;
  message: string;
}

export interface ValidationResult {
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}

export interface CatalogOSVersion {
  version: string;
  label: string;
}
export interface CatalogDistribution {
  distribution: string;
  label: string;
  requiresLicense: boolean;
  versions: CatalogOSVersion[];
}
export interface CatalogOSFamily {
  family: string;
  distributions: CatalogDistribution[];
}
export interface CatalogApp {
  category: string;
  name: string;
  label: string;
  availableVersions: string[];
  availableEditions: string[];
}
export interface CatalogHardware {
  storageTypes: string[];
  raidLevels: string[];
  networkBandwidths: number[];
  redundancy: string[];
}
export interface Catalog {
  osFamilies: CatalogOSFamily[];
  applications: CatalogApp[];
  hardware: CatalogHardware;
  stageRequiredFields?: string[];
}

export interface CompatibilityEntry {
  appName: string;
  appVersion: string;
  supportedOSDistributions: string[];
  notes?: string | null;
}
export interface CompatibilityMatrix {
  entries: CompatibilityEntry[];
}
