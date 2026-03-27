from __future__ import annotations


def _premium_score(premium_cents: int) -> int:
    if premium_cents >= 100_000_000:
        return 25
    if premium_cents >= 50_000_000:
        return 18
    if premium_cents >= 10_000_000:
        return 10
    return 0


def _vol_oi_score(volume: int, oi: int) -> int:
    if oi <= 0:
        return 0
    ratio = volume / oi
    if ratio > 2:
        return 25
    if ratio > 1:
        return 18
    if ratio > 0.5:
        return 10
    return 0


_SIDE_SCORES: dict[str, int] = {
    "BUY": 25,
    "MID": 10,
    "SELL": 0,
}


def _side_score(side: str) -> int:
    return _SIDE_SCORES.get(side.upper(), 0)


def _sweep_bonus(is_sweep: bool) -> int:
    return 15 if is_sweep else 0


def _dte_adjust(dte: int | None) -> int:
    if dte is None:
        return 0
    if 7 <= dte <= 45:
        return 10
    if dte < 7:
        return -10
    return 0


def _iv_crush_adjust(iv: float) -> int:
    """Penalize flows with extremely high IV (earnings/events inflate IV, reducing signal reliability)."""
    if iv > 1.5:
        return -15
    if iv > 1.0:
        return -8
    return 0


_DIRECTION_MAP: dict[tuple[str, str], str] = {
    ("CALL", "BUY"): "BULLISH",
    ("PUT", "BUY"): "BEARISH",
    ("CALL", "SELL"): "BEARISH",
    ("PUT", "SELL"): "BULLISH",
    # short aliases for compatibility
    ("C", "BUY"): "BULLISH",
    ("P", "BUY"): "BEARISH",
    ("C", "SELL"): "BEARISH",
    ("P", "SELL"): "BULLISH",
}


def _determine_direction(put_call: str, side: str) -> str:
    return _DIRECTION_MAP.get((put_call.upper(), side.upper()), "NEUTRAL")


def score_flow(flow_data: dict) -> dict:
    premium = int(flow_data.get("premium", 0))
    volume = int(flow_data.get("volume", 0))
    oi = int(flow_data.get("oi", 0))
    side = str(flow_data.get("side", ""))
    is_sweep = bool(flow_data.get("is_sweep", False))
    dte = flow_data.get("dte")
    if dte is not None:
        dte = int(dte)
    put_call = str(flow_data.get("put_call", ""))
    iv = float(flow_data.get("iv", 0) or 0)

    score = (
        _premium_score(premium)
        + _vol_oi_score(volume, oi)
        + _side_score(side)
        + _sweep_bonus(is_sweep)
        + _dte_adjust(dte)
        + _iv_crush_adjust(iv)
    )
    score = max(0, min(100, score))

    flow_data["score"] = score
    flow_data["direction"] = _determine_direction(put_call, side)
    return flow_data
