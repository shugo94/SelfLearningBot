import { useEffect, useState } from "react";
import { api, type Portfolio, type Trade } from "../api/client";

export default function PortfolioPanel() {
  const [pf, setPf] = useState<Portfolio | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const load = () => {
    Promise.all([api.portfolio(), api.trades()])
      .then(([p, t]) => { setPf(p); setTrades(t); })
      .catch((e) => setErr(String(e)));
  };

  useEffect(load, []);

  if (err) return <div className="error">{err}</div>;
  if (!pf) return <div className="empty">Loading…</div>;

  return (
    <>
      <div className="header">
        <h2>Portfolio</h2>
        <button onClick={load}>Refresh</button>
      </div>

      <div className="grid grid-3">
        <div className="card"><h3>Equity</h3><div className="kpi">₹{pf.equity.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</div></div>
        <div className="card"><h3>Cash</h3><div className="kpi">₹{pf.cash.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</div></div>
        <div className="card"><h3>Positions</h3><div className="kpi">{pf.positions.length}</div></div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h3>Open Positions</h3>
        {pf.positions.length === 0 ? <div className="empty">No open positions</div> : (
          <table>
            <thead>
              <tr><th>Symbol</th><th className="num">Qty</th><th className="num">Avg Cost</th>
                <th className="num">Last</th><th className="num">Market Value</th><th className="num">Unrealized P&amp;L</th></tr>
            </thead>
            <tbody>
              {pf.positions.map((p) => (
                <tr key={p.symbol}>
                  <td>{p.symbol}</td>
                  <td className="num">{p.qty}</td>
                  <td className="num">{p.avg_price.toFixed(2)}</td>
                  <td className="num">{p.last_price.toFixed(2)}</td>
                  <td className="num">{p.market_value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</td>
                  <td className={`num ${p.unrealized_pnl >= 0 ? "pos" : "neg"}`}>
                    {p.unrealized_pnl.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h3>Trade History</h3>
        {trades.length === 0 ? <div className="empty">No trades yet</div> : (
          <table>
            <thead>
              <tr><th>Time</th><th>Symbol</th><th>Side</th><th className="num">Qty</th>
                <th className="num">Price</th><th className="num">P&amp;L</th><th>Strategy</th><th>Reason</th></tr>
            </thead>
            <tbody>
              {trades.map((t) => (
                <tr key={t.id}>
                  <td>{new Date(t.timestamp).toLocaleString()}</td>
                  <td>{t.symbol}</td>
                  <td><span className={`signal-pill ${t.side}`}>{t.side}</span></td>
                  <td className="num">{t.qty}</td>
                  <td className="num">{t.price.toFixed(2)}</td>
                  <td className={`num ${t.pnl >= 0 ? "pos" : "neg"}`}>{t.pnl ? t.pnl.toFixed(2) : "—"}</td>
                  <td>{t.strategy}</td>
                  <td style={{ color: "var(--muted)", fontSize: 11 }}>{t.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
