# Signal Performance Report
**Generated:** 2026-08-17 05:07 UTC | **Period:** Last 6h + 24h + 7d

## Overall Stats (24h)
- **Total closed trades:** 35
- **Active signals:** ~22 signal+direction combos

---

## KILLED (executed)

All kill candidates already dead — no new kills needed this run.

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| range_breakout+ | LONG | 25.0% | -$0.41 | 8 (7d) | Already killed (RANGE_BREAKOUT_PLUS_ENABLED=False) |
| trend_momentum_near_sma+ | LONG | 16.7% | -$0.37 | 6 (7d) | Already killed (TREND_MOMENTUM_NEAR_SMA_PLUS_ENABLED=False) |
| mover+ | LONG | 28.6% | -$0.15 | 7 (7d) | Already killed (MOMENTUM_LEADERBOARD_PLUS_ENABLED=False) |

**Note:** ct-hot- SHORT (0% WR, -$0.19, 4 trades 7d) is in NEVER_REENABLE_FLAGS but was re-enabled per user 2026-08-16. Flag reads "TESTING MODE — DO NOT DISABLE." Respecting user override.

---

## BOOSTED (executed)

No new boosts — top performers already enabled.

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+ | LONG | 58.3% | +$0.21 | 24 (7d) | Already enabled (BB_BOUNCE_PLUS_ENABLED=True) |
| r2-trend-long2 | LONG | 64.7% | +$0.19 | 17 (7d) | Part of R2_TREND_LONG_ENABLED=True |
| bb_bounce+,hl_copy_trader | LONG | 100.0% | +$0.26 | 2 (24h) | Already enabled |
| r2-trend-long3 | LONG | 60.0% | +$0.11 | 5 (24h) | Part of R2_TREND_LONG_ENABLED=True |

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ct-hot+ | LONG | 42.4% | -$0.42 | 33 (7d) | NEVER_REENABLE, user override testing |
| wave_catcher+ | LONG | 37.5% | -$0.42 | 8 (7d) | Monitor — near kill threshold |
| bb_bounce+,hzscore+ | LONG | 36.8% | -$0.30 | 19 (7d) | hzscore+ standalone blocked, combo bleeding |
| accel-300- | SHORT | 55.0% | -$0.30 | 40 (7d) | Inverted R:R — wins small, losses big |
| continuation-,hzscore- | SHORT | 40.0% | -$0.24 | 5 (7d) | Bleeding combo |
| hzscore- | SHORT | 54.3% | -$0.22 | 35 (7d) | Killed today — inverted R:R |
| ct-hot- | SHORT | 0.0% | -$0.19 | 4 (7d) | NEVER_REENABLE but user testing |
| mover+ | LONG | 28.6% | -$0.15 | 7 (7d) | Already killed |
| range_finder+ | LONG | 33.3% | -$0.14 | 9 (7d) | Already disabled |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| return_exhaustion_long | LONG | 100.0% | +$0.43 | 4 (7d) | Enabled, niche |
| bb_bounce+ | LONG | 58.3% | +$0.21 | 24 (7d) | Enabled — system workhorse |
| bb_bounce+,hl_copy_trader | LONG | 40.0% | +$0.21 | 5 (7d) | Enabled |
| r2-trend-long6 | LONG | 100.0% | +$0.20 | 4 (7d) | Enabled |
| r2-trend-long2 | LONG | 64.7% | +$0.19 | 17 (7d) | Enabled — best r2 variant |
| wave_catcher+ | SHORT | 42.9% | +$0.15 | 7 (7d) | Enabled |
| hzscore-,range_breakout- | SHORT | 75.0% | +$0.12 | 4 (7d) | Enabled |
| range_breakout_short | SHORT | 50.0% | -$0.04 | 26 (7d) | Enabled — re-tested |

---

## ISSUES

- **No signal inversions found.** All signals respect direction labels.
- **ct-hot+ LONG** (33T, 42.4% WR, -$0.42) is the biggest active bleed — in NEVER_REENABLE but user re-enabled for testing. Watch closely.
- **Accelerated SL hits** continue to dominate losses system-wide — ATR_SL is the #1 exit reason for losers.
- **7d overall:** System is roughly flat to slightly negative. Winners and losers cancel out. No extreme drawdowns.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-17 | 0abb30f | CEO: 53rd run — NO CHANGES, system strong, PM_TRAIL 84.2% WR... |
| 2026-08-17 | a61d89d | CEO run 46: system IMPROVING, hzscore- killed, NO param chan... |
| 2026-08-17 | 5da2ebe | CEO: Kill hzscore- (testing failed, inverted R:R) |
| 2026-08-16 | 442af24 | CEO: 44th run - no changes, system improving, ct-hot+ testin... |
| 2026-08-16 | 9c40820 | CEO: RAISED MIN_COMPOSITE 70→75. ct-hot+ 12T/24h 25% WR ALL ... |
| 2026-08-16 | ce0169f | CEO: RAISED MIN_COMPOSITE 65→70. ct-hot+ ALL entries NEUTRAL... |
| 2026-08-16 | 5e49f6e | CEO: RAISED MIN_COMPOSITE 60→65 (40th run) |
| 2026-08-16 | 9a6c712 | CEO: RAISED MIN_COMPOSITE 55→60 — ct-hot+ ATR_SL 52% of loss... |
| 2026-08-16 | 607c6f0 | CEO: 37th run — NO CHANGES, eval window active, legacy clear... |
| 2026-08-16 | ceba10c | CEO: 35th run — NO CHANGES, eval window active |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*
