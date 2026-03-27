"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";

interface Props {
  symbol: string;
}

const LS_KEY = "anthropic_api_key";

function renderInsight(text: string): React.ReactNode {
  // Simple bold rendering: **text** → <strong>text</strong>
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i} className="text-[var(--text-primary)]">{part.slice(2, -2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

export function AIInsightPanel({ symbol }: Props) {
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [insight, setInsight] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastSymbol, setLastSymbol] = useState("");

  // Load saved API key from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(LS_KEY) || "";
      setApiKey(saved);
    } catch {}
  }, []);

  // Reset insight when symbol changes
  useEffect(() => {
    if (lastSymbol && lastSymbol !== symbol) {
      setInsight(null);
      setError(null);
    }
    setLastSymbol(symbol);
  }, [symbol, lastSymbol]);

  const handleAnalyze = useCallback(async () => {
    const key = apiKey.trim();
    // Save to localStorage
    try {
      if (key) localStorage.setItem(LS_KEY, key);
    } catch {}

    setLoading(true);
    setInsight(null);
    setError(null);

    try {
      const res = await apiFetch<{ insight: string }>(
        `/api/v1/analysis/${symbol}/ai-insight`,
        {
          method: "POST",
          body: JSON.stringify({ api_key: key || null }),
        }
      );
      setInsight(res.insight);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "AI 分析失败，请检查 API Key");
    } finally {
      setLoading(false);
    }
  }, [apiKey, symbol]);

  return (
    <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-[var(--text-primary)]">AI 综合分析</span>
        <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-500/20 text-purple-400 border border-purple-500/30">
          Claude
        </span>
        <span className="text-xs text-[var(--text-muted)] ml-auto">
          汇聚 GEX / OI / 大单 / 情绪 → 综合建议
        </span>
      </div>

      {/* API Key input + button */}
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Anthropic API Key（sk-ant-...）"
            className="w-full px-3 py-2 rounded-lg text-sm bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-purple-500/50"
          />
        </div>
        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="px-4 py-2 rounded-lg text-sm font-medium bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white whitespace-nowrap transition-colors"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              分析中...
            </span>
          ) : (
            "一键AI分析"
          )}
        </button>
      </div>

      <div className="text-xs text-[var(--text-muted)]">
        Key 仅用于本次请求，保存在本地浏览器，不上传至服务器存储。
        如服务器已配置 <code className="text-purple-400">ANTHROPIC_API_KEY</code>，可留空直接分析。
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Result */}
      {insight && (
        <div className="bg-[var(--bg-primary)] border border-purple-500/20 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-[var(--border-color)]">
            <span className="text-xs font-semibold text-purple-400">{symbol} · AI 分析报告</span>
            <button
              onClick={() => setInsight(null)}
              className="ml-auto text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            >
              关闭
            </button>
          </div>
          <div className="text-sm text-[var(--text-secondary)] leading-relaxed whitespace-pre-wrap">
            {renderInsight(insight)}
          </div>
        </div>
      )}
    </div>
  );
}
