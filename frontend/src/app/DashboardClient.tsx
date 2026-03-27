"use client";

import { FlowTable } from "@/components/FlowTable";
import { SentimentBar } from "@/components/SentimentBar";
import type { Flow } from "@/store/flowStore";
import clsx from "clsx";

interface FlowStats {
  total_flows: number;
  avg_score: number;
  bullish_ratio: number;
  sweep_ratio: number;
}

interface SentimentData {
  [symbol: string]: { bullish: number; bearish: number; neutral: number };
}

interface Props {
  stats: FlowStats | null;
  flows: Flow[];
  sentiment: SentimentData | null;
}

const STAT_CARDS = [
  {
    key: "total_flows" as const,
    label: "今日大单数",
    icon: "📋",
    format: (v: number) => v.toLocaleString(),
    accent: "blue",
  },
  {
    key: "avg_score" as const,
    label: "平均评分",
    icon: "⭐",
    format: (v: number) => v.toFixed(1),
    accent: "purple",
  },
  {
    key: "bullish_ratio" as const,
    label: "看涨比例",
    icon: "📈",
    format: (v: number) => `${(v * 100).toFixed(1)}%`,
    accent: "green",
  },
  {
    key: "sweep_ratio" as const,
    label: "扫单占比",
    icon: "⚡",
    format: (v: number) => `${(v * 100).toFixed(1)}%`,
    accent: "orange",
  },
];

const accentColors: Record<string, string> = {
  blue: "from-blue-500/20 to-blue-600/5 border-blue-500/20",
  purple: "from-purple-500/20 to-purple-600/5 border-purple-500/20",
  green: "from-green-500/20 to-green-600/5 border-green-500/20",
  orange: "from-orange-500/20 to-orange-600/5 border-orange-500/20",
};

export function DashboardClient({ stats, flows, sentiment }: Props) {
  const topSymbols = sentiment
    ? Object.entries(sentiment)
        .sort((a, b) => (b[1].bullish + b[1].bearish) - (a[1].bullish + a[1].bearish))
        .slice(0, 5)
    : [];

  return (
    <div className="space-y-6 pb-20 md:pb-0">
      <h1 className="text-xl font-bold text-[var(--text-primary)]">大盘监控</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {STAT_CARDS.map((card) => (
          <div
            key={card.key}
            className={clsx(
              "rounded-lg border p-4 bg-gradient-to-br",
              accentColors[card.accent]
            )}
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">{card.icon}</span>
              <span className="text-xs text-[var(--text-muted)]">{card.label}</span>
            </div>
            <div className="text-2xl font-bold text-[var(--text-primary)]">
              {stats ? card.format(stats[card.key]) : "—"}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Latest flows */}
        <div className="xl:col-span-2 bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4">
          <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-4">
            最新大单
          </h2>
          <FlowTable flows={flows} />
        </div>

        {/* Sentiment bars */}
        <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4">
          <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-4">
            市场情绪
          </h2>
          {topSymbols.length > 0 ? (
            <div className="space-y-3">
              {topSymbols.map(([symbol, data]) => (
                <SentimentBar
                  key={symbol}
                  symbol={symbol}
                  bullish={data.bullish}
                  bearish={data.bearish}
                />
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-32 text-[var(--text-muted)] text-sm">
              暂无数据
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
