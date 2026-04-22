import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { Catalog, CompatibilityMatrix, Stage } from "@/schema/record";

export function useCatalog(stage?: Stage) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .catalog(stage)
      .then((c) => alive && setCatalog(c))
      .catch((e) => alive && setError(e));
    return () => {
      alive = false;
    };
  }, [stage]);

  return { catalog, error };
}

export function useCompatibility() {
  const [matrix, setMatrix] = useState<CompatibilityMatrix | null>(null);
  useEffect(() => {
    let alive = true;
    api.compatibility().then((m) => alive && setMatrix(m));
    return () => {
      alive = false;
    };
  }, []);
  return matrix;
}
