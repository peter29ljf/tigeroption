"use client";

import { FilterBar } from "@/components/FilterBar";
import { FlowTable } from "@/components/FlowTable";
import { useFlowStream } from "@/hooks/useFlowStream";
import { useFlowStore } from "@/store/flowStore";

export default function FlowsPage() {
  const { filters } = useFlowStore();
  const { connected, flows } = useFlowStream(filters);

  const filtered = flows.filter((f) => {
    if (filters.symbols.length > 0 && !filters.symbols.includes(f.symbol)) return false;
    if (filters.min_premium > 0 && f.premium < filters.min_premium * 100) return false;
    if (filters.direction !== "ALL" && f.direction !== filters.direction) return false;
    if (filters.min_score > 0 && f.score < filters.min_score) return false;
    return true;
  });

  return (
    <div className="space-y-6 pb-20 md:pb-0">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-[var(--text-primary)]">实时流</h1>
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              connected ? "bg-green-400 animate-pulse" : "bg-red-400"
            }`}
          />
          <span className="text-xs text-[var(--text-secondary)]">
            {connected ? "已连接" : "未连接"}
          </span>
          <span className="text-xs text-[var(--text-muted)] ml-2">
            {filtered.length} 条记录
          </span>
        </div>
      </div>

      <FilterBar />

      <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4">
        <FlowTable flows={filtered} />
      </div>
    </div>
  );
}
