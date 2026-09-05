/**
 * Verification indicator shown after any image sourced from the internet.
 *
 * Fixed format, per spec:
 *   SIMILARITY   98.06%
 *   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━●━━
 *   HIGH CONFIDENCE
 *
 * The bar is a 33-cell monospace track; the ● sits at the cell corresponding to
 * the score. Drawn with text glyphs rather than a styled div so it stays exactly
 * on the monospace grid and carries no gradient, glow or rounded fill.
 */

const TRACK = 33;

function band(score: number, threshold: number) {
  if (score >= 0.75) return { label: "HIGH CONFIDENCE", cls: "chip-ok" };
  if (score >= threshold) return { label: "MODERATE CONFIDENCE", cls: "chip-warn" };
  return { label: "BELOW THRESHOLD", cls: "chip-bad" };
}

export function SimilarityMeter({
  score,
  threshold = 0.4,
  compact = false,
}: {
  score: number | null | undefined;
  threshold?: number;
  compact?: boolean;
}) {
  if (score === null || score === undefined) {
    return (
      <div className="sim">
        <div className="sim-head">
          <span className="sim-label">similarity</span>
          <span className="sim-value">—</span>
        </div>
        {!compact && (
          <div className="sim-track" aria-hidden="true">
            {"━".repeat(TRACK)}
          </div>
        )}
        <span className="sim-band">not scored</span>
      </div>
    );
  }

  const pct = Math.max(0, Math.min(1, score));
  const dot = Math.round(pct * (TRACK - 1));
  const bar = "━".repeat(dot) + "●" + "━".repeat(TRACK - 1 - dot);
  const { label, cls } = band(score, threshold);

  return (
    <div className="sim">
      <div className="sim-head">
        <span className="sim-label">similarity</span>
        <span className="sim-value">{(pct * 100).toFixed(2)}%</span>
      </div>
      {!compact && (
        <div
          className="sim-track"
          role="meter"
          aria-valuenow={Number((pct * 100).toFixed(2))}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="similarity to the input face"
        >
          {bar}
        </div>
      )}
      <span className={`chip ${cls} sim-band`}>{label}</span>
    </div>
  );
}
