import logoUrl from "../assets/hh-goa-logo.svg";

/**
 * The wordmark, used verbatim. The SVG file is byte-identical to the one supplied
 * and is referenced as an asset rather than inlined, so nothing can modify it.
 */
export function HHGoaMark({ height = 34 }: { height?: number }) {
  return (
    <img
      src={logoUrl}
      alt="HH GOA"
      height={height}
      style={{ height, width: "auto", display: "block" }}
    />
  );
}

/**
 * A small palm. Single-weight strokes, drawn by hand in path data — not a stock
 * illustration, and deliberately tiny enough to read as a mark rather than art.
 */
export function PalmMark({ size = 14 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={{ flexShrink: 0 }}
    >
      <path d="M12 22c0-5 .6-8.4 1.6-11" />
      <path d="M13.6 11C11.8 8.6 9 7.6 6.2 8.6" />
      <path d="M13.6 11c2.6-1.9 5.7-2 8.2-.4" />
      <path d="M13.6 11c-.6-2.9.3-5.6 2.3-7.4" />
      <path d="M13.6 11c-2.4.7-4.3 2.4-5.2 4.8" />
    </svg>
  );
}

/**
 * A restrained hand-drawn rule. One irregular stroke, no flourish — it exists to
 * separate, not to decorate.
 */
export function HandRule() {
  return (
    <svg
      viewBox="0 0 600 6"
      preserveAspectRatio="none"
      width="100%"
      height="6"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.3"
      strokeLinecap="round"
      aria-hidden="true"
      style={{ display: "block", opacity: 0.85 }}
    >
      <path d="M2 4.1C64 2.6 128 3.5 196 2.9c72-.6 140 1.4 210 .7 62-.6 122-1.3 192-.4" />
    </svg>
  );
}
