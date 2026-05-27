# SelfLearningBot

A paper-trading desktop app for Indian markets with a modular AI/ML core that learns from its own closed trades. Built as a foundation for a larger self-improving trading system.

> **Honest scope:** this is an MVP **skeleton**, not a profitable trading system. It runs end-to-end (live quotes → AI signal → paper order → P&L → RL parameter update) so you can iterate on real plumbing. Real edge takes months of data, validation, and risk discipline. Do not run this against real money without months of paper-trade evidence and a rewrite of the risk layer.

---

## How to use it (quick start)

1. **Start backend:**
   ```bash
   cd backend && source .venv/bin/activate
   uvicorn app.main:app --reload --port 8765
   ```

2. **Start frontend (new terminal):**
   ```bash
   cd frontend && npm install && npm run dev
   ```

3. **App opens in Electron window** — 7 tabs:
   - **Dashboard** — top AI picks, portfolio snapshot, recent learning
   - **Chart & Signal** — live candlesticks (5m intraday or daily) with AI entry/exit signals + manual trading
   - **Screener** — stock universe ranked by momentum+trend+breakout score
   - **Backtest** — historical simulation + ML model training
   - **Portfolio** — open positions, trade history, P&L
   - **Learning Log** — what the bot learned from its own trades
   - **Settings** — Angel One credentials (for live NSE/BSE data)

4. **Search stocks** — all symbol inputs have a searchable dropdown:
   - Type to filter default universe (RELIANCE.NS, TCS.NS, etc.)
   - If Angel One is configured, also searches live instrument master
   - 🔴 = Angel One (live), 📊 = Yahoo (delayed)

5. **Place trades:**
   - Chart tab → select symbol → view AI signal → adjust qty → click Buy/Sell
   - Paper money, real market data

6. **Watch it learn:**
   - Close a trade
   - Learning Log updates with P&L
   - RL tuner nudges strategy parameters
   - Next trade uses refined parameters

---

## What's in the box

**Backend** (`backend/`, Python 3.9+ + FastAPI)
- `data/` — pluggable `DataSource` interface. **Yahoo Finance** adapter works out of the box; **Angel One SmartAPI** stub falls back to Yahoo until you supply credentials.
- `strategy/` — technical indicators (SMA/EMA/RSI/MACD/Bollinger/ATR) + an RL-tunable MA-crossover strategy.
- `ml/` — **XGBoost** signal on engineered features + a simple **RL parameter tuner** (EMA-rewards + random search) that nudges strategy parameters after every closed trade.
- `trading/` — paper broker with SQLite persistence (cash, positions, trade history).
- `backtest/` — bar-by-bar backtest engine with Sharpe / drawdown / win-rate metrics.
- `screener/` — composite ranker (momentum + trend + breakout + volume) across a configurable universe.
- `db/` — SQLAlchemy models for trades, positions, strategy params, and a learning log.

**Frontend** (`frontend/`, Electron + React + TypeScript + Vite)
- Dashboard, Chart & Signal (TradingView Lightweight Charts), Screener, Backtest, Portfolio, Learning Log.

---

## Quick start (macOS)

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # defaults are fine for paper trading
uvicorn app.main:app --reload --port 8765
```

Backend is now on http://localhost:8765 — visit `/docs` for the auto-generated API browser.

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev                # runs Vite + opens the Electron desktop window
```

You can also run just the web UI (no Electron) with `npm run dev:web` and open http://localhost:5173.

### 3. First flow

1. Open the **Screener** tab → click Refresh → wait ~10s for the universe to score.
2. Open **Chart & Signal** → enter `RELIANCE.NS` → see the candlestick + AI signal panel.
3. Open **Backtest** → click "Train ML on 5y" to fit the XGBoost model (one-time per symbol) → then "Run Backtest" to see metrics.
4. Place a paper Buy from the Chart panel → close it later from the same panel → check **Portfolio** + **Learning Log** to see the RL tuner record the outcome.

---

## Switching to Angel One (NSE/BSE real-time)

Edit `backend/.env`:

```
DATA_SOURCE=angel_one
ANGEL_API_KEY=...
ANGEL_CLIENT_ID=...
ANGEL_PASSWORD=...
ANGEL_TOTP_SECRET=...
```

Then `pip install smartapi-python pyotp` and implement the two methods in `backend/app/data/angel_one.py` (clearly marked TODOs). Until then, the app keeps working — the stub falls back to Yahoo.

---

## What deliberately isn't here yet

These were in the original spec but cut for an honest first cut. Each one is a real project:

- **Chart computer-vision (OpenCV/CNN/OCR)** — pattern detection from screenshots is a research problem and a toy version would be misleading. The text/numeric path covers the same intent for now.
- **Live broker integration** — paper only. The order-routing seam is clean; swap `paper_broker` with a real broker adapter when ready.
- **Real RL (PPO / contextual bandits)** — the tuner is a coordinate-search stand-in. The DB schema and reward seam are right; swap the algorithm without touching the rest.
- **Multi-user auth, encrypted DB, Docker, k8s** — single-user local app. Add when you actually deploy.
- **Web/news ingestion** — no LLM news layer yet. Easy to bolt on later; not load-bearing for the trading loop.

---

## Architecture seams (so future-you can extend cleanly)

- New data vendor → implement `DataSource` in `backend/app/data/`, register in `data/__init__.py`.
- New strategy → subclass `Strategy` in `backend/app/strategy/`, add params model + RL ranges in `ml/rl_tuner.py`.
- New ML model → add a sibling to `xgb_model.py`, blend its output in `api/routes.py::signal`.
- New broker → mirror `paper_broker.py` and switch via env flag.
