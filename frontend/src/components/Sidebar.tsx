"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import clsx from "clsx";

const NAV_ITEMS = [
  { href: "/", label: "大盘监控", icon: "📊" },
  { href: "/flows", label: "实时流", icon: "📈" },
  { href: "/analysis/SPY", label: "个股分析", icon: "🔍" },
  { href: "/alerts", label: "告警规则", icon: "🔔" },
  { href: "/abnormal", label: "异常大单", icon: "⚡" },
  { href: "/mcp", label: "MCP 工具", icon: "🔌" },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={clsx(
          "hidden md:flex flex-col bg-[var(--bg-sidebar)] border-r border-[var(--border-color)] transition-all duration-300 shrink-0",
          collapsed ? "w-16" : "w-56"
        )}
      >
        <div className="h-14 flex items-center px-4 border-b border-[var(--border-color)]">
          {!collapsed && (
            <span className="text-lg font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent whitespace-nowrap">
              OptionFlow Pro
            </span>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className={clsx(
              "text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors",
              collapsed ? "mx-auto" : "ml-auto"
            )}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {collapsed ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
              )}
            </svg>
          </button>
        </div>

        <nav className="flex-1 py-4 space-y-1 px-2">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                isActive(item.href)
                  ? "bg-[var(--accent-blue)]/15 text-[var(--accent-blue)]"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]"
              )}
            >
              <span className="text-base shrink-0">{item.icon}</span>
              {!collapsed && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        {!collapsed && (
          <div className="p-4 border-t border-[var(--border-color)]">
            <p className="text-[10px] text-[var(--text-muted)]">
              OptionFlow Pro v0.1.0
            </p>
          </div>
        )}
      </aside>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-[var(--bg-card)] border-t border-[var(--border-color)] flex">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={clsx(
              "flex-1 flex flex-col items-center gap-1 py-2 text-xs transition-colors",
              isActive(item.href)
                ? "text-[var(--accent-blue)]"
                : "text-[var(--text-muted)]"
            )}
          >
            <span className="text-lg">{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
    </>
  );
}
