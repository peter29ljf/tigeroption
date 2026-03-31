from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/watchlist", tags=["watchlist"])

REDIS_KEY = "watchlist:symbols"


async def get_dynamic_watchlist(redis) -> list[str]:
    """Read the canonical watchlist from Redis, seeding from .env on first call."""
    members = await redis.smembers(REDIS_KEY)
    if members:
        return sorted(members)
    settings = get_settings()
    defaults = settings.watchlist_symbols
    if defaults:
        await redis.sadd(REDIS_KEY, *defaults)
    return defaults


class WatchlistResponse(BaseModel):
    symbols: list[str]


class SymbolBody(BaseModel):
    symbol: str


@router.get("", response_model=WatchlistResponse)
async def list_watchlist(request: Request) -> WatchlistResponse:
    redis = request.app.state.redis
    symbols = await get_dynamic_watchlist(redis)
    return WatchlistResponse(symbols=symbols)


@router.post("", response_model=WatchlistResponse)
async def add_symbol(body: SymbolBody, request: Request) -> WatchlistResponse:
    sym = body.symbol.strip().upper()
    if not sym:
        raise HTTPException(status_code=400, detail="Symbol cannot be empty")
    redis = request.app.state.redis
    await get_dynamic_watchlist(redis)
    count = await redis.scard(REDIS_KEY)
    if count >= 30:
        raise HTTPException(status_code=400, detail="Watchlist limit reached (max 30)")
    await redis.sadd(REDIS_KEY, sym)
    members = await redis.smembers(REDIS_KEY)
    return WatchlistResponse(symbols=sorted(members))


@router.delete("/{symbol}", response_model=WatchlistResponse)
async def remove_symbol(symbol: str, request: Request) -> WatchlistResponse:
    sym = symbol.strip().upper()
    redis = request.app.state.redis
    await redis.srem(REDIS_KEY, sym)
    members = await redis.smembers(REDIS_KEY)
    return WatchlistResponse(symbols=sorted(members))
