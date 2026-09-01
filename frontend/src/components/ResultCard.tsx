import type { SearchResult } from "../types";

interface Props {
  result: SearchResult;
}

export function ResultCard({ result }: Props) {
  return (
    <div className="glass-card p-5 animate-slide-down space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-200 truncate text-sm">
            {result.title || "Untitled Result"}
          </h3>
          <p className="text-xs text-gray-400 mt-1 truncate">{result.snippet}</p>
        </div>
        {result.thumbnail && (
          <img
            src={result.thumbnail}
            alt=""
            className="w-14 h-14 rounded-lg object-cover border border-glass-border flex-shrink-0"
          />
        )}
      </div>

      <div className="flex flex-wrap gap-2 text-xs">
        <span className="px-2 py-1 rounded-full bg-accent-blue/15 text-accent-blue">
          {result.domain}
        </span>
        {result.platform && (
          <span className="px-2 py-1 rounded-full bg-accent-purple/15 text-accent-purple">
            {result.platform}
          </span>
        )}
        <span className="px-2 py-1 rounded-full bg-glass-white text-gray-400">
          Search result
        </span>
      </div>

      <a
        href={result.url}
        target="_blank"
        rel="noopener noreferrer"
        className="block text-xs text-accent-cyan hover:underline truncate"
      >
        {result.url}
      </a>
    </div>
  );
}
