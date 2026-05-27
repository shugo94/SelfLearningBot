import { useEffect, useState } from "react";
import Dashboard from "./components/Dashboard";
import ChartPanel from "./components/ChartPanel";
import ScreenerPanel from "./components/ScreenerPanel";
import BacktestPanel from "./components/BacktestPanel";
import PortfolioPanel from "./components/PortfolioPanel";
import LearningPanel from "./components/LearningPanel";
import SettingsPanel from "./components/SettingsPanel";
import { api, type BrokerStatus } from "./api/client";

type Tab = "dashboard" | "chart" | "screener" | "backtest" | "portfolio" | "learning" | "settings";

const TABS: { id: Tab; label: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "chart", label: "Chart & Signal" },
  { id: "screener", label: "Screener" },
  { id: "backtest", label: "Backtest" },
  { id: "portfolio", label: "Portfolio" },
  { id: "learning", label: "Learning Log" },
  { id: "settings", label: "Settings" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [broker, setBroker] = useState<BrokerStatus | null>(null);

  useEffect(() => {
    api.brokerStatus().then(setBroker).catch(() => {});
  }, []);

  const sourceLabel = broker?.active_source === "angel_one" ? "Angel One · LIVE" : "Yahoo · delayed";
  const sourceColor = broker?.active_source === "angel_one" ? "var(--green)" : "var(--warn)";

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>● SelfLearningBot</h1>
        {TABS.map((t) => (
          <div
            key={t.id}
            className={`nav-item ${tab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </div>
        ))}
        <div style={{ flex: 1 }} />
        <div
          onClick={() => setTab("settings")}
          style={{
            padding: "10px 10px", borderRadius: 6, cursor: "pointer",
            background: "var(--panel-2)", border: `1px solid ${sourceColor}33`,
            fontSize: 11, color: "var(--muted)",
          }}
          title="Click to change data source"
        >
          Data source<br />
          <span style={{ color: sourceColor, fontWeight: 600 }}>● {sourceLabel}</span>
        </div>
      </aside>
      <main className="main">
        {tab === "dashboard" && <Dashboard onNavigate={setTab as (t: string) => void} />}
        {tab === "chart" && <ChartPanel />}
        {tab === "screener" && <ScreenerPanel />}
        {tab === "backtest" && <BacktestPanel />}
        {tab === "portfolio" && <PortfolioPanel />}
        {tab === "learning" && <LearningPanel />}
        {tab === "settings" && <SettingsPanel onStatusChange={setBroker} />}
      </main>
    </div>
  );
}
