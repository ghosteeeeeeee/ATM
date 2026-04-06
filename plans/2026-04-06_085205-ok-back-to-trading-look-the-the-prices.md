# DYDX Trading Analysis — Plan
**Goal:** Extract actionable lessons from DYDX trading history (Mar 19–26, 2026) to improve SL/TP design, entry discipline, and cascade-flip behavior.
**Output:** A written brief with specific rule changes + updated ATM/config/stoploss.md

---

## Data Sources

| Source | Path | Contents |
|--------|------|----------|
| HL Fills (ground truth) | `/root/.hermes/data/hl_fills_0x324a9713603863FE3A678E83d7a81E20186126E7.csv` | All HL fills — entries, exits, sizes, prices, PnL |
| Signals DB | `/root/.hermes/data/signals_hermes_runtime.db` | DYDX signals with confidence, type, decision |
| Trade Analysis | `/root/.hermes/data/trade_analysis_full.csv` | Reconstructed trades with exit reasons |
| Price history | `signals_hermes_runtime.db` (price_history table) | 1-min candles for DYDX around entry/exit times |

---

## Step-by-Step Plan

### Step 1 — Extract all DYDX fills from HL fills CSV

Filter `hl_fills_*.csv` for `coin=DYDX`. Parse into:
- Open events: timestamp, direction, size, entry_price
- Close events: timestamp, exit_price, closedPnl, fee, profit_loss

Reconstruct individual "round-trip trades" by pairing opens with closes by same `oid`.

**Expected output:** List of round-trips with entry_time, exit_time, direction, entry_px, exit_px, pnl_pct, pnl_usd, close_reason.

**File:** `analyze_dydx.py` (new script in `/root/.hermes/scripts/`)

---

### Step 2 — Pull DYDX signals from signals DB

Query `signals` table where `token='DYDX'` and `created_at >= '2026-03-19'`.
Extract: signal_type, confidence, direction, decision, price, z_score, RSI, MACD at signal time.

Overlay signals onto the trade timeline — were we entering on high-confidence signals or marginal ones?

**Verification:** Confirm signals existed before each HL fill entry. Any entries with no prior signal?

---

### Step 3 — Pull price candles from signal_gen price cache

Get 1-minute (or 5-minute) candles for DYDX around each entry/exit window (±2 hours).
Compute:
- Price at signal time vs entry price (slippage?)
- Z-score at entry vs price path to SL/TP
- 5m velocity at entry (were we chasing a move already in progress?)
- RSI at entry (overbought/oversold — did we enter against RSI?)
- Volume spike at entry (breakout or fade?)

---

### Step 4 — Analyze each trade round-trip

For each round-trip trade, answer:

| Question | Why It Matters |
|----------|---------------|
| Entry: clean single entry or multiple scale-ins? | Multiple opens = overtrading, diluted size |
| SL distance: % from entry to SL? | Too tight = stopped out before trend develops |
| TP: was TP hit, or did price reverse? | If price hit TP range but reversed, TP was too tight |
| Close reason: SL, TP, cascade flip, stale rotation, manual? | Identify which exit type is costing us |
| Signal confidence at entry: >85% or marginal? | Marginal signals = gambling |
| Regime at entry: did regime align with direction? | Fighting regime = trading against momentum |
| RSI at entry: overbought/oversold? | Entering SHORT at RSI oversold = catching a knife |
| Time in trade: how long? | Short stint = tight stop vs trend continuation |

---

### Step 5 — Identify patterns across all DYDX trades

Specifically look for:

**Overtrading cluster:**
- Mar 19: 4 SHORT entries in ~2.5 hours (11:30, 11:45, 12:36, 16:56)
- Were these separate signals or the same signal being executed multiple times?
- Was the first loss (SL at 11:42) the trigger for over-entries chasing the move?

**SL tightness:**
- Trade 1: entry 0.08728, SL at -1.17% (closed 11:42), price only moved 0.034% against us
- Is the SL too tight for a token with this volatility profile?
- What was the actual HL price path minute-by-minute?

**Cascade flip opportunity:**
- After the Mar 19 SHORT closes at loss (-$0.039), did a LONG signal appear?
- Did we flip to LONG or miss the bottom?
- Was there a clear cascade flip setup (loss + opposite signal)?

**TP vs price reality:**
- DYDX moved ~1.4% over the full Mar 19 session
- If we SHORTed at 0.08728 and rode to 0.08627 = 1.15% move
- Did we capture that move or get stopped out early?

---

### Step 6 — Synthesize findings into rule changes

For each finding, write a concrete rule recommendation:

1. **SL rule change:** For tokens with avg_volatility > X, widen SL to 2× ATR(14) or 2× the normal %
2. **Scale-in rule:** Only ONE clean entry per signal. No re-entry on same signal within 30 min unless cascade flip
3. **Cascade flip enforcement:** After a loss, mandatory wait for opposite signal before re-entering
4. **Entry coherence gate:** Entry must have RSI < 70 (for LONG) or RSI > 30 (for SHORT) — no entering when RSI is already at extremes
5. **Velocity gate:** Only enter if 5m velocity is aligned with direction AND < 50% of daily velocity (avoid chasing)

---

## Files to Create/Modify

### New files
- `/root/.hermes/scripts/analyze_dydx.py` — DYDX trade analysis script
- `/root/.hermes/plans/DYDX-analysis-findings.md` — findings brief

### Modified files
- `/root/.hermes/ATM/config/stoploss.md` — add DYDX-specific SL/TP findings
- `/root/.hermes/brain/trading.md` — add DYDX analysis results under Live Log

---

## Validation

- Run `analyze_dydx.py` — produces a formatted table of all DYDX round-trips
- Cross-check: do HL fill PnL figures match what our DB shows?
- If cascade flip was missed: confirm by checking signals DB for LONG signal within 15 min of each SHORT close

---

## Risks / Open Questions

1. **Historical prices at entry times** — do we have minute-level price data for Mar 19-20 in the DB? If not, need to source from HL API or accept approximation
2. **Signal vs fill alignment** — HL fills may not align 1:1 with our signals (paper trades may differ from what HL shows)
3. **Mar 26+ trades** — user mentioned "started trading around March 26th" — need to check if DYDX fills exist beyond Mar 20 in the CSV
4. **TL feedback** — should present findings to T for his qualitative read on whether rules make sense for his trading style
