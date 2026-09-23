# Signal Performance Report
**Generated:** 2026-09-23 17:03 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 2,677 | **WR:** 51.7% | **PnL:** -99.42%
- **Date range:** 2026-07-29 → 2026-09-23

---

## WINNERS (WR > 55%, PnL > 0)

None found.

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| mover+ | LONG | 3 | 33.3% | -1.09 | ENABLED | Needs more data |
| bb-bounce-v2-long+ | LONG | 9 | 44.4% | -1.05 | ❓ | Borderline |
| accel-300-breakout | SHORT | 2 | 50.0% | -0.53 | ENABLED | Needs more data |
| volume-breakout-long+ | LONG | 2 | 50.0% | -0.46 | ❓ | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] mover+ LONG** — WR=33.3%, PnL=-1.09% over 3 trades. Monitor next cycle.
2. **[WATCH] bb-bounce-v2-long+ LONG** — WR=44.4%, PnL=-1.05% over 9 trades. Monitor next cycle.
3. **[WATCH] accel-300-breakout SHORT** — WR=50.0%, PnL=-0.53% over 2 trades. Monitor next cycle.
4. **[WATCH] volume-breakout-long+ LONG** — WR=50.0%, PnL=-0.46% over 2 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-09-23 | 2f756ed | Signals: Complete pump_chain_v5_short following add-signal c... |
| 2026-09-23 | e61cd1f | Fix: add accel-30 to STANDALONE_BYPASS_SIGNALS |
| 2026-09-23 | b50be86 | fix: add return-exhaustion-short (hyphen) to bypass list — w... |
| 2026-09-23 | 2f23e0a | signals: add pullback-entry- SHORT dead hours 0,1,10,11 |
| 2026-09-23 | f52bb96 | fix: RR_ENGINE_CONF_HARD_BLOCK_RR 0.95→0.70 — allow lower R:... |
| 2026-09-23 | 6b66d7c | fix: SHORT_RSI_FLOOR 50→40 — 50 blocked SHORT in downtrends,... |
| 2026-09-23 | a668cbf | brain_auditor: 12:00 UTC audit — no config change, 3 creativ... |
| 2026-09-23 | cec7ef3 | brain_auditor: LONG_RSI_FLOOR=30 added (Sep 23 ~08:00 UTC) |
| 2026-09-23 | 393ad43 | brain_auditor: SHORT_RSI_FLOOR 35→50 + audit report |
| 2026-09-23 | d339ea7 | CEO: Fix dead hours bug + correct dead hours configs |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*