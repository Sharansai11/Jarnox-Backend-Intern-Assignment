// main.js (updated - removed ML predict feature entirely)
const API_BASE = 'http://localhost:8000';

const priceCtx = document.getElementById('priceChart').getContext('2d');
const priceChart = new Chart(priceCtx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [
      { label: 'Close', data: [], borderColor: '#22d3ee', tension: 0.2, pointRadius: 0 },
      { label: 'Buy', data: [], borderColor: '#22c55e', showLine: false, pointRadius: 7 },
      { label: 'Sell', data: [], borderColor: '#ef4444', showLine: false, pointRadius: 7 },
      
    ],
  },
  options: {
    responsive: true,
    scales: {
      x: { type: 'time', adapters: { date: { zone: 'utc' } }, time: { tooltipFormat: 'yyyy-LL-dd HH:mm' } },
      y: { beginAtZero: false },
    },
  },
});

const equityCtx = document.getElementById('equityChart').getContext('2d');
const equityChart = new Chart(equityCtx, {
  type: 'line',
  data: { labels: [], datasets: [{ label: 'Equity', data: [], borderColor: '#a78bfa', tension: 0.2, pointRadius: 0 }] },
  options: {
    responsive: true,
    scales: {
      x: { type: 'time', adapters: { date: { zone: 'utc' } }, time: { tooltipFormat: 'yyyy-LL-dd HH:mm' } },
      y: { beginAtZero: false },
    },
  },
});

let ws;

function addCandle(ts, close, signal) {
  priceChart.data.labels.push(ts);
  priceChart.data.datasets[0].data.push(close);
  if (signal === 1) {
    priceChart.data.datasets[1].data.push({ x: ts, y: close });
  } else if (signal === -1) {
    priceChart.data.datasets[2].data.push({ x: ts, y: close });
  }
  priceChart.update('none');
}

async function loadHistorical(symbol) {
  const source = document.getElementById('source')?.value || 'sample';
  // For binance, load a shorter, lower timeframe history so movement is visible and matches live 1m stream
  const interval = source === 'binance' ? '1m' : '1h';
  const lookback = source === 'binance' ? '12h' : '7d';
  const url = `${API_BASE}/api/historical?symbol=${encodeURIComponent(symbol)}&interval=${interval}&lookback=${lookback}&source=${source}`;
  try {
    const res = await fetch(url);
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch { throw new Error(text.slice(0, 200)); }
    if (!res.ok) throw new Error(data?.detail || 'Historical fetch failed');
    priceChart.data.labels = data.t;
    priceChart.data.datasets[0].data = data.c;
    priceChart.data.datasets[1].data = [];
    priceChart.data.datasets[2].data = [];
    priceChart.update();
  } catch (err) {
    alert(`Historical data error: ${err.message}`);
  }
}

function startLive() {
  const symbol = document.getElementById('symbol').value;
  const strategy = document.getElementById('strategy').value;
  const fast = Number(document.getElementById('fast').value || 10);
  const slow = Number(document.getElementById('slow').value || 20);
  const rsi = Number(document.getElementById('rsi').value || 14);
  const source = document.getElementById('source')?.value || 'sample';
  // speed_ms only affects sample/yfinance mock stream (not binance); lower for faster ticks
  const speed_ms = source === 'binance' ? 60000 : 250;
  const wsUrl = `ws://localhost:8000/ws/live?symbol=${encodeURIComponent(symbol)}&strategy=${strategy}&fast=${fast}&slow=${slow}&rsi_period=${rsi}&source=${source}&speed_ms=${speed_ms}`;
  ws = new WebSocket(wsUrl);
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.error) {
      alert(msg.error);
      return;
    }
    addCandle(msg.t, msg.c, msg.signal);
  };
  ws.onopen = () => console.log('WS open');
  ws.onclose = () => console.log('WS closed');
}

function stopLive() {
  if (ws) {
    ws.close();
    ws = undefined;
  }
}

async function runBacktest() {
  const symbol = document.getElementById('symbol').value;
  const strategy = document.getElementById('strategy').value;
  const fast = Number(document.getElementById('fast').value || 10);
  const slow = Number(document.getElementById('slow').value || 20);
  const rsi = Number(document.getElementById('rsi').value || 14);
  const start = document.getElementById('btStart').value;
  const end = document.getElementById('btEnd').value;
  const initial_cash = Number(document.getElementById('btCash').value || 10000);
  const source = document.getElementById('source')?.value || 'sample';
  const payload = {
    symbol,
    strategy,
    params: { fast, slow, rsi_period: rsi },
    start,
    end,
    initial_cash,
    source,
  };
  const res = await fetch(`${API_BASE}/api/backtest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const text = await res.text();
  let out;
  try { out = JSON.parse(text); } catch { out = { error: text.slice(0, 500) }; }
  if (!res.ok) {
    alert(out.detail || out.error || 'Backtest failed');
  }
  document.getElementById('backtestOut').textContent = JSON.stringify(out, null, 2);
  if (out && out.equity) {
    const labels = out.equity.map(e => e.timestamp);
    const values = out.equity.map(e => e.equity);
    equityChart.data.labels = labels;
    equityChart.data.datasets[0].data = values;
    equityChart.update();
  }
  if (out && typeof out.pnl !== 'undefined') {
    const sum = document.getElementById('btSummary');
    sum.textContent = `PnL: ${Number(out.pnl).toFixed(2)} | Trades: ${out.num_trades}`;
  }
}

// main.js (updated event listener section)
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('start').addEventListener('click', startLive);
  document.getElementById('stop').addEventListener('click', stopLive);
  document.getElementById('runBacktest').addEventListener('click', runBacktest);
  document.getElementById('source')?.addEventListener('change', () => {
    const symbol = document.getElementById('symbol').value || 'BTC-USD';
    loadHistorical(symbol);
  });

  (async function init() {
    await loadHistorical('BTC-USD');
  })();
});