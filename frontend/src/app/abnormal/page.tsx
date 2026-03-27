"use client";

import { useState, useCallback } from "react";
import { useAbnormalFlows } from "@/hooks/useFlows";
import { apiFetch } from "@/lib/api";
import { FlowTable } from "@/components/FlowTable";

function renderAnalysis(text: string) {
  const parts = text.split(/\*\*(.*?)\*\*/g);
  return parts.map((part, i) =>
    i % 2 === 1
      ? <strong key={i} className="text-[var(--text-primary)] font-semibold">{part}</strong>
      : <span key={i}>{part}</span>
  );
}

export default function AbnormalPage() {
  const { data: flows, loading, error } = useAbnormalFlows(200);
  const [analysisText, setAnalysisText] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [showAnalysis, setShowAnalysis] = useState(false);

  const total = flows?.length ?? 0;
  const bullish = flows?.filter((f) => f.direction === "BULLISH").length ?? 0;
  const bearish = flows?.filter((f) => f.direction === "BEARISH").length ?? 0;
  const sweeps = flows?.filter((f) => f.is_sweep).length ?? 0;
  const darkPools = flows?.filter((f) => f.is_dark_pool).length ?? 0;

  const handleAnalyze = useCallback(async () => {
    setAnalyzing(true);
    setShowAnalysis(true);
    try {
      const res = await apiFetch<{ analysis: string }>("/api/v1/abnormal/ai-analysis", {
        method: "POST",
        body: JSON.stringify({}),
      });
      setAnalysisText(res.analysis);
    } catch {
      setAnalysisText("AI 分析请求失败，请稍后重试。");
    } finally {
      setAnalyzing(false);
    }
  }, []);

  const handleClear = useCallback(async () => {
    if (!window.confirm(`确认清空全部 ${total} 条异常大单标记？（历史数据保留，仅移出异常列表）`)) return;
    setClearing(true);
    try {
      await apiFetch<{ cleared: number }>("/api/v1/abnormal", { method: "DELETE" });
      window.location.reload();
    } catch {
      alert("清空失败，请重试");
    } finally {
      setClearing(false);
    }
  }, [total]);

  return (
    <div className="space-y-4 pb-20 md:pb-0">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-[var(--text-primary)]">异常大单</h1>
          {!loading && (
            <span className="text-sm text-[var(--text-muted)]">
              共 <span className="text-[var(--text-primary)] font-medium">{total}</span> 条
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleAnalyze}
            disabled={analyzing || total === 0}
            className="flex items-center gap-2 px-4 py-2 bg-[var(--accent-blue)]/15 hover:bg-[var(--accent-blue)]/25 text-[var(--accent-blue)] text-sm font-medium rounded-lg border border-[var(--accent-blue)]/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {analyzing ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-[var(--accent-blue)] border-t-transparent rounded-full animate-spin" />
                分析中...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.35A3.001 3.001 0 0112 21a3.001 3.001 0 01-2.121-.879l-.347-.349a5 5 0 010-7.072z" />
                </svg>
                AI 分析
              </>
            )}
          </button>
          <button
            onClick={handleClear}
            disabled={clearing || total === 0}
            className="flex items-center gap-2 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-sm font-medium rounded-lg border border-red-500/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {clearing ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-red-400 border-t-transparent rounded-full animate-spin" />
                清空中...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                一键清空
              </>
            )}
          </button>
        </div>
      </div>

      {/* AI Analysis Panel */}
      {showAnalysis && (
        <div className="bg-[var(--bg-card)] border border-[var(--accent-blue)]/30 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-[var(--accent-blue)]">AI 规律分析</span>
            <button
              onClick={() => setShowAnalysis(false)}
              className="text-[var(--text-muted)] hover:text-[var(--text-primary)] text-lg leading-none"
            >
              ×
            </button>
          </div>
          {analyzing ? (
            <div className="flex items-center gap-2 text-[var(--text-muted)] text-sm">
              <div className="w-4 h-4 border-2 border-[var(--accent-blue)] border-t-transparent rounded-full animate-spin" />
              正在分析 {total} 条异常大单的规律，请稍候...
            </div>
          ) : (
            <p className="text-sm text-[var(--text-secondary)] leading-relaxed whitespace-pre-wrap">
              {analysisText && renderAnalysis(analysisText)}
            </p>
          )}
        </div>
      )}

      {/* Stats bar */}
      {!loading && total > 0 && (
        <div className="flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
            <span className="text-[var(--text-muted)]">看涨</span>
            <span className="font-medium text-[var(--text-primary)]">
              {total > 0 ? `${Math.round(bullish / total * 100)}%` : "—"}
            </span>
            <span className="text-[var(--text-muted)]">({bullish})</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-400 inline-block" />
            <span className="text-[var(--text-muted)]">看跌</span>
            <span className="font-medium text-[var(--text-primary)]">
              {total > 0 ? `${Math.round(bearish / total * 100)}%` : "—"}
            </span>
            <span className="text-[var(--text-muted)]">({bearish})</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-yellow-400 inline-block" />
            <span className="text-[var(--text-muted)]">扫单</span>
            <span className="font-medium text-[var(--text-primary)]">{sweeps}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-purple-400 inline-block" />
            <span className="text-[var(--text-muted)]">暗池</span>
            <span className="font-medium text-[var(--text-primary)]">{darkPools}</span>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center h-48 text-[var(--text-muted)]">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-[var(--accent-blue)] border-t-transparent rounded-full animate-spin" />
            加载中...
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">
          加载失败: {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && total === 0 && (
        <div className="flex flex-col items-center justify-center h-64 gap-3 text-[var(--text-muted)]">
          <svg className="w-12 h-12 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p className="text-sm">暂无异常大单</p>
          <p className="text-xs text-center max-w-xs">
            系统实时监控中，评分≥75、大额扫单、暗池大单将自动出现在这里
          </p>
        </div>
      )}

      {/* Flow Table */}
      {!loading && flows && flows.length > 0 && (
        <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4">
          <FlowTable flows={flows} />
        </div>
      )}
    </div>
  );
}
