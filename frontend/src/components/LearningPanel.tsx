import { useEffect, useState } from "react";
import { api, type LearningEntry } from "../api/client";

export default function LearningPanel() {
  const [entries, setEntries] = useState<LearningEntry[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.learning().then(setEntries).catch((e) => setErr(String(e)));
  }, []);

  return (
    <>
      <div className="header">
        <h2>Learning Log</h2>
        <span className="badge">what the bot has learned from its own trades</span>
      </div>
      {err && <div className="error">{err}</div>}
      <div className="card">
        {entries.length === 0
          ? <div className="empty">No insights yet. The bot logs here whenever it closes a trade and the RL tuner updates strategy parameters.</div>
          : entries.map((e) => (
            <div className="log-line" key={e.id}>
              <span className={`kind-chip ${e.kind}`}>{e.kind}</span>
              {e.message}
              <div className="log-meta">{new Date(e.timestamp).toLocaleString()}</div>
            </div>
          ))}
      </div>
    </>
  );
}
