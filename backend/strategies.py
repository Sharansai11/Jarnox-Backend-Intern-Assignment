from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from . import indicators as ind


def sma_crossover(df: pd.DataFrame, fast: int = 10, slow: int = 20) -> pd.Series:
    fast_sma = ind.sma(df["close"], fast)
    slow_sma = ind.sma(df["close"], slow)
    signal = (fast_sma > slow_sma).astype(int)
    # Convert to -1/0/1 with crossovers
    shifted = signal.shift(1).fillna(0)
    raw = signal - shifted
    entries = raw.where(raw <= 0, 1)  # 1 on bullish cross
    exits = raw.where(raw >= 0, -1)   # -1 on bearish cross
    combined = entries.where(entries != 0, exits).fillna(0)
    return combined


def rsi_momentum(df: pd.DataFrame, rsi_period: int = 14, overbought: int = 70, oversold: int = 30) -> pd.Series:
    r = ind.rsi(df["close"], period=rsi_period)
    above = (r > overbought).astype(int)
    below = (r < oversold).astype(int)
    long_entry = ((r.shift(1) < oversold) & (r >= oversold)).astype(int)
    long_exit = ((r.shift(1) > overbought) & (r <= overbought)).astype(int)
    signal = pd.Series(0, index=df.index)
    signal = signal.where(~(long_entry == 1), 1)
    signal = signal.where(~(long_exit == 1), -1)
    return signal.fillna(0)


def evaluate_latest(df: pd.DataFrame, strategy_name: str, params: Dict) -> int:
    if strategy_name == "sma_crossover":
        s = sma_crossover(df, fast=int(params.get("fast", 10)), slow=int(params.get("slow", 20)))
        return int(s.iloc[-1] if len(s) else 0)
    elif strategy_name == "rsi_momentum":
        s = rsi_momentum(df, rsi_period=int(params.get("rsi_period", 14)))
        return int(s.iloc[-1] if len(s) else 0)
    else:
        return 0


