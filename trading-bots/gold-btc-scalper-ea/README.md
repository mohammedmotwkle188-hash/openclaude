# Gold/BTC Scalper EA (MQL5)

A MetaTrader 5 Expert Advisor that scalps continuously (no session/time filter, no cooldown) using an EMA(5/13) crossover on M1 confirmed by RSI momentum, with ATR-based stops so the same code adapts automatically to very different instruments (gold vs. BTC). It supports true hedging (simultaneous buy + sell), up to `InpMaxTrades` concurrent positions, breakeven + trailing stop, and optional TP extension so winners can keep running instead of being capped early.

## Requirements

- MetaTrader 5, broker account in **hedging** margin mode (required to hold buy and sell positions on the same symbol at once — netting accounts will merge them).
- Broker must offer both symbols you want to trade, e.g. `XAUUSD` and `BTCUSD` (exact names vary by broker — check Market Watch).
- Algo Trading enabled in MT5.

## Install

1. Copy `GoldBtcScalperEA.mq5` into `MQL5/Experts/` (File → Open Data Folder from MT5).
2. Open it in MetaEditor and compile (F7) — should produce no errors.
3. Attach it to a **Gold chart** (e.g. XAUUSD, M1) and separately to a **BTC chart** (e.g. BTCUSD, M1). Each chart runs its own instance/position book.
4. Give each instance a different `InpMagic` (e.g. 990033 for gold, 990034 for BTC) so they don't interfere with each other's position counting.

## What it does

- **Signal**: EMA(5) crosses EMA(13) on M1 → direction flips as often as the market does, no bias toward one side.
- **Stops sized by ATR**, not fixed points — this is what lets one EA run on both a $2000 instrument (gold) and a $60000 one (BTC) without re-tuning.
- **Breakeven + trailing SL**: once profit reaches `InpBreakevenATRMult × ATR`, SL moves to entry + a small locked buffer, then trails behind price — it only ever moves in the trade's favor, never loosens.
- **TP extension** (`InpExtendTP`): if price approaches the take-profit while the EMA trend is still aligned, TP is pushed further out instead of closing — lets a strong move keep compounding instead of capping the win.
- **Hedging**: `InpAllowHedging = true` lets it hold buy and sell positions on the same symbol at the same time.
- **Up to `InpMaxTrades` (default 10)** concurrent positions per symbol/magic.
- No time-of-day/session filter, no trade cooldown, and the spread filter (`InpMaxSpreadPoints`) defaults to **0 = disabled**.

## Inputs worth tuning per account size

| Input | Purpose |
|---|---|
| `InpLotSize` | Fixed lot per trade. With up to 10 concurrent trades, total exposure = `InpLotSize × InpMaxTrades` — size this to your account, not the other way around. |
| `InpMaxTrades` | Hard cap on concurrent positions per symbol/magic. |
| `InpSLATRMult` / `InpTPATRMult` | Initial risk:reward shape. |
| `InpMaxSpreadPoints` | Set > 0 if you want a spread guard during illiquid hours; 0 keeps every setup untouched as requested. |

## Honest expectations

This is a real scalping strategy (volatility-adaptive stops, trailing profit, momentum confirmation), not a toy — but running it with no filters, no cooldown, and up to 10 simultaneous positions means drawdowns can move fast in both directions. No configuration of this EA (or any EA) can guarantee a specific dollar return like $500–$1000; that depends entirely on lot size, account equity, and market conditions at the time. Test on a demo account first and size `InpLotSize` conservatively relative to account equity before going live.
