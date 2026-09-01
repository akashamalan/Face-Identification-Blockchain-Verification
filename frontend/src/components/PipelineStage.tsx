import type { StageStatus } from "../types";

interface Props {
  label: string;
  status: StageStatus;
  detail?: string;
  isLast?: boolean;
}

export function PipelineStage({ label, status, detail, isLast }: Props) {
  const icon = {
    idle: "○",
    running: "◌",
    success: "✓",
    error: "✗",
  }[status];

  const colors = {
    idle: "text-gray-500 border-gray-600",
    running: "text-accent-cyan border-accent-cyan animate-pulse-glow",
    success: "text-accent-green border-accent-green",
    error: "text-accent-red border-accent-red",
  }[status];

  const bgColors = {
    idle: "",
    running: "bg-accent-cyan/10",
    success: "bg-accent-green/10",
    error: "bg-accent-red/10",
  }[status];

  return (
    <div className="flex items-start gap-4">
      {/* Icon column */}
      <div className="flex flex-col items-center">
        <div
          className={`w-10 h-10 rounded-full border-2 flex items-center justify-center
            text-lg font-bold transition-all duration-500 ${colors} ${bgColors}`}
        >
          {status === "running" ? (
            <span className="animate-spin text-sm">⟳</span>
          ) : (
            icon
          )}
        </div>
        {!isLast && (
          <div className="connector-line h-8 mt-1" />
        )}
      </div>

      {/* Text column */}
      <div className="pt-2 flex-1 min-w-0">
        <p className={`font-semibold text-sm ${
          status === "success" ? "text-accent-green" :
          status === "error" ? "text-accent-red" :
          status === "running" ? "text-accent-cyan" :
          "text-gray-400"
        }`}>
          {label}
        </p>
        {detail && (
          <p className="text-xs text-gray-500 mt-0.5 truncate">{detail}</p>
        )}
      </div>
    </div>
  );
}
