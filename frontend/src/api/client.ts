const BASE = (import.meta as any).env?.VITE_API_BASE ?? "http://127.0.0.1:8765";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export interface Candle { time: string; open: number; high: number; low: number; close: number; volume: number; }
export interface Quote { symbol: string; price: number; change_pct: number; volume: number; timestamp: string; }
export interface Signal {
  symbol: string; action: "BUY" | "SELL" | "HOLD";
  rule_confidence: number; ml_p_up: number | null; blended_confidence: number;
  reason: string; stop_loss: number | null; target: number | null; params: Record<string, number>;
}
export interface PortfolioPos {
  symbol: string; qty: number; avg_price: number; last_price: number; market_value: number; unrealized_pnl: number;
}
export interface Portfolio { cash: number; equity: number; positions: PortfolioPos[]; }
export interface Trade {
  id: number; symbol: string; side: string; qty: number; price: number;
  timestamp: string; strategy: string; confidence: number; reason: string; pnl: number;
}
export interface ScreenerRow {
  symbol: string; price: number; ret_1m_pct: number; ret_3m_pct: number;
  rsi14: number; score: number; ai_signal: string; ai_confidence: number; reason: string;
}
export interface BacktestResult {
  symbol: string; period: string;
  metrics: Record<string, number>;
  equity_curve: { timestamp: string; equity: number }[];
  trades: any[];
}
export interface LearningEntry { id: number; timestamp: string; kind: string; message: string; }
export interface BrokerStatus {
  configured: boolean;
  active_source: "yahoo" | "angel_one";
  broker: string | null;
  api_key_preview?: string | null;
  client_id?: string | null;
  totp_secret_preview?: string | null;
  last_login_at?: string | null;
  last_error?: string | null;
  updated_at?: string | null;
}
export interface BrokerCreds {
  api_key: string;
  client_id: string;
  password: string;
  totp_secret: string;
}

export const api = {
  quote: (symbol: string) => req<Quote>(`/api/quote?symbol=${encodeURIComponent(symbol)}`),
  history: (symbol: string, period = "6mo", interval = "1d") =>
    req<{ symbol: string; candles: Candle[] }>(
      `/api/history?symbol=${encodeURIComponent(symbol)}&period=${period}&interval=${interval}`
    ),
  signal: (symbol: string) => req<Signal>(`/api/signal?symbol=${encodeURIComponent(symbol)}`),
  screener: (topN = 10) => req<ScreenerRow[]>(`/api/screener?top_n=${topN}`),
  portfolio: () => req<Portfolio>(`/api/portfolio`),
  trades: () => req<Trade[]>(`/api/trades`),
  learning: () => req<LearningEntry[]>(`/api/learning`),
  config: () => req<{ data_source: string; starting_cash: number; default_universe: string[] }>(`/api/config`),
  trainMl: (symbol: string, period = "5y") =>
    req<any>(`/api/ml/train`, { method: "POST", body: JSON.stringify({ symbol, period }) }),
  backtest: (symbol: string, period = "2y", interval = "1d") =>
    req<BacktestResult>(`/api/backtest`, {
      method: "POST", body: JSON.stringify({ symbol, period, interval }),
    }),
  order: (symbol: string, side: "BUY" | "SELL", qty: number, strategy = "manual", confidence = 0, reason = "") =>
    req<any>(`/api/order`, {
      method: "POST",
      body: JSON.stringify({ symbol, side, qty, strategy, confidence, reason }),
    }),
  brokerStatus: () => req<BrokerStatus>(`/api/broker/status`),
  saveBrokerCreds: (creds: BrokerCreds) =>
    req<BrokerStatus>(`/api/broker/credentials`, { method: "POST", body: JSON.stringify(creds) }),
  deleteBrokerCreds: () =>
    req<BrokerStatus>(`/api/broker/credentials`, { method: "DELETE" }),
  testBroker: () =>
    req<{ ok: boolean; message: string; sample_quote: Quote; session_status: boolean }>(
      `/api/broker/test`,
      { method: "POST" }
    ),
};
