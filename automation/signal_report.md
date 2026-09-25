# Signal Performance Report
**Generated:** 2026-09-25 18:30 UTC | **Period:** Last 6h + 24h + 48h

## Overall Stats
- **Trades (24h):** 5 | **Trades (48h):** 45
- **Unique signals (48h):** 9
- **Pipeline status:** Running, low volume (normal for current market)

---

## KILLED (executed this cycle)

None. All problematic signals already disabled:
- `mover+` LONG — killed 2026-09-24 (auto_1hr), 0%WR 3T/24h
- `accel-300-breakout` SHORT — in NEVER_REENABLE, `ACCEL_300_BREAKOUT_ENABLED = False`
- `accel-300-v3-short` — in NEVER_REENABLE, `ACCEL_300_V3_SHORT_ENABLED = False`

---

## BOOSTED (executed this cycle)

None. No signals meet boost criteria (WR>55%, 5+ trades, positive PnL).

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades (48h) | Status |
|--------|-----|-----|-----|------|--------|
| pump-chain- | SHORT | 48.1% | -$0.55 | 27 | **HIGH regime blocked** (0.0x mult since 2026-09-24) |
| accel-300-breakout | SHORT | 20.0% | -$0.07 | 5 | Already dead (NEVER_REENABLE) |
| mover+ | LONG | 0.0% | -$0.61 | 3 | Already dead (killed 2026-09-24) |
| bb-bounce-v2-long+ | LONG | 33.3% | -$0.16 | 3 | CEO re-enabled 2026-09-22, monitoring |
| ema300-breakthrough+ | LONG | 0.0% | -$0.28 | 1 | Too small sample |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades (48h) | Status |
|--------|-----|-----|-----|------|--------|
| continuum-osc+ | LONG | 66.7% | -$0.06 | 3 | Good WR, small sample |
| pump-chain- (NORMAL) | SHORT | 100% | +$0.06 | 2 | Winning in NORMAL regime |

---

## REGIME ANALYSIS

### pump-chain- SHORT (27 trades, 48.1% WR)
- **EXTREME:** 20T, 50% WR, -$0.01 — breakeven, no action
- **HIGH:** 5T, 20% WR, -$0.60 — **BLOCKED at 0.0x** (volatility_gate_v2.py)
- **NORMAL:** 2T, 100% WR, +$0.06 — winning, no action

### mover+ LONG (3 trades, 0% WR)
- **EXTREME:** 1T, 0% WR, -$0.45 — already dead
- **HIGH:** 2T, 0% WR, -$0.16 — already dead

---

## SIGNAL INVERSIONS

**No inversions found.** All signals respect their direction labels.

---

## ISSUES

1. **Low trade volume** — Only 5 trades in 24h. Pipeline running but signal generation is quiet. This is normal for current market conditions (low volatility).

2. **pump-chain- HIGH regime** — Block added today (2026-09-24) after 5 HIGH regime trades already opened. Block is now active — no new HIGH trades expected.

---

## RECOMMENDATIONS

1. **No action required.** All kill candidates already handled. System is stable.
2. **Monitor bb-bounce-v2-long+** — CEO re-enabled Sep 22, currently 33.3% WR with 3 trades. If WR stays below 40% after 10+ trades, consider re-kill.
3. **continuum-osc+** — 66.7% WR but only 4 trades in 7d. Watch for more data before boosting.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-09-25 | 9fe15f9 | signals: add pullback-entry- SHORT dead hours h7,h19 |
| 2026-09-25 | 454b870 | CEO: ATR_SL_MAX widened 1.5→1.8% + EXTREME regime 1.2x multi |
| 2026-09-25 | 46add4b | signals: add pullback-entry- SHORT hour 22 to dead hours |
| 2026-09-25 | 9b67d4b | auto_1hr: pump-chain+ LONG dead hours — added hours 14,20 |
| 2026-09-25 | fb594d2 | signals: contrarian zone flip at strong SL zones (Phase 1) |
| 2026-09-25 | c46c9b2 | brain-auditor: CHASE_GAP_MAX_PCT 3.0→2.0 + audit report |
| 2026-09-25 | 2f87efe | scripts: add pump-chain- SHORT dead hour 18 |
| 2026-09-25 | f5c419e | auto_1hr: add pump-chain+ LONG dead hours 0,23 |
| 2026-09-25 | 52923bc | fix: pump-chain- SHORT dead hours — remove profitable [4,17] |
| 2026-09-24 | fa3ed2b | scripts: Add pump-chain- SHORT dead hours [4,9,17,20] |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*
