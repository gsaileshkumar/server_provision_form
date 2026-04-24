import { useRecordStore } from "@/state/recordStore";
import { useCatalog } from "@/hooks/useCatalog";
import { Field, NumberInput, Select, TextInput } from "@/components/fields/Field";
import type {
  Application,
  ApplicationCategory,
  InstallSource,
  LicenseTier,
  Stage,
} from "@/schema/record";

const CATEGORY_OPTIONS: { value: ApplicationCategory; label: string }[] = [
  { value: "database", label: "Database" },
  { value: "web server", label: "Web server" },
  { value: "app runtime", label: "App runtime" },
  { value: "cache", label: "Cache" },
  { value: "message queue", label: "Message queue" },
  { value: "monitoring", label: "Monitoring" },
  { value: "custom", label: "Custom" },
];

export function ApplicationsTab({ stage, locked }: { stage: Stage; locked: boolean }) {
  const record = useRecordStore((s) => s.record);
  const setApplications = useRecordStore((s) => s.setApplications);
  const { catalog } = useCatalog(stage);
  if (!record) return null;
  const apps = record.applications;

  const showProposal = stage === "proposal" || stage === "provisioning";
  const showProvisioning = stage === "provisioning";

  const addApp = () => setApplications([...apps, {}]);
  const removeApp = (idx: number) =>
    setApplications(apps.filter((_, i) => i !== idx));
  const updateApp = (idx: number, patch: Partial<Application>) =>
    setApplications(apps.map((a, i) => (i === idx ? { ...a, ...patch } : a)));

  return (
    <section style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {apps.map((app, idx) => {
        const availableApps =
          catalog?.applications.filter((a) => a.category === app.category) ?? [];
        const catalogApp = catalog?.applications.find((a) => a.name === app.name);
        return (
          <div key={idx} style={cardStyle}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong>Application {idx + 1}</strong>
              {!locked && (
                <button onClick={() => removeApp(idx)} style={linkButton}>
                  Remove
                </button>
              )}
            </div>
            <Grid>
              <Field label="Category" required>
                <Select<ApplicationCategory>
                  value={app.category ?? null}
                  disabled={locked}
                  options={CATEGORY_OPTIONS}
                  onChange={(v) =>
                    updateApp(idx, { category: v, name: null, version: null, edition: null })
                  }
                />
              </Field>
              <Field label="Application" required>
                <Select
                  value={app.name ?? null}
                  disabled={locked || !app.category}
                  options={availableApps.map((a) => ({ value: a.name, label: a.label }))}
                  onChange={(v) =>
                    updateApp(idx, { name: v, version: null, edition: null })
                  }
                />
              </Field>
              {showProposal && (
                <>
                  <Field label="Version" required>
                    <Select
                      value={app.version ?? null}
                      disabled={locked || !catalogApp}
                      options={
                        catalogApp?.availableVersions.map((v) => ({
                          value: v,
                          label: v,
                        })) ?? []
                      }
                      onChange={(v) => updateApp(idx, { version: v })}
                    />
                  </Field>
                  <Field label="Edition" required>
                    <Select<LicenseTier>
                      value={app.edition ?? null}
                      disabled={locked || !catalogApp}
                      options={
                        (catalogApp?.availableEditions as LicenseTier[] | undefined)?.map(
                          (e) => ({ value: e, label: e }),
                        ) ?? [
                          { value: "Community", label: "Community" },
                          { value: "Enterprise", label: "Enterprise" },
                        ]
                      }
                      onChange={(v) => updateApp(idx, { edition: v })}
                    />
                  </Field>
                  <Field label="Expected data volume (GB)" required>
                    <NumberInput
                      value={app.expectedDataVolumeGb ?? null}
                      disabled={locked}
                      min={0}
                      onChange={(v) => updateApp(idx, { expectedDataVolumeGb: v })}
                    />
                  </Field>
                </>
              )}
              {showProvisioning && (
                <>
                  <Field label="HA config" required>
                    <TextInput
                      value={app.haConfig ?? ""}
                      disabled={locked}
                      onChange={(v) => updateApp(idx, { haConfig: v })}
                      placeholder="e.g. primary/replica, sharded"
                    />
                  </Field>
                  <Field label="Install source" required>
                    <Select<InstallSource>
                      value={app.installSource ?? null}
                      disabled={locked}
                      options={[
                        { value: "package manager", label: "Package manager" },
                        { value: "binary", label: "Binary" },
                        { value: "container image", label: "Container image" },
                        { value: "custom URL", label: "Custom URL" },
                      ]}
                      onChange={(v) => updateApp(idx, { installSource: v })}
                    />
                  </Field>
                </>
              )}
            </Grid>
          </div>
        );
      })}
      {!locked && (
        <button onClick={addApp} style={buttonStyle}>
          + Add application
        </button>
      )}
    </section>
  );
}

const cardStyle: React.CSSProperties = {
  border: "1px solid #ddd",
  borderRadius: 6,
  padding: "0.75rem 1rem",
  background: "white",
  display: "flex",
  flexDirection: "column",
  gap: "0.75rem",
};
const buttonStyle: React.CSSProperties = {
  padding: "0.5rem 1rem",
  background: "#2e5f8a",
  color: "white",
  border: "none",
  borderRadius: 4,
  cursor: "pointer",
  alignSelf: "flex-start",
};
const linkButton: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "#c33",
  cursor: "pointer",
  fontSize: "0.85rem",
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
