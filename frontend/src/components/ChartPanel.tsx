import { useEffect, useRef, useState } from "react";
import { createChart, type IChartApi, type ISeriesApi } from "lightweight-charts";
import { api, type Signal } from "../api/client";
import SymbolSearch from "./SymbolSearch";

type Tf = { label: string; interval: string; period: string; isIntraday: boolean };
const TIMEFRAMES: Tf[] = [
  { label: "1m",  interval: "1m",  period: "1d",  isIntraday: true  },
  { label: "5m",  interval: "5m",  period: "5d",  isIntraday: true  },
  { label: "15m", interval: "15m", period: "1mo", isIntraday: true  },
  { label: "1h",  interval: "60m", period: "3mo", isIntraday: true  },
  { label: "1D",  interval: "1d",  period: "5y",  isIntraday: false },  // Changed from 6mo to 5y for full history
];
const REFRESH_MS = 30_000;

export default function ChartPanel() {
  const [symbol, setSymbol] = useState("AAPL");
  const [input, setInput] = useState("AAPL");
  const [tf, setTf] = useState<Tf>(TIMEFRAMES[4]); // default 1D (5y history)
  const [sig, setSig] = useState<Signal | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [qty, setQty] = useState(1);
  const [busy, setBusy] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>("");

  const hostRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!hostRef.current) return;
    const chart = createChart(hostRef.current, {
      layout: { background: { color: "#121826" }, textColor: "#e6ecf5" },
      grid: { vertLines: { color: "#243049" }, horzLines: { color: "#243049" } },
      timeScale: { borderColor: "#243049" },
      rightPriceScale: { borderColor: "#243049" },
      autoSize: true,
    });
    const series = chart.addCandlestickSeries({
      upColor: "#2ecc71", downColor: "#ff5c5c",
      borderUpColor: "#2ecc71", borderDownColor: "#ff5c5c",
      wickUpColor: "#2ecc71", wickDownColor: "#ff5c5c",
    });
    chartRef.current = chart;
    seriesRef.current = series;
    return () => { chart.remove(); chartRef.current = null; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      setErr(null);
      api.history(symbol, tf.period, tf.interval).then((h) => {
        if (cancelled) return;
        seriesRef.current?.setData(
          h.candles.map((c) => ({
            // Lightweight Charts wants seconds-since-epoch for intraday,
            // YYYY-MM-DD for daily. Convert accordingly.
            time: tf.isIntraday
              ? Math.floor(new Date(c.time).getTime() / 1000)
              : c.time.slice(0, 10),
            open: c.open, high: c.high, low: c.low, close: c.close,
          })) as any
        );
        chartRef.current?.timeScale().fitContent();
        setLastUpdate(new Date().toLocaleTimeString());
      }).catch((e) => !cancelled && setErr(String(e)));
      api.signal(symbol).then((s) => !cancelled && setSig(s)).catch(() => {});
    };
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => { cancelled = true; clearInterval(id); };
  }, [symbol, tf]);

  const placeOrder = async (side: "BUY" | "SELL") => {
    setBusy(true);
    try {
      await api.order(
        symbol, side, qty,
        sig?.action === side ? "ma_crossover" : "manual",
        sig?.blended_confidence ?? 0,
        sig?.reason ?? "",
      );
      alert(`${side} ${qty} ${symbol} filled`);
    } catch (e) { alert(`Order failed: ${e}`); }
    finally { setBusy(false); }
  };

  return (
    <>
      <div className="header">
        <h2>Chart & AI Signal</h2>
        <div className="row">
          {TIMEFRAMES.map((t) => (
            <button
              key={t.label}
              onClick={() => setTf(t)}
              className={tf.label === t.label ? "primary" : ""}
              style={{ padding: "4px 10px" }}
            >{t.label}</button>
          ))}
          <div style={{ width: 220 }}>
            <SymbolSearch
              value={input}
              onChange={setInput}
              onSelect={setSymbol}
              placeholder="Search symbol..."
            />
          </div>
          <button className="primary" onClick={() => setSymbol(input)}>Load</button>
          {lastUpdate && <span className="sub">⟳ {lastUpdate}</span>}
        </div>
      </div>

      {err && <div className="error">{err}</div>}

      <div className="grid grid-2" style={{ gridTemplateColumns: "2fr 1fr" }}>
        <div className="card">
          <h3>{symbol}</h3>
          <div className="chart-host" ref={hostRef} />
        </div>

        <div className="card">
          <h3>AI Signal</h3>
          {!sig ? <div className="empty">Loading signal…</div> : (
            <>
              <div className="row" style={{ marginBottom: 10 }}>
                <span className={`signal-pill ${sig.action}`}>{sig.action}</span>
                <span className="sub" style={{ marginLeft: 8 }}>{sig.reason}</span>
              </div>

              <div className="sub">Blended confidence</div>
              <div className="bar" style={{ marginBottom: 8 }}>
                <div style={{ width: `${Math.round(sig.blended_confidence * 100)}%` }} />
              </div>
              <table>
                <tbody>
                  <tr><td>Rule confidence</td><td className="num">{(sig.rule_confidence * 100).toFixed(0)}%</td></tr>
                  <tr><td>ML P(up)</td><td className="num">{sig.ml_p_up != null ? `${(sig.ml_p_up * 100).toFixed(0)}%` : "—"}</td></tr>
                  <tr><td>Stop loss</td><td className="num">{sig.stop_loss?.toFixed(2) ?? "—"}</td></tr>
                  <tr><td>Target</td><td className="num">{sig.target?.toFixed(2) ?? "—"}</td></tr>
                </tbody>
              </table>

              <div className="row" style={{ marginTop: 12 }}>
                <input type="number" value={qty} min={1} onChange={(e) => setQty(parseInt(e.target.value || "1"))} style={{ width: 80 }} />
                <button className="primary" disabled={busy} onClick={() => placeOrder("BUY")}>Buy</button>
                <button disabled={busy} onClick={() => placeOrder("SELL")}>Sell</button>
              </div>
              <div className="sub" style={{ marginTop: 10 }}>
                {sig.ml_p_up == null && <>ML model not trained yet — go to Backtest tab to train.</>}
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
