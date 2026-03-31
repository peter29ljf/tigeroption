"""
OptionFlow Pro MCP Server
~~~~~~~~~~~~~~~~~~~~~~~~~
Exposes OptionFlow Pro data as MCP tools for Claude Desktop / Claude Code.

Usage:
    # stdio mode (local, default)
    python -m services.mcp.server

    # SSE/HTTP mode (remote access)
    python -m services.mcp.server --transport sse --host 0.0.0.0 --port 8001

Environment:
    OPTIONFLOW_API_URL  Base URL of the running API (default: http://localhost:8000)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from mcp import types
from starlette.applications import Starlette
from starlette.routing import Mount, Route

API_BASE = os.getenv("OPTIONFLOW_API_URL", "http://localhost:8000").rstrip("/")

server = Server("optionflow-pro")


def _fmt(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


async def _get(path: str, params: dict | None = None) -> object:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{API_BASE}{path}", params=params or {})
        resp.raise_for_status()
        return resp.json()


# ── Tool definitions ──────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_abnormal_flows",
            description=(
                "获取当前标记的异常期权大单列表。"
                "异常大单包括：高评分信号（≥75分）、大额扫单（≥$200k）、暗池大单（≥$500k）。"
                "返回字段：symbol、方向、溢价、评分、是否扫单、是否暗池、异常原因、时间戳。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回条数上限，默认50，最大500",
                        "default": 50,
                    }
                },
            },
        ),
        types.Tool(
            name="get_symbol_analysis",
            description=(
                "获取指定美股标的的期权大单综合分析。"
                "包含：过去N天内的大单数量、平均评分、看涨/看跌比例、当前股价、Top 10 高溢价大单。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码，如 NVDA、AAPL、SPY",
                    },
                    "days": {
                        "type": "integer",
                        "description": "统计天数，默认7天，范围1-90",
                        "default": 7,
                    },
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="get_market_sentiment",
            description=(
                "获取全市场期权大单情绪分布。"
                "统计自选标的在指定时间窗口内的看涨/看跌大单数量和比例，反映机构资金整体偏向。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "统计时间窗口（小时），默认24小时，范围1-168",
                        "default": 24,
                    }
                },
            },
        ),
        types.Tool(
            name="get_flow_stats",
            description=(
                "获取近1小时期权大单统计摘要。"
                "包含：总大单数、平均评分、看涨数量、看跌数量。"
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="search_symbol",
            description=(
                "通过股票代码或公司名搜索美股标的。"
                "例如输入 'apple' 返回 AAPL，输入 'nvidia' 返回 NVDA。"
                "仅返回美股（EQUITY/ETF），过滤海外市场。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，可以是股票代码片段或公司名称",
                    }
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_gex",
            description=(
                "获取指定标的的 Gamma 曝露（GEX）分布。"
                "GEX 反映做市商在各价位的 delta 对冲压力，高 GEX 区域对股价有磁铁效应（支撑/阻力）。"
                "返回各行权价的 Call GEX、Put GEX、Net GEX，以及当前 GEX 最大值所在行权价。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码，如 NVDA、SPY",
                    }
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="get_oi_distribution",
            description=(
                "获取指定标的的未平仓量（OI）分布。"
                "包含各行权价的 Call OI、Put OI、P/C 比率。"
                "P/C 比率 > 1.5 通常表示机构偏空，< 0.7 偏多。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码，如 NVDA、AAPL",
                    },
                    "expiry_count": {
                        "type": "integer",
                        "description": "统计的最近到期合约数，默认2，范围1-5",
                        "default": 2,
                    },
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="get_gex_surface",
            description=(
                "获取个股 GEX 按到期日分组的详细数据（行权价 × 到期日 × Gamma曝露）。"
                "比 get_gex 多了到期日维度，可识别不同到期日的 GEX 分布差异和关键支撑/阻力位。"
                "返回字段：strike（行权价）、expiry（到期日）、call_gex、put_gex、net_gex。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码，如 NVDA、SPY",
                    },
                    "expiry_count": {
                        "type": "integer",
                        "description": "统计的到期日数量，默认4，范围1-6",
                        "default": 4,
                    },
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="get_oi_surface",
            description=(
                "获取个股 OI 按到期日分组的详细数据（行权价 × 到期日 × 未平仓量）。"
                "比 get_oi_distribution 多了到期日维度，可对比不同到期日的 OI 堆积和机构重仓区。"
                "返回字段：strike（行权价）、expiry（到期日）、call_oi、put_oi，及整体 P/C 比率。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码，如 NVDA、AAPL",
                    },
                    "expiry_count": {
                        "type": "integer",
                        "description": "统计的到期日数量，默认4，范围1-6",
                        "default": 4,
                    },
                },
                "required": ["symbol"],
            },
        ),
    ]


# ── Tool dispatcher ───────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        result = await _dispatch(name, arguments)
        return [types.TextContent(type="text", text=_fmt(result))]
    except httpx.HTTPStatusError as e:
        return [types.TextContent(type="text", text=f"API 错误 {e.response.status_code}: {e.response.text}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"调用失败: {e}")]


async def _dispatch(name: str, args: dict) -> object:
    if name == "get_abnormal_flows":
        limit = int(args.get("limit", 50))
        return await _get("/api/v1/abnormal", {"limit": limit})

    elif name == "get_symbol_analysis":
        symbol = str(args["symbol"]).upper()
        days = int(args.get("days", 7))
        return await _get(f"/api/v1/analysis/{symbol}", {"days": days})

    elif name == "get_market_sentiment":
        hours = int(args.get("hours", 24))
        return await _get("/api/v1/market/sentiment", {"hours": hours})

    elif name == "get_flow_stats":
        return await _get("/api/v1/flows/stats")

    elif name == "search_symbol":
        query = str(args["query"])
        return await _get("/api/v1/search", {"q": query})

    elif name == "get_gex":
        symbol = str(args["symbol"]).upper()
        return await _get(f"/api/v1/analysis/{symbol}/gex")

    elif name == "get_oi_distribution":
        symbol = str(args["symbol"]).upper()
        expiry_count = int(args.get("expiry_count", 2))
        return await _get(
            f"/api/v1/analysis/{symbol}/oi-distribution",
            {"expiry_count": expiry_count},
        )

    elif name == "get_gex_surface":
        symbol = str(args["symbol"]).upper()
        expiry_count = int(args.get("expiry_count", 4))
        return await _get(
            f"/api/v1/analysis/{symbol}/gex-surface",
            {"expiry_count": expiry_count},
        )

    elif name == "get_oi_surface":
        symbol = str(args["symbol"]).upper()
        expiry_count = int(args.get("expiry_count", 4))
        return await _get(
            f"/api/v1/analysis/{symbol}/oi-surface",
            {"expiry_count": expiry_count},
        )

    else:
        raise ValueError(f"Unknown tool: {name}")


# ── Entry point ───────────────────────────────────────────────────────────────

async def _run_stdio() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def _run_sse(host: str, port: int) -> None:
    import uvicorn

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )

    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )
    print(f"OptionFlow MCP SSE server listening on http://{host}:{port}/sse")
    uvicorn.run(starlette_app, host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OptionFlow Pro MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport mode: stdio (local) or sse (remote HTTP, default: stdio)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="SSE bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8001, help="SSE bind port (default: 8001)")
    args = parser.parse_args()

    if args.transport == "sse":
        _run_sse(args.host, args.port)
    else:
        asyncio.run(_run_stdio())
