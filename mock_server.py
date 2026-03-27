#!/usr/bin/env python3
"""
Mock API server for OptionFlow Pro frontend testing.
Serves fake option flow data on port 8000.
"""
import json
import random
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta, timezone
import threading

SYMBOLS = ["NVDA", "AAPL", "TSLA", "SPY", "QQQ", "AMZN", "MSFT", "META", "GOOGL", "AMD"]

def random_flow(i: int = 0) -> dict:
    symbol = random.choice(SYMBOLS)
    put_call = random.choice(["C", "P"])
    direction = random.choices(
        ["BULLISH", "BEARISH", "NEUTRAL"],
        weights=[0.45, 0.35, 0.20]
    )[0]
    score = random.randint(55, 99) if direction != "NEUTRAL" else random.randint(30, 60)
    premium = random.randint(1_000_000_000, 50_000_000_000)  # cents
    base_prices = {
        "NVDA": 850, "AAPL": 220, "TSLA": 280, "SPY": 560, "QQQ": 490,
        "AMZN": 210, "MSFT": 430, "META": 600, "GOOGL": 185, "AMD": 165,
    }
    stock_price = base_prices[symbol] + random.uniform(-10, 10)
    strike_options = [round(stock_price * m / 5) * 5 for m in [0.9, 0.95, 1.0, 1.05, 1.10]]
    strike = random.choice(strike_options)
    days_ahead = random.choice([3, 7, 14, 21, 45, 60, 90])
    expiry = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc)
    ts = (now - timedelta(minutes=random.randint(0, 60))).isoformat()
    ai_notes = [
        f"NVDA | 850 Call | 03/28到期 | 信号强度：{score}/100 | 方向：强看涨↑↑ | 主动买入，Vol/OI达{random.uniform(1.2,3.5):.1f}x，距行权价+{random.uniform(0.5,5):.1f}%，扫单特征明显，看多情绪强烈。⚠️仅供参考，不构成投资建议",
        f"TSLA | 280 Call | 04/17到期 | 信号强度：{score}/100 | 方向：强看涨↑↑ | 大额主动买入，溢价${premium/100/1e6:.1f}M，Vol/OI={random.uniform(0.8,2.5):.1f}x，机构布局迹象，短期看多。⚠️仅供参考，不构成投资建议",
        f"SPY | 560 Put | 04/04到期 | 信号强度：{score}/100 | 方向：强看跌↓↓ | 大额保护性买入，距行权价-{random.uniform(0.5,3):.1f}%，或为对冲操作，市场存在下行风险。⚠️仅供参考，不构成投资建议",
        None,
    ]

    return {
        "id": str(100 + i),
        "symbol": symbol,
        "strike": float(strike),
        "expiry": expiry,
        "put_call": put_call,
        "side": random.choices(["BUY", "SELL", "MID"], weights=[0.55, 0.25, 0.20])[0],
        "premium": premium,
        "volume": random.randint(200, 5000),
        "oi": random.randint(500, 20000),
        "is_sweep": random.random() < 0.35,
        "score": score,
        "direction": direction,
        "ai_note": random.choice(ai_notes),
        "stock_price": round(stock_price, 2),
        "timestamp": ts,
    }


def generate_flows(n=30):
    return [random_flow(i) for i in range(n)]


def generate_stats():
    return {
        "total_flows": random.randint(320, 580),
        "avg_score": round(random.uniform(65, 80), 1),
        "bullish_ratio": round(random.uniform(0.45, 0.65), 3),
        "sweep_ratio": round(random.uniform(0.28, 0.45), 3),
    }


def generate_sentiment():
    result = {}
    for sym in SYMBOLS:
        total = random.randint(20, 80)
        bullish = int(total * random.uniform(0.35, 0.7))
        bearish = int(total * random.uniform(0.15, 0.45))
        neutral = max(0, total - bullish - bearish)
        result[sym] = {"bullish": bullish, "bearish": bearish, "neutral": neutral}
    return result


def generate_analysis(symbol: str):
    base_prices = {
        "NVDA": 850, "AAPL": 220, "TSLA": 280, "SPY": 560, "QQQ": 490,
        "AMZN": 210, "MSFT": 430, "META": 600, "GOOGL": 185, "AMD": 165,
    }
    stock_price = base_prices.get(symbol.upper(), 200)
    flow_count = random.randint(30, 120)
    bullish_count = int(flow_count * random.uniform(0.4, 0.65))
    bearish_count = int(flow_count * random.uniform(0.15, 0.35))
    return {
        "symbol": symbol.upper(),
        "current_price": round(stock_price + random.uniform(-5, 5), 2),
        "flow_count": flow_count,
        "avg_score": round(random.uniform(65, 82), 1),
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "top_flows": generate_flows(10),
    }


def generate_alerts():
    return [
        {
            "id": 1,
            "symbol": "NVDA",
            "min_premium": 10_000_000_000,
            "min_score": 75,
            "direction": "BULLISH",
            "wechat_openid": "o****xx",
            "is_active": True,
            "created_at": "2026-03-20T10:00:00Z",
        }
    ]


class MockHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[mock] {self.address_string()} - {format % args}")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/v1/flows/stats":
            self._json(generate_stats())
        elif path == "/api/v1/flows":
            limit = int(qs.get("limit", ["30"])[0])
            self._json(generate_flows(limit))
        elif path == "/api/v1/market/sentiment":
            self._json(generate_sentiment())
        elif path.startswith("/api/v1/analysis/"):
            symbol = path.split("/")[-1]
            self._json(generate_analysis(symbol))
        elif path == "/api/v1/alerts":
            self._json(generate_alerts())
        elif path == "/health":
            self._json({"status": "ok"})
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()
            self.wfile.write(b'{"error":"not found"}')

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self._json({"id": random.randint(1, 999), "status": "created"}, 201)

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")


if __name__ == "__main__":
    port = 8000
    server = HTTPServer(("0.0.0.0", port), MockHandler)
    print(f"Mock API server running at http://localhost:{port}")
    print("Endpoints:")
    print("  GET /api/v1/flows/stats")
    print("  GET /api/v1/flows?limit=N")
    print("  GET /api/v1/market/sentiment")
    print("  GET /api/v1/analysis/{symbol}")
    print("  GET /api/v1/alerts")
    server.serve_forever()
