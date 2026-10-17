# Exit-Ladder P0 — Signal-Scoped TAT Grid Verdict (brain_auditor, 2026-10-17 14:45 UTC)

**Status: P0 CLOSED. No config change. Live TAT state already optimal.**

The 8x-requested exit-ladder candle backtest, run by brain_auditor after self_learner
undelivered. Signal-scoped ONLY (universal MFE-CUT dead per same-day 11:05 verdict).
Mechanism as-coded (position_manager.py:3565-3595): open at age>=T AND live_pnl
(unleveraged %) < ARM => close. Script: `analysis/exit_ladder_tat_grid_2026-10-17.py`
(+ underwater-only ARM=0.0 variant, same session). Units: cf$ = amount_usdt * lp/100
(amount NOTIONAL; lev is margin metadata). Bar: fk <=20% of cohort winners AND net >0
AND fired >=5. 30d candle OOS, 782 closed trades, 1m candle marks at open+T.

## Grid 1 — as-coded ARM=0.40 (live condition)

| Cohort | T | fire (FKw) | fk% | NET$ | verdict |
|--------|---|-----------|-----|------|---------|
| pump-chain- SHORT | 30/40/45/50/55/60/80 | 35-57 (13-22) | 26-44% | -$0.86..+$0.56 | **FAIL all** |
| bb-squeeze+ LONG | 40/45/50/55/60 | 20-25 (5-8) | 11-18% | +$0.70..+$1.07 | **PASS all** |
| pump-chain+ LONG | 50/55/60 | 37-38 (16-17) | 31-33% | -$1.02..-$1.47 | **FAIL all** |

## Grid 2 — underwater-only ARM=0.0 (creative variant; never tested in 11:05 MFE grid)

| Cohort | T | fire (FKw) | fk% | NET$ | verdict |
|--------|---|-----------|-----|------|---------|
| pump-chain- SHORT | 30-80 | 24-33 (7-12) | 14-24% | -$0.09..-$0.70 | **FAIL all** |
| pump-chain+ LONG | 45/55/60 | 22-30 (5-7) | 10-14% | -$0.00..-$0.96 | **FAIL all** |
| bb-squeeze+ LONG | 40/55/60 | 15-21 (3-7) | 7-16% | +$0.17..+$1.02 | **PASS all** |

## Findings

1. **bb-squeeze is the ONLY TAT-eligible signal.** Passes every T in [40,60] under both
   ARMs; T=55/ARM=0.40 nets +$1.07 (fk 11.1%) vs live T=60 +$1.02 — delta $0.05/30d =
   noise. **No churn. Keep live T=60.** Robustness across the local grid proves the
   mechanism is not overfit to the Oct 12 tuning point.

2. **pump-chain- SHORT: exit-side DEAD END, confirmed across 14 (T x ARM) cells.**
   Even underwater-only cannot clear net>0: underwater-at-T winners recover often
   enough (costs >= saves). Winners are slow grinders (median hold 127-134m; hard_sl
   winners end +0.33% unleveraged — never arm). The 30d chop bleed (58T, -$4.49) is
   NOT fixable by any fixed-time cut. Entry-gap autopsy: diffuse (4 gap bands, no
   clean save; deep-dump band 58T -$0.61 holds ~24 trail winners — blocking kills
   >20% winners). **Remaining lever for pump-chain- = the standing CEO kill decision,
   not a new filter or exit mechanism.**

3. **pump-chain+ T=45 live = confirmed wash.** Every later T is worse (slow-grinder
   FKs: FOGO/AVAX/ADA/JUP class underwater at T yet end +4-6% unleveraged). Keep,
   no comment/code change.

4. **Progressive/underwater TAT variants add nothing.** ARM=0 lowers fk but does not
   make any failing family pass; for bb-squeeze it only reshuffles saves/costs at the
   same net. The "multi-point exit ladder" concept (T=30/-0.1%, T=45/-0.2%,
   T=55/-0.3%) is dead for the same root reason universal MFE-CUT died: at any fixed
   time, crypto slow-grinder winners are observationally identical to dead chop.

5. **TAT-eligibility meta-rule (pre-registered, reusable):** a signal qualifies for
   trail-arm-timeout only if median winner hold < T < median loser hold with >=2x
   separation, AND candle OOS clears fk<=20% AND net>0. bb-squeeze meets it (winners
   median 34m close before T; losers median 73m stall past T). pump-chain- fails the
   premise (winners median 127-134m overlap loser holds). Apply this screen BEFORE
   commissioning any future TAT shadow.

## Actions

- 0 config changes. Live: bb-squeeze T=60, pump-chain T=45, no pump-chain- TAT — all correct.
- Exit-ladder P0 request (8x) CLOSED. Do not re-request a universal or progressive cut.
- pump-chain- kill decision remains CEO-owned standing escalation.
