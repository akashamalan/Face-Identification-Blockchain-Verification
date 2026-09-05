import type { SearchResult } from "../types";
import { SimilarityMeter } from "./SimilarityMeter";

export function ResultCard({
  result,
  threshold = 0.4,
}: {
  result: SearchResult;
  threshold?: number;
}) {
  return (
    <div className="panel p-4 animate-slide-down">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 style={{ fontSize: "var(--text-xl2)" }} className="truncate">
            {result.title || "Untitled result"}
          </h3>
          {result.snippet && (
            <p
              className="m-0 mt-1 text-[0.75rem] truncate"
              style={{ color: "var(--color-muted-fg)" }}
            >
              {result.snippet}
            </p>
          )}
        </div>
        {result.thumbnail && (
          <img
            src={result.thumbnail}
            alt={`Matched image from ${result.domain || "the discovered result"}`}
            className="w-16 h-16 img-thumb shrink-0"
            style={{ objectFit: "cover" }}
          />
        )}
      </div>

      <div className="flex flex-wrap gap-2 mt-3">
        {result.domain && <span className="chip">{result.domain}</span>}
        {result.platform && <span className="chip">{result.platform}</span>}
      </div>

      {/* verification indicator — this image came from the internet */}
      <SimilarityMeter score={result.similarity} threshold={threshold} />

      {result.match_reason && (
        <p className="eyebrow m-0 mt-2" style={{ letterSpacing: "0.08em" }}>
          {result.match_reason}
        </p>
      )}

      <a
        href={result.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mono-break block mt-3 underline"
      >
        {result.url}
      </a>
    </div>
  );
}
