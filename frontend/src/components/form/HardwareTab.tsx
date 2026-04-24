import { useRecordStore } from "@/state/recordStore";
import { ramHint } from "@/hooks/useLinkedDefaults";
import { useCatalog } from "@/hooks/useCatalog";
import { Checkbox, Field, NumberInput, Select, TextInput } from "@/components/fields/Field";
import type { Stage, RaidLevel, Redundancy, StorageType, WorkloadProfile } from "@/schema/record";

const WORKLOAD_OPTIONS: { value: WorkloadProfile; label: string }[] = [
  { value: "web", label: "Web" },
  { value: "database", label: "Database" },
  { value: "app", label: "Application" },
  { value: "analytics", label: "Analytics" },
  { value: "general-purpose", label: "General purpose" },
];

export function HardwareTab({ stage, locked }: { stage: Stage; locked: boolean }) {
  const record = useRecordStore((s) => s.record);
  const setHardware = useRecordStore((s) => s.setHardware);
  const { catalog } = useCatalog(stage);
  if (!record) return null;
  const hw = record.hardware;
  const showProposal = stage === "proposal" || stage === "provisioning";
  const showProvisioning = stage === "provisioning";

  const storageTypes: StorageType[] = (catalog?.hardware.storageTypes as StorageType[]) ?? [
    "HDD",
    "SSD",
    "NVMe",
  ];
  const raidLevels: RaidLevel[] = (catalog?.hardware.raidLevels as RaidLevel[]) ?? [
    "none",
    "1",
    "5",
    "10",
  ];
  const bandwidths = catalog?.hardware.networkBandwidths ?? [1, 10, 25, 40];
  const redundancy: Redundancy[] = (catalog?.hardware.redundancy as Redundancy[]) ?? [
    "none",
    "active-passive",
    "active-active",
  ];

  return (
    <section style={sectionStyle}>
      <Grid>
        <Field label="Workload profile" required>
          <Select
            value={hw.workloadProfile ?? null}
            disabled={locked}
            onChange={(v) => setHardware({ workloadProfile: v })}
            options={WORKLOAD_OPTIONS}
          />
        </Field>
        <Field label="Expected concurrent users" required>
          <NumberInput
            value={hw.expectedConcurrentUsers ?? null}
            disabled={locked}
            min={1}
            onChange={(v) => setHardware({ expectedConcurrentUsers: v })}
          />
        </Field>
        <Field label="CPU cores" required>
          <NumberInput
            value={hw.cpuCores ?? null}
            disabled={locked}
            min={1}
            max={256}
            onChange={(v) => setHardware({ cpuCores: v })}
          />
        </Field>
        <Field
          label="RAM (GB)"
          required
          hint={ramHint(hw.workloadProfile ?? null, hw.cpuCores ?? null, hw.ramGb ?? null)}
        >
          <NumberInput
            value={hw.ramGb ?? null}
            disabled={locked}
            min={1}
            onChange={(v) => setHardware({ ramGb: v })}
          />
        </Field>
        <Field label="Primary storage (GB)" required>
          <NumberInput
            value={hw.primaryStorageGb ?? null}
            disabled={locked}
            min={1}
            onChange={(v) => setHardware({ primaryStorageGb: v })}
          />
        </Field>
      </Grid>

      {showProposal && (
        <>
          <h4 style={headingStyle}>Proposal</h4>
          <Grid>
            <Field label="Storage type" required>
              <Select
                value={hw.storageType ?? null}
                disabled={locked}
                onChange={(v) => setHardware({ storageType: v })}
                options={storageTypes.map((t) => ({ value: t, label: t }))}
              />
            </Field>
            <Field
              label="RAID level"
              required
              hint={hw.storageType ? null : "Pick a storage type to enable RAID."}
            >
              <Select
                value={hw.raidLevel ?? null}
                disabled={locked || !hw.storageType}
                onChange={(v) => setHardware({ raidLevel: v })}
                options={raidLevels.map((r) => ({ value: r, label: r }))}
              />
            </Field>
            <Field label="Network bandwidth (Gbps)" required>
              <Select
                value={hw.networkBandwidthGbps ?? null}
                disabled={locked}
                onChange={(v) => setHardware({ networkBandwidthGbps: v })}
                options={bandwidths.map((b) => ({ value: b, label: `${b} Gbps` }))}
              />
            </Field>
            <Field label="GPU" required>
              <Checkbox
                value={hw.gpuRequired}
                disabled={locked}
                onChange={(v) => setHardware({ gpuRequired: v })}
                label="GPU required"
              />
            </Field>
            {hw.gpuRequired ? (
              <>
                <Field label="GPU model" required>
                  <TextInput
                    value={hw.gpuModel ?? ""}
                    disabled={locked}
                    onChange={(v) => setHardware({ gpuModel: v })}
                  />
                </Field>
                <Field label="GPU VRAM (GB)" required>
                  <NumberInput
                    value={hw.gpuVramGb ?? null}
                    disabled={locked}
                    min={1}
                    onChange={(v) => setHardware({ gpuVramGb: v })}
                  />
                </Field>
              </>
            ) : null}
          </Grid>
        </>
      )}

      {showProvisioning && (
        <>
          <h4 style={headingStyle}>Provisioning</h4>
          <Grid>
            <Field label="Redundancy / HA" required>
              <Select
                value={hw.redundancy ?? null}
                disabled={locked}
                onChange={(v) => setHardware({ redundancy: v })}
                options={redundancy.map((r) => ({ value: r, label: r }))}
              />
            </Field>
            <Field label="Rack units (U)" required>
              <NumberInput
                value={hw.rackUnits ?? null}
                disabled={locked}
                min={1}
                max={20}
                onChange={(v) => setHardware({ rackUnits: v })}
              />
            </Field>
            <Field label="Power draw (W)" required>
              <NumberInput
                value={hw.powerDrawWatts ?? null}
                disabled={locked}
                min={0}
                onChange={(v) => setHardware({ powerDrawWatts: v })}
              />
            </Field>
          </Grid>
        </>
      )}
    </section>
  );
}

const sectionStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "1rem",
};
const headingStyle: React.CSSProperties = {
  margin: "0.5rem 0 0",
  fontSize: "0.95rem",
  color: "#333",
  borderBottom: "1px solid #eee",
  paddingBottom: "0.25rem",
};

function Grid({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        gap: "0.75rem",
      }}
    >
      {children}
    </div>
  );
}
