"use client";

import { useState, useEffect, useRef } from "react";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";
import { isUSMarketOpen } from "@/lib/format";
import { useWatchlistStore } from "@/store/watchlistStore";

dayjs.extend(utc);
dayjs.extend(timezone);

export function Navbar() {
  const [time, setTime] = useState("");
  const [marketOpen, setMarketOpen] = useState(false);
  const syncFromServer = useWatchlistStore((s) => s.syncFromServer);
  const synced = useWatchlistStore((s) => s.synced);
  const syncRef = useRef(false);

  useEffect(() => {
    if (!syncRef.current && !synced) {
      syncRef.current = true;
      syncFromServer();
    }
  }, [syncFromServer, synced]);

  useEffect(() => {
    const tick = () => {
      setTime(dayjs().tz("Asia/Shanghai").format("YYYY-MM-DD HH:mm:ss"));
      setMarketOpen(isUSMarketOpen());
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-14 border-b border-[var(--border-color)] bg-[var(--bg-card)] flex items-center justify-between px-4 md:px-6 shrink-0">
      <div className="flex items-center gap-3 md:hidden">
        <span className="text-lg font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
          OptionFlow Pro
        </span>
      </div>

      <div className="hidden md:block" />

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              marketOpen ? "bg-green-400 animate-pulse" : "bg-gray-500"
            }`}
          />
          <span className="text-xs text-[var(--text-secondary)]">
            {marketOpen ? "美股开盘中" : "美股休市"}
          </span>
        </div>

        <div className="text-xs text-[var(--text-muted)] font-mono tabular-nums">
          北京时间 {time}
        </div>
      </div>
    </header>
  );
}
