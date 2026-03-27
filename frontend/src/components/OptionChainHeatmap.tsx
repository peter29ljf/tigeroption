"use client";

import { useMemo, useState } from "react";
import type { ChainSnapshotRow } from "@/hooks/useFlows";
import { formatPremiumUSD } from "@/lib/format";

interface Props {
  rows: ChainSnapshotRow[];
}

function heatColor(value: number, max: number, type: "call" | "put"): string {
  if (max === 0 || value === 0) return "transparent";
  const ratio = Math.min(value / max, 1);
  const alpha = Math.round(ratio * 85 + 10); // 10–95
  return type === "call"
    ? `rgba(34,197,94,${alpha / 100})`   // green for calls
    : `rgba(239,68,68,${alpha / 100})`;   // red for puts
}

export function OptionChainHeatmap({ rows }: Props) {
  const [hover, setHover] = useState<ChainSnapshotRow | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const { expiries, strikesByExpiry, maxCallVol, maxPutVol } = useMemo(() => {
    const expSet = new Set<string>();
    const allRows: Record<string, ChainSnapshotRow> = {};
    let maxCall = 0;
    let maxPut = 0;

    for (const row of rows) {
      expSet.add(row.expiry);
      const key = `${row.strike}_${row.expiry}`;
      allRows[key] = row;
      if (row.call_volume > maxCall) maxCall = row.call_volume;
      if (row.put_volume > maxPut) maxPut = row.put_volume;
    }

    const expiries = Array.from(expSet).sort();
    const strikes = Array.from(new Set(rows.map((r) => r.strike))).sort((a, b) => b - a);

    return { expiries, strikesByExpiry: { allRows, strikes }, maxCallVol: maxCall, maxPutVol: maxPut };
  }, [rows]);

  if (rows.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 border border-dashed border-[var(--border-color)] rounded-lg text-[var(--text-muted)] text-sm">
        暂无期权链数据
      </div>
    );
  }

  const { allRows, strikes } = strikesByExpiry;

  return (
    <div className="relative overflow-x-auto">
      {/* Tooltip */}
      {hover && (
        <div
          className="fixed z-50 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-3 text-xs shadow-xl pointer-events-none"
          style={{ left: tooltipPos.x + 12, top: tooltipPos.y - 60 }}
        >
          <div className="font-semibold text-[var(--text-primary)] mb-1">
            ${hover.strike} · {hover.expiry}
          </div>
          <div className="text-green-400">
            Call 量: {hover.call_volume.toLocaleString()} · {formatPremiumUSD(hover.call_premium)}
          </div>
          <div className="text-red-400">
            Put 量: {hover.put_volume.toLocaleString()} · {formatPremiumUSD(hover.put_premium)}
          </div>
        </div>
      )}

      <table className="text-xs w-full border-collapse">
        <thead>
          <tr>
            <th className="text-left p-2 text-[var(--text-muted)] sticky left-0 bg-[var(--bg-card)] z-10 border-b border-[var(--border-color)]">
              行权价
            </th>
            {expiries.map((exp) => (
              <th
                key={exp}
                className="text-center p-2 text-[var(--text-muted)] border-b border-[var(--border-color)] min-w-[80px]"
              >
                {exp.slice(5)} {/* MM-DD */}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {strikes.map((strike) => (
            <tr key={strike} className="border-b border-[var(--border-color)]/30">
              <td className="p-2 font-mono text-[var(--text-primary)] sticky left-0 bg-[var(--bg-card)] z-10">
                ${strike}
              </td>
              {expiries.map((exp) => {
                const row = allRows[`${strike}_${exp}`];
                if (!row) {
                  return <td key={exp} className="p-1" />;
                }
                const callBg = heatColor(row.call_volume, maxCallVol, "call");
                const putBg = heatColor(row.put_volume, maxPutVol, "put");
                // Split cell: left=call, right=put
                return (
                  <td
                    key={exp}
                    className="p-0 cursor-pointer"
                    onMouseEnter={(e) => {
                      setHover(row);
                      setTooltipPos({ x: e.clientX, y: e.clientY });
                    }}
                    onMouseMove={(e) => setTooltipPos({ x: e.clientX, y: e.clientY })}
                    onMouseLeave={() => setHover(null)}
                  >
                    <div className="flex h-7">
                      <div
                        className="flex-1 flex items-center justify-center text-[10px] font-mono"
                        style={{ background: callBg }}
                      >
                        {row.call_volume > 0 ? row.call_volume.toLocaleString() : ""}
                      </div>
                      <div
                        className="flex-1 flex items-center justify-center text-[10px] font-mono"
                        style={{ background: putBg }}
                      >
                        {row.put_volume > 0 ? row.put_volume.toLocaleString() : ""}
                      </div>
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-3 text-xs text-[var(--text-muted)]">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-sm bg-green-500/60" />
          <span>Call 成交量（左）</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-sm bg-red-500/60" />
          <span>Put 成交量（右）</span>
        </div>
        <span className="ml-auto">颜色越深 = 成交量越大</span>
      </div>
    </div>
  );
}
