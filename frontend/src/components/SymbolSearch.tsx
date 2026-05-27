import { useEffect, useState } from "react";
import { api, type SymbolMatch } from "../api/client";

interface Props {
  value: string;
  onChange: (symbol: string) => void;
  onSelect?: (symbol: string) => void;
  placeholder?: string;
}

export default function SymbolSearch({ value, onChange, onSelect, placeholder = "Search stocks..." }: Props) {
  const [results, setResults] = useState<SymbolMatch[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!value.trim()) {
      api.searchSymbols("").then(setResults).catch(() => setResults([]));
      setOpen(true);
      return;
    }
    setLoading(true);
    const timer = setTimeout(() => {
      api.searchSymbols(value).then(setResults).catch(() => setResults([])).finally(() => setLoading(false));
    }, 300); // debounce
    return () => clearTimeout(timer);
  }, [value]);

  const handleSelect = (sym: string) => {
    onChange(sym);
    onSelect?.(sym);
    setOpen(false);
  };

  return (
    <div style={{ position: "relative", width: "100%" }}>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value.toUpperCase())}
        onFocus={() => setOpen(true)}
        placeholder={placeholder}
        style={{ width: "100%", paddingRight: 20 }}
        spellCheck={false}
        autoComplete="off"
      />
      {loading && <span style={{ position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)", fontSize: 11, color: "var(--muted)" }}>...</span>}
      {open && results.length > 0 && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            background: "var(--panel)",
            border: "1px solid var(--border)",
            borderTop: "none",
            borderRadius: "0 0 6px 6px",
            maxHeight: 300,
            overflowY: "auto",
            zIndex: 10,
            boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
          }}
        >
          {results.map((r, i) => (
            <div
              key={`${r.symbol}-${i}`}
              onClick={() => handleSelect(r.symbol)}
              style={{
                padding: "8px 12px",
                cursor: "pointer",
                borderBottom: "1px solid var(--border)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--panel-2)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <span style={{ fontWeight: 500 }}>{r.symbol}</span>
              <span style={{ fontSize: 10, color: "var(--muted)" }}>
                {r.source === "angel_one" ? `${r.exchange} 🔴` : "📊"}
              </span>
            </div>
          ))}
        </div>
      )}
      {open && results.length === 0 && value && !loading && (
        <div style={{
          position: "absolute",
          top: "100%",
          left: 0,
          right: 0,
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderTop: "none",
          padding: "12px",
          color: "var(--muted)",
          fontSize: 12,
          textAlign: "center",
        }}>
          <div>No symbols found</div>
          {value.length < 3 && (
            <div style={{ fontSize: 10, marginTop: 6, color: "var(--muted)" }}>
              Type 3+ chars to search all stocks
            </div>
          )}
          <div style={{ fontSize: 10, marginTop: 6, color: "var(--accent)" }}>
            💡 Configure Angel One in Settings for access to all ~10k NSE/BSE stocks
          </div>
        </div>
      )}
    </div>
  );
}
