"use client";

import { useState } from "react";
import { useAlertRules, type AlertRule } from "@/hooks/useFlows";

const DIRECTION_OPTIONS = [
  { value: "", label: "不限" },
  { value: "BULLISH", label: "看涨" },
  { value: "BEARISH", label: "看跌" },
];

export default function AlertsPage() {
  const { rules, loading, createRule, toggleRule, deleteRule } = useAlertRules();

  const [symbol, setSymbol] = useState("");
  const [minScore, setMinScore] = useState(60);
  const [direction, setDirection] = useState("");
  const [minPremium, setMinPremium] = useState("");
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    setCreating(true);
    try {
      await createRule({
        symbol: symbol || undefined,
        min_score: minScore,
        direction: direction || undefined,
        min_premium: minPremium ? Number(minPremium) : undefined,
        active: true,
      });
      setSymbol("");
      setMinScore(60);
      setDirection("");
      setMinPremium("");
    } catch {
      /* handle error */
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6 pb-20 md:pb-0">
      <h1 className="text-xl font-bold text-[var(--text-primary)]">告警规则</h1>

      {/* Create rule form */}
      <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4 space-y-4">
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">新建规则</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="text-xs text-[var(--text-muted)] mb-1 block">标的 (可选)</label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="例如: NVDA"
              className="w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-blue)]"
            />
          </div>
          <div>
            <label className="text-xs text-[var(--text-muted)] mb-1 block">
              最低评分: <span className="text-[var(--text-primary)]">{minScore}</span>
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-full mt-2"
            />
          </div>
          <div>
            <label className="text-xs text-[var(--text-muted)] mb-1 block">方向</label>
            <select
              value={direction}
              onChange={(e) => setDirection(e.target.value)}
              className="w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-blue)]"
            >
              {DIRECTION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-[var(--text-muted)] mb-1 block">最低溢价 (USD)</label>
            <input
              type="number"
              value={minPremium}
              onChange={(e) => setMinPremium(e.target.value)}
              placeholder="例如: 50000"
              className="w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-blue)]"
            />
          </div>
        </div>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="px-6 py-2 bg-[var(--accent-blue)] hover:bg-[var(--accent-blue)]/80 disabled:opacity-50 text-white text-sm font-medium rounded transition-colors"
        >
          {creating ? "创建中..." : "创建规则"}
        </button>
      </div>

      {/* Rules list */}
      <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4">
        <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-4">已有规则</h2>

        {loading && (
          <div className="flex items-center justify-center h-32 text-[var(--text-muted)]">
            加载中...
          </div>
        )}

        {!loading && rules.length === 0 && (
          <div className="flex items-center justify-center h-32 text-[var(--text-muted)] text-sm">
            暂无告警规则
          </div>
        )}

        {rules.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-color)] text-[var(--text-muted)]">
                  <th className="text-left py-3 px-3 font-medium">标的</th>
                  <th className="text-center py-3 px-3 font-medium">最低评分</th>
                  <th className="text-center py-3 px-3 font-medium">方向</th>
                  <th className="text-right py-3 px-3 font-medium">最低溢价</th>
                  <th className="text-center py-3 px-3 font-medium">状态</th>
                  <th className="text-center py-3 px-3 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr
                    key={rule.id}
                    className="border-b border-[var(--border-color)]/50 hover:bg-[var(--bg-card-hover)] transition-colors"
                  >
                    <td className="py-2.5 px-3 font-medium text-[var(--text-primary)]">
                      {rule.symbol || "全部"}
                    </td>
                    <td className="py-2.5 px-3 text-center text-[var(--text-secondary)]">
                      {rule.min_score}
                    </td>
                    <td className="py-2.5 px-3 text-center text-[var(--text-secondary)]">
                      {rule.direction === "BULLISH"
                        ? "看涨"
                        : rule.direction === "BEARISH"
                        ? "看跌"
                        : "不限"}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-[var(--text-secondary)]">
                      {rule.min_premium
                        ? `$${rule.min_premium.toLocaleString()}`
                        : "—"}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <button
                        onClick={() => toggleRule(rule.id, !rule.active)}
                        className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                          rule.active
                            ? "bg-green-500/20 text-green-400"
                            : "bg-gray-500/20 text-gray-400"
                        }`}
                      >
                        {rule.active ? "已启用" : "已停用"}
                      </button>
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <button
                        onClick={() => deleteRule(rule.id)}
                        className="text-red-400 hover:text-red-300 text-xs transition-colors"
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
