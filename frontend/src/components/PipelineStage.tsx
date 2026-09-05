import type { StageStatus } from "../types";

interface Props {
  label: string;
  status: StageStatus;
  detail?: string;
  isLast?: boolean;
}

export function PipelineStage({ label, status, detail, isLast }: Props) {
  const glyph = { idle: "○", running: "▸", success: "✓", error: "✗" }[status];

  return (
    <div className="flex items-start gap-4">
      <div className="flex flex-col items-center self-stretch">
        <div
          className={`stage-node ${status === "running" ? "animate-pulse-glow" : ""}`}
          data-status={status}
        >
          {glyph}
        </div>
        {!isLast && <div className="connector-line flex-1 min-h-6 mt-1" />}
      </div>

      <div className="pt-1.5 flex-1 min-w-0 pb-4">
        <p className="text-[0.938rem] font-bold leading-tight">{label}</p>
        {detail && (
          <p
            className="mono-break mt-1"
            style={{ color: "var(--color-muted-fg)" }}
          >
            {detail}
          </p>
        )}
      </div>
    </div>
  );
}
