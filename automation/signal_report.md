# Signal Performance Report
**Generated:** 2026-10-01 17:18 UTC | **Period:** Last 6h + 24h
**Source:** PostgreSQL brain DB (queried live, not from prior report)

## 6h Performance
No signal+direction with ≥2 closed trades. Quiet hour window.

## 24h Performance (≥3 trades)

| Signal | Dir | Trades | WR | PnL (USDT) |
|--------|-----|--------|-----|------------|
| pump-chain- | SHORT | 9 | 22.2% | -$0.63 |
| accel-300- | SHORT | 8 | 37.5% | -$0.34 |
| pump-chain-v5 | LONG | 7 | 28.6% | -$0.34 |

---

## KILLED (executed this cycle)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| accel-300- | SHORT | 37.5% | -$0.34 | 8 | **Already killed** 10:50 UTC by auto_1hr — `ACCEL_300_MINUS_ENABLED = False` **verified**. Last signal 10:18. No new signals after kill. |
| pump-chain-v5 | LONG | 28.6% | -$0.34 | 7 | **Already killed** 10:18 UTC by auto_1hr — `PUMP_CHAIN_V5_ENABLED = False` **verified**. Last signal 09:42. No new signals after kill. |

**No new kills this cycle.** Both kill-criterion losers from 24h were already disabled earlier today; flags re-verified False in `hermes_constants.py`.

---

## BOOSTED (executed this cycle)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | **None.** No signal met all boost criteria (WR>55%, 5+ trades, PnL>$0.05). |

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 22.2% | -$0.63 | 9 | **WATCH — do NOT kill.** Kill criteria met on 24h numbers, but regime analysis shows NORMAL edge: all-time NORMAL 75% WR (8T, +$0.09). EXTREME 52.1% (96T), HIGH 46.2% (26T). SOP: regime has ≥55% WR → block losing regimes only. CEO directive 2026-09-28: "never blanket disable, route via regime." `PUMP_CHAIN_V5_SHORT_ENABLED = True` kept. |

**pump-chain- regime routing (verified active):**
- EXTREME: `VOL_PHASE_MULTS` Pump_Flow=0.0 + override `('EXTREME','pump-chain-')=0.0` → combined_mult=0.0 (hard block, verified by direct function call with source)
- HIGH: family Pump_Flow=0.0 + `PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED=True` in signal_compactor
- NORMAL: multiplier 1.0 (the edge)
- All 9 × 24h losses were EXTREME; **last pump-chain- trade closed 08:39 UTC**. No trades since despite continued signal generation — execution gate holding.

---

## WINNERS

None with meaningful sample in 24h (need ≥3 trades). Single-trade positives: r2-trend-short3 +$0.07, pump-chain-,rs-r54 +$0.03 — below boost threshold.

---

## Inversions

**None.** Zero direction mismatches (long-named signals with SHORT direction or vice versa) in 24h.

---

## ISSUES

1. **pump_chain_v5_short.py generates without entry-quality filters** — signal_compactor enforces `PUMP_CHAIN_SHORT_RSI_MIN=40` and HIGH-vol block at execution, but the generator does not. Today: 342 × `pump-chain-` signals, **0 executed** (all EXPIRED). Execution path is saving us; generation is spamming known-losers (RSI 14–39 in signal metadata). Suggested fix: fetch live RSI/vol in generator before `add_signal`, or accept noise since gates hold. Not a money-losing bug today.
2. **REGIME_SIGNALS['EXTREME'] still lists pump-chain- as "works in storms"** — stale; contradicts `VOL_PHASE_MULTS` EXTREME Pump_Flow=0.0. `should_trade_v2` has no execution callers today (dead path), latent bypass only.
3. **signals/__init__.py registry uses string flag names** (`'enabled': 'PUMP_CHAIN_V5_SHORT_ENABLED'`) — always truthy at registry level; real gating is inside each signal function. Works, fragile.
4. **ACCEL_300_ENABLED=True master switch** still on while `ACCEL_300_MINUS_ENABLED=False`. SHORT is gated inside `accel_300.py` via MINUS flag — OK, but master-on/min-off is confusing for auditors.

---

## Flags Verified (this cycle)

| Flag | Value | Note |
|------|-------|------|
| ACCEL_300_MINUS_ENABLED | False | Killed 10:50 today |
| PUMP_CHAIN_V5_ENABLED | False | Killed 10:18 today |
| PUMP_CHAIN_V5_SHORT_ENABLED | True | Intentional — NORMAL edge, regime-routed |
| PUMP_FLOW_MINUS_ENABLED | False | pump_flow_signal SHORT gated off |
| PUMP_FLOW_PLUS_ENABLED | False | LONG side dead |
| PUMP_CHAIN_V4_ENABLED | False | NEVER_REENABLE |
| ACCEL_300_ENABLED | True | Master switch; MINUS flag gates SHORT |

---

*Report auto-generated from live DB query. Next report: ~6h.*
