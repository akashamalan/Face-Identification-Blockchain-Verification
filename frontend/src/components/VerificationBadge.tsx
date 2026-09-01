interface Props {
  verified: boolean;
  status: string;
  localFingerprint: string;
  onChainFingerprint: string;
  transactionHash: string;
}

export function VerificationBadge({
  verified,
  status,
  localFingerprint,
  onChainFingerprint,
  transactionHash,
}: Props) {
  return (
    <div
      className={`glass-card p-6 text-center animate-slide-down ${
        verified ? "glow-green" : "glow-red"
      }`}
    >
      <div
        className={`text-5xl font-black tracking-wider mb-3 ${
          verified ? "text-accent-green" : "text-accent-red"
        }`}
      >
        {status}
      </div>

      <p className={`text-sm mb-4 ${verified ? "text-green-400" : "text-red-400"}`}>
        {verified
          ? "The data fingerprint matches the blockchain record."
          : "The data has been modified since it was recorded on the blockchain."}
      </p>

      <div className="space-y-2 text-left text-xs">
        <div className="flex gap-2">
          <span className="text-gray-500 w-28 flex-shrink-0">Local Hash</span>
          <code className="text-gray-300 truncate flex-1 bg-dark-800/50 px-2 py-1 rounded">
            {localFingerprint}
          </code>
        </div>
        <div className="flex gap-2">
          <span className="text-gray-500 w-28 flex-shrink-0">On-Chain Hash</span>
          <code className="text-gray-300 truncate flex-1 bg-dark-800/50 px-2 py-1 rounded">
            {onChainFingerprint}
          </code>
        </div>
        {transactionHash && (
          <div className="flex gap-2">
            <span className="text-gray-500 w-28 flex-shrink-0">TX Hash</span>
            <code className="text-gray-300 truncate flex-1 bg-dark-800/50 px-2 py-1 rounded">
              {transactionHash}
            </code>
          </div>
        )}
      </div>
    </div>
  );
}
