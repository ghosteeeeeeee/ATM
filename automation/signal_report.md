# Signal Performance Report
**Generated:** 2026-08-10 19:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 720 | **WR:** 45.0% | **PnL:** -10.82%
- **Date range:** 2026-07-29 → 2026-08-10

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
| hzscore+,range_finder+ | LONG | 3 | 33.3% | -1.29 | ENABLED | Needs more data |
| hl_copy_trader,range_breakout- | SHORT | 2 | 50.0% | -0.20 | ❓ | Needs more data |
| range_breakout-,vortex_break_short | SHORT | 2 | 50.0% | +0.12 | ENABLED | Needs more data |
| hzscore-,vortex_break_short | SHORT | 2 | 50.0% | +0.74 | ENABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] hzscore+,range_finder+ LONG** — WR=33.3%, PnL=-1.29% over 3 trades. Monitor next cycle.
2. **[WATCH] hl_copy_trader,range_breakout- SHORT** — WR=50.0%, PnL=-0.20% over 2 trades. Monitor next cycle.
3. **[WATCH] range_breakout-,vortex_break_short SHORT** — WR=50.0%, PnL=+0.12% over 2 trades. Monitor next cycle.
4. **[WATCH] hzscore-,vortex_break_short SHORT** — WR=50.0%, PnL=+0.74% over 2 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-10 | d2c8eea | blacklist: add AXS, LINK, CELO to LONG_BLACKLIST |
| 2026-08-10 | 4d961b4 | CEO: revert Aug 10 SL tightening + widen trailing + cut_lose... |
| 2026-08-10 | 32d1a03 | CEO: disable vortex_break_short |
| 2026-08-10 | 36e4cd0 | trading: tighten SL from 1.2% to 0.5% to match cut_loser thr... |
| 2026-08-10 | 5b4876a | auto_1hr: kill range_finder+ — 20T -$0.44 (24h), 0% WR today... |
| 2026-08-10 | 9dfb9e7 | signals: tune fast_momentum params and enable both direction... |
| 2026-08-10 | 3f2effe | trading: tighten TRAILING_DISTANCE_PCT from 0.7% to 0.3% |
| 2026-08-10 | fad8948 | CEO: Option A — 15m trend filter for SHORT (was 1h, too rest... |
| 2026-08-10 | 3a0fb69 | Daily trading system update (2026-08-10) |
| 2026-08-10 | 5a2429c | signals: relax SHORT thresholds to balance LONG/SHORT flow |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*