from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from services.api.models.database import engine
from services.api.routers import abnormal, alerts, analysis, backtest, flows, search, sentiment, watchlist
from services.api.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)
ws_manager = WebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    logger.info("Starting OptionFlow Pro API")

    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    await ws_manager.start()

    yield

    await ws_manager.stop()
    await app.state.redis.aclose()
    await engine.dispose()
    logger.info("OptionFlow Pro API shut down")


app = FastAPI(
    title="OptionFlow Pro",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flows.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(backtest.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(sentiment.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(abnormal.router, prefix="/api/v1")
app.include_router(watchlist.router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "service": "optionflow-pro-api"}


@app.websocket("/ws/flows")
async def websocket_flows(
    websocket: WebSocket,
    symbol: str | None = Query(None),
    min_score: int | None = Query(None),
    direction: str | None = Query(None),
) -> None:
    await ws_manager.connect(websocket, symbol=symbol, min_score=min_score, direction=direction)
    await ws_manager.listen(websocket)
