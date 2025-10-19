from __future__ import annotations

import asyncio
import math
import json  
from typing import AsyncGenerator, Dict, List, Optional

import pandas as pd
import requests
import websockets


BASE_URL = "https://api.binance.com"
WS_URL = "wss://stream.binance.com:9443/ws"


def _to_binance_symbol(symbol: str) -> Optional[str]:
    s = symbol.upper().replace("-", "")
    if s.endswith("USD"):
        s = s[:-3] + "USDT"  # BTC-USD -> BTCUSDT
    if any(s.startswith(p) for p in ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "MATIC"]):
        return s
    return None


def _interval_to_binance(interval: str) -> str:
    return interval


def _parse_lookback_to_limit(lookback: str, interval: str) -> int:
    unit = lookback[-1]
    try:
        num = int(lookback[:-1])
    except Exception:
        num = 7
        unit = 'd'
    minutes_per = {
        'm': 1,
        'h': 60,
        'd': 60 * 24,
    }.get(interval[-1], 1) * max(int(interval[:-1]) if interval[:-1].isdigit() else 1, 1)
    total_minutes = {
        'm': num,
        'h': num * 60,
        'd': num * 60 * 24,
    }.get(unit, num * 60 * 24)
    limit = min(1000, max(1, math.ceil(total_minutes / minutes_per)))
    return limit


def get_historical_df(symbol: str, interval: str, lookback: str) -> pd.DataFrame:
    bsymbol = _to_binance_symbol(symbol)
    if not bsymbol:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    binterval = _interval_to_binance(interval)
    limit = _parse_lookback_to_limit(lookback, interval)
    url = f"{BASE_URL}/api/v3/klines"
    params = {"symbol": bsymbol, "interval": binterval, "limit": limit}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code != 200:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    data = r.json()
    rows = []
    for k in data:
        rows.append({
            "time": pd.to_datetime(k[0], unit='ms', utc=True),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        })
    df = pd.DataFrame(rows).set_index("time").sort_index()
    return df


async def kline_stream(symbol: str, interval: str) -> AsyncGenerator[Dict, None]:
    bsymbol = _to_binance_symbol(symbol)
    if not bsymbol:
        return
    stream_name = f"{bsymbol.lower()}@kline_{_interval_to_binance(interval)}"
    uri = "wss://stream.binance.com:9443/ws"
    async with websockets.connect(uri) as ws:
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": [stream_name],
            "id": 1
        }
        await ws.send(json.dumps(subscribe_message))
        while True:
            try:
                message = await ws.recv()
                payload = json.loads(message)  # Now json is defined
                k = payload.get("k") or (payload.get("data") or {}).get("k")
                if k and k.get("x", False):  # Only process closed candles
                    yield {
                        "t": pd.to_datetime(k["T"], unit='ms', utc=True).isoformat(),
                        "o": float(k["o"]),
                        "h": float(k["h"]),
                        "l": float(k["l"]),
                        "c": float(k["c"]),
                        "v": float(k["v"]),
                    }
            except websockets.ConnectionClosed:
                print("WebSocket connection closed, attempting to reconnect...")
                await asyncio.sleep(1)
                break  # Exit and let the caller handle reconnection if needed
            except Exception as e:
                print(f"WebSocket error: {e}")
                await asyncio.sleep(1)