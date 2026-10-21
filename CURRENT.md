# Current State — brain_auditor #47 Oct 21 ~01:40 UTC

**Last Updated: 2026-10-21 01:40 UTC**
**Updated by: brain_auditor #47 — 0 config changes (vacation soak). All steers triaged. HML re-entry cooldown rejected-with-data.**

## PIPELINE STATUS

- **Trading LIVE** with size-reduce **0.5x** (vacation_size_reduce.json authoritative — PnL −$2.73 still fails −$2.00 resume leg).
- **24h 24T 5W −$0.37 (20.8%) — shallow, containing (max loss −$0.31).** 7d 159T 35.8% −$2.73. 
- **7d exit family: profit-monster-trail 30T 93.3% +$1.70 | TRAIL/TP 28T 53.6% +$1.99 vs atr_sl_hit 47T 2.1% −$3.44 | CHOP/SL 32T 0% −$3.15.** Wealth gap unchanged.
- **Open 1: BTC SHORT #16317 ai-trader-pending @82804, cur 82933, −0.16%, SL 83052 / TP 82350** — HOLD; precheck advisory FAIL (chop 6 flips) reported per CEO-trade rule.
- **Regime: btc_15m LONG_BIAS, btc_4h LONG_BIAS, continuum BELOW EMA300, zscore STRONG_NEG, volatility NORMAL.** Chop-pin with bear lean.
- **Vacation mode ACTIVE** — shadow-first, no constants changes. Protected flags untouched.

## THIS RUN — brain_auditor #47 (01:40 UTC)

**0 config changes.**

1. **WATCHDOG TRIAGE:** 001 pending order ALREADY EXECUTED (#16317, SL caps risk) | 002 structural trail-vs-chop | 003 known cohorts | **004/005 pump-chain± kills REJECTED 6th** (14d +$0.93 / +$0.23).
2. **LOSING AUTOPSY 24h:** 19 losers all small (max −$0.31). pump-chain+ LONG 6T 0W −$0.55 = chop cohort HIGH/EXTREME. Zero new patterns.
3. **LAST-RUN VERIFY: ALL HOLDING** — ARM-GAP 0 fires = correct (CFX/BLUR timeout trades never hit MFE≥0.40) | TAT scope 9/15 | BTC #16309 resolved +$0.09.

## CREATIVE (this run)

**HML re-entry cooldown — REJECTED WITH DATA.** 14d same token+direction re-entry within 24h of hard_max_loss: 28T 25%WR −$0.53. Blocking all saves $0.53 but kills $0.69 of winners = **net −$0.16**. Logged in creative_improvements so it is not re-proposed from loser-only view.

**Near-miss arm band (MFE 0.30-0.40) — PRE-REGISTERED.** ARM-GAP log currently floors at 0.40; trail_arm_timeout cohort (pump-chain+ 15T −$0.57/14d) may cluster just under. Extend log floor at vacation-end if data justifies — evaluates ARM=0.35 without candle re-derivation.

## STANDING PRE-REGISTRATIONS (vacation-end Oct 23)

- **pump-chain+ non-EXTREME (HIGH/NORMAL/FLAT) 0.7x confidence dampen** (#46) — 30d EXTREME +$1.69 only-profitable band; sim net save $0.41, winner-kill 15.8%.
- **Escalation #15 (22nd):** signal-scoped candle OOS vehicle — blocks peak-trail flip, dual-condition TAT, dampen confirmation.
- **pp-cond shadow flip:** failed bars (#39), re-eval vacation-end.
- **coin_regime:** n=10/20 conf≥25.
- **Post-vacation stack: ~15+ unvalidated soaks** — CEO eyeball on resume (~Oct 23).

## OPEN LOOPS

- **BTC SHORT #16317** — SL 83052 (~0.3% risk); precheck FAIL already reported.
- **TAT bb-bounce flip:** 9/15 valid unique fires (need 6 more).
- **Near-miss arm band:** awaiting ARM-GAP fire accumulation.
- **Sideways:** auto_1hr log-writer shell-expansion corruption ($ eaten) — cosmetic, fix when touching that script.
