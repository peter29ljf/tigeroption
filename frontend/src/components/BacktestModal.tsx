"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { formatPremiumUSD, formatContract } from "@/lib/format";
import { TradingViewChart } from "@/components/TradingViewChart";
import { useSignalStats } from "@/hooks/useFlows";
import type { CandleBar } from "@/components/TradingViewChart";

interface BacktestReturns {
  d5: number | null;
  d10: number | null;
  d30: number | null;
}

interface BacktestResult {
  price_at_signal: number | null;
  bars: Array<{ time: string; open: number; high: number; low: number; close: number; volume: number }>;
  returns: BacktestReturns;
}

interface Props {
  flowId: number;
  label: string;
  direction?: string;
  minScore?: number;
  onClose: () => void;
}

function ReturnBadge({ value, label }: { value: number | null; label: string }) {
  if (value === null) return <div className="text-center"><div className="text-xs text-[var(--text-muted)]">{label}</div><div className="text-sm text-[var(--text-muted)]">—</div></div>;
  const color = value > 0 ? "text-green-400" : value < 0 ? "text-red-400" : "text-[var(--text-muted)]";
  const sign = value > 0 ? "+" : "";
  return (
    <div className="text-center">
      <div className="text-xs text-[var(--text-muted)] mb-0.5">{label}</div>
      <div className={`text-lg font-bold font-mono ${color}`}>{sign}{value}%</div>
    </div>
  );
}

function WinRateBadge({ rate, avg }: { rate: number | null; avg: number | null }) {
  if (rate === null) return <div className="text-[var(--text-muted)] text-sm">—</div>;
  const rateColor = rate >= 60 ? "text-green-400" : rate < 40 ? "text-red-400" : "text-yellow-400";
  const avgSign = avg != null && avg > 0 ? "+" : "";
  return (
    <div className="text-center">
      <div className={`text-base font-bold font-mono ${rateColor}`}>{rate}%</div>
      {avg !== null && (
        <div className={`text-xs font-mono ${avg > 0 ? "text-green-400" : avg < 0 ? "text-red-400" : "text-[var(--text-muted)]"}`}>
          {avgSign}{avg}%
        </div>
      )}
    </div>
  );
}

export function BacktestModal({ flowId, label, direction, minScore = 60, onClose }: Props) {
  const [data, setData] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { data: statsData, loading: statsLoading } = useSignalStats(direction, minScore);

  useEffect(() => {
    apiFetch<BacktestResult>(`/api/v1/backtest/${flowId}`)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [flowId]);

  const bars: CandleBar[] = (data?.bars ?? []).map((b) => ({
    time: b.time,
    open: b.open,
    high: b.high,
    low: b.low,
    close: b.close,
    volume: b.volume,
  }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[var(--border-color)]">
          <div>
            <h2 className="font-semibold text-[var(--text-primary)]">信号复盘</h2>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">{label}</p>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] text-xl leading-none px-2"
          >
            ×
          </button>
        </div>

        <div className="p-4 space-y-4">
          {loading && (
            <div className="flex items-center justify-center h-32 text-[var(--text-muted)]">
              <div className="w-5 h-5 border-2 border-[var(--accent-blue)] border-t-transparent rounded-full animate-spin mr-2" />
              加载回测数据...
            </div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded p-3 text-red-400 text-sm">
              {error}
            </div>
          )}

          {data && (
            <>
              {/* Signal price */}
              {data.price_at_signal && (
                <div className="text-sm text-[var(--text-muted)]">
                  信号时股价：<span className="font-mono text-[var(--text-primary)]">${data.price_at_signal.toFixed(2)}</span>
                </div>
              )}

              {/* Returns */}
              <div className="grid grid-cols-3 gap-4 bg-[var(--bg-primary)] rounded-lg p-4">
                <ReturnBadge value={data.returns.d5} label="第5天" />
                <ReturnBadge value={data.returns.d10} label="第10天" />
                <ReturnBadge value={data.returns.d30} label="第30天" />
              </div>

              {/* Price chart */}
              <div>
                <div className="text-xs text-[var(--text-muted)] mb-2">信号后股价走势</div>
                <TradingViewChart data={bars} height={200} />
              </div>

              <p className="text-xs text-[var(--text-muted)] bg-yellow-500/10 border border-yellow-500/20 rounded p-2">
                ⚠️ 仅供参考，不构成投资建议。历史表现不代表未来收益。
              </p>
            </>
          )}

          {/* Historical win rate */}
          {direction && (
            <div className="border-t border-[var(--border-color)] pt-4">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs font-semibold text-[var(--text-primary)]">
                  类似信号历史胜率
                </span>
                <span className="text-xs text-[var(--text-muted)]">
                  方向: {direction} · 评分 ≥ {minScore}
                  {statsData ? ` · ${statsData.total} 条已复盘` : ""}
                </span>
              </div>
              {statsLoading ? (
                <div className="text-xs text-[var(--text-muted)]">加载中...</div>
              ) : statsData && statsData.total > 0 ? (
                <div className="bg-[var(--bg-primary)] rounded-lg p-3">
                  <div className="grid grid-cols-4 gap-2 text-center">
                    <div className="text-xs text-[var(--text-muted)]" />
                    <div className="text-xs text-[var(--text-muted)] font-medium">5天</div>
                    <div className="text-xs text-[var(--text-muted)] font-medium">10天</div>
                    <div className="text-xs text-[var(--text-muted)] font-medium">30天</div>
                    <div className="text-xs text-[var(--text-muted)] text-left">胜率/均收益</div>
                    <WinRateBadge rate={statsData.d5_win_rate} avg={statsData.d5_avg_return} />
                    <WinRateBadge rate={statsData.d10_win_rate} avg={statsData.d10_avg_return} />
                    <WinRateBadge rate={statsData.d30_win_rate} avg={statsData.d30_avg_return} />
                  </div>
                </div>
              ) : (
                <div className="text-xs text-[var(--text-muted)]">
                  暂无历史胜率数据（需先点击复盘积累数据）
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
