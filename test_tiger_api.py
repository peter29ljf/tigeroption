#!/usr/bin/env python3
"""
Tiger OpenAPI 连通性测试脚本（休市/开市均可使用）
"""
import sys
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.trade.trade_client import TradeClient
from tigeropen.common.consts import Market

CONFIG_PATH = "/Users/junfenglin/workspace/claude/option/optionflow-pro/secrets/tiger_openapi_config.properties"

def test_connection():
    print("=" * 55)
    print("Tiger OpenAPI 连通性测试（休市友好版）")
    print("=" * 55)

    config = TigerOpenClientConfig(props_path=CONFIG_PATH)
    print(f"\n✓ 配置加载成功")
    print(f"  Tiger ID : {config.tiger_id}")
    print(f"  Account  : {config.account}")
    print(f"  License  : {config.license}")

    quote = QuoteClient(config)
    trade = TradeClient(config)
    passed = 0
    failed = 0

    # ── 1. 账户资产 ──────────────────────────────────────────
    print("\n[1] 账户资产...")
    try:
        assets = trade.get_assets(account=config.account)
        if assets:
            a = assets[0]
            print(f"  ✓ 净资产: ${getattr(a, 'net_liquidation', 'N/A')}")
            print(f"    可用: ${getattr(a, 'cash', 'N/A')}")
        passed += 1
    except Exception as e:
        print(f"  ✗ {e}")
        failed += 1

    # ── 2. 持仓列表 ──────────────────────────────────────────
    print("\n[2] 持仓列表...")
    try:
        positions = trade.get_positions(account=config.account)
        print(f"  ✓ 当前持仓 {len(positions)} 只")
        for p in positions[:5]:
            print(f"    {p.contract.symbol:8s} qty={p.quantity}  cost={p.average_cost:.2f}")
        passed += 1
    except Exception as e:
        print(f"  ✗ {e}")
        failed += 1

    # ── 3. 期权到期日（无需实时行情权限）────────────────────
    print("\n[3] 期权到期日（AAPL）...")
    try:
        expirations = quote.get_option_expirations(["AAPL"])
        aapl = expirations.get("AAPL", [])
        print(f"  ✓ {len(aapl)} 个到期日")
        print(f"    最近 5 个: {aapl[:5]}")
        passed += 1
    except Exception as e:
        print(f"  ✗ {e}")
        failed += 1

    # ── 4. 期权链快照（休市时返回收盘数据）──────────────────
    print("\n[4] 期权链快照（AAPL 近月）...")
    try:
        expirations = quote.get_option_expirations(["AAPL"])
        aapl = expirations.get("AAPL", [])
        if aapl:
            expiry = aapl[0]
            chain = quote.get_option_chain(
                identifier="AAPL",
                expiry=expiry,
                market=Market.US
            )
            print(f"  ✓ {expiry} 期权链: {len(chain)} 个合约")
            calls = [c for c in chain if c.put_call == "C"][:3]
            puts  = [c for c in chain if c.put_call == "P"][:3]
            print(f"    Call 样本:")
            for c in calls:
                print(f"      行权价 {c.strike:7.1f}  bid={c.bid_price}  ask={c.ask_price}  OI={c.open_interest}")
            print(f"    Put 样本:")
            for c in puts:
                print(f"      行权价 {c.strike:7.1f}  bid={c.bid_price}  ask={c.ask_price}  OI={c.open_interest}")
        passed += 1
    except Exception as e:
        print(f"  ✗ {e}")
        failed += 1

    # ── 5. 股票收盘价（历史快照，不依赖实时权限）────────────
    print("\n[5] 股票报价快照...")
    try:
        symbols = ["AAPL", "NVDA", "SPY"]
        briefs = quote.get_stock_briefs(symbols)
        print(f"  ✓ {len(briefs)} 只")
        for b in briefs:
            price = getattr(b, 'latest_price', None) or getattr(b, 'close', 'N/A')
            print(f"    {b.symbol:6s}  价格: ${price}")
        passed += 1
    except Exception as e:
        print(f"  ✗ {e}")
        failed += 1

    # ── 结果汇总 ──────────────────────────────────────────────
    print("\n" + "=" * 55)
    print(f"结果: {passed} 通过 / {failed} 失败")
    if failed == 0:
        print("✓ 全部通过，API 可正常用于数据采集！")
    elif passed > 0:
        print("⚠ 部分权限受限，已通过的接口足以运行 MVP")
    else:
        print("✗ 无法连接，请检查权限配置")
    print("=" * 55)
    return passed > 0

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
