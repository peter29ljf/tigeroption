from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])

YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


class StockResult(BaseModel):
    symbol: str
    name: str


@lru_cache(maxsize=512)
def _cached_search(q: str) -> list[tuple[str, str]]:
    """Synchronous cached Yahoo Finance search (called via asyncio.to_thread)."""
    try:
        resp = httpx.get(
            YAHOO_SEARCH_URL,
            params={"q": q, "quotesCount": 10, "newsCount": 0},
            headers=_HEADERS,
            timeout=3.0,
        )
        resp.raise_for_status()
        data = resp.json()
        US_EXCHANGES = {"NMS", "NYQ", "PCX", "NGM", "NCM", "ASE", "BTS", "CBOE", "PNK"}
        results = []
        for item in data.get("quotes", []):
            if item.get("quoteType") not in ("EQUITY", "ETF"):
                continue
            # Skip non-US symbols (contain "." like AAPL.TO, NVDA.DE)
            symbol = item.get("symbol", "")
            if not symbol or "." in symbol:
                continue
            exchange = item.get("exchange", "")
            if exchange and exchange not in US_EXCHANGES:
                continue
            name = item.get("shortname") or item.get("longname") or symbol
            results.append((symbol, name))
        return results[:8]
    except Exception as e:
        logger.warning("Yahoo Finance search failed for %r: %s", q, e)
        return []


@router.get("", response_model=list[StockResult])
async def search_symbols(q: Optional[str] = None) -> list[StockResult]:
    if not q or len(q.strip()) < 1:
        return []
    import asyncio
    pairs = await asyncio.to_thread(_cached_search, q.strip().upper())
    return [StockResult(symbol=sym, name=name) for sym, name in pairs]
