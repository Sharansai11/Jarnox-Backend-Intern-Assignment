Live Trading Simulation / Algo Trading System Prototype

Overview

This project provides a minimal end-to-end prototype of a trading system with:
- FastAPI backend (historical data via yfinance or bundled sample, mock live websocket)
- Two strategies: SMA crossover and RSI momentum
- Backtesting and paper-trading style execution with PnL tracking
- SQLite persistence for trades and portfolio equity snapshots
- Static HTML/JS dashboard (Chart.js) showing price, signals, and live updates

Folder Structure

- `backend/` — FastAPI app, strategies, backtesting, data, database
- `frontend/` — static HTML/CSS/JS dashboard
- `requirements.txt` — Python dependencies

Quick Start

1) Create and activate a virtual environment (recommended):

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

2) Install dependencies:

```bash
pip install -r requirements.txt
```

3) Run the backend server:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

4) Open the dashboard:

Open `frontend/index.html` in your browser. By default it connects to `http://localhost:8000` REST and `ws://localhost:8000` websocket.

Notes

- Historical data is fetched via `yfinance` if network and the symbol exist. If fetching fails, the backend falls back to `backend/data/sample_data.csv`.
- The websocket provides a mock live feed (random-walk with drift seeded from the last known price), emitting OHLCV candles each second and strategy signals.
- Backtests run server-side; results, trades and equity curve can be viewed via the dashboard or API.

API Endpoints (Selected)

- `GET /api/health` — health check
- `GET /api/historical?symbol=BTC-USD&interval=1m&lookback=7d` — historical candles JSON
- `POST /api/backtest` — run backtest; body:

```json
{
  "symbol": "BTC-USD",
  "strategy": "sma_crossover",
  "params": {"fast": 10, "slow": 20},
  "start": "2024-01-01",
  "end": "2024-03-01",
  "initial_cash": 10000
}
```

- `GET /api/trades` — list stored trades (SQLite)
- `GET /api/equity` — portfolio equity snapshots
- `WS /ws/live?symbol=BTC-USD&strategy=sma_crossover&fast=10&slow=20` — mock live candles with signals

Strategies

- `sma_crossover`: Buy when fast SMA crosses above slow SMA; sell/exit when crosses below.
- `rsi_momentum`: Buy when RSI crosses up from oversold; sell when RSI crosses down from overbought.

Run Tests/Examples

- Start the server and open the dashboard. Choose symbol (e.g., `BTC-USD` or `AAPL`), pick strategy, and click Start Live to see the stream and signals. Use the Backtest form to run historical backtests.

Development Notes (200–300 words)

This prototype aims to balance clarity with useful trading-system features. The backend exposes both historical and live-style data paths. Historical candles are pulled from `yfinance` when available, otherwise a bundled sample CSV is used. The live data path is a mock websocket that emits synthetic candles derived from the last historical close, which keeps the demo predictable and offline-capable. Two simple strategies, SMA crossover and RSI momentum, are implemented using shared indicator utilities. The backtesting engine applies each strategy over the candle series, simulating orders, position state, and PnL with an equity curve. A small SQLite database persists trades and equity snapshots for later inspection.

On the frontend, a static HTML/JS dashboard uses Chart.js to plot price and overlays buy/sell markers in real time, while a performance panel shows PnL metrics. The design favors minimal dependencies and easy local setup on Windows. Key challenges included organizing real-time streams with strategy evaluation per incoming candle and ensuring indicators are efficiently recomputed. The solution updates indicators incrementally and encapsulates strategy rules for reuse by both backtesting and the live mock stream. Future enhancements could add real exchange paper trading (e.g., Alpaca or Binance Testnet), risk controls like dynamic position sizing and stop losses, WebSocket-based broadcasting to multiple clients, and deployment via Docker on a free cloud service.


