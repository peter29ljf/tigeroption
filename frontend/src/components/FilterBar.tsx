"use client";

import { useState } from "react";
import { useFlowStore, type FlowFilters } from "@/store/flowStore";
import { useWatchlistStore, DEFAULT_SYMBOLS } from "@/store/watchlistStore";
import clsx from "clsx";

const DIRECTIONS = [
  { value: "ALL", label: "全部" },
  { value: "BULLISH", label: "看涨" },
  { value: "BEARISH", label: "看跌" },
] as const;

export function FilterBar() {
  const { filters, updateFilters } = useFlowStore();
  const watchlist = useWatchlistStore((s) => s.symbols.length > 0 ? s.symbols : DEFAULT_SYMBOLS);
  const [localSymbols, setLocalSymbols] = useState<string[]>(filters.symbols);
  const [localPremium, setLocalPremium] = useState(String(filters.min_premium || ""));
  const [localDirection, setLocalDirection] = useState<FlowFilters["direction"]>(filters.direction);
  const [localScore, setLocalScore] = useState(filters.min_score);

  const toggleSymbol = (sym: string) => {
    setLocalSymbols((prev) =>
      prev.includes(sym) ? prev.filter((s) => s !== sym) : [...prev, sym]
    );
  };

  const applyFilters = () => {
    updateFilters({
      symbols: localSymbols,
      min_premium: Number(localPremium) || 0,
      direction: localDirection,
      min_score: localScore,
    });
  };

  return (
    <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4 space-y-4">
      <div className="flex items-center gap-2 text-sm font-medium text-[var(--text-primary)]">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
        </svg>
        筛选条件
      </div>

      {/* Symbols */}
      <div>
        <label className="text-xs text-[var(--text-muted)] mb-2 block">标的</label>
        <div className="flex flex-wrap gap-2">
          {watchlist.map((sym) => (
            <button
              key={sym}
              onClick={() => toggleSymbol(sym)}
              className={clsx(
                "px-2.5 py-1 rounded text-xs font-medium transition-colors border",
                localSymbols.includes(sym)
                  ? "bg-[var(--accent-blue)]/20 text-[var(--accent-blue)] border-[var(--accent-blue)]/40"
                  : "bg-[var(--bg-primary)] text-[var(--text-muted)] border-[var(--border-color)] hover:border-[var(--text-muted)]"
              )}
            >
              {sym}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Min premium */}
        <div>
          <label className="text-xs text-[var(--text-muted)] mb-2 block">最低溢价 (USD)</label>
          <input
            type="number"
            value={localPremium}
            onChange={(e) => setLocalPremium(e.target.value)}
            placeholder="例如: 100000"
            className="w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-blue)] transition-colors"
          />
        </div>

        {/* Direction */}
        <div>
          <label className="text-xs text-[var(--text-muted)] mb-2 block">方向</label>
          <div className="flex gap-1">
            {DIRECTIONS.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setLocalDirection(value as FlowFilters["direction"])}
                className={clsx(
                  "flex-1 px-3 py-2 rounded text-xs font-medium transition-colors border",
                  localDirection === value
                    ? "bg-[var(--accent-blue)]/20 text-[var(--accent-blue)] border-[var(--accent-blue)]/40"
                    : "bg-[var(--bg-primary)] text-[var(--text-muted)] border-[var(--border-color)]"
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Min score */}
        <div>
          <label className="text-xs text-[var(--text-muted)] mb-2 block">
            最低评分: <span className="text-[var(--text-primary)] font-medium">{localScore}</span>
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={localScore}
            onChange={(e) => setLocalScore(Number(e.target.value))}
            className="w-full"
          />
        </div>
      </div>

      <button
        onClick={applyFilters}
        className="px-6 py-2 bg-[var(--accent-blue)] hover:bg-[var(--accent-blue)]/80 text-white text-sm font-medium rounded transition-colors"
      >
        应用筛选
      </button>
    </div>
  );
}
