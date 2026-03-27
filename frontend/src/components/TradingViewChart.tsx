"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type CandlestickData,
  type Time,
} from "lightweight-charts";

export interface CandleBar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface FlowMarker {
  time: string;
  direction: "BULLISH" | "BEARISH" | "NEUTRAL";
  premium: number;
  score: number;
}

interface Props {
  data: CandleBar[];
  markers?: FlowMarker[];
  height?: number;
}

export function TradingViewChart({ data, markers = [], height = 320 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.05)" },
        horzLines: { color: "rgba(255,255,255,0.05)" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.1)" },
      timeScale: { borderColor: "rgba(255,255,255,0.1)", timeVisible: true },
    });
    chartRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    const candles: CandlestickData[] = data.map((b) => ({
      time: b.time as Time,
      open: b.open,
      high: b.high,
      low: b.low,
      close: b.close,
    }));
    candleSeries.setData(candles);

    // Flow markers
    if (markers.length > 0) {
      const markerList = markers.map((m) => ({
        time: m.time as Time,
        position: m.direction === "BULLISH" ? ("belowBar" as const) : ("aboveBar" as const),
        color: m.direction === "BULLISH" ? "#22c55e" : "#ef4444",
        shape: m.direction === "BULLISH" ? ("arrowUp" as const) : ("arrowDown" as const),
        text: `${m.score}分`,
      }));
      candleSeries.setMarkers(markerList);
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [data, markers, height]);

  if (data.length === 0) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center border border-dashed border-[var(--border-color)] rounded-lg text-[var(--text-muted)] text-sm"
      >
        暂无价格数据（交易时段外）
      </div>
    );
  }

  return <div ref={containerRef} style={{ height }} className="w-full" />;
}
