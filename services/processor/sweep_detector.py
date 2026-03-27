from __future__ import annotations

import time
from collections import deque

WINDOW_MS = 500
MIN_FILLS = 3


def _contract_key(flow: dict) -> str:
    return (
        f"{flow.get('symbol')}|{flow.get('strike')}|"
        f"{flow.get('expiry')}|{flow.get('put_call')}"
    )


def detect_sweep(flow: dict, buffer: deque[dict]) -> bool:
    now_ms = int(flow.get("timestamp_ms", time.time() * 1000))
    flow["_ts_ms"] = now_ms
    flow["_contract_key"] = _contract_key(flow)

    while buffer and now_ms - buffer[0]["_ts_ms"] > WINDOW_MS:
        buffer.popleft()

    buffer.append(flow)

    key = flow["_contract_key"]
    matches = [f for f in buffer if f["_contract_key"] == key]

    if len(matches) >= MIN_FILLS:
        for m in matches:
            m["is_sweep"] = True
        return True

    return False
