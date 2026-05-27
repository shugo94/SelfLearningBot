import { useEffect, useState } from "react";
import { api, type ScreenerRow } from "../api/client";

export default function ScreenerPanel() {
  const [rows, setRows] = useState<ScreenerRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = () => {
    setLoading(true); setErr(null);
    api.screener(15).then(setRows).catch((e) => setErr(String(e))).finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <>
      <div className="header">
        <h2>Stock Screener</h2>
        <button className="primary" onClick={load} disabled={loading}>{loading ? "Scoring…" : "Refresh"}</button>
      </div>
      {err && <div className="error">{err}</div>}
      <div className="card">
        <h3>Universe ranking — composite score blends momentum, trend, breakout, volume</h3>
        <table>
          <thead>
            <tr>
              <th>Symbol</th><th>AI Signal</th>
              <th className="num">Score</th><th className="num">Price</th>
              <th className="num">1m %</th><th className="num">3m %</th>
              <th className="num">RSI</th><th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.symbol}>
                <td>{r.symbol}</td>
                <td><span className={`signal-pill ${r.ai_signal}`}>{r.ai_signal}</span></td>
                <td className="num">{r.score.toFixed(2)}</td>
                <td className="num">{r.price.toFixed(2)}</td>
                <td className={`num ${r.ret_1m_pct >= 0 ? "pos" : "neg"}`}>{r.ret_1m_pct.toFixed(1)}</td>
                <td className={`num ${r.ret_3m_pct >= 0 ? "pos" : "neg"}`}>{r.ret_3m_pct.toFixed(1)}</td>
                <td className="num">{r.rsi14}</td>
                <td style={{ color: "var(--muted)", fontSize: 11 }}>{r.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && !loading && <div className="empty">No data</div>}
      </div>
    </>
  );
}
