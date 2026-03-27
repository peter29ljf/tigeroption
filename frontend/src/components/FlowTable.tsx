"use client";

import { useState } from "react";
import type { Flow } from "@/store/flowStore";
import {
  formatPremiumUSD,
  formatPremiumCNY,
  formatBeijingTime,
  formatContract,
} from "@/lib/format";
import { ScoreBadge } from "./ScoreBadge";
import { DirectionTag } from "./DirectionTag";
import { FlowCard } from "./FlowCard";
import { BacktestModal } from "./BacktestModal";
import clsx from "clsx";

export function FlowTable({ flows }: { flows: Flow[] }) {
  const [backtestFlow, setBacktestFlow] = useState<Flow | null>(null);

  const sorted = [...flows].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  if (sorted.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-[var(--text-muted)]">
        暂无数据
      </div>
    );
  }

  return (
    <>
      {backtestFlow && (
        <BacktestModal
          flowId={Number(backtestFlow.id)}
          label={formatContract(
            backtestFlow.symbol,
            backtestFlow.strike,
            backtestFlow.expiry,
            backtestFlow.put_call
          )}
          onClose={() => setBacktestFlow(null)}
        />
      )}

      {/* Desktop table */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border-color)] text-[var(--text-muted)]">
              <th className="text-left py-3 px-3 font-medium">时间</th>
              <th className="text-left py-3 px-3 font-medium">标的</th>
              <th className="text-left py-3 px-3 font-medium">合约</th>
              <th className="text-left py-3 px-3 font-medium">方向</th>
              <th className="text-right py-3 px-3 font-medium">溢价(USD)</th>
              <th className="text-right py-3 px-3 font-medium">溢价(CNY)</th>
              <th className="text-center py-3 px-3 font-medium">评分</th>
              <th className="text-center py-3 px-3 font-medium">类型</th>
              <th className="text-left py-3 px-3 font-medium">AI解读</th>
              <th className="py-3 px-3" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((flow) => (
              <tr
                key={flow.id}
                className={clsx(
                  "border-b border-[var(--border-color)]/50 transition-colors hover:bg-[var(--bg-card-hover)]",
                  flow.direction === "BULLISH" && "bg-green-500/[0.03]",
                  flow.direction === "BEARISH" && "bg-red-500/[0.03]"
                )}
              >
                <td className="py-2.5 px-3 text-[var(--text-muted)] whitespace-nowrap">
                  {formatBeijingTime(flow.timestamp)}
                </td>
                <td className="py-2.5 px-3 font-semibold text-[var(--text-primary)]">
                  {flow.symbol}
                </td>
                <td className="py-2.5 px-3 text-[var(--text-secondary)] whitespace-nowrap">
                  {formatContract(flow.symbol, flow.strike, flow.expiry, flow.put_call)}
                </td>
                <td className="py-2.5 px-3">
                  <DirectionTag direction={flow.direction} />
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-[var(--text-primary)]">
                  {formatPremiumUSD(flow.premium)}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-[var(--text-muted)]">
                  {formatPremiumCNY(flow.premium)}
                </td>
                <td className="py-2.5 px-3 text-center">
                  <ScoreBadge score={flow.score} />
                </td>
                <td className="py-2.5 px-3 text-center">
                  <div className="flex items-center justify-center gap-1 flex-wrap">
                    {flow.is_sweep && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-orange-500/20 text-orange-400">
                        扫单
                      </span>
                    )}
                    {flow.is_dark_pool && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-500/20 text-purple-400">
                        暗池
                      </span>
                    )}
                    {!flow.is_sweep && !flow.is_dark_pool && (
                      <span className="text-[var(--text-muted)] text-xs">普通</span>
                    )}
                  </div>
                </td>
                <td className="py-2.5 px-3 text-xs text-[var(--text-secondary)] max-w-[200px] truncate">
                  {flow.ai_note || "—"}
                </td>
                <td className="py-2.5 px-3">
                  <button
                    onClick={() => setBacktestFlow(flow)}
                    className="text-xs text-[var(--accent-blue)] hover:underline whitespace-nowrap"
                  >
                    复盘
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="md:hidden flex flex-col gap-3">
        {sorted.map((flow) => (
          <FlowCard key={flow.id} flow={flow} onBacktest={() => setBacktestFlow(flow)} />
        ))}
      </div>
    </>
  );
}
