# Signal Performance Report
**Generated:** 2026-09-11 17:03 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 2,321 | **WR:** 51.8% | **PnL:** -98.75%
- **Date range:** 2026-07-29 → 2026-09-11

---

## WINNERS (WR > 55%, PnL > 0)

None found.

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| pump-chain+ | LONG | 5 | 20.0% | -2.54 | 11 | 27.3% | -5.56 | ❓ | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| pump-chain- | SHORT | 16 | 50.0% | -2.91 | ❓ | Borderline |
| pullback-entry- | SHORT | 9 | 44.4% | -2.45 | ENABLED | Borderline |
| bb-bounce-v2-long+ | LONG | 3 | 33.3% | -1.38 | ❓ | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] pump-chain+ LONG** — WR=27.3%, PnL=-5.56% over 11 trades (24h).
2. **[WATCH] pump-chain- SHORT** — WR=50.0%, PnL=-2.91% over 16 trades. Monitor next cycle.
3. **[WATCH] pullback-entry- SHORT** — WR=44.4%, PnL=-2.45% over 9 trades. Monitor next cycle.
4. **[WATCH] bb-bounce-v2-long+ LONG** — WR=33.3%, PnL=-1.38% over 3 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-09-11 | f346602 | config: disable accel_300_v4_short, re-enable accel_300_shor... |
| 2026-09-11 | ef6f5ec | fix: bug hunter findings — NEVER_REENABLE cleanup, Pump_Flow... |
| 2026-09-11 | f21407f | config: enable TL_BREAK_ENABLED master switch (2026-09-11) |
| 2026-09-11 | 2bf0228 | config: enable tl_break_long in NORMAL regime (2026-09-11) |
| 2026-09-11 | 2cfd770 | auto_1hr: KILL pump-chain+ (PUMP_FLOW_PLUS_ENABLED=False) — ... |
| 2026-09-11 | 62026ef | config: re-enable pump_chain LONG and accel_300_v4_short (20... |
| 2026-09-11 | fa17d3e | Signals: Add support proximity filter to pullback_entry |
| 2026-09-11 | b15d4a9 | auto_1hr: KILL pump-chain+ LONG (PUMP_FLOW_PLUS_ENABLED=Fals... |
| 2026-09-11 | 5873e7f | auto_1hr: Kill accel-300-v4-short- (0% WR, 3T, -/usr/bin/bas... |
| 2026-09-11 | d287cf7 | Auto 1hr: no changes - system healthy (2026-09-11 09:10 UTC) |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*