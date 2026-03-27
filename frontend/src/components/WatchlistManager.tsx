"use client";

import { useState, useEffect, useRef } from "react";
import { apiFetch } from "@/lib/api";
import { useWatchlistStore, DEFAULT_SYMBOLS } from "@/store/watchlistStore";

interface StockResult {
  symbol: string;
  name: string;
}

interface Props {
  onClose: () => void;
}

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export function WatchlistManager({ onClose }: Props) {
  const { symbols, addSymbol, removeSymbol, resetToDefault } = useWatchlistStore();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockResult[]>([]);
  const [searching, setSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setResults([]);
      return;
    }
    let cancelled = false;
    setSearching(true);
    apiFetch<StockResult[]>(`/api/v1/search?q=${encodeURIComponent(debouncedQuery.trim())}`)
      .then((data) => { if (!cancelled) setResults(data); })
      .catch(() => { if (!cancelled) setResults([]); })
      .finally(() => { if (!cancelled) setSearching(false); });
    return () => { cancelled = true; };
  }, [debouncedQuery]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl shadow-2xl w-full max-w-md max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[var(--border-color)] flex-shrink-0">
          <span className="font-semibold text-[var(--text-primary)]">自选标的管理</span>
          <button
            onClick={onClose}
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] text-xl leading-none px-2"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Search */}
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索股票代码或公司名（如 NVDA、apple）..."
              className="w-full px-3 py-2 rounded-lg text-sm bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-blue)]/60 transition-colors"
            />
            {searching && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <div className="w-3.5 h-3.5 border-2 border-[var(--accent-blue)] border-t-transparent rounded-full animate-spin" />
              </div>
            )}
          </div>

          {/* Search results */}
          {results.length > 0 && (
            <div className="border border-[var(--border-color)] rounded-lg overflow-hidden">
              {results.map((stock) => {
                const already = symbols.includes(stock.symbol);
                return (
                  <div
                    key={stock.symbol}
                    className="flex items-center gap-3 px-3 py-2.5 border-b border-[var(--border-color)]/50 last:border-0 hover:bg-[var(--bg-primary)] transition-colors"
                  >
                    <span className="text-sm font-bold text-[var(--text-primary)] w-14 flex-shrink-0">
                      {stock.symbol}
                    </span>
                    <span className="text-sm text-[var(--text-muted)] flex-1 truncate">
                      {stock.name}
                    </span>
                    <button
                      onClick={() => { if (!already) addSymbol(stock.symbol); }}
                      disabled={already}
                      className={`px-2.5 py-1 rounded text-xs font-medium flex-shrink-0 transition-colors ${
                        already
                          ? "text-green-400 bg-green-500/10 border border-green-500/20 cursor-default"
                          : "text-[var(--accent-blue)] bg-[var(--accent-blue)]/10 border border-[var(--accent-blue)]/30 hover:bg-[var(--accent-blue)]/20"
                      }`}
                    >
                      {already ? "✓ 已添加" : "+ 添加"}
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {/* No results hint */}
          {!searching && query.trim() && results.length === 0 && (
            <p className="text-xs text-[var(--text-muted)] text-center py-2">
              未找到匹配结果
            </p>
          )}

          {/* Current watchlist */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-[var(--text-muted)]">
                当前自选（{symbols.length} / 30）
              </span>
              <button
                onClick={resetToDefault}
                className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
              >
                恢复默认
              </button>
            </div>

            {symbols.length === 0 ? (
              <p className="text-xs text-yellow-400 bg-yellow-500/10 border border-yellow-500/20 rounded p-3">
                自选为空 —— 点击「恢复默认」还原
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {symbols.map((sym) => (
                  <span
                    key={sym}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)]"
                  >
                    {sym}
                    <button
                      onClick={() => removeSymbol(sym)}
                      className="text-[var(--text-muted)] hover:text-red-400 transition-colors leading-none ml-0.5"
                      aria-label={`删除 ${sym}`}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-[var(--border-color)] flex-shrink-0">
          <p className="text-xs text-[var(--text-muted)]">
            自选列表保存在本地浏览器，最多添加 30 个标的。
          </p>
        </div>
      </div>
    </div>
  );
}
