export function SentimentBar({
  symbol,
  bullish,
  bearish,
}: {
  symbol: string;
  bullish: number;
  bearish: number;
}) {
  const total = bullish + bearish || 1;
  const bullPct = Math.round((bullish / total) * 100);
  const bearPct = 100 - bullPct;

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm font-medium w-14 text-[var(--text-primary)]">
        {symbol}
      </span>
      <div className="flex-1 flex h-5 rounded-full overflow-hidden bg-[var(--bg-primary)]">
        {bullPct > 0 && (
          <div
            className="bg-green-500/80 flex items-center justify-center text-[10px] font-medium text-white transition-all duration-500"
            style={{ width: `${bullPct}%` }}
          >
            {bullPct > 15 ? `${bullPct}%` : ""}
          </div>
        )}
        {bearPct > 0 && (
          <div
            className="bg-red-500/80 flex items-center justify-center text-[10px] font-medium text-white transition-all duration-500"
            style={{ width: `${bearPct}%` }}
          >
            {bearPct > 15 ? `${bearPct}%` : ""}
          </div>
        )}
      </div>
      <div className="flex gap-2 text-xs w-24 justify-end">
        <span className="text-green-400">{bullPct}%</span>
        <span className="text-[var(--text-muted)]">/</span>
        <span className="text-red-400">{bearPct}%</span>
      </div>
    </div>
  );
}
