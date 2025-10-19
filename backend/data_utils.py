from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List
import os
import time
import requests

import pandas as pd


SAMPLE_CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "sample_data.csv")


def load_sample() -> pd.DataFrame:
    if os.path.exists(SAMPLE_CSV_PATH):
        df = pd.read_csv(SAMPLE_CSV_PATH, parse_dates=["time"])  # type: ignore
        df = df.set_index("time").sort_index()
        return df[["open", "high", "low", "close", "volume"]]
    # synthesise tiny frame if file missing
    idx = pd.date_range(end=pd.Timestamp.utcnow(), periods=200, freq="1H")
    base = 100.0
    df = pd.DataFrame(index=idx, data={
        "open": base,
        "high": base * 1.01,
        "low": base * 0.99,
        "close": base,
        "volume": 1000,
    })
    return df


def generate_synthetic_from_range(start: str, end: str, interval: str = "1h", base: float = 100.0) -> pd.DataFrame:
    idx = pd.date_range(start=pd.to_datetime(start, utc=True), end=pd.to_datetime(end, utc=True), freq=interval)
    if len(idx) == 0:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])  # empty
    import numpy as np
    prices = [base]
    for _ in range(len(idx) - 1):
        ret = 0.0005 + np.random.normal(0, 0.003)
        prices.append(max(0.1, prices[-1] * (1 + ret)))
    closes = pd.Series(prices, index=idx)
    opens = closes.shift(1).fillna(closes.iloc[0])
    highs = pd.concat([opens, closes], axis=1).max(axis=1) * (1 + 0.002)
    lows = pd.concat([opens, closes], axis=1).min(axis=1) * (1 - 0.002)
    vols = pd.Series(1000, index=idx)
    df = pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": vols})
    return df


def get_historical_data(symbol: str, interval: str, lookback: str, source: str = "sample") -> pd.DataFrame:
    # yfinance removed; only 'sample' and external providers (e.g., binance from providers/) are supported.
    return load_sample()


def get_historical_data_by_range(symbol: str, start: str | None, end: str | None, source: str = "sample") -> pd.DataFrame:
    # yfinance removed; generate synthetic range for sample
    if start and end:
        return generate_synthetic_from_range(start=start, end=end, interval="1h")
    return load_sample()


def _ensure_series(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame.columns:
        return pd.Series([], dtype=float)
    col = frame[name]
    # If duplicate column names lead to a DataFrame, take the first column
    if isinstance(col, pd.DataFrame):
        col = col.iloc[:, 0]
    return pd.to_numeric(col, errors="coerce")


def df_to_candles(df: pd.DataFrame) -> Dict[str, List]:
    if df is None or df.empty:
        return {"t": [], "o": [], "h": [], "l": [], "c": [], "v": []}
    idx = pd.to_datetime(df.index)
    o = _ensure_series(df, "open").round(6).to_list()
    h = _ensure_series(df, "high").round(6).to_list()
    l = _ensure_series(df, "low").round(6).to_list()
    c = _ensure_series(df, "close").round(6).to_list()
    v = _ensure_series(df, "volume").round(6).to_list()
    return {
        "t": [ts.isoformat() for ts in idx.to_pydatetime().tolist()],
        "o": o,
        "h": h,
        "l": l,
        "c": c,
        "v": v,
    }


