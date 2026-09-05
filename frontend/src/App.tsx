import { useCallback, useState } from "react";
import { ImageUpload } from "./components/ImageUpload";
import { PipelineStage } from "./components/PipelineStage";
import { ResultCard } from "./components/ResultCard";
import { VerificationBadge } from "./components/VerificationBadge";
import { HealthStatus } from "./components/HealthStatus";
import { SimilarityMeter } from "./components/SimilarityMeter";
import { PalmMark, HandRule, HackerHouseWordmark } from "./components/Marks";
import { runPipeline } from "./services/api";
import type { PipelineResult, SearchResult, StageStatus } from "./types";

interface Stages {
  face: StageStatus;
  search: StageStatus;
  matching: StageStatus;
  fingerprint: StageStatus;
  blockchain: StageStatus;
  verification: StageStatus;
}

const INITIAL_STAGES: Stages = {
  face: "idle",
  search: "idle",
  matching: "idle",
  fingerprint: "idle",
  blockchain: "idle",
  verification: "idle",
};

const STAGE_KEYS: (keyof Stages)[] = [
  "face",
  "search",
  "matching",
  "fingerprint",
  "blockchain",
  "verification",
];

export default function App() {
  const [stages, setStages] = useState<Stages>(INITIAL_STAGES);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [activeResult, setActiveResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const handleRun = useCallback(async (file: File) => {
    setRunning(true);
    setResult(null);
    setActiveResult(null);
    setError(null);
    setNotice(null);
    setStages({ ...INITIAL_STAGES, face: "running" });

    try {
      const res = await runPipeline(file);
      if (!res.success || !res.data)
        throw new Error(res.error?.message || "Pipeline failed");

      const data = res.data;

      if (data.status === "no_confident_match") {
        setStages({
          ...INITIAL_STAGES,
          face: "success",
          search: "success",
          matching: "error",
        });
        setNotice(data.error || "No confident match.");
        setResult(data);
        return;
      }

      if (data.status === "error") {
        setStages((prev) => {
          const next = { ...prev };
          if (!data.face.face_detected) next.face = "error";
          else if (!data.search.results.length) next.search = "error";
          else if (data.matching?.selected_position === null)
            next.matching = "error";
          else if (!data.fingerprint.value) next.fingerprint = "error";
          else if (!data.blockchain.transaction_hash) next.blockchain = "error";
          else next.verification = "error";
          return next;
        });
        setError(data.error || "Pipeline failed");
        setResult(data);
        return;
      }

      setStages({
        face: "success",
        search: "success",
        matching: "success",
        fingerprint: "success",
        blockchain: "success",
        verification: "success",
      });
      setResult(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unexpected error";
      setError(msg);
      setStages((prev) => {
        const next = { ...prev };
        for (const k of STAGE_KEYS) {
          if (next[k] === "running" || next[k] === "idle") {
            next[k] = "error";
            break;
          }
        }
        return next;
      });
    } finally {
      setRunning(false);
    }
  }, []);

  const m = result?.matching;

  return (
    <div className="max-w-6xl mx-auto px-5 py-8" style={{ backgroundColor: "var(--color-bg)", minHeight: "100vh" }}>
      <header className="pb-4 mb-8" style={{ borderBottom: "2px solid var(--color-fg)" }}>
        <div className="brand-lockup">
          <HackerHouseWordmark />
          <p className="task-three">Task 3</p>
        </div>

        <h1
          style={{
            fontSize: "var(--text-4xl2)",
            fontVariationSettings: '"opsz" 100',
            lineHeight: 1.06,
          }}
          className="mt-3 mb-4"
        >
          Face Verification
          <br />
          Pipeline
        </h1>
        <p
          className="eyebrow m-0 mb-4"
          style={{ letterSpacing: "0.1em", color: "var(--color-fg)" }}
        >
          face → search → re-encode &amp; score → fingerprint → chain → read-back
        </p>
        <HealthStatus />
      </header>

      <div className="grid gap-8 lg:grid-cols-2 split-rule">
        <div className="flex flex-col gap-6 min-w-0">
          <section>
            <p className="eyebrow mb-2">1 · upload face image</p>
            <ImageUpload onFileSelected={handleRun} disabled={running} />
          </section>

          <section>
            <p className="eyebrow mb-2">2 · pipeline</p>
            <div className="panel p-5">
              <PipelineStage
                label="Face detection"
                status={stages.face}
                detail={
                  result?.face.face_detected
                    ? `${result.face.engine} · ${result.face.face_count} face · det_score ${result.face.det_score.toFixed(3)} · ${result.face.processing_time_ms}ms`
                    : undefined
                }
              />
              <PipelineStage
                label="Web / social search"
                status={stages.search}
                detail={
                  result?.search.results_found
                    ? `${result.search.results_found} results · ${result.search.search_time_ms}ms`
                    : undefined
                }
              />
              <PipelineStage
                label="Face match — re-encode &amp; score"
                status={stages.matching}
                detail={
                  m && m.candidates_total > 0
                    ? `${m.candidates_scored}/${m.candidates_total} scored · best ${
                        m.best_similarity !== null
                          ? m.best_similarity.toFixed(4)
                          : "n/a"
                      } · thr ${m.threshold.toFixed(2)} · ${m.matching_time_ms}ms`
                    : undefined
                }
              />
              <PipelineStage
                label="SHA-256 fingerprint"
                status={stages.fingerprint}
                detail={
                  result?.fingerprint.value
                    ? `${result.fingerprint.value.slice(0, 32)}…`
                    : undefined
                }
              />
              <PipelineStage
                label="Blockchain record"
                status={stages.blockchain}
                detail={
                  result?.blockchain.transaction_hash
                    ? `${result.blockchain.network} · block #${result.blockchain.block_number} · ${result.blockchain.submission_time_ms}ms`
                    : undefined
                }
              />
              <PipelineStage
                label="Read-back &amp; verify"
                status={stages.verification}
                detail={result?.verification.status}
                isLast
              />
            </div>

            {result && result.total_time_ms > 0 && (
              <p className="eyebrow mt-3 m-0">
                total {(result.total_time_ms / 1000).toFixed(1)}s
              </p>
            )}
          </section>
        </div>

        <div className="flex flex-col gap-6 min-w-0">
          {error && (
            <div
              className="panel p-4 animate-slide-down"
              style={{ borderColor: "var(--color-danger)" }}
            >
              <span className="chip chip-bad">error</span>
              <p className="mono-break m-0 mt-2">{error}</p>
            </div>
          )}

          {notice && (
            <div className="panel p-4 animate-slide-down">
              <span className="chip chip-warn">no confident match</span>
              <p className="mono-break m-0 mt-2">{notice}</p>
              <p className="eyebrow m-0 mt-2" style={{ letterSpacing: "0.08em" }}>
                candidates were found but none scored above the measured
                threshold. nothing was registered on-chain — a visual lookalike
                is not an identity match.
              </p>
            </div>
          )}

          {result?.search.selected_result && (
            <section>
              <div className="flex items-baseline justify-between gap-3 mb-2">
                <p className="eyebrow m-0">3 · matched result</p>
                <span className="eyebrow">
                  {result.search.results_found} candidates
                </span>
              </div>
              <ResultCard
                result={activeResult || result.search.selected_result}
                threshold={m ? m.threshold : 0.4}
              />

              {result.search.results.length > 1 && (
                <details className="panel p-3 mt-3">
                  <summary className="eyebrow cursor-pointer">
                    view all {result.search.results.length} candidates
                  </summary>
                  <div className="mt-3 max-h-60 overflow-y-auto pr-1 flex flex-col gap-1">
                    {result.search.results.map((item, idx) => (
                      <button
                        key={idx}
                        onClick={() => setActiveResult(item)}
                        className="text-left p-2 panel-flat"
                        style={{
                          background:
                            (activeResult?.url ||
                              result.search.selected_result?.url) === item.url
                              ? "var(--color-muted)"
                              : "var(--color-bg)",
                        }}
                      >
                        <span className="mono-break block truncate">
                          {item.title || item.domain}
                        </span>
                        <SimilarityMeter
                          score={item.similarity}
                          threshold={m ? m.threshold : 0.4}
                          compact
                        />
                      </button>
                    ))}
                  </div>
                </details>
              )}
            </section>
          )}

          {m && m.candidates_total > 0 && (
            <section>
              <p className="eyebrow mb-2">candidate audit bundle</p>
              <div className="panel p-4">
                <div className="flex justify-between mb-2">
                  <span className="eyebrow">threshold</span>
                  <span className="mono-break">{m.threshold.toFixed(3)}</span>
                </div>
                <p className="eyebrow m-0">bundle sha-256</p>
                <p className="mono-break m-0 mb-3">{m.audit_bundle_sha256}</p>

                <div className="max-h-64 overflow-y-auto flex flex-col gap-1">
                  {m.candidates.map((c) => (
                    <div
                      key={c.position}
                      className="aud-row"
                      data-decision={c.decision}
                    >
                      <span style={{ color: "var(--color-muted-fg)" }}>
                        #{c.position}
                      </span>
                      <span>
                        {c.similarity !== null ? c.similarity.toFixed(4) : "—"}
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate">{c.domain}</span>
                        <span
                          className="block truncate"
                          style={{ color: "var(--color-muted-fg)" }}
                        >
                          {c.reason}
                        </span>
                      </span>
                    </div>
                  ))}
                </div>

                <p className="eyebrow m-0 mt-3" style={{ letterSpacing: "0.08em" }}>
                  all {m.candidates_total} candidates in search order, each with
                  its score and decision. this digest is inside the on-chain
                  fingerprint — reordering or dropping any candidate changes it.
                </p>
              </div>
            </section>
          )}

          {result?.blockchain.transaction_hash && (
            <section>
              <p className="eyebrow mb-2">4 · blockchain record</p>
              <div className="panel p-4">
                <dl
                  className="grid gap-2"
                  style={{ gridTemplateColumns: "7.5rem 1fr" }}
                >
                  <dt className="eyebrow pt-0.5">network</dt>
                  <dd className="m-0 mono-break">
                    {result.blockchain.network}
                  </dd>
                  <dt className="eyebrow pt-0.5">block</dt>
                  <dd className="m-0 mono-break">
                    #{result.blockchain.block_number}
                  </dd>
                  <dt className="eyebrow pt-0.5">tx hash</dt>
                  <dd className="m-0 mono-break">
                    {result.blockchain.transaction_hash}
                  </dd>
                </dl>
                {result.blockchain.explorer_url && (
                  <a
                    href={result.blockchain.explorer_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mono-break underline block mt-3"
                  >
                    view on etherscan ↗
                  </a>
                )}
              </div>
            </section>
          )}

          {result?.verification.status &&
            result.verification.status !== "PENDING" && (
              <section>
                <p className="eyebrow mb-2">5 · verification</p>
                <VerificationBadge
                  verified={result.verification.verified}
                  status={result.verification.status}
                  localFingerprint={result.verification.local_fingerprint}
                  onChainFingerprint={result.verification.on_chain_fingerprint}
                  transactionHash={result.verification.transaction_hash}
                  recordId={result.verification.record_id}
                />
              </section>
            )}
        </div>
      </div>

      <footer className="foot-hh">
        <HandRule />
        <div className="foot-line">
          <span className="foot-mark">
            <PalmMark size={14} />
            4 days. one rhythm. everything intentional.
          </span>
          <span className="eyebrow">
            only publicly available content is processed
          </span>
        </div>
      </footer>
    </div>
  );
}
