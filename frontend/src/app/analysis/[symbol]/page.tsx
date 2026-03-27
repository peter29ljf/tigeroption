"use client";

import { useParams } from "next/navigation";
import { useAnalysis } from "@/hooks/useFlows";
import { FlowTable } from "@/components/FlowTable";
import { ScoreBadge } from "@/components/ScoreBadge";
import { SentimentBar } from "@/components/SentimentBar";
import { formatNumber } from "@/lib/format";
import Link from "next/link";

const SYMBOLS = ["NVDA", "AAPL", "TSLA", "SPY", "QQQ", "AMZN", "MSFT", "META", "GOOGL", "AMD"];

export default function AnalysisPage() {
  const params = useParams();
  const symbol = (params.symbol as string)?.toUpperCase() || "SPY";
  const { data, loading, error } = useAnalysis(symbol);

  return (
    <div className="space-y-6 pb-20 md:pb-0">
      {/* Symbol selector */}
      <div className="flex flex-wrap gap-2">
        {SYMBOLS.map((sym) => (
          <Link
            key={sym}
            href={`/analysis/${sym}`}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors border ${
              sym === symbol
                ? "bg-[var(--accent-blue)]/20 text-[var(--accent-blue)] border-[var(--accent-blue)]/40"
                : "bg-[var(--bg-card)] text-[var(--text-muted)] border-[var(--border-color)] hover:text-[var(--text-primary)]"
            }`}
          >
            {sym}
          </Link>
        ))}
      </div>

      {/* Header */}
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">{symbol}</h1>
        {data?.current_price && (
          <span className="text-xl font-mono text-[var(--accent-blue)]">
            ${data.current_price.toFixed(2)}
          </span>
        )}
      </div>

      {loading && (
        <div className="flex items-center justify-center h-48 text-[var(--text-muted)]">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-[var(--accent-blue)] border-t-transparent rounded-full animate-spin" />
            加载中...
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">
          加载失败: {error}
        </div>
      )}

      {data && (
        <>
          {/* Stats cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4">
              <div className="text-xs text-[var(--text-muted)] mb-1">大单数量</div>
              <div className="text-xl font-bold text-[var(--text-primary)]">
                {formatNumber(data.flow_count)}
              </div>
            </div>
            <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4">
              <div className="text-xs text-[var(--text-muted)] mb-1">平均评分</div>
              <div className="text-xl font-bold">
                <ScoreBadge score={Math.round(data.avg_score)} />
              </div>
            </div>
            <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4 col-span-2">
              <div className="text-xs text-[var(--text-muted)] mb-2">情绪比例</div>
              <SentimentBar
                symbol={symbol}
                bullish={data.bullish_count}
                bearish={data.bearish_count}
              />
            </div>
          </div>

          {/* Chart placeholder */}
          <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4">
            <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-4">价格走势</h2>
            <div className="flex items-center justify-center h-64 border border-dashed border-[var(--border-color)] rounded-lg text-[var(--text-muted)] text-sm">
              TradingView 图表 (即将上线)
            </div>
          </div>

          {/* Top flows */}
          <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4">
            <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-4">
              最高评分大单 (Top 10)
            </h2>
            <FlowTable flows={data.top_flows || []} />
          </div>
        </>
      )}
    </div>
  );
}
