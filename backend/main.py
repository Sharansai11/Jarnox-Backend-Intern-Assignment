from __future__ import annotations

import asyncio
import json
import math
import os
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import os

from . import data_utils, strategies, backtest
from .providers import binance as bin_provider


app = FastAPI(title="Trading Prototype", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    return
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Ensure clients always get JSON, not an HTML/plain error
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "error": str(exc)[:500]})



FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


@app.get("/")
def serve_index() -> FileResponse:
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)


@app.get("/styles.css")
def serve_css() -> FileResponse:
    css_path = os.path.join(FRONTEND_DIR, "styles.css")
    if not os.path.exists(css_path):
        raise HTTPException(status_code=404, detail="styles.css not found")
    return FileResponse(css_path)


@app.get("/main.js")
def serve_js() -> FileResponse:
    js_path = os.path.join(FRONTEND_DIR, "main.js")
    if not os.path.exists(js_path):
        raise HTTPException(status_code=404, detail="main.js not found")
    return FileResponse(js_path)


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/historical")
def get_historical(
    symbol: str = Query("BTC-USD"),
    interval: str = Query("1h"),
    lookback: str = Query("30d"),
    source: str = Query("sample"),
) -> JSONResponse:
    if source == "binance":
        df = bin_provider.get_historical_df(symbol=symbol, interval=interval, lookback=lookback)
    else:
        df = data_utils.get_historical_data(symbol=symbol, interval=interval, lookback=lookback, source=source)
    if df.empty:
        raise HTTPException(status_code=502, detail="Historical data unavailable from provider")
    return JSONResponse(content=data_utils.df_to_candles(df))


@app.post("/api/backtest")
def run_backtest(payload: Dict[str, Any]) -> JSONResponse:
    symbol = payload.get("symbol", "BTC-USD")
    strategy_name = payload.get("strategy", "sma_crossover")
    params = payload.get("params", {})
    start = payload.get("start")
    end = payload.get("end")
    initial_cash = float(payload.get("initial_cash", 10000.0))
    source = payload.get("source", "sample")

    if source == "binance":
        # Binance v3 klines does not support date range in this simple helper; use lookback approximation
        df = bin_provider.get_historical_df(symbol=symbol, interval="1h", lookback="60d")
    else:
        df = data_utils.get_historical_data_by_range(symbol=symbol, start=start, end=end, source=source)
    if df.empty:
        raise HTTPException(status_code=502, detail="Historical data unavailable for backtest")

    result = backtest.run_backtest(df=df, strategy_name=strategy_name, params=params, initial_cash=initial_cash, symbol=symbol)
    return JSONResponse(content=result)


## DB routes removed (stateless mode)


## prediction endpoint removed per user request


# main.py (updated websocket_live function)
@app.websocket("/ws/live")
async def websocket_live(
    websocket: WebSocket,
    symbol: str = "BTC-USD",
    strategy: str = "sma_crossover",
    fast: int = 10,
    slow: int = 20,
    rsi_period: int = 14,
    source: str = "sample",
    speed_ms: int = 1000,
):
    await websocket.accept()
    print(f"WebSocket connected for symbol={symbol}, source={source}")
    try:
        if source == "binance":
            base_df = bin_provider.get_historical_df(symbol=symbol, interval="1m", lookback="2d")
        else:
            base_df = data_utils.get_historical_data(symbol=symbol, interval="1m", lookback="2d", source=source)
        if base_df.empty:
            await websocket.send_text(json.dumps({"error": "Historical data unavailable"}))
            await websocket.close()
            return
        df = base_df.copy()

        last_close = float(df["close"].iloc[-1])
        ts = pd.to_datetime(df.index[-1]).to_pydatetime()

        position = 0
        entry_price: Optional[float] = None

        if source == "binance":
            print("Starting Binance stream...")
            async for k in bin_provider.kline_stream(symbol=symbol, interval="1m"):
                print(f"Received kline: {k}")  # Debug log
                df.loc[pd.Timestamp(k["t"])] = {"open": k["o"], "high": k["h"], "low": k["l"], "close": k["c"], "volume": k["v"]}
                sig = strategies.evaluate_latest(df=df, strategy_name=strategy, params={"fast": fast, "slow": slow, "rsi_period": rsi_period})
                action = None
                if sig == 1 and position == 0:
                    position = 1
                    entry_price = k["c"]
                    action = "BUY"
                elif sig == -1 and position == 1:
                    position = 0
                    action = "SELL"
                payload = {**k, "signal": sig, "action": action}
                await websocket.send_text(json.dumps(payload))
                print(f"Sent payload: {payload}")  # Debug log
        else:
            while True:
                ts = ts + timedelta(seconds=60)
                drift = 0.0005
                vol = 0.005
                ret = drift + random.gauss(0, vol)
                new_close = last_close * (1 + ret)
                high = max(last_close, new_close) * (1 + abs(random.gauss(0, 0.001)))
                low = min(last_close, new_close) * (1 - abs(random.gauss(0, 0.001)))
                open_ = last_close
                volume = abs(random.gauss(1_000, 300))

                new_row = {
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": new_close,
                    "volume": volume,
                }
                df.loc[pd.Timestamp(ts)] = new_row
                last_close = new_close

                signal = strategies.evaluate_latest(
                    df=df,
                    strategy_name=strategy,
                    params={"fast": fast, "slow": slow, "rsi_period": rsi_period},
                )

                action = None
                if signal == 1 and position == 0:
                    position = 1
                    entry_price = new_close
                    action = "BUY"
                elif signal == -1 and position == 1:
                    position = 0
                    action = "SELL"

                payload = {
                    "t": ts.isoformat(),
                    "o": float(open_),
                    "h": float(high),
                    "l": float(low),
                    "c": float(new_close),
                    "v": float(volume),
                    "signal": signal,
                    "action": action,
                }
                await websocket.send_text(json.dumps(payload))
                await asyncio.sleep(max(0.05, speed_ms / 1000))
    except WebSocketDisconnect:
        print("WebSocket disconnected by client")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()