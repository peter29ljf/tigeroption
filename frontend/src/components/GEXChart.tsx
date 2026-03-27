"use client";

import { useMemo } from "react";

interface GEXStrike {
  strike: number;
  call_gex: number;
  put_gex: number;
  net_gex: number;
}

interface Props {
  strikes: GEXStrike[];
  maxGexStrike: number | null;
  stockPrice: number | null;
}

function fmt(v: number): string {
  if (Math.abs(v) >= 1_000_000_000) return (v / 1_000_000_000).toFixed(1) + "B";
  if (Math.abs(v) >= 1_000_000) return (v / 1_000_000).toFixed(1) + "M";
  if (Math.abs(v) >= 1_000) return (v / 1_000).toFixed(0) + "K";
  return v.toFixed(0);
}

export function GEXChart({ strikes, maxGexStrike, stockPrice }: Props) {
  // All hooks must be called before any early return
  const maxAbs = useMemo(
    () => Math.max(...strikes.map((s) => Math.abs(s.net_gex)), 1),
    [strikes]
  );

  const displayed = useMemo(() => {
    if (!stockPrice) return strikes.slice(0, 20);
    const sorted = [...strikes].sort((a, b) => Math.abs(a.strike - stockPrice) - Math.abs(b.strike - stockPrice));
    return sorted.slice(0, 20).sort((a, b) => b.strike - a.strike);
  }, [strikes, stockPrice]);

  const allZero = strikes.every((s) => s.net_gex === 0);

  if (strikes.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 border border-dashed border-[var(--border-color)] rounded-lg text-[var(--text-muted)] text-sm">
        暂无 GEX 数据（需市场数据权限）
      </div>
    );
  }

  if (allZero) {
    return (
      <div className="flex flex-col items-center justify-center h-32 border border-dashed border-[var(--border-color)] rounded-lg gap-1">
        <div className="text-[var(--text-muted)] text-sm">非交易时段，Delta 数据为零</div>
        <div className="text-[var(--text-muted)] text-xs">{strikes.length} 个行权价已加载，交易时段将显示 GEX 分布</div>
      </div>
    );
  }

  return (
    <div className="space-y-1 overflow-y-auto max-h-[360px] pr-1">
      {displayed.map((row) => {
        const isMax = row.strike === maxGexStrike;
        const isAtm = stockPrice && Math.abs(row.strike - stockPrice) / stockPrice < 0.005;
        const pct = Math.abs(row.net_gex) / maxAbs;
        const barWidth = `${Math.max(pct * 100, 1)}%`;
        const positive = row.net_gex >= 0;

        return (
          <div key={row.strike} className="flex items-center gap-2 group">
            {/* Strike label */}
            <div className={`w-14 text-right text-xs font-mono flex-shrink-0 ${
              isAtm ? "text-yellow-400 font-bold" : "text-[var(--text-muted)]"
            }`}>
              ${row.strike}
              {isAtm && <span className="ml-1 text-[10px]">◀</span>}
            </div>

            {/* Bar */}
            <div className="flex-1 relative h-5 flex items-center">
              <div
                className={`h-3 rounded-sm transition-all ${positive ? "bg-green-500/70" : "bg-red-500/70"} ${
                  isMax ? "ring-1 ring-yellow-400/60" : ""
                }`}
                style={{ width: barWidth }}
              />
              {isMax && (
                <span className="absolute right-0 text-[10px] text-yellow-400 font-medium">磁铁</span>
              )}
            </div>

            {/* Value */}
            <div className={`w-14 text-xs font-mono flex-shrink-0 ${positive ? "text-green-400" : "text-red-400"}`}>
              {positive ? "+" : ""}{fmt(row.net_gex)}
            </div>
          </div>
        );
      })}

      {/* Legend */}
      <div className="flex items-center gap-4 pt-2 text-xs text-[var(--text-muted)] border-t border-[var(--border-color)]/50">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-2 rounded-sm bg-green-500/70" />正GEX（做市商净多Gamma）
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-2 rounded-sm bg-red-500/70" />负GEX（做市商净空Gamma）
        </div>
      </div>
    </div>
  );
}
