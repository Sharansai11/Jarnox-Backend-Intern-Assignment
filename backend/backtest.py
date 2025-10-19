from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from . import strategies


def run_backtest(df: pd.DataFrame, strategy_name: str, params: Dict[str, Any], initial_cash: float, symbol: str) -> Dict[str, Any]:
    signal_series = None
    if strategy_name == "sma_crossover":
        signal_series = strategies.sma_crossover(df, fast=int(params.get("fast", 10)), slow=int(params.get("slow", 20)))
    elif strategy_name == "rsi_momentum":
        signal_series = strategies.rsi_momentum(df, rsi_period=int(params.get("rsi_period", 14)))
    else:
        signal_series = pd.Series(0, index=df.index)

    position = 0
    cash = initial_cash
    equity_curve = []
    trades = []
    entry_price = None

    for ts, row in df.iterrows():
        price = float(row["close"])
        signal = int(signal_series.loc[ts]) if ts in signal_series.index else 0

        if signal == 1 and position == 0:
            position = 1
            entry_price = price
            trades.append({"timestamp": ts.isoformat(), "symbol": symbol, "side": "BUY", "price": price, "size": 1.0})
        elif signal == -1 and position == 1:
            position = 0
            trades.append({"timestamp": ts.isoformat(), "symbol": symbol, "side": "SELL", "price": price, "size": 1.0})
            if entry_price is not None:
                cash += (price - entry_price)
            entry_price = None

        position_value = (price - (entry_price or price)) if position == 1 and entry_price is not None else 0.0
        equity = cash + (price - (entry_price or price) if position == 1 and entry_price is not None else 0)
        equity_curve.append({"timestamp": ts.isoformat(), "equity": float(equity)})

    # Stateless mode: skip DB persistence

    pnl = cash - initial_cash
    return {
        "initial_cash": float(initial_cash),
        "final_cash": float(cash),
        "pnl": float(pnl),
        "num_trades": len(trades),
        "equity": equity_curve,
        "trades": trades,
    }