import { useState } from "react";
import { api, type BacktestResult } from "../api/client";

export default function BacktestPanel() {
  const [symbol, setSymbol] = useState("RELIANCE.NS");
  const [period, setPeriod] = useState("2y");
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [trainBusy, setTrainBusy] = useState(false);
  const [trainOut, setTrainOut] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);

  const runBacktest = () => {
    setBusy(true); setErr(null);
    api.backtest(symbol, period).then(setResult).catch((e) => setErr(String(e))).finally(() => setBusy(false));
  };
  const trainMl = () => {
    setTrainBusy(true); setTrainOut("");
    api.trainMl(symbol, "5y")
      .then((r) => setTrainOut(JSON.stringify(r, null, 2)))
      .catch((e) => setTrainOut(`Error: ${e}`))
      .finally(() => setTrainBusy(false));
  };

  return (
    <>
      <div className="header"><h2>Backtest & ML Training</h2></div>

      <div className="card" style={{ marginBottom: 14 }}>
        <h3>Run a backtest</h3>
        <div className="row">
          <input value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} />
          <select value={period} onChange={(e) => setPeriod(e.target.value)}>
            <option value="6mo">6 months</option>
            <option value="1y">1 year</option>
            <option value="2y">2 years</option>
            <option value="5y">5 years</option>
          </select>
          <button className="primary" onClick={runBacktest} disabled={busy}>
            {busy ? "Running…" : "Run Backtest"}
          </button>
          <button onClick={trainMl} disabled={trainBusy}>
            {trainBusy ? "Training…" : "Train ML on 5y"}
          </button>
        </div>
        {err && <div className="error">{err}</div>}
        {trainOut && <pre style={{ background: "var(--panel-2)", padding: 10, borderRadius: 6, marginTop: 10, fontSize: 11 }}>{trainOut}</pre>}
      </div>

      {result && (
        <>
          <div className="grid grid-3">
            {Object.entries(result.metrics).map(([k, v]) => (
              <div className="card" key={k}>
                <h3>{k}</h3>
                <div className="kpi">{typeof v === "number" ? v.toFixed(2) : String(v)}</div>
              </div>
            ))}
          </div>

          <div className="card" style={{ marginTop: 14 }}>
            <h3>Trades ({result.trades.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>Time</th><th>Side</th>
                  <th className="num">Qty</th><th className="num">Price</th>
                  <th className="num">P&amp;L</th><th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {result.trades.slice(-30).reverse().map((t: any, i: number) => (
                  <tr key={i}>
                    <td>{new Date(t.timestamp).toLocaleDateString()}</td>
                    <td><span className={`signal-pill ${t.side}`}>{t.side}</span></td>
                    <td className="num">{t.qty}</td>
                    <td className="num">{t.price.toFixed(2)}</td>
                    <td className={`num ${t.pnl >= 0 ? "pos" : "neg"}`}>{t.pnl ? t.pnl.toFixed(2) : "—"}</td>
                    <td style={{ color: "var(--muted)", fontSize: 11 }}>{t.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
