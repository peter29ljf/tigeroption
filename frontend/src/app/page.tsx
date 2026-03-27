import { apiFetch } from "@/lib/api";
import { DashboardClient } from "./DashboardClient";

interface FlowStats {
  total_flows: number;
  avg_score: number;
  bullish_ratio: number;
  sweep_ratio: number;
}

interface Flow {
  id: string;
  symbol: string;
  strike: number;
  expiry: string;
  put_call: string;
  direction: "BULLISH" | "BEARISH" | "NEUTRAL";
  premium: number;
  score: number;
  is_sweep: boolean;
  ai_note?: string;
  timestamp: string;
}

interface SentimentData {
  [symbol: string]: { bullish: number; bearish: number; neutral: number };
}

async function getStats(): Promise<FlowStats | null> {
  try {
    const raw = await apiFetch<Record<string, number | null>>("/api/v1/flows/stats");
    const total = Number(raw.total_count ?? raw.total_flows ?? 0);
    const bullish = Number(raw.bullish_count ?? 0);
    const bearish = Number(raw.bearish_count ?? 0);
    const sweep = Number(raw.sweep_count ?? 0);
    const denom = total || 1;
    return {
      total_flows: total,
      avg_score: Number(raw.avg_score ?? 0),
      bullish_ratio: bullish / denom,
      sweep_ratio: sweep / denom,
    };
  } catch {
    return null;
  }
}

async function getLatestFlows(): Promise<Flow[]> {
  try {
    const raw = await apiFetch<unknown>("/api/v1/flows?limit=10");
    if (Array.isArray(raw)) return raw as Flow[];
    return [];
  } catch {
    return [];
  }
}

async function getSentiment(): Promise<SentimentData | null> {
  try {
    const raw = await apiFetch<Record<string, unknown>>("/api/v1/market/sentiment");
    // API returns { symbols: [{symbol, bullish_count, bearish_count}] }
    // or already in { SYMBOL: {bullish, bearish, neutral} } format
    if (raw.symbols && Array.isArray(raw.symbols)) {
      const result: SentimentData = {};
      for (const item of raw.symbols as Array<Record<string, unknown>>) {
        const sym = String(item.symbol ?? "");
        if (sym) {
          result[sym] = {
            bullish: Number(item.bullish_count ?? item.bullish ?? 0),
            bearish: Number(item.bearish_count ?? item.bearish ?? 0),
            neutral: Number(item.neutral_count ?? item.neutral ?? 0),
          };
        }
      }
      return Object.keys(result).length ? result : null;
    }
    // Already in expected format
    return raw as SentimentData;
  } catch {
    return null;
  }
}

export const revalidate = 30;

export default async function DashboardPage() {
  const [stats, flows, sentiment] = await Promise.all([
    getStats(),
    getLatestFlows(),
    getSentiment(),
  ]);

  return <DashboardClient stats={stats} flows={flows} sentiment={sentiment} />;
}
