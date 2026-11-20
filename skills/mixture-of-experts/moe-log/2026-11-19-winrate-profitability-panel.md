# MoE Decision Panel — How Do We Improve Winrate & Profitability

**Date:** 2026-11-19 23:50 UTC
**Question:** Similar to the 2026-09-04 panel — how do we improve winrate and profitability? New additions this round: large shadow-data troves, new exit logic, new entry signals.
**Panel:** Full (6/6 experts), dispatched in parallel, independent queries, no shared verdicts.

---

## Baseline (verified by router before dispatch — CORRECTED during panel)

| Window | n | WR | `pnl_usdt` (GROSS) | fees | TRUE NET |
|--------|---|-----|--------|------|----------|
| 30d | 649 | 51.9% | -$4.80 | $6.96 | **-$11.76** |
| 7d | 108 | 49.1% | +$0.44 | $1.57 | **-$1.13** |
| Last-200 LONG | 100 | 41.0% | -$1.48 | $1.40 | -$2.88 |
| Last-200 SHORT | 104 | 53.8% | -$0.55 | $1.49 | **-$2.04** |

> ⚠️ **The router's opening baseline was mislabeled.** `pnl_usdt` is GROSS — fees live in the JSON `fees` column (`{entry_fee, exit_fee, fee_total, net_pnl}`). The "+$0.44 net" at panel open is **-$1.13**. Independently confirmed by Risk, Statistician, and router re-query.

**Equity:** $15.51 (verified via clearinghouseState). 30d drawdown -$11.82 = **-76% of equity**.

---

## Activated Experts

| Expert | Weight | Data Quality |
|--------|--------|-------------|
| Signal Analyst | 0.25 | GOOD — re-queried 30d, read bypass list + 9 new signal files |
| Risk Manager | 0.25 | GOOD — fee JSON parsed, MFE/MAE, equity verified |
| Statistician | 0.15→0.25 (raised: primary for this question) | GOOD — ran queries twice, reproduced ride_it replay |
| Code Architect | 0.15 | GOOD — read 8 files + logs in full |
| Regime Analyst | 0.15 | GOOD — shadow vol_regime × direction, n in thousands |
| Systems Engineer | 0.05 | GOOD — pipeline, timers, services, execution lag measured |

---

## Expert Verdicts

### 1. Signal Analyst — Signal Quality: MEDIUM, Direction Confidence 70%

1. **Two statistically proven losers still filling** (n≥10, exact binomial vs 50%):
   - `hl_copy_trader` n=22, **22.7% WR**, CI [10.1,43.4], **p=0.017**, net -$0.35 — still live through bypass despite `HL_COPY_TRADING_ENABLED=False` (:4394)
   - `ai-trader-pending` n=48, **31.3% WR**, CI [19.9,45.3], **p=0.013**, net +$0.08 — manual pending flow fills despite `AI_TRADER_ENABLED=False` (:3816)
   - All other sub-50 signals are n<30 → NEEDS MORE DATA
2. **New signals are not helping.** Live: volume-buildup- n=61 62.3% WR **net -$0.77**; atr-trend n=47 57.4% -$0.63; pump-chain-v6 n=11 -$0.47; grind_breakout/jup_liq/linreg_fade = 0–1 trades. Shadow counterfactuals (`net_pnl_pct`): **pump-chain-v6 n=3437, 34.2% WR, avg -0.157%**; linreg_fade_short n=1239 36.2% -0.132%; atr_trend_accel_short n=1749 48.9%; volume_buildup_short n=2808 54.2%. Only grind_breakout_short positive (n=230, +0.234%).
3. **Confluence gate effectively off**: 30d single 619T vs multi 30T. `STANDALONE_BYPASS_SIGNALS` (:3528-3645) admits nearly everything solo — **95% of fills are single-source**.
4. **Entry-quality cells**: LONG `rsi_exec` 55–70 = **n=128, 46.9%, -$3.21** (biggest loss cell); LONG `gap` 0.5–1% = **n=88, 46.6%, -$2.29**. LONG rsi≥70 is *positive* (43T, 65.1%, +$0.62) — ceiling fine, mid-band bleeds.
5. Biggest net losers aren't WR problems: jup_yolo_mirrored n=169 62.7% net -$0.78 on $2.44 fees.

**Top 3 levers:** (1) prune `hl_copy_trader` from bypass + exec-time gate for `ai-trader-pending`; (2) gate mid-band LONGs (rsi 55–70 AND gap 0.5–1%); (3) halt promotion of losing shadows — set `PUMP_CHAIN_V6_ENABLED=False`, don't scale linreg_fade until its 11-27 study flips the sign.

**Confidence: MEDIUM**

### 2. Statistician — Sample n=648 ADEQUATE

- **Measured expectancy: -$0.0181/trade NET of fees**, CI95 [-0.0266, -0.0096], t=-4.18, **p=2.9e-5** (≈ -0.137%/trade of $13.17 notional). Gross -$0.0074 CI [-0.0158, +0.0010] p=0.083 (inconclusive gross). **7d n=108 INSUFFICIENT.**
- **Is the edge real? NO** — significantly net-negative. All-history n=6,583 gross -$0.0031, p=0.034; net worse (fees $209 total).
- **WR is the wrong metric; payoff ratio is the story.** 30d payoff **0.71** (avg win $0.0687 / avg loss $0.0971). WR 51.9% CI [48.1,55.7] = indistinguishable from 50%. Breakeven: **WR ≥65% (fees only) or ≥73% (fees+slip)** at payoff 0.71; or **payoff ≥1.14–1.40** at current WR.
- **The "$0.08/day cap" arithmetic fails twice.** The 0.104%/trade premise traces to a brief's **avg-WIN dollar column**, not expectancy (that table's own math = -$0.009/trade). And even accepting 0.104%: 0.104% × $13.17 × 21.6 trades/day = **$0.30/day, not $0.08**. Fees are proportional to notional → notional is a **linear multiplier on the edge; it cannot "cap" a positive edge, only amplify a negative one.**
- **Last-200 SHORT claim fails reproduction**: claimed 56.0% gross +$0.11; measured **53.8%, gross -$0.55, net -$2.04**. Shorts are no longer gross-positive.
- **ride_it survives multiple-comparison correction — but only on atr_trend_accel.** Paired replay n=1,803: +0.182pp, t=5.89, **p=3.9e-9**; survives Bonferroni over 8–13 engines (α≈0.004–0.006). universal_hold (p=0.0064) marginally fails. **BUT on the full shadow book (n=38,349) ride is WORSE: -0.023pp, t=-3.33, p=0.0009. Do not generalize.**
- **hard_max_loss confirmed**: 30d n=76, 0% WR, gross -$9.24, **net -$10.36 = 88% of total net bleed**. Removing it entirely still leaves -$1.40. (Report's 148T/-$17.95 was its own 779T window — direction confirmed, number not reproducible now.)
- **Shadow power census** (124 registry entries): 27 n≥30, 16 n<30, **81 no parseable n**. Of 28 **open** studies: only **6 powered** (n=97–1830), 7 explicitly under-powered (n=5–24), 15 cite no n. The four `data/*_shadow.jsonl` (11,356 lines) carry **zero pnl outcomes** — they cannot support winrate claims without a join.

**Top 3 levers:** (1) fix the measurement layer — recompute every KPI net-of-fee with CI + payoff ratio; (2) attack hard_max_loss (88% of bleed) — extend stop-tighten beyond its current 53% coverage; (3) pre-register conversion bars with multiplicity correction.

**Confidence: HIGH** on net-negative expectancy; **MEDIUM** on registry power counts.

### 3. Risk Manager — Risk Level: EXTREME, Sizing APPROPRIATE (not the lever)

- **Fees = 0.10% of notional round-trip; gross edge = -0.055%/trade.** Both scale linearly with notional → **any size gives the same sign.** Sizing is also floor-bound: avg $13.16 vs `HL_MIN_NOTIONAL_USDT`=11.0 (69.5% floored) → `LOSERS_SIZE_MULT`/`FAVORITES_SIZE_MULT` mostly inert.
- **Losses are entry-side, not stop-side.** Stop family 30d = 228T gross -$25.96 (`atr_sl_hit` 98T -$10.28, `hard_max_loss` 76T -$9.24, cut-loser 20T, manual_sl 20T). **MFE/MAE on stop-family (201T): MFE 0.246% vs MAE 0.698% — these trades never went favorable.** Winners (320T): MFE 0.721 / MAE 0.235. *Stops at ~0.8% are landing where price was always going.*
- **Breakeven WR: 56.3% gross / 65.2% net** vs actual 51.9% → gap is **entry quality, not exit engineering**.
- `profit-monster-trail` 228T **95.6% WR +$13.02** — the only engine paying bills.
- **Concentration**: LONG 428T (66% of volume) gross -$3.83; ETH 23T -$0.85 (5× worst per-trade). Max concurrent 6; correlation low.
- **Drawdown**: 30d peak-to-trough -$11.82 = **-76% of $15.51 equity**; worst day -$1.43 (-9.2%); run-rate ≈ -75%/month.

**Top 3 levers:** (1) entry filter on stop family (174T, 0% WR, -$19.52 gross) — halving it = **+$10–13/30d, the only lever that moves the sign**; (2) fee path — need gross edge >0.10%/trade or maker routing, **~$7/30d**; (3) cut negative cells (LONG/ETH/HYPE) by reducing trade count — **+$3–4/30d**.

**Confidence: MEDIUM** (fee attribution from 500/649 rows; 149 rows lack fee record).

**Flagged outside question:** dashboards label gross as net — fix reporting before any sizing decision; `hard_max_loss` 148T/-$17.95 not reproducible (measured 76T/-$9.24).

### 4. Code Architect — Code Quality: HAS ISSUES, Architecture ACCEPTABLE

1. **MED→HIGH — duplicate APPROVED rows from preserve-upsert.** `signal_compactor.py:5944` SELECTs only `decision='APPROVED' AND executed=0`; when the prior row went `executed=1/FAILED`, no match → INSERT (:5965). Empirical: 43 `[PRESERVE-APPROVED-UPSERT]` lines; COMP SHORT has 4 rows at 23:35:34 (3 with `price=0.0`), EXEC'd 4× in 5 min. Same candidate re-claimed every cycle ~30min; if the block clears, two rows can both claim → **double-open path**. The `⚠️ signal NOT rolled back (prevents retry loop)` intent is defeated by the re-insert.
2. **MED — ride_it phase-1 can widen the stop and bypasses stop-tighten.** `ride_it_exit.py:359` (`should_update` true for any change, "must allow widening"), `_persist_sl` :226–234 = bare `UPDATE trades SET stop_loss` — no `status='open'`, no CAS, **no `tpsl_utils.stop_tighten_sl` hook**. Reachable live: `VOLUME_BUILDUP_MINUS_ENABLED=True`, exit `ride_it` enabled, `'volume-buildup-'` ∈ `STOP_TIGHTEN_SOURCES` (:761). PM order makes it stick (clamp at :2483 runs first, engines rewrite after :3595→:3611). 0 `RIDE-IT-P1` lines today = frequency unverified.
3. **MED — engines not mutually exclusive.** `position_manager.py:3409–3417` (pump_exit), `3589–3595` (ride_it), `3624–3638` (rr_engine) each fire if *any* comma-part maps → combo source runs 2–3 writers, last wins. **All three gated on `RR_EXIT_ENABLED`** — flipping one flag silently kills pump_exit and ride_it too.
4. **MED — signal_type collision.** `grind_breakout_v2.py:70-71` identical to `grind_breakout.py:65-66` (`grind_breakout_long/short`); both enabled. Decay/kill stats group by `signal_type` → v1/v2 pooled; **v2 can't be killed or credited separately.**
5. **MED (convention) — hardcoded thresholds** in `volume_buildup.py:103,173-182,214`, `vol_momentum.py:159,163`, `grind_breakout_v2.py:368,128-151`, `pump_chain_v6.py:196`.
6. **LOW — dead entries generated.** `atr_trend_accel.py:239-243,265` has no detect-time RSI floor → 4 COMP SHORTs fired at detect RSI 36.8, all killed by `[EXEC-RSI-DETECT-FLOOR]`, each marked FAILED, **occupying hotset 5 cycles**.
7. **LOW — 0-SL window** `decider_run.py:5535-5538` (mitigated by cut_loser P1 + HL side + ATR within 1min).
8. **Sideways LOW** — defunct `from signal_gen import` in 6 unregistered files (`phase_accel.py:207`, `pump_catcher.py:436`, `ma_cross_5m.py:570`, `macd_1m.py:188`, `ema20_50.py:413`, `range_finder_short.py:347`) — landmine on re-enable.
9. **Verified clean:** registry 89/52 enabled, **0 enabled with `run=None`**; pipeline.log 0 Traceback, 0 SIGNAL-ERROR; linreg-fade correctly bypasses engines; atr-trend ride_it trial inert; **stop-tighten 0.75 ENFORCE correct and binding live**; win-capture log-only (exit still 0.30); TP gate correct (`position_manager.py:646-658`).

**Top 3 levers:** (1) stop the preserve-upsert re-insert — biggest measurable hygiene win; (2) generation-time RSI floor for atr_trend_accel SHORT; (3) make exit engines mutually exclusive + route ride_it SL writes through `stop_tighten_sl`.

**Confidence: MEDIUM**

### 5. Regime Analyst — Current Regime: 4h SHORT_BIAS (90/130 tokens), 15m mostly NEUTRAL. **Regime Match: NO**

1. **Baseline re-verified**: 30d n=648, WR 51.9%, net -$4.80 gross.
2. **The WR gap is regime-invariant.** Shadow vol_regime × direction (n in thousands): EXTREME 48.0% S vs 44.5% L; HIGH 50.6 vs 44.3; NORMAL 41.2 vs 36.4; FLAT 19.2 vs 15.3. **SHORT beats LONG in every regime by a near-constant 4–6pp** → regime is not the cause.
3. **⚠️ Regime-match is BACKWARDS.** Shadow `has_regime`: **COUNTER beats ALIGNED everywhere** — LONG 40.0% (n=22,335) vs 38.6% (n=7,838); SHORT 46.2% (n=17,507) vs 44.0% (n=13,391). OOS last-14d: SHORT 47.6% counter vs 41.7% aligned. Live: **LONG in SHORT_BIAS 57.6% (n=118, net +$0.17) beats LONG in LONG_BIAS 48.8% (n=80, net -$1.48)**, z=-2.13. **Strengthening direction-regime matching would cut winners.**
4. **Gates near-coin-flip calibrated**: blocked avg -0.135% vs admitted -0.126% (0.01pp discrimination). 12/22 cells blocked-outcome better than admitted. SHORT-REGIME-GATE (n=567) and LONG-NEUTRAL-CHOP (n=482, 29.5%) block below-baseline → correct. **But CTX-GATE blocks LONGs at -0.094% avg (n=2,081, WR 48.7%) — better than admitted baseline → LONG side is blocking winners.**
5. **New signals**: `btc_pump_rider_long` blocked cohort n=1,195 WR 59.0% avg -0.072% vs admitted n=225 WR 46.7% avg -0.142% — inversion. `linreg_fade_short` fires 42% (552/1,323) in **BEAR_TREND where it's worst: WR 31.9% CI[28.0,36.0], avg -0.245%**; only positive cell RANGING +0.135% (n=182). `ichimoku_long` worst cell BEAR_TREND (n=480, 43.8%, -0.256%). **Counter-regime SHORTs work**: `atr_trend_accel_short` BULL_TREND n=143 **62.2%**, `ichimoku_short` BULL_TREND n=839 **59.5%**.

**Top 3 levers:** (1) audit CTX-GATE's LONG rules (blocks above-baseline outcomes incl. our newest best LONG signal); (2) regime-weight `linreg_fade_short` toward RANGING (score haircut, not a gate); (3) lean LONG capacity toward pump-riders (`btc_pump_rider_long` +0.185% in BEAR n=70, `volume_buildup_long` +0.148% n=25) away from trend-following longs (`ichimoku_long` -0.256%) — selection by signal type, not direction or time blocks.

**Confidence: MEDIUM** — large shadow n but exits simulated; live per-cell n often <120.

### 6. Systems Engineer — Pipeline HEALTHY, Data FRESH, Services RUNNING

1. **Pipeline clean**: 836 cycles/24h, median gap 49s, max 177s, zero >3min; lock held by live PID (not stuck); 0 Tracebacks 24h. Only 3 ERROR lines = `AUTO-EXEC REJECTED: BTC SHORT — RSI < knife 35` (filter doing its job) — but **3 pending ladder orders silently failed** (LOW-MED, wasted auto-exec cycles).
2. **Freshness**: 1m 73s, 5m 193s, latest_prices 9s, hotset 33s.
3. **Services**: `systemctl --failed` = 0. 6 err/24h: `hermes-brain-auditor` start-timeout ×3 (previous run still executing — **fix: `TimeoutStartSec=infinity`**), `liquidation-map` ×2 self-recovered, `hermes-auto-1hr` ×1 self-recovered. None touch the trade path.
4. **Signal path delivers**: FAST 47 + SLOW 5 = 52 registered, 0 errors; compactor finishes every 60s; new signals fire (`jup_yolo_mirrored` 255 rows/24h).
5. **⚠️ Execution RSI drift**: median **6.1 pts**, max 29.9, **23/86 trades >10 pts drift** — the documented v2-filter gap. (Staleness itself solved: median 1.99 min, **0 of 89 trades >10min**.)
6. **Sideways MED**: 134 files in `scripts/signals/` but only **52 registered, 29 flag-disabled, ~81 never registered** — dead code or signals someone thinks are live.
7. **Sideways MED**: `logs/signal-compactor.err.log` holds **6,808 errors** (`ImportError: SPEED_HOTSET_THRESHOLD`, `NameError: _vol_regime`) — stale (mtime Nov 15), current runs clean. **Rotate it or it poisons the next log audit.**
8. **Sideways**: "structure-trail" = commit-message concept, **0 hits in code** — actual change is the TP gate (verified by Code at `position_manager.py:646-658`). Router confirmed: no missing feature, naming mismatch only.
9. **No lock contention**: 0 `LOCK-WAIT` lines; shadow collectors never take the pipeline lock → **shadow load costs nothing, not a winrate factor.**
10. **Loss concentration (7d)**: SL-family (`hard_max_loss` 16, `atr_sl_hit` 14, `manual_sl_hit` 10) = **116.9% of gross losses**; armed 56T **83.9% +$4.43** vs never-armed 53T **11.3% -$4.10**.

**Top 3 levers:** (1) re-validate entry filters at execution time (RSI drift, root fix in execution path); (2) **close the never-armed hole** (53/108 trades, 88% of the 7d net gap); (3) kill SL-family bleed — ship corrected-ATR-SL beyond JUP scope + queued `giveback_frac` profiles.

**Confidence: HIGH** (measured directly); MEDIUM on structure-trail naming.

---

## Synthesis

### Consensus

| Expert | Verdict | Weight | Confidence |
|--------|---------|--------|------------|
| Signal Analyst | MODIFY — prune proven losers, gate mid-band LONGs | 0.25 | MEDIUM |
| Statistician | **REJECT BASELINE** — edge is significantly net-negative (p=2.9e-5) | 0.25 | HIGH |
| Risk Manager | EXTREME risk — fix measurement, then entry filter | 0.25 | MEDIUM |
| Code Architect | REWORK — 1 MED→HIGH bug, engine collisions | 0.15 | MEDIUM |
| Regime Analyst | **DISSENT** — do NOT strengthen regime matching | 0.15 | MEDIUM |
| Systems Engineer | FIX FIRST — never-armed hole, RSI drift | 0.05 | HIGH |

**Weighted Confidence Score: 0.82 / 1.00**

### The one-line diagnosis (all 6 agree)

> **The system does not have an exit problem or a sizing problem — it has an entry-quality problem measured wrong: expectancy is -$0.0181/trade net of fees (p=2.9e-5), payoff 0.71, and the single largest identified hole (never-armed, 53/108 trades at 11.3% WR) is an execution-state bug, not a strategy.**

### Dissent Notes (NOT suppressed)

1. **Regime Analyst dissents against intuition:** counter-regime beats aligned in every cell (n in thousands, OOS-confirmed). *Any proposal to "align trades with regime" will cut winners.* This contradicts the natural reading of the LONG/SHORT gap and must not be implemented without a fresh counterfactual.
2. **Statistician dissents on ride_it generalization:** survives Bonferroni on atr_trend (p=3.9e-9) but **reverses sign on the full book** (n=38,349, p=0.0009). Do not roll ride_it out beyond atr_trend on this evidence.
3. **Risk + Statistician jointly reject the prior "notional cap" thesis:** notional is a linear multiplier — it cannot cap a positive edge, only amplify a negative one. The "$0.08/day" premise traces to a mislabeled avg-WIN column.

### Contradictions resolved by the router

| Conflict | Resolution |
|----------|-----------|
| ride_it flag: Risk says ON, Code says OFF | **Both right** — `ATR_TREND_EXIT_TRIAL_ENABLED=False` (:4723, trial scoped) vs `RIDE_IT_ENABLED=True` (:5490, generic engine live for volume-buildup etc.) |
| "net" baseline | **Gross** — `pnl_usdt` excludes fees (JSON `fees.fee_total`). Router's opening table mislabeled; corrected above |
| hard_max_loss 148T/-$17.95 vs 76T/-$9.24 | **Window difference** — report used its own 779T window. Current 30d = 76T/-$10.36 net. Direction confirmed by both |
| structure-trail 0 hits vs commit title | **Naming mismatch** — commit describes the TP-gate change (`check_atr_tp_sl_hits`), verified landed at `position_manager.py:646-658` |

---

## Recommendation

**FIX THE MEASUREMENT LAYER FIRST, THEN ATTACK ENTRIES. Do not touch sizing, do not strengthen regime matching, do not roll out ride_it beyond atr_trend.**

### Phase 0 — Measurement (Day 1, no trading impact)
1. Recompute every KPI **net-of-fee** with CI + payoff ratio. Dashboards currently call gross "net" — every downstream decision inherits the error. (Statistician lever 1, Risk flag (a))
2. Fix the `$0.08/day` premise wherever it's cited — it traces to a mislabeled column.

### Phase 1 — Close the execution holes (Days 1–3, highest certainty)
1. **Never-armed hole** — 53/108 trades, 11.3% WR, -$4.10/7d = **88% of the 7d net gap**. Verify the queued arm tripwire / prearm-BE lands (brain_auditor 11-21 batch). *(Systems lever 2)*
2. **preserve-upsert re-insert** — `signal_compactor.py:5944-5965`. Removes 4–5× EXEC churn and the double-open path. *(Code lever 1)*
3. **Prune the two proven losers from bypass** — `hl_copy_trader` (p=0.017), exec-gate `ai-trader-pending` (p=0.013). *(Signal lever 1)*

### Phase 2 — Entry quality (Week 1, needs shadow validation first)
1. **Entry filter on the stop family** — 174T, 0% WR, MFE 0.246% (never went favorable). Halving it = **+$10–13/30d — the only lever that moves the sign.** *(Risk lever 1)*
2. **Gate mid-band LONGs** — `rsi_exec` 55–70 (128T, -$3.21) AND `gap` 0.5–1% (88T, -$2.29); hook beside the chase filter at `decider_run.py:6370`. Backtest before flipping. *(Signal lever 2)*
3. **Re-validate entry filters at exec time** — RSI drift median 6.1 pts, 23/86 >10pts. Root fix in execution path, not per-signal. *(Systems lever 1)*
4. **Audit CTX-GATE LONG rules** — currently blocking above-baseline winners. Shadow-first counterfactual, no constants change. *(Regime lever 1)*

### Phase 3 — Stop the bleeding (Week 1–2)
1. **hard_max_loss** — n=76, 0% WR, net -$10.36 = **88% of the 30d net bleed**. Extend stop-tighten beyond its current 53% coverage (out-of-scope stop-family n=54, -$5.59/14d). *(Statistician lever 2)*
2. **Halt promotion of losing shadows** — `PUMP_CHAIN_V6_ENABLED=False` (shadow n=3437 @34.2%); don't scale linreg_fade (n=1239 @36.2%) until its 11-27 study flips. Only grind_breakout_short (+0.234%, n=230) is a promote candidate. *(Signal lever 3)*

### Explicitly NOT recommended
- ❌ **Sizing changes** — inert (69.5% floored) and mathematically incapable of flipping a negative sign.
- ❌ **Strengthening regime-direction matching** — Regime Analyst's dissent: it cuts winners.
- ❌ **Rolling ride_it beyond atr_trend** — sign reversal on the full book.
- ❌ **New entry signals** — 9 shipped in 45d, 3 with large-n losing shadows, most at n≤11 live.

---

## Evidence Summary

- Net expectancy **-$0.0181/trade**, CI95 [-0.0266, -0.0096], **p=2.9e-5** (n=648, run twice, identical)
- Breakeven needs **WR ≥65%** at payoff 0.71, or **payoff ≥1.14** at current WR
- 30d: gross -$4.80, fees $6.96, **net -$11.76**; equity $15.51 → **-76% drawdown**
- Never-armed: 53T **11.3% WR -$4.10** vs armed 56T **83.9% +$4.43** (7d)
- Stop family MFE **0.246%** vs MAE **0.698%** — never went favorable; winners MFE 0.721/MAE 0.235
- `hard_max_loss` n=76, 0% WR, net -$10.36 = **88% of bleed**
- `profit-monster-trail` 228T **95.6% WR +$13.02** — only engine paying bills
- Two proven losers: `hl_copy_trader` p=0.017, `ai-trader-pending` p=0.013 — still filling via bypass
- New signals: pump_chain_v6 shadow n=3437 **34.2%**, linreg_fade_short n=1239 **36.2%**
- Regime: COUNTER 40.0% (n=22,335) vs ALIGNED 38.6% (n=7,838) — matching cuts winners
- Shadow power: **only 6 of 28 open studies powered (n≥30)**; 4 JSONL files carry zero pnl outcomes
- ride_it: atr_trend p=3.9e-9 ✓ survives Bonferroni; full book n=38,349 **p=0.0009 WORSE**
- Pipeline healthy: 836 cycles/24h, 0 Tracebacks, 0 failed units, no lock contention, 0 trades >10min stale
