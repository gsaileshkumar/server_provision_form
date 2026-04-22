import { useRecordStore } from "@/state/recordStore";
import { useCatalog } from "@/hooks/useCatalog";
import { Field, Select, TextInput } from "@/components/fields/Field";
import type {
  HardeningProfile,
  LicensingModel,
  OSFamily,
  PatchingPolicy,
  Stage,
} from "@/schema/record";

export function SoftwareOSTab({ stage, locked }: { stage: Stage; locked: boolean }) {
  const record = useRecordStore((s) => s.record);
  const setSoftwareOS = useRecordStore((s) => s.setSoftwareOS);
  const { catalog } = useCatalog(stage);
  if (!record) return null;
  const os = record.softwareOS;
  const showProposal = stage === "proposal" || stage === "provisioning";
  const showProvisioning = stage === "provisioning";

  const familyEntry = catalog?.osFamilies.find((f) => f.family === os.osFamily);
  const distros = familyEntry?.distributions ?? [];
  const distroEntry = distros.find((d) => d.distribution === os.osDistribution);
  const versions = distroEntry?.versions ?? [];

  return (
    <section style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <Grid>
        <Field label="OS family" required>
          <Select<OSFamily>
            value={os.osFamily ?? null}
            disabled={locked}
            onChange={(v) => setSoftwareOS({ osFamily: v })}
            options={
              catalog?.osFamilies.map((f) => ({
                value: f.family as OSFamily,
                label: f.family,
              })) ?? []
            }
          />
        </Field>
        <Field label="OS distribution" required>
          <Select
            value={os.osDistribution ?? null}
            disabled={locked || !os.osFamily}
            onChange={(v) => setSoftwareOS({ osDistribution: v })}
            options={distros.map((d) => ({ value: d.distribution, label: d.label }))}
          />
        </Field>
        <Field label="OS version" required>
          <Select
            value={os.osVersion ?? null}
            disabled={locked || !os.osDistribution}
            onChange={(v) => setSoftwareOS({ osVersion: v })}
            options={versions.map((v) => ({ value: v.version, label: v.label }))}
          />
        </Field>
      </Grid>

      {showProposal && (
        <>
          <h4 style={headingStyle}>Proposal</h4>
          <Grid>
            <Field label="Licensing model" required>
              <Select<LicensingModel>
                value={os.licensingModel ?? null}
                disabled={locked}
                onChange={(v) => setSoftwareOS({ licensingModel: v })}
                options={[
                  { value: "BYOL", label: "BYOL" },
                  { value: "included", label: "Included" },
                  { value: "subscription", label: "Subscription" },
                ]}
              />
            </Field>
            <Field label="Patching policy" required>
              <Select<PatchingPolicy>
                value={os.patchingPolicy ?? null}
                disabled={locked}
                onChange={(v) => setSoftwareOS({ patchingPolicy: v })}
                options={[
                  { value: "auto", label: "Auto" },
                  { value: "manual", label: "Manual" },
                  { value: "scheduled", label: "Scheduled" },
                ]}
              />
            </Field>
          </Grid>
        </>
      )}

      {showProvisioning && (
        <>
          <h4 style={headingStyle}>Provisioning</h4>
          <Grid>
            <Field label="Hardening profile" required>
              <Select<HardeningProfile>
                value={os.hardeningProfile ?? null}
                disabled={locked}
                onChange={(v) => setSoftwareOS({ hardeningProfile: v })}
                options={[
                  { value: "none", label: "None" },
                  { value: "CIS", label: "CIS" },
                  { value: "custom", label: "Custom" },
                ]}
              />
            </Field>
            <Field label="Filesystem layout" required>
              <TextInput
                value={os.filesystemLayout ?? ""}
                disabled={locked}
                onChange={(v) => setSoftwareOS({ filesystemLayout: v })}
                placeholder="e.g. ext4 /, xfs /var"
              />
            </Field>
            <Field label="Timezone" required>
              <TextInput
                value={os.timezone ?? ""}
                disabled={locked}
                onChange={(v) => setSoftwareOS({ timezone: v })}
                placeholder="e.g. UTC"
              />
            </Field>
            <Field label="Locale" required>
              <TextInput
                value={os.locale ?? ""}
                disabled={locked}
                onChange={(v) => setSoftwareOS({ locale: v })}
                placeholder="e.g. en_US.UTF-8"
              />
            </Field>
          </Grid>
        </>
      )}
    </section>
  );
}

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
