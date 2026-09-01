import { useCallback, useState } from "react";
import { ImageUpload } from "./components/ImageUpload";
import { PipelineStage } from "./components/PipelineStage";
import { ResultCard } from "./components/ResultCard";
import { VerificationBadge } from "./components/VerificationBadge";
import { HealthStatus } from "./components/HealthStatus";
import { runPipeline } from "./services/api";
import type { PipelineResult, StageStatus } from "./types";

interface Stages {
  face: StageStatus;
  search: StageStatus;
  fingerprint: StageStatus;
  blockchain: StageStatus;
  verification: StageStatus;
}

const INITIAL_STAGES: Stages = {
  face: "idle",
  search: "idle",
  fingerprint: "idle",
  blockchain: "idle",
  verification: "idle",
};

export default function App() {
  const [stages, setStages] = useState<Stages>(INITIAL_STAGES);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const updateStage = (key: keyof Stages, status: StageStatus) =>
    setStages((prev) => ({ ...prev, [key]: status }));

  const handleRun = useCallback(async (file: File) => {
    setRunning(true);
    setResult(null);
    setError(null);
    setStages(INITIAL_STAGES);

    // Animate stages sequentially for UX feedback
    const stageKeys: (keyof Stages)[] = [
      "face", "search", "fingerprint", "blockchain", "verification",
    ];

    // Set first stage to running
    updateStage("face", "running");

    try {
      const res = await runPipeline(file);

      if (!res.success || !res.data) {
        throw new Error(res.error?.message || "Pipeline failed");
      }

      const data = res.data;

      // Animate through stages based on what we got back
      for (const key of stageKeys) {
        updateStage(key, "success");
        await new Promise((r) => setTimeout(r, 200));
      }

      // Check for pipeline-level errors
      if (data.status === "error") {
        setError(data.error || "Pipeline failed");
        // Mark the failed stage
        if (!data.face.face_detected) updateStage("face", "error");
        else if (!data.search.selected_result) updateStage("search", "error");
        else if (!data.fingerprint.value) updateStage("fingerprint", "error");
        else if (!data.blockchain.transaction_hash) updateStage("blockchain", "error");
        else updateStage("verification", "error");
      }

      setResult(data);
    } catch (err: any) {
      const msg = err?.message || "An unexpected error occurred";
      setError(msg);

      // Mark first incomplete stage as error
      setStages((prev) => {
        const updated = { ...prev };
        for (const key of stageKeys) {
          if (updated[key] === "running" || updated[key] === "idle") {
            updated[key] = "error";
            break;
          }
        }
        return updated;
      });
    } finally {
      setRunning(false);
    }
  }, []);

  return (
    <div className="min-h-screen bg-dark-900">
      {/* Background gradient */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/3 w-[500px] h-[500px] bg-accent-purple/5 rounded-full blur-[120px]" />
        <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-accent-cyan/5 rounded-full blur-[120px]" />
      </div>

      <div className="relative max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <header className="text-center mb-10">
          <h1 className="text-3xl font-bold gradient-text mb-2">
            Hacker House Goa — Face Verification Pipeline
          </h1>
          <p className="text-gray-500 text-sm mb-4">
            Face Scan → Detection → Web Search → Fingerprint → Blockchain → Verification
          </p>
          <HealthStatus />
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Upload + Pipeline Stages */}
          <div className="space-y-6">
            <section>
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                1 · Upload Face Image
              </h2>
              <ImageUpload onFileSelected={handleRun} disabled={running} />
            </section>

            <section>
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                2 · Pipeline Progress
              </h2>
              <div className="glass-card p-5 space-y-1">
                <PipelineStage
                  label="Face Detection"
                  status={stages.face}
                  detail={result?.face.face_detected ? `${result.face.face_count} face · ${result.face.confidence.toFixed(2)} confidence · ${result.face.processing_time_ms}ms` : undefined}
                />
                <PipelineStage
                  label="Web / Social Search"
                  status={stages.search}
                  detail={result?.search.selected_result ? `${result.search.results_found} results · ${result.search.search_time_ms}ms` : undefined}
                />
                <PipelineStage
                  label="SHA-256 Fingerprint"
                  status={stages.fingerprint}
                  detail={result?.fingerprint.value ? `${result.fingerprint.value.slice(0, 24)}…` : undefined}
                />
                <PipelineStage
                  label="Blockchain Record"
                  status={stages.blockchain}
                  detail={result?.blockchain.transaction_hash ? `Block #${result.blockchain.block_number} · ${result.blockchain.submission_time_ms}ms` : undefined}
                />
                <PipelineStage
                  label="Verification"
                  status={stages.verification}
                  detail={result?.verification.status}
                  isLast
                />
              </div>
            </section>

            {/* Timing */}
            {result && result.total_time_ms > 0 && (
              <div className="text-xs text-gray-500 text-center">
                Total pipeline time: {(result.total_time_ms / 1000).toFixed(1)}s
              </div>
            )}
          </div>

          {/* Right: Results */}
          <div className="space-y-6">
            {/* Error */}
            {error && (
              <div className="glass-card p-4 border-accent-red/30 animate-slide-down">
                <p className="text-accent-red text-sm font-medium">Error</p>
                <p className="text-gray-400 text-xs mt-1">{error}</p>
              </div>
            )}

            {/* Search Result */}
            {result?.search.selected_result && (
              <section>
                <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                  3 · Discovered Result
                </h2>
                <ResultCard result={result.search.selected_result} />
              </section>
            )}

            {/* Fingerprint */}
            {result?.fingerprint.value && (
              <section className="animate-slide-down">
                <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                  4 · Fingerprint
                </h2>
                <div className="glass-card p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-accent-purple/15 text-accent-purple">
                      {result.fingerprint.algorithm}
                    </span>
                  </div>
                  <code className="text-xs text-gray-300 break-all leading-relaxed">
                    {result.fingerprint.value}
                  </code>
                </div>
              </section>
            )}

            {/* Blockchain */}
            {result?.blockchain.transaction_hash && (
              <section className="animate-slide-down">
                <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                  5 · Blockchain Transaction
                </h2>
                <div className="glass-card p-4 space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Network</span>
                    <span className="text-accent-cyan">{result.blockchain.network}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Block</span>
                    <span className="text-gray-300">#{result.blockchain.block_number}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">TX Hash</span>
                    <code className="block text-gray-300 mt-1 truncate bg-dark-800/50 px-2 py-1 rounded">
                      {result.blockchain.transaction_hash}
                    </code>
                  </div>
                  {result.blockchain.explorer_url && (
                    <a
                      href={result.blockchain.explorer_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent-cyan hover:underline block"
                    >
                      View on Etherscan ↗
                    </a>
                  )}
                </div>
              </section>
            )}

            {/* Verification */}
            {result?.verification.status && result.verification.status !== "PENDING" && (
              <section>
                <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                  6 · Verification Result
                </h2>
                <VerificationBadge
                  verified={result.verification.verified}
                  status={result.verification.status}
                  localFingerprint={result.verification.local_fingerprint}
                  onChainFingerprint={result.verification.on_chain_fingerprint}
                  transactionHash={result.verification.transaction_hash}
                />
              </section>
            )}
          </div>
        </div>

        {/* Footer */}
        <footer className="text-center text-xs text-gray-600 mt-12 pb-4">
          <p>Hacker House Goa 2026 · Task 3 · Face Verification Pipeline</p>
          <p className="mt-1">
            This is a demonstration system. Only publicly available content is processed.
          </p>
        </footer>
      </div>
    </div>
  );
}
