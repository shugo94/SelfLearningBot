# Symbol Search Feature

## Overview
Added a **searchable dropdown** to all symbol inputs (Chart, Backtest) similar to TradingView.

## Stock coverage

**Without Angel One (using Yahoo Finance):**
- 24 popular NSE/BSE stocks (hardcoded defaults)
- RELIANCE, TCS, INFY, HDFC Bank, ICICI, SBI, Axis, L&T, ITC, Kotak, Airtel, HUL, Maruti, Wipro, ONGC, Bajaj Finance, Sun Pharma, Asian Paint, Bajaj Auto, JSW Steel, Tata Steel, Power Grid, Grasim, UPL

**With Angel One configured:**
- All ~10,000 NSE/BSE listed stocks
- Search activates when you type 3+ characters
- First shows matches from default list (fastest)
- Then adds matches from full instrument master

## How it works

### Frontend
- **New component:** `SymbolSearch.tsx` — reusable autocomplete input
- **Behavior:**
  1. User types a symbol (e.g., "REL")
  2. Dropdown shows matching symbols from API
  3. Click a result to select it
  4. Optionally press Enter to load

### Backend
- **New endpoint:** `GET /api/symbols/search?q=<query>`
- **Returns:**
  - Empty query → entire default universe (12 symbols)
  - "REL" → RELIANCE.NS
  - "TCS" → TCS.NS
  - etc.

- **Data sources:**
  1. **Default universe** — hardcoded NSE/BSE stocks (from config)
  2. **Angel One instrument master** — if credentials configured, searches all ~10k NSE/BSE symbols

### UI Indicators
- 📊 = Yahoo Finance (15-min delayed)
- 🔴 = Angel One (live, real-time)

## Integration

### Chart Panel
```tsx
<SymbolSearch
  value={input}
  onChange={setInput}
  onSelect={setSymbol}
  placeholder="Search symbol..."
/>
```

### Backtest Panel
```tsx
<SymbolSearch
  value={symbol}
  onChange={setSymbol}
  placeholder="e.g. RELIANCE.NS"
/>
```

## Files Changed

**Backend:**
- `app/api/routes.py` — added `search_symbols()` endpoint + `/api/symbols/search` route

**Frontend:**
- `src/components/SymbolSearch.tsx` — new reusable component
- `src/components/ChartPanel.tsx` — integrated SymbolSearch
- `src/components/BacktestPanel.tsx` — integrated SymbolSearch
- `src/api/client.ts` — added `searchSymbols()` method + types
- `package.json` — added `downshift` dep (currently unused, could add for more features)

## Future enhancements

- Add **keyboard navigation** (arrow keys, Enter to select)
- Add **recent symbols** history
- Add **favorites** (star symbol to remember)
- Show **quote preview** when hovering (price, change %)
- **Fuzzy matching** instead of substring match
