"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import type { Flow, FlowFilters } from "@/store/flowStore";

interface UseDataResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

function useApi<T>(path: string | null): UseDataResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!path) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiFetch<T>(path)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [path]);

  return { data, loading, error };
}

export function useFlows(filters?: Partial<FlowFilters>) {
  const params = new URLSearchParams();
  if (filters?.symbols?.length) {
    filters.symbols.forEach((s) => params.append("symbol", s));
  }
  if (filters?.min_premium) params.set("min_premium", String(filters.min_premium));
  if (filters?.direction && filters.direction !== "ALL") {
    params.set("direction", filters.direction);
  }
  if (filters?.min_score) params.set("min_score", String(filters.min_score));

  const query = params.toString();
  const path = `/api/v1/flows${query ? `?${query}` : ""}`;
  return useApi<Flow[]>(path);
}

export interface FlowStats {
  total_flows: number;
  avg_score: number;
  bullish_ratio: number;
  sweep_ratio: number;
}

export function useFlowStats() {
  return useApi<FlowStats>("/api/v1/flows/stats");
}

export interface SymbolAnalysis {
  symbol: string;
  current_price?: number;
  flow_count: number;
  avg_score: number;
  bullish_count: number;
  bearish_count: number;
  top_flows: Flow[];
}

export function useAnalysis(symbol: string, days = 7) {
  return useApi<SymbolAnalysis>(
    symbol ? `/api/v1/analysis/${symbol}?days=${days}` : null
  );
}

export interface SentimentData {
  [symbol: string]: { bullish: number; bearish: number; neutral: number };
}

export function useSentiment() {
  return useApi<SentimentData>("/api/v1/market/sentiment");
}

export interface AlertRule {
  id: string;
  symbol?: string;
  min_score: number;
  direction?: string;
  min_premium?: number;
  active: boolean;
}

export interface CandleBar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export function usePrices(symbol: string, days = 60) {
  return useApi<CandleBar[]>(
    symbol ? `/api/v1/analysis/${symbol}/prices?days=${days}` : null
  );
}

export interface ChainSnapshotRow {
  strike: number;
  expiry: string;
  call_volume: number;
  put_volume: number;
  call_premium: number;
  put_premium: number;
}

export interface ChainSnapshot {
  symbol: string;
  rows: ChainSnapshotRow[];
}

export function useChainSnapshot(symbol: string, hours = 24) {
  return useApi<ChainSnapshot>(
    symbol ? `/api/v1/analysis/${symbol}/chain-snapshot?hours=${hours}` : null
  );
}

export interface GEXStrike {
  strike: number;
  call_gex: number;
  put_gex: number;
  net_gex: number;
}

export interface GEXData {
  symbol: string;
  strikes: GEXStrike[];
  max_gex_strike: number | null;
  stock_price: number | null;
}

export function useGEX(symbol: string) {
  return useApi<GEXData>(
    symbol ? `/api/v1/analysis/${symbol}/gex` : null
  );
}

export interface OIStrike {
  strike: number;
  call_oi: number;
  put_oi: number;
  net_oi: number;
}

export interface OIDistribution {
  symbol: string;
  put_call_oi_ratio: number | null;
  total_call_oi: number;
  total_put_oi: number;
  strikes: OIStrike[];
  top_oi_strikes: { strike: number; total_oi: number }[];
}

export function useOIDistribution(symbol: string, expiryCount = 2) {
  return useApi<OIDistribution>(
    symbol
      ? `/api/v1/analysis/${symbol}/oi-distribution?expiry_count=${expiryCount}`
      : null
  );
}

export function useAlertRules() {
  const result = useApi<AlertRule[]>("/api/v1/alerts");
  const [rules, setRules] = useState<AlertRule[]>([]);

  useEffect(() => {
    if (result.data) setRules(result.data);
  }, [result.data]);

  const createRule = useCallback(
    async (rule: Omit<AlertRule, "id">) => {
      const created = await apiFetch<AlertRule>("/api/v1/alerts", {
        method: "POST",
        body: JSON.stringify(rule),
      });
      setRules((prev) => [...prev, created]);
      return created;
    },
    []
  );

  const toggleRule = useCallback(async (id: string, active: boolean) => {
    await apiFetch(`/api/v1/alerts/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ active }),
    });
    setRules((prev) =>
      prev.map((r) => (r.id === id ? { ...r, active } : r))
    );
  }, []);

  const deleteRule = useCallback(async (id: string) => {
    await apiFetch(`/api/v1/alerts/${id}`, { method: "DELETE" });
    setRules((prev) => prev.filter((r) => r.id !== id));
  }, []);

  return { rules, loading: result.loading, error: result.error, createRule, toggleRule, deleteRule };
}

export interface SignalStats {
  total: number;
  d5_win_rate: number | null;
  d10_win_rate: number | null;
  d30_win_rate: number | null;
  d5_avg_return: number | null;
  d10_avg_return: number | null;
  d30_avg_return: number | null;
}

export function useSignalStats(
  direction?: string,
  minScore = 60,
  symbol?: string
) {
  const params = new URLSearchParams();
  if (direction) params.set("direction", direction);
  params.set("min_score", String(minScore));
  if (symbol) params.set("symbol", symbol);
  const path = `/api/v1/backtest/stats?${params.toString()}`;
  return useApi<SignalStats>(path);
}
