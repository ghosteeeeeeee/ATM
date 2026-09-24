# Signal Performance Report
**Generated:** 2026-09-24 23:30 UTC | **Period:** Last 6h + 24h

## Overall Stats (24h)
- **Total trades:** 30 | **Winners:** 9 | **WR:** 30.0% | **PnL:** -$2.61 | **Avg:** -$0.087/trade

---

## BUG FIX (executed)

**volatility_gate_v2.py — regime block enforcement broken**

The `VOL_PHASE_MULTS` 0.0 multipliers (regime bans) were being clamped to 0.3 by `max(0.3, min(2.0, mult))` and `should_trade_v2` never checked the multiplier — it returned 'TRADE' regardless. Pump_Flow trades were still firing in EXTREME/HIGH despite being "blocked."

**Fix:**
1. `get_combined_multiplier`: preserve 0.0 before clamp (`if mult == 0.0: return 0.0`)
2. `should_trade_v2`: check `combined_mult == 0.0` → return `('SKIP', 'regime_block: ...')`

**Impact:** pump-chain- SHORT in EXTREME/HIGH will now actually be blocked (was firing ~18 trades/day in blocked regimes).

---

## KILLED (executed)

None — no signals meet full kill criteria (WR<30% + 5+ trades + PnL<-$0.10 + active>24h).

---

## BOOSTED (executed)

None — no signals meet boost criteria (WR>55% + 5+ trades + PnL>$0.05 in 24h).

---

## REGIME BLOCKS (verified)

| Signal | Dir | Regime | WR | PnL | Action |
|--------|-----|--------|-----|-----|--------|
| pump-chain- | SHORT | EXTREME | 33.3% | -$0.70 | BLOCKED (0.0x) |
| pump-chain- | SHORT | HIGH | 16.7% | -$0.60 | BLOCKED (0.0x) |
| pump-chain- | SHORT | NORMAL | 100% | +$0.06 | ALLOWED |
| mover+ | LONG | EXTREME | 0.0% | -$0.45 | BLOCKED (0.0x) |
| pullback-entry- | SHORT | NORMAL | 16.7% | -$0.83 | BLOCKED (0.0x) |

---

## LOSERS (watch list — 24h)

| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| pump-chain- | SHORT | 18 | 38.9% | -$0.91 | Regime-blocked EXTREME/HIGH |
| mover+ | LONG | 3 | 0.0% | -$0.61 | Below kill threshold (3T) |
| bb-bounce-v2-long+ | LONG | 3 | 33.3% | -$0.16 | Below kill threshold (3T) |
| continuum-osc+ | LONG | 2 | 50.0% | -$0.11 | Needs more data |
| r2-trend-short4 | SHORT | 1 | 0.0% | -$0.21 | Insufficient data |
| ema300-breakthrough+ | LONG | 1 | 0.0% | -$0.28 | Insufficient data |

---

## WINNERS (24h)

None with 5+ trades. pump-chain- SHORT in NORMAL regime: 2T, 100% WR, +$0.06.

---

## 7d CONTEXT (10+ trades)

| Signal | Dir | Trades | WR | PnL | Note |
|--------|-----|--------|-----|-----|------|
| pullback-entry- | SHORT | 29 | 31.0% | -$2.27 | Slow bleed all regimes |
| mover+ | LONG | 14 | 42.9% | -$1.12 | EXTREME blocked |
| pump-chain- | SHORT | 32 | 43.8% | -$0.96 | EXTREME/HIGH blocked |
| bb-bounce-v2-long+ | LONG | 12 | 41.7% | -$0.26 | Watch |
| grind-trend+ | LONG | 18 | 50.0% | +$0.24 | OK |
| pump-chain+ | LONG | 55 | 41.8% | +$1.23 | Net positive |
| volume-breakout-long+ | LONG | 15 | 73.3% | +$1.76 | Strong |

---

## SIGNAL INVERSIONS (24h)

**No inversions found.**

---

## RECOMMENDATIONS

1. **[DONE] Fix regime block bug** — 0.0 multiplier was clamped to 0.3, trades leaked through. Fixed in volatility_gate_v2.py.
2. **[WATCH] pullback-entry- SHORT** — 29T/7d, 31% WR, -$2.27. Losing across all regimes (EXTREME 30%, HIGH 38.5%, NORMAL 16.7%). Signal quality issue, not regime-specific. Consider kill if no improvement next cycle.
3. **[WATCH] mover+ LONG** — 14T/7d, 42.9% WR, -$1.12. EXTREME blocked. HIGH at 50% WR is marginal. Below24h kill threshold (3T only).
4. **[MONITOR] pump-chain- SHORT** — With regime blocks now enforced, expect fewer EXTREME/HIGH trades. NORMAL regime (100% WR) should dominate.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-09-24 | fa3ed2b | scripts: Add pump-chain- SHORT dead hours [4,9,17,20] |
| 2026-09-24 | 64e2c7a | CEO: REGIME_CONF_MULTIPLIER deployed — EXTREME +15%, NORMAL -15% |
| 2026-09-24 | 76ffdba | signals: add pump-chain- SHORT dead hours [2,3] |
| 2026-09-24 | 02581c8 | CEO: DISABLE CL-T1 — 25T/14d 0%WR -$3.11 |
| 2026-09-24 | 9441fe6 | CEO: RAISE SHORT_RSI_FLOOR 40→50 |
| 2026-09-24 | cb1739e | signals: KILL mover+ LONG — 3T 0%WR |
| 2026-09-24 | f143248 | CEO: Fix SHORT_RSI_FLOOR soft penalty → hard block |
| 2026-09-24 | c0975ff | CEO: widen CL-T1 range -2.0→-3.0 |
| 2026-09-24 | 0c91d2f | brain-auditor: PUMP_CHAIN_LONG_RSI_MAX 75→70 |
| 2026-09-23 | 29aa478 | signals: kill accel-300-breakout, block Mover EXTREME |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*
