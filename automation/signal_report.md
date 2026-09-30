# Signal Performance Report
**Generated:** 2026-09-30 05:10 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 5,397 | **WR:** 45.5% | **PnL:** -$12.45
- **Date range:** 2026-05-20 → 2026-09-30
- **24h trades:** 41

---

## KILLED (executed)

None. No signals met kill criteria in the last 24h.

---

## BOOSTED (executed)

None. No signals met boost criteria in the last 24h.

---

## LOSERS (watch list)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|-------|--------|---------|--------|
| pump-chain- | SHORT | 12 | 41.7% | -$0.27 | ⚠️ Regime issue |
| rs-s30 | LONG | 3 | 0.0% | -$0.08 | ⚠️ Too few trades |

**pump-chain- SHORT** — loses in HIGH regime (48% WR, -$0.36) but wins in EXTREME (54.8% WR, +$0.43) and NORMAL (85.7% WR, +$0.16). Already blocked in HIGH via `volatility_gate_v2.py` `Pump_Flow` family 0.0x. Per-signal override allows EXTREME. No action needed.

---

## WINNERS

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|-------|--------|---------|--------|
| bb-bounce-v2-long+ | LONG | 4 | 50.0% | +$0.04 | ✅ Neutral |
| doji-bottom-long | LONG | 4 | 75.0% | +$0.12 | ✅ Watch |

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## REGIME-BASED BLOCKING STATUS

| Signal | Family | EXTREME | HIGH | NORMAL | FLAT |
|--------|--------|---------|------|--------|------|
| pump-chain- | Pump_Flow | 1.0x (override) | 0.0x (block) | 1.0x | 1.0x |

Regime gating is correctly configured. No changes needed.

---

## ALL-TIME WORST (10+ trades, for context)

| Signal | Dir | T | WR | PnL |
|--------|-----|---|-----|-----|
| ct_hot | LONG | 99 | 38.4% | -$4.07 |
| accel_300+,rs_s | LONG | 275 | 37.8% | -$2.91 |
| accel_300_,rs_r | SHORT | 281 | 45.6% | -$1.81 |
| ema300_dip_short | SHORT | 24 | 41.7% | -$1.48 |

These are chronic losers across the full history but not active in last 24h. They may already be disabled or filtered.

---

## RECOMMENDATIONS

1. **[WATCH] doji-bottom-long LONG** — 75% WR over 4 trades. Needs more volume to confirm. Monitor next cycle.
2. **[NO ACTION] pump-chain- SHORT** — Regime block already in place for HIGH. Data confirms EXTREME/NORMAL are profitable. No changes needed.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-09-30 | eff23ff | brain-audit: Sep 30 03:35 UTC — LONG RSI>70 leak, hotset con... |
| 2026-09-29 | b76bec7 | fix: bug hunter findings — V5 integration bugs |
| 2026-09-29 | 9265efa | Implement Thesis Validation System (TVS) |
| 2026-09-29 | f9daa25 | fix: pump_chain_v5 not reaching hotset — add to compactor wh... |
| 2026-09-29 | 76b66ae | brain_auditor: CASHCAT blacklisted from SHORT (2 consecutive... |
| 2026-09-29 | d74ec39 | Daily orchestrator 2026-09-29 18:30 UTC — pipeline healthy, ... |
| 2026-09-29 | 350dd43 | CEO: Fix SHORT R:R + pump-chain+ cold streak (Sep 29) |
| 2026-09-29 | e5c119d | Fix hard_sl losses: 4 root causes found by bug hunter |
| 2026-09-29 | 4a962dd | Remove rs from STANDALONE_BYPASS_SIGNALS |
| 2026-09-29 | b556ae4 | Update RSI thresholds based on 30d/14d data analysis |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*
