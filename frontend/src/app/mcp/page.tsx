"use client";

import { useState } from "react";

const TOOLS = [
  {
    name: "get_abnormal_flows",
    desc: "获取当前异常大单列表（评分≥75、大额扫单、暗池大单）",
    params: [{ name: "limit", type: "int", default: "50", desc: "返回条数上限（最大500）" }],
  },
  {
    name: "get_symbol_analysis",
    desc: "获取个股期权大单综合分析（大单数、评分、情绪比、Top流）",
    params: [
      { name: "symbol", type: "string", required: true, desc: "股票代码，如 NVDA" },
      { name: "days", type: "int", default: "7", desc: "统计天数（1-90）" },
    ],
  },
  {
    name: "get_market_sentiment",
    desc: "获取全市场看涨/看跌情绪分布",
    params: [{ name: "hours", type: "int", default: "24", desc: "统计时间窗口小时数（1-168）" }],
  },
  {
    name: "get_flow_stats",
    desc: "获取近1小时大单统计摘要（总数、平均评分、多空数量）",
    params: [],
  },
  {
    name: "search_symbol",
    desc: "通过公司名或代码片段搜索美股标的",
    params: [{ name: "query", type: "string", required: true, desc: "搜索词，如 apple 或 NVD" }],
  },
  {
    name: "get_gex",
    desc: "获取个股 Gamma 曝露（GEX）分布，识别价格支撑/阻力区",
    params: [{ name: "symbol", type: "string", required: true, desc: "股票代码" }],
  },
  {
    name: "get_oi_distribution",
    desc: "获取个股未平仓量（OI）分布，含 P/C 比率",
    params: [
      { name: "symbol", type: "string", required: true, desc: "股票代码" },
      { name: "expiry_count", type: "int", default: "2", desc: "统计近N个到期日（1-5）" },
    ],
  },
];

const DESKTOP_CONFIG_LOCAL = `{
  "mcpServers": {
    "optionflow": {
      "command": "python",
      "args": ["-m", "services.mcp.server"],
      "cwd": "/path/to/optionflow-pro",
      "env": {
        "OPTIONFLOW_API_URL": "http://localhost:8000"
      }
    }
  }
}`;

const DESKTOP_CONFIG_REMOTE = `{
  "mcpServers": {
    "optionflow": {
      "url": "http://your-server-ip:8001/sse"
    }
  }
}`;

const CODE_CONFIG_LOCAL = `{
  "mcpServers": {
    "optionflow": {
      "command": "python",
      "args": ["-m", "services.mcp.server"],
      "cwd": "/path/to/optionflow-pro",
      "env": {
        "OPTIONFLOW_API_URL": "http://localhost:8000"
      }
    }
  }
}`;

const CODE_CONFIG_REMOTE = `{
  "mcpServers": {
    "optionflow": {
      "url": "http://your-server-ip:8001/sse"
    }
  }
}`;

const EXAMPLE_PROMPTS = [
  "帮我分析当前异常大单，是否有集中布局的迹象？",
  "获取 NVDA 最近7天的期权大单情况，给出交易方向建议。",
  "对比 NVDA 和 AMD 的市场情绪，哪个更值得关注？",
  "当前市场整体偏多还是偏空？给出理由。",
  "TSLA 的 GEX 显示最大支撑位在哪里？",
  "SPY 的未平仓量分布如何？P/C 比率说明什么？",
];

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
    >
      {copied ? (
        <>
          <svg className="w-3.5 h-3.5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          已复制
        </>
      ) : (
        <>
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          复制
        </>
      )}
    </button>
  );
}

function CodeBlock({ code, label }: { code: string; label?: string }) {
  return (
    <div className="rounded-lg overflow-hidden border border-[var(--border-color)]">
      {label && (
        <div className="flex items-center justify-between px-4 py-2 bg-[var(--bg-primary)] border-b border-[var(--border-color)]">
          <span className="text-xs text-[var(--text-muted)] font-mono">{label}</span>
          <CopyButton text={code} />
        </div>
      )}
      <pre className="p-4 overflow-x-auto text-xs text-[var(--text-secondary)] bg-[var(--bg-card)] font-mono leading-relaxed">
        {code}
      </pre>
      {!label && (
        <div className="flex justify-end px-3 py-2 border-t border-[var(--border-color)] bg-[var(--bg-card)]">
          <CopyButton text={code} />
        </div>
      )}
    </div>
  );
}

export default function MCPPage() {
  return (
    <div className="space-y-8 pb-20 md:pb-0 max-w-3xl">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-[var(--text-primary)] mb-2">MCP 工具配置</h1>
        <p className="text-sm text-[var(--text-muted)] leading-relaxed">
          通过{" "}
          <span className="text-[var(--text-primary)] font-medium">Model Context Protocol (MCP)</span>
          ，让 Claude Desktop 和 Claude Code 直接读取本应用的实时大单数据，进行智能分析。
        </p>
      </div>

      {/* Tools list */}
      <section className="space-y-3">
        <h2 className="text-base font-semibold text-[var(--text-primary)]">可用工具（7 个）</h2>
        <div className="space-y-2">
          {TOOLS.map((tool) => (
            <div
              key={tool.name}
              className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 space-y-2"
            >
              <div className="flex items-start gap-3">
                <code className="text-xs font-mono text-[var(--accent-blue)] bg-[var(--accent-blue)]/10 px-2 py-0.5 rounded shrink-0">
                  {tool.name}
                </code>
                <p className="text-sm text-[var(--text-secondary)]">{tool.desc}</p>
              </div>
              {tool.params.length > 0 && (
                <div className="flex flex-wrap gap-2 pl-1">
                  {tool.params.map((p) => (
                    <span
                      key={p.name}
                      className="text-xs text-[var(--text-muted)] bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-2 py-0.5"
                    >
                      <span className="text-[var(--text-primary)]">{p.name}</span>
                      <span className="text-[var(--text-muted)]">: {p.type}</span>
                      {"required" in p
                        ? <span className="text-red-400 ml-1">*必填</span>
                        : <span className="text-[var(--text-muted)] ml-1">= {(p as { default: string }).default}</span>
                      }
                      <span className="ml-1">— {p.desc}</span>
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Setup steps */}
      <section className="space-y-4">
        <h2 className="text-base font-semibold text-[var(--text-primary)]">快速启动</h2>

        <div className="space-y-2">
          <p className="text-sm text-[var(--text-muted)]">
            <span className="text-[var(--text-primary)] font-medium">Step 1</span>{" "}
            安装 MCP 依赖（首次使用）
          </p>
          <CodeBlock code="pip install mcp" />
        </div>

        <div className="space-y-2">
          <p className="text-sm text-[var(--text-muted)]">
            <span className="text-[var(--text-primary)] font-medium">Step 2</span>{" "}
            确保本应用 API 已在运行（默认端口 8000）
          </p>
          <CodeBlock code="uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload" />
        </div>

        <div className="space-y-2">
          <p className="text-sm text-[var(--text-muted)]">
            <span className="text-[var(--text-primary)] font-medium">Step 3（远程访问）</span>{" "}
            以 SSE/HTTP 模式启动 MCP server，供远程客户端连接
          </p>
          <CodeBlock code="python -m services.mcp.server --transport sse --host 0.0.0.0 --port 8001" />
          <p className="text-xs text-[var(--text-muted)]">
            本地模式无需此步骤，直接跳到 Step 4 配置客户端即可。
          </p>
        </div>

        <div className="space-y-2">
          <p className="text-sm text-[var(--text-muted)]">
            <span className="text-[var(--text-primary)] font-medium">Step 4</span>{" "}
            配置 Claude Desktop 或 Claude Code（见下方）
          </p>
        </div>
      </section>

      {/* Claude Desktop config */}
      <section className="space-y-3">
        <h2 className="text-base font-semibold text-[var(--text-primary)]">Claude Desktop 配置</h2>
        <p className="text-xs text-[var(--text-muted)]">
          配置文件位置：
          <code className="text-[var(--text-primary)] ml-1">
            ~/Library/Application Support/Claude/claude_desktop_config.json
          </code>
          （macOS）
        </p>

        <p className="text-xs text-[var(--text-muted)] font-medium text-[var(--text-primary)]">方式一：本地模式（Claude Desktop 与项目在同一台机器）</p>
        <p className="text-xs text-[var(--text-muted)]">
          将 <code className="text-[var(--text-primary)]">/path/to/optionflow-pro</code> 替换为项目实际路径。
        </p>
        <CodeBlock code={DESKTOP_CONFIG_LOCAL} label="claude_desktop_config.json（本地）" />

        <p className="text-xs text-[var(--text-muted)] font-medium text-[var(--text-primary)] pt-2">方式二：远程模式（MCP server 跑在服务器上）</p>
        <p className="text-xs text-[var(--text-muted)]">
          将 <code className="text-[var(--text-primary)]">your-server-ip</code> 替换为实际服务器 IP 或域名。
          无需在本地安装任何依赖。
        </p>
        <CodeBlock code={DESKTOP_CONFIG_REMOTE} label="claude_desktop_config.json（远程）" />
      </section>

      {/* Claude Code config */}
      <section className="space-y-3">
        <h2 className="text-base font-semibold text-[var(--text-primary)]">Claude Code 配置</h2>
        <p className="text-xs text-[var(--text-muted)]">
          在项目根目录创建或编辑{" "}
          <code className="text-[var(--text-primary)]">.mcp.json</code>，添加以下内容：
        </p>

        <p className="text-xs text-[var(--text-muted)] font-medium text-[var(--text-primary)]">方式一：本地模式</p>
        <CodeBlock code={CODE_CONFIG_LOCAL} label=".mcp.json（本地）" />

        <p className="text-xs text-[var(--text-muted)] font-medium text-[var(--text-primary)] pt-2">方式二：远程模式</p>
        <CodeBlock code={CODE_CONFIG_REMOTE} label=".mcp.json（远程）" />

        <p className="text-xs text-[var(--text-muted)]">
          配置完成后在 Claude Code 会话中运行{" "}
          <code className="text-[var(--text-primary)]">/mcp</code> 查看可用工具列表。
        </p>
      </section>

      {/* Example prompts */}
      <section className="space-y-3">
        <h2 className="text-base font-semibold text-[var(--text-primary)]">示例提问</h2>
        <p className="text-xs text-[var(--text-muted)]">配置完成后，可以直接对 Claude 说：</p>
        <div className="space-y-2">
          {EXAMPLE_PROMPTS.map((prompt, i) => (
            <div
              key={i}
              className="flex items-center justify-between gap-3 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg px-4 py-3"
            >
              <span className="text-sm text-[var(--text-secondary)]">{prompt}</span>
              <CopyButton text={prompt} />
            </div>
          ))}
        </div>
      </section>

      {/* Note */}
      <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4 text-xs text-yellow-400 leading-relaxed space-y-1">
        <p>注意：无论哪种模式，OptionFlow Pro 后端（端口 8000）必须持续运行，MCP server 会调用它获取数据。</p>
        <p>远程模式下，确保服务器防火墙开放 8001 端口（MCP SSE）和 8000 端口（API），或通过 Nginx 反代并配置 HTTPS。</p>
      </div>
    </div>
  );
}
