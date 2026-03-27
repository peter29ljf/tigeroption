"use client";

import { useMemo } from "react";

interface OIStrike {
  strike: number;
  call_oi: number;
  put_oi: number;
  net_oi: number;
}

interface Props {
  strikes: OIStrike[];
  totalCallOI: number;
  totalPutOI: number;
  putCallRatio: number | null;
  stockPrice: number | null;
}

function fmtOI(v: number): string {
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + "M";
  if (v >= 1_000) return (v / 1_000).toFixed(0) + "K";
  return v.toFixed(0);
}

export function OIDistributionChart({
  strikes,
  totalCallOI,
  totalPutOI,
  putCallRatio,
  stockPrice,
}: Props) {
  const maxOI = useMemo(
    () => Math.max(...strikes.map((s) => Math.max(s.call_oi, s.put_oi)), 1),
    [strikes]
  );

  const displayed = useMemo(() => {
    if (!stockPrice) return strikes.slice(0, 20);
    const sorted = [...strikes].sort(
      (a, b) => Math.abs(a.strike - stockPrice) - Math.abs(b.strike - stockPrice)
    );
    return sorted.slice(0, 20).sort((a, b) => b.strike - a.strike);
  }, [strikes, stockPrice]);

  if (strikes.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 border border-dashed border-[var(--border-color)] rounded-lg text-[var(--text-muted)] text-sm">
        暂无 OI 数据（需市场数据权限）
      </div>
    );
  }

  const ratioColor =
    putCallRatio === null
      ? "text-[var(--text-muted)]"
      : putCallRatio > 1.5
      ? "text-red-400"
      : putCallRatio < 0.7
      ? "text-green-400"
      : "text-yellow-400";

  return (
    <div className="space-y-3">
      {/* Summary row */}
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-2 rounded-sm bg-green-500/70" />
          <span className="text-[var(--text-muted)]">Call OI:</span>
          <span className="font-mono text-green-400">{fmtOI(totalCallOI)}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-2 rounded-sm bg-red-500/70" />
          <span className="text-[var(--text-muted)]">Put OI:</span>
          <span className="font-mono text-red-400">{fmtOI(totalPutOI)}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[var(--text-muted)]">P/C 比率:</span>
          <span className={`font-mono font-bold ${ratioColor}`}>
            {putCallRatio !== null ? putCallRatio.toFixed(2) : "—"}
          </span>
          {putCallRatio !== null && putCallRatio > 1.5 && (
            <span className="text-[10px] text-red-400">偏空</span>
          )}
          {putCallRatio !== null && putCallRatio < 0.7 && (
            <span className="text-[10px] text-green-400">偏多</span>
          )}
        </div>
      </div>

      {/* Dual-direction bar chart */}
      <div className="space-y-1 overflow-y-auto max-h-[320px] pr-1">
        {displayed.map((row) => {
          const isAtm = stockPrice && Math.abs(row.strike - stockPrice) / stockPrice < 0.005;
          const callPct = (row.call_oi / maxOI) * 100;
          const putPct = (row.put_oi / maxOI) * 100;
          // Highlight heavy Put concentration (institutional bearish)
          const heavyPut = putCallRatio !== null && row.put_oi > 0 &&
            row.put_oi / Math.max(row.call_oi, 1) > 1.5;

          return (
            <div key={row.strike} className="flex items-center gap-2 group">
              {/* Strike label */}
              <div
                className={`w-14 text-right text-xs font-mono flex-shrink-0 ${
                  isAtm ? "text-yellow-400 font-bold" : "text-[var(--text-muted)]"
                }`}
              >
                ${row.strike}
                {isAtm && <span className="ml-1 text-[10px]">◀</span>}
              </div>

              {/* Dual bar: Put (left, red) ← center → Call (right, green) */}
              <div className="flex-1 flex items-center gap-0.5 h-5">
                {/* Put bar — grows left */}
                <div className="flex-1 flex justify-end items-center">
                  <div
                    className={`h-3 rounded-l-sm transition-all ${
                      heavyPut ? "bg-red-500" : "bg-red-500/60"
                    }`}
                    style={{ width: `${Math.max(putPct, 1)}%` }}
                    title={`Put OI: ${fmtOI(row.put_oi)}`}
                  />
                </div>

                {/* Center divider */}
                <div className="w-px h-4 bg-[var(--border-color)] flex-shrink-0" />

                {/* Call bar — grows right */}
                <div className="flex-1 flex justify-start items-center">
                  <div
                    className="h-3 rounded-r-sm bg-green-500/60 transition-all"
                    style={{ width: `${Math.max(callPct, 1)}%` }}
                    title={`Call OI: ${fmtOI(row.call_oi)}`}
                  />
                </div>
              </div>

              {/* Net OI value */}
              <div
                className={`w-12 text-xs font-mono flex-shrink-0 text-right ${
                  row.net_oi >= 0 ? "text-green-400" : "text-red-400"
                }`}
              >
                {row.net_oi >= 0 ? "+" : ""}{fmtOI(Math.abs(row.net_oi))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 pt-1 text-xs text-[var(--text-muted)] border-t border-[var(--border-color)]/50">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-2 rounded-sm bg-green-500/60" />Call OI（看涨方向）
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-2 rounded-sm bg-red-500/60" />Put OI（看跌方向）
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-2 rounded-sm bg-red-500" />P/C {">"}1.5（机构偏空区）
        </div>
      </div>
    </div>
  );
}
