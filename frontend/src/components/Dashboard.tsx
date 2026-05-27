import { useEffect, useState } from "react";
import { api, type Portfolio, type ScreenerRow, type LearningEntry } from "../api/client";

export default function Dashboard({ onNavigate }: { onNavigate: (t: string) => void }) {
  const [pf, setPf] = useState<Portfolio | null>(null);
  const [picks, setPicks] = useState<ScreenerRow[]>([]);
  const [learn, setLearn] = useState<LearningEntry[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.portfolio(), api.screener(5), api.learning()])
      .then(([p, s, l]) => { setPf(p); setPicks(s); setLearn(l.slice(0, 5)); })
      .catch((e) => setErr(String(e)));
  }, []);

  if (err) return <div className="error">Backend not reachable: {err}<br/>Start it with: <code>cd backend && uvicorn app.main:app --reload --port 8765</code></div>;
  if (!pf) return <div className="empty">Loading…</div>;

  const pnl = pf.equity - 1_000_000; // crude — compares vs default starting cash
  const pnlClass = pnl >= 0 ? "green" : "red";

  return (
    <>
      <div className="header">
        <h2>Dashboard</h2>
        <span className="badge">paper trading</span>
      </div>

      <div className="grid grid-3">
        <div className="card">
          <h3>Equity</h3>
          <div className="kpi">₹{pf.equity.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</div>
          <div className={`sub ${pnlClass}`}>
            {pnl >= 0 ? "▲" : "▼"} ₹{Math.abs(pnl).toLocaleString("en-IN", { maximumFractionDigits: 0 })} vs starting
          </div>
        </div>
        <div className="card">
          <h3>Cash</h3>
          <div className="kpi">₹{pf.cash.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</div>
          <div className="sub">{pf.positions.length} open position(s)</div>
        </div>
        <div className="card">
          <h3>Unrealized P&amp;L</h3>
          {(() => {
            const u = pf.positions.reduce((a, p) => a + p.unrealized_pnl, 0);
            return (
              <>
                <div className={`kpi ${u >= 0 ? "green" : "red"}`}>₹{u.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</div>
                <div className="sub">across all positions</div>
              </>
            );
          })()}
        </div>
      </div>

      <div className="grid grid-2" style={{ marginTop: 14 }}>
        <div className="card">
          <h3>Top AI Picks</h3>
          {picks.length === 0 ? <div className="empty">No picks yet</div> :
            <table>
              <thead><tr><th>Symbol</th><th>Signal</th><th className="num">Score</th><th className="num">RSI</th><th className="num">1m %</th></tr></thead>
              <tbody>
                {picks.map((p) => (
                  <tr key={p.symbol} onClick={() => onNavigate("chart")} style={{cursor: "pointer"}}>
                    <td>{p.symbol}</td>
                    <td><span className={`signal-pill ${p.ai_signal}`}>{p.ai_signal}</span></td>
                    <td className="num">{p.score.toFixed(2)}</td>
                    <td className="num">{p.rsi14}</td>
                    <td className={`num ${p.ret_1m_pct >= 0 ? "pos" : "neg"}`}>{p.ret_1m_pct.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          }
        </div>
        <div className="card">
          <h3>Recent Learning</h3>
          {learn.length === 0
            ? <div className="empty">The bot hasn't logged anything yet. Run a trade or backtest to start.</div>
            : learn.map((l) => (
              <div className="log-line" key={l.id}>
                <span className={`kind-chip ${l.kind}`}>{l.kind}</span>
                {l.message}
                <div className="log-meta">{new Date(l.timestamp).toLocaleString()}</div>
              </div>
            ))}
        </div>
      </div>
    </>
  );
}
