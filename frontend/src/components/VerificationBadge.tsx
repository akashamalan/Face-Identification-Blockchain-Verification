interface Props {
  verified: boolean;
  status: string;
  localFingerprint: string;
  onChainFingerprint: string;
  transactionHash: string;
  recordId?: string;
}

export function VerificationBadge({
  verified,
  status,
  localFingerprint,
  onChainFingerprint,
  transactionHash,
  recordId,
}: Props) {
  return (
    <div className="panel panel-lg p-4 animate-slide-down">
      <div className="flex items-center gap-3 mb-4">
        <span className={`chip ${verified ? "chip-ok" : "chip-bad"}`}>
          {status}
        </span>
        <span className="eyebrow">
          {verified
            ? "recomputed hash matches the chain"
            : "recomputed hash differs from the chain"}
        </span>
      </div>

      <dl className="grid gap-2" style={{ gridTemplateColumns: "7.5rem 1fr" }}>
        <dt className="eyebrow pt-0.5">local</dt>
        <dd className="mono-break m-0">{localFingerprint || "—"}</dd>

        <dt className="eyebrow pt-0.5">on-chain</dt>
        <dd className="mono-break m-0">{onChainFingerprint || "—"}</dd>

        {recordId && (
          <>
            <dt className="eyebrow pt-0.5">record id</dt>
            <dd className="mono-break m-0">{recordId}</dd>
          </>
        )}

        <dt className="eyebrow pt-0.5">tx</dt>
        <dd className="mono-break m-0">{transactionHash || "—"}</dd>
      </dl>
    </div>
  );
}
