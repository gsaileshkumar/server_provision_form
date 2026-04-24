import { create } from "zustand";
import { api } from "@/api/client";
import type { Application, Hardware, Record as ApiRecord, SoftwareOS } from "@/schema/record";

interface RecordState {
  record: ApiRecord | null;
  loading: boolean;
  dirty: boolean;
  error: string | null;
  load: (id: string) => Promise<void>;
  setHardware: (patch: Partial<Hardware>) => void;
  setSoftwareOS: (patch: Partial<SoftwareOS>) => void;
  setApplications: (apps: Application[]) => void;
  setRecordName: (name: string) => void;
  save: () => Promise<void>;
  reset: () => void;
}

export const useRecordStore = create<RecordState>((set, get) => ({
  record: null,
  loading: false,
  dirty: false,
  error: null,
  async load(id) {
    set({ loading: true, error: null });
    try {
      const rec = await api.getRecord(id);
      set({ record: rec, loading: false, dirty: false });
    } catch (e) {
      set({ loading: false, error: String(e) });
    }
  },
  setHardware(patch) {
    const r = get().record;
    if (!r) return;
    set({
      record: { ...r, hardware: { ...r.hardware, ...patch } },
      dirty: true,
    });
  },
  setSoftwareOS(patch) {
    const r = get().record;
    if (!r) return;
    set({
      record: { ...r, softwareOS: { ...r.softwareOS, ...patch } },
      dirty: true,
    });
  },
  setApplications(apps) {
    const r = get().record;
    if (!r) return;
    set({ record: { ...r, applications: apps }, dirty: true });
  },
  setRecordName(name) {
    const r = get().record;
    if (!r) return;
    set({ record: { ...r, recordName: name }, dirty: true });
  },
  async save() {
    const r = get().record;
    if (!r?._id) return;
    try {
      const updated = await api.patchRecord(r._id, {
        recordName: r.recordName,
        hardware: r.hardware,
        softwareOS: r.softwareOS,
        applications: r.applications,
      });
      set({ record: updated, dirty: false, error: null });
    } catch (e) {
      set({ error: String(e) });
    }
  },
  reset() {
    set({ record: null, dirty: false, error: null });
  },
}));
