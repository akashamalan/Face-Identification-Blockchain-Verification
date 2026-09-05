import { useEffect, useState } from "react";
import type { HealthResponse } from "../types";
import { checkHealth } from "../services/api";

export function HealthStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    checkHealth().then(setHealth).catch(() => setError(true));
  }, []);

  if (error)
    return (
      <div className="flex items-center gap-2">
        <span className="chip chip-bad">backend offline</span>
      </div>
    );

  if (!health)
    return (
      <div className="flex items-center gap-2">
        <span className="chip">connecting…</span>
      </div>
    );

  const ok = health.status === "ok";

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className={`chip ${ok ? "chip-ok" : "chip-warn"}`}>
        {ok ? "all systems ready" : "degraded"}
      </span>
      {Object.entries(health.services).map(([k, v]) => (
        <span
          key={k}
          className={`chip ${
            v === "ready" || v === "configured" || v === "connected"
              ? ""
              : "chip-warn"
          }`}
        >
          {k}: {v}
        </span>
      ))}
      <span className="eyebrow">v{health.version}</span>
    </div>
  );
}
