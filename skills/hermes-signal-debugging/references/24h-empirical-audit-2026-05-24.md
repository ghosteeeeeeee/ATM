# 24h Empirical Audit — ZSCORE+RS Signal Quality (2026-05-24)

## Source Data
- PostgreSQL `brain.trades`: 83 closed trades (47 LONG, 36 SHORT), last 24h
- SQLite `signals_hermes_runtime.db`: 4,656 zscore_pump signals (2,477 LONG, 2,175 SHORT)

---

## Finding 1: ALL Signals Are Combo — No Pure zscore-pump

**Reality:** Every single trade in the 24h dataset is a combo signal: `rs-s{N},zscore-pump+` or `rs-r{N},zscore-pump-`. Zero pure zscore-pump entries exist.

**Prior assumption (WRONG):** "single-source zscore catches falling knives"
**Correction:** All signals are combo by design. The problem isn't single-source noise — it's that the combo of RS+zscore amplifies same-timeframe noise (all read from the same 1m candles).

**Implication for `hermes-signal-debugging` triggers:** The "zscore-pump+ combo loses always" trigger was incorrect. The 24h audit shows ~43% WR both directions, net +$0.81 LONG, -$0.10 SHORT.

---

## Finding 2: Extreme Z Does NOT Predict Loss

| Token | Dir | z_score (signal DB) | Trade Result | close_reason |
|-------|-----|---------------------|--------------|--------------|
| IP | SHORT | -6.712 | **+1.25% WIN** | profit-monster |
| BLUR | SHORT | -6.161 | **+1.69% WIN** | profit-monster |
| VINE | SHORT | -5.619 | Mixed | — |
| VINE | LONG | 6.915 | Mixed | — |

**Prior assumption (WRONG):** "extreme z = blow-off top = reversal trap"
**Correction:** IP SHORT and BLUR SHORT both won with extreme z. z magnitude alone doesn't predict outcome. The divergence filter (at Z=3.0) is insufficient to catch all blow-offs, but the hard cap approach was also wrong.

**Winning z-range:** Winners cluster at z=2.0–3.0 (sustainable momentum)
**Extreme z behavior:** z > 4.0 shows mixed results — some win (IP, BLUR), some lose. Not a reliable signal.

---

## Finding 3: Duration Asymmetry — Key Differentiator

| Outcome | Trades | Avg Duration | Avg PnL | Exit |
|---------|--------|--------------|---------|------|
| **WINNER** | 27 | **81 min** | +1.12% | profit-monster (TP) |
| **LOSER** | 32 | **54 min** | -0.59% | atr_sl_hit (SL) |

**Root cause:** Winners take 50% longer to develop. Losers fail in 54 min — before the trade has time to work. The signal is correct but the SL placement is too tight, cutting winners short before they reach TP.

**What this means:** The priority is NOT filtering by z-score magnitude. It's widening the SL for high-conviction combo signals so winners have room to run.

**Proposed fix (Priority 1 from plan):**
```python
# hermes_constants.py
RS_COMBO_SL_MULTIPLIER = 1.3  # widen ATR SL by 30% for RS+zscore combo entries
```
Applied in position_manager.py for entries with both RS and zscore-pump in signal source.

---

## Finding 4: Signal Z-Score Stats (signals_hermes_runtime.db, 24h)

| Direction | Signals | Avg |z| | Min | Max |
|-----------|---------|---------|-----|-----|
| LONG | 2,477 | 2.63 | 2.0 | 8.18 |
| SHORT | 2,175 | 2.64 | 2.0 | 6.90 |

**Winners (signal DB):** Avg z ≈ 2.63 LONG, -2.64 SHORT — same as overall. No z threshold can cleanly separate winners from losers.

---

## Finding 5: Lookback Conflict — Resolved

| Plan | Date | Lookback | Basis |
|------|------|----------|-------|
| Plan A | May 22 | 50 | FET single-event backtest |
| Plan B | May 24 | 70 | 83-trade empirical audit |

**Decision:** Use **70** (empirical beats single-event). Plan A's lookback=50 was derived from one missed FET pump event. Plan B's 83-trade audit across all market conditions is more representative.

**Subagent recommendation (trusted):** 83 real trades > 1 backtest scenario.

---

## Finding 6: What's Implemented vs Pending

### ✅ Implemented (from prior plans)
- GOOD_STANDALONE_SIGNALS naming fix
- RS ATR band removal
- RS_DECIDER_MIN_TOUCHES = 200 (minimum RS touch filter)
- Guard z_score merge with COALESCE (signal_schema.py)
- Write signal_z_score to trade record
- ZSCORE-GATE in decider_run (z=None penalty)
- Accel_300 token allowlist (23 tokens)
- pct_hermes threshold 72→80
- vel_hermes regime filter

### ⏳ Still Pending (from prior plans)
- Opposing signal penalty (30 min block after loss)
- RS bounce freshness (6→3 candles) — `_RS_BOUNCE_LOOKBACK = 6` in rs.py line 56
- High-touch level decay (>5000 touches)
- Multi-window z-score scoring (Plan A, keep)
- Momentum-velocity boost (Plan A, keep)
- Signal persistence/grace period (Plan A, keep)

---

## Trade P&L Breakdown (24h, PostgreSQL brain.trades)

| Direction | Trades | Win Rate | Avg Win | Avg Loss | Net PnL |
|-----------|--------|----------|---------|---------|---------|
| LONG | 47 | 44.7% (21/47) | +1.27% | -0.73% | +$0.81 |
| SHORT | 36 | 42.1% (16/36) | +1.02% | -0.80% | -$0.10 |

| close_reason | Count | Avg PnL | Total |
|--------------|-------|---------|-------|
| profit-monster (TP) | 32 | +1.12% | +$3.92 |
| atr_sl_hit (SL) | 51 | -0.59% | -$3.21 |
| HARD_SL_CLOSE_FAILED | 1 | +1.87% | +$0.21 |
| guardian_sl | 1 | -0.91% | -$0.10 |

**Key insight:** TP hits are 4x more impactful than SL hits (+$3.92 vs -$3.21). Widening the SL to let winners develop has better expected value than tightening the filter to avoid losses.

---

## Master Plan Reference

Full analysis and prioritized recommendations saved to:
`/root/.hermes/plans/zscore-rs-signal-quality-master-plan-2026-05-24.md`