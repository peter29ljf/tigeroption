import type { Flow } from "@/store/flowStore";
import {
  formatPremiumUSD,
  formatPremiumCNY,
  formatBeijingTime,
  formatContract,
} from "@/lib/format";
import { ScoreBadge } from "./ScoreBadge";
import { DirectionTag } from "./DirectionTag";
import clsx from "clsx";

export function FlowCard({ flow }: { flow: Flow }) {
  return (
    <div
      className={clsx(
        "rounded-lg border p-4 transition-colors",
        flow.direction === "BULLISH" && "border-green-500/20 bg-green-500/5",
        flow.direction === "BEARISH" && "border-red-500/20 bg-red-500/5",
        flow.direction === "NEUTRAL" && "border-[var(--border-color)] bg-[var(--bg-card)]"
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold text-[var(--text-primary)]">
            {flow.symbol}
          </span>
          <DirectionTag direction={flow.direction} />
          {flow.is_sweep && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-orange-500/20 text-orange-400 border border-orange-500/30">
              扫单
            </span>
          )}
        </div>
        <ScoreBadge score={flow.score} />
      </div>

      <div className="text-sm text-[var(--text-secondary)] mb-2">
        {formatContract(flow.symbol, flow.strike, flow.expiry, flow.put_call)}
      </div>

      <div className="flex items-center justify-between">
        <div>
          <div className="text-base font-semibold text-[var(--text-primary)]">
            {formatPremiumUSD(flow.premium)}
          </div>
          <div className="text-xs text-[var(--text-muted)]">
            {formatPremiumCNY(flow.premium)}
          </div>
        </div>
        <div className="text-xs text-[var(--text-muted)]">
          {formatBeijingTime(flow.timestamp)}
        </div>
      </div>

      {flow.ai_note && (
        <div className="mt-3 pt-3 border-t border-[var(--border-color)]">
          <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
            <span className="text-[var(--accent-purple)] font-medium">AI </span>
            {flow.ai_note}
          </p>
        </div>
      )}
    </div>
  );
}
