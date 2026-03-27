#!/usr/bin/env python3
"""
Tiger API 返回格式诊断——确认字段名和数据类型，用于修正 tiger_client.py
"""
import sys
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.consts import Market

CONFIG_PATH = "/Users/junfenglin/workspace/claude/option/optionflow-pro/secrets/tiger_openapi_config.properties"

config = TigerOpenClientConfig(props_path=CONFIG_PATH)
quote = QuoteClient(config)

# ── 1. get_option_expirations 返回格式 ──────────────────────────
print("=" * 55)
print("[1] get_option_expirations 返回类型和字段")
try:
    result = quote.get_option_expirations(["AAPL"])
    print(f"  type: {type(result)}")
    print(f"  value: {result}")
    # 如果是 dict
    if isinstance(result, dict):
        for k, v in result.items():
            print(f"  key={k}, val_type={type(v)}, val={v}")
            if hasattr(v, 'columns'):
                print(f"    DataFrame columns: {list(v.columns)}")
                print(v.head(3).to_string())
            elif isinstance(v, list) and v:
                print(f"    list[0] type={type(v[0])}, val={v[0]}")
except Exception as e:
    print(f"  ✗ {e}")

# ── 2. get_option_chain 返回格式 ────────────────────────────────
print("\n[2] get_option_chain 返回类型和字段")
try:
    # 先拿到到期日
    exp_result = quote.get_option_expirations(["AAPL"])
    # 尝试从不同格式提取第一个到期日
    first_expiry = None
    if hasattr(exp_result, 'columns') and 'date' in exp_result.columns:
        first_expiry = exp_result["date"].iloc[0]
    elif isinstance(exp_result, dict) and "AAPL" in exp_result:
        v = exp_result["AAPL"]
        if isinstance(v, list) and v:
            first_expiry = v[0]
    print(f"  using expiry: {first_expiry}")

    if first_expiry:
        chain = quote.get_option_chain(
            symbol="AAPL",
            expiry=first_expiry,
            market=Market.US
        )
        print(f"  type: {type(chain)}")
        if hasattr(chain, 'columns'):
            print(f"  DataFrame shape: {chain.shape}")
            print(f"  columns: {list(chain.columns)}")
            print(chain.head(2).to_string())
        elif isinstance(chain, list) and chain:
            item = chain[0]
            print(f"  list[0] type: {type(item)}")
            if hasattr(item, '__dict__'):
                print(f"  attributes: {vars(item)}")
            elif isinstance(item, dict):
                print(f"  keys: {list(item.keys())}")
                print(f"  sample: {item}")
    else:
        print("  ✗ 无法获取到期日，跳过")
except Exception as e:
    print(f"  ✗ {e}")

# ── 3. get_stock_briefs 返回格式 ────────────────────────────────
print("\n[3] get_stock_briefs 返回类型和字段")
try:
    briefs = quote.get_stock_briefs(["AAPL"])
    print(f"  type: {type(briefs)}")
    if hasattr(briefs, 'columns'):
        print(f"  DataFrame columns: {list(briefs.columns)}")
        print(briefs.head(2).to_string())
    elif isinstance(briefs, list) and briefs:
        item = briefs[0]
        print(f"  list[0] type: {type(item)}")
        if hasattr(item, '__dict__'):
            print(f"  attributes: {vars(item)}")
        elif isinstance(item, dict):
            print(f"  keys: {list(item.keys())}")
except Exception as e:
    print(f"  ✗ {e}")

print("\n" + "=" * 55)
print("诊断完成")
