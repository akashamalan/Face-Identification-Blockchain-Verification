import { useEffect, useState } from "react";
import type { HealthResponse } from "../types";
import { checkHealth } from "../services/api";

export function HealthStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <div className="flex items-center gap-2 text-xs text-accent-red">
        <span className="w-2 h-2 rounded-full bg-accent-red" />
        Backend offline
      </div>
    );
  }

  if (!health) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span className="w-2 h-2 rounded-full bg-gray-500 animate-pulse" />
        Connecting…
      </div>
    );
  }

  const allGood = health.status === "ok";

  return (
    <div className="flex items-center gap-3 text-xs">
      <div className={`flex items-center gap-1.5 ${allGood ? "text-accent-green" : "text-accent-amber"}`}>
        <span className={`w-2 h-2 rounded-full ${allGood ? "bg-accent-green" : "bg-accent-amber"}`} />
        {health.status === "ok" ? "All systems ready" : "Degraded"}
      </div>
      {Object.entries(health.services).map(([key, val]) => (
        <span
          key={key}
          className={`px-2 py-0.5 rounded-full ${
            val === "ready" || val === "configured" || val === "connected"
              ? "bg-accent-green/10 text-accent-green"
              : "bg-accent-amber/10 text-accent-amber"
          }`}
        >
          {key}: {val}
        </span>
      ))}
      <span className="text-gray-600">v{health.version}</span>
    </div>
  );
}
