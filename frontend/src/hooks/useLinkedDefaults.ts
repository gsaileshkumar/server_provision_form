import { useEffect, useRef } from "react";
import { useRecordStore } from "@/state/recordStore";
import type { WorkloadProfile } from "@/schema/record";

const WORKLOAD_DEFAULTS: Record<
  WorkloadProfile,
  { cpuCores: number; ramGb: number; storagePerUserGb: number; minRamPerCore: number }
> = {
  web: { cpuCores: 2, ramGb: 8, storagePerUserGb: 0.05, minRamPerCore: 1 },
  database: { cpuCores: 4, ramGb: 32, storagePerUserGb: 0.5, minRamPerCore: 4 },
  app: { cpuCores: 4, ramGb: 16, storagePerUserGb: 0.1, minRamPerCore: 2 },
  analytics: { cpuCores: 8, ramGb: 64, storagePerUserGb: 1, minRamPerCore: 4 },
  "general-purpose": { cpuCores: 2, ramGb: 8, storagePerUserGb: 0.1, minRamPerCore: 2 },
};

/**
 * Wires the reactive linked-field rules described in the spec.
 * - Picking a workload profile populates suggested CPU / RAM / storage if
 *   those fields are currently blank (the user can override afterwards).
 * - Toggling gpuRequired=false clears gpuModel and gpuVramGb.
 * - Changing osFamily clears osDistribution+osVersion; changing osDistribution
 *   clears osVersion.
 */
export function useLinkedDefaults() {
  const record = useRecordStore((s) => s.record);
  const setHardware = useRecordStore((s) => s.setHardware);
  const setSoftwareOS = useRecordStore((s) => s.setSoftwareOS);

  const lastWorkload = useRef<string | null>(null);
  const lastOSFamily = useRef<string | null>(null);
  const lastOSDistribution = useRef<string | null>(null);

  useEffect(() => {
    if (!record) return;
    const hw = record.hardware;

    if (hw.workloadProfile && hw.workloadProfile !== lastWorkload.current) {
      lastWorkload.current = hw.workloadProfile;
      const d = WORKLOAD_DEFAULTS[hw.workloadProfile];
      const patch: Partial<typeof hw> = {};
      if (d) {
        if (hw.cpuCores == null) patch.cpuCores = d.cpuCores;
        if (hw.ramGb == null) patch.ramGb = d.ramGb;
        const users = hw.expectedConcurrentUsers ?? 0;
        if (hw.primaryStorageGb == null && users > 0) {
          patch.primaryStorageGb = Math.max(100, Math.ceil(users * d.storagePerUserGb));
        }
      }
      if (Object.keys(patch).length > 0) setHardware(patch);
    }

    if (hw.gpuRequired === false && (hw.gpuModel || hw.gpuVramGb)) {
      setHardware({ gpuModel: null, gpuVramGb: null });
    }
  }, [record, setHardware]);

  useEffect(() => {
    if (!record) return;
    const os = record.softwareOS;

    if (os.osFamily !== lastOSFamily.current) {
      if (
        lastOSFamily.current !== null &&
        (os.osDistribution || os.osVersion)
      ) {
        setSoftwareOS({ osDistribution: null, osVersion: null });
      }
      lastOSFamily.current = os.osFamily ?? null;
    }
    if (os.osDistribution !== lastOSDistribution.current) {
      if (lastOSDistribution.current !== null && os.osVersion) {
        setSoftwareOS({ osVersion: null });
      }
      lastOSDistribution.current = os.osDistribution ?? null;
    }
  }, [record, setSoftwareOS]);
}

export function ramHint(
  workload: WorkloadProfile | null | undefined,
  cpuCores: number | null | undefined,
  ramGb: number | null | undefined,
): string | null {
  if (!workload || !cpuCores || !ramGb) return null;
  const d = WORKLOAD_DEFAULTS[workload];
  if (!d) return null;
  const min = d.minRamPerCore * cpuCores;
  if (ramGb < min) {
    return `Recommended minimum for ${workload}: ${min} GB (${d.minRamPerCore} GB/core).`;
  }
  return null;
}

export function useAgentMode(): "A" | "B" | null {
  const record = useRecordStore((s) => s.record);
  if (!record) return null;
  return record.stage === "provisioning" ? "B" : "A";
}
