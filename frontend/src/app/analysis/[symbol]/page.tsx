"use client";

import { useParams } from "next/navigation";
import { useAnalysis, usePrices, useChainSnapshot, useGEX } from "@/hooks/useFlows";
import { FlowTable } from "@/components/FlowTable";
import { ScoreBadge } from "@/components/ScoreBadge";
import { SentimentBar } from "@/components/SentimentBar";
import { TradingViewChart } from "@/components/TradingViewChart";
import { OptionChainHeatmap } from "@/components/OptionChainHeatmap";
import { GEXChart } from "@/components/GEXChart";
import { formatNumber } from "@/lib/format";
import Link from "next/link";
import type { FlowMarker } from "@/components/TradingViewChart";

const SYMBOLS = ["NVDA", "AAPL", "TSLA", "SPY", "QQQ", "AMZN", "MSFT", "META", "GOOGL", "AMD"];

export default function AnalysisPage() {
  const params = useParams();
  const symbol = (params.symbol as string)?.toUpperCase() || "SPY";
  const { data, loading, error } = useAnalysis(symbol);
  const { data: prices } = usePrices(symbol, 60);
  const { data: chainData } = useChainSnapshot(symbol, 24);
  const { data: gexData } = useGEX(symbol);

  const flowMarkers: FlowMarker[] = (data?.top_flows ?? [])
    .filter((f) => f.timestamp && f.direction)
    .map((f) => ({
      time: f.timestamp.slice(0, 10),
      direction: f.direction as "BULLISH" | "BEARISH" | "NEUTRAL",
      premium: f.premium,
      score: f.score,
    }));

  return (
    <div className="space-y-6 pb-20 md:pb-0">
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
                <ScoreBadge score={Math.round(data.avg_score ?? 0)} />
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

          <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">价格走势（近60日）</h2>
              <span className="text-xs text-[var(--text-muted)]">箭头标记 = 大单信号</span>
            </div>
            <TradingViewChart data={prices ?? []} markers={flowMarkers} height={320} />
          </div>

          {/* GEX and chain heatmap side by side on desktop */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-[var(--text-primary)]">Gamma曝露 (GEX)</h2>
                <span className="text-xs text-[var(--text-muted)]">磁铁 = 价格支撑/阻力区</span>
              </div>
              <GEXChart
                strikes={gexData?.strikes ?? []}
                maxGexStrike={gexData?.max_gex_strike ?? null}
                stockPrice={gexData?.stock_price ?? null}
              />
            </div>

            <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-[var(--text-primary)]">期权链热力图（近24h）</h2>
                <span className="text-xs text-[var(--text-muted)]">Call绿 / Put红</span>
              </div>
              <OptionChainHeatmap rows={chainData?.rows ?? []} />
            </div>
          </div>

          <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4">
            <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-4">
              最高溢价大单 (Top 10) — 点击「复盘」查看信号后走势
            </h2>
            <FlowTable flows={data.top_flows ?? []} />
          </div>
        </>
      )}
    </div>
  );
}
