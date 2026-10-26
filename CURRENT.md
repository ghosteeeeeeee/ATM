# Current State — brain_auditor #157 2026-10-26 07:55 UTC
**Last Updated: 2026-10-26 07:55 UTC**
**Updated by: brain_auditor #157. Prior: #156 07:05 / #155 05:41 / #154 04:45 (preserved in git history).**

## HEADLINE — TWO SHIPS: the daily-commit guard exception was broken by its own post-stage
read (07:15 live test failed), and the Oct-27 PROMOTE finally got its control arm.

**1) GUARD FIX (`scripts/daily_git_commit.py`).** #156's `constants_diff_is_losers_only()`
was called AFTER `git add -A` and read `git diff` (worktree vs index) — staging empties it,
so the predicate always returned False and the LOSERS exception could never pass. Proof:
commit `fc7d21b1` message lists "Scripts (1 files): scripts/hermes_constants.py" while the
commit contains **no** constants diff (a lying audit trail = exactly how drift and false
rogue-edit alarms reproduce). **Now:** decision taken BEFORE staging, predicate reads
`git diff HEAD`, message drops constants it will not commit, `--selfcheck` added.
Verified: py_compile PASS · selfcheck **4/4** (LOSERS-only unstaged / LOSERS-only **staged**
= the regression / rogue flag / comment-only) · **live on the real repo pre-stage True AND
post-stage True**. The sanctioned losers_tracker rewrite is committed deliberately this run.

**2) PROMOTE CONTROL ARM (`analysis/contrarian_both_sides_2026-10-26.py`, --selfcheck PASS).**
The pre-registered bar read "pump-chain- flip-WR 64.6% n=347" with no original-direction
number beside it — one-armed. Same 347 events, same +/-0.40/0.40 30x5m rule, both directions:

| signal | orig WR | flip WR | discordant (F>O / F<O) | exact p |
|---|---|---|---|---|
| pump-chain- | **36.6%** | **64.6%** | 218 / 121 | **<0.0001** |
| btc-pump-rider+ | **73.4%** | **25.1%** | 50 / 146 | **<0.0001** (do-NOT-flip) |

OOS halves same sign: pump-chain- older 34.7→66.8 (p<0.0001), newer 39.0→61.7 (p=0.0058).
**Caveats travel with the number:** touch-rule price-move % only (no fees/leverage — UNITS
RULE), and a flipped signal meets LONG-direction gates (realized book ≠ touch book).

## CREATIVE — WAIVER-LAPSE IMPACT (decides nothing, informs tomorrow 00:00Z)
Does the hottest family depend on the sub-45 exemption? **No.** 7d volume-buildup- SHORT:
`rsi_exec>=45` = **6T 83.3% `+$0.42`** vs `rsi_exec<45` = **13T 69.2% `+$0.01`** — every dollar
of family PnL comes from >=45 entries; the waiver band adds zero on 13 trades.
14d all-Shorts <45 = 15T 66.7% `+$0.26` (n<20, below bar). => **lets it lapse stand**
(#154/#155 recommendation, contingency failed its `>+$0.30` bar Oct 25).

## CHOP-COVERAGE LEDGER — re-based on the NEVER-ARMED denominator
14d never-armed losers **`-$13.22` / 147T** (the #90 ledger used HML exits only):
killed 27T `-$2.78` (21.0%) · disabled ai-trader+ 11T `-$1.08` (8.2%) · CONF_FLOOR pc± 20T
`-$1.81` (13.7%) · MFE-CUT bb-bounce 20T `-$1.87` (14.1%) = **OWNED 57.0% (target 80%)**;
residual 69T `-$5.68` with **no cell at n>=20** → gap closes only when CONF_FLOOR ships.

## MANDATE — CHOP vs TREND (fresh PG, 14d)
- TRAIL/TP family: pm-trail 80T 91.3% `+$4.45` + atr_trail 24T 79.2% `+$3.47` + trail_sl
  `+$0.69` + rr_trail `+$0.54` = **`+$9.15`** vs **hard_max_loss 64T 0.0% `-$6.33`**
  vs atr_sl_hit 79T 1.3% `-$5.50`
- armed 165T 69.7% `+$8.38` vs unarmed 162T 5.6% `-$12.93` · loser MFE `<0.10% 67T -$6.73` = 44% of gross
- arm rate: TREND volume-buildup- 78.6 / pump-chain- 66.7 · CHOP ai-trader 45.0 / bb-bounce 43.2 / pump-chain+ 40.0 / doji 31.3
- chop-bleed share 86.2% = baseline → **ENTRY QUALITY owns the bleed; exits are working**

## LOSING AUTOPSY — WRONG-SIDE REFUTED 81st CONSECUTIVE RUN
`recovery_replay.py` adverse-first (`--selfcheck PASS`, vacuity 182/190 reproduced):
**48h n=11 = 5 never-adverse / 5 recovered / 1 NEVER** — ICP #16409 SHORT `-$0.09`
(waiver bear-exemption). 14d 190 losers = 38 / 123 / **29 NEVER = 17.5%** structural cohort
(re-enter-on-recovery already REJECTED-WITH-DATA p=0.158 — not reopened). Refs #61 p=0.116, #84 t=-0.04.

## DEEP-DIVE — 0 new shippable sub-50% n>=15 targets
14d: bb-bounce-v2-long+ 37T 37.8% `-$1.11` (kill bar FAIL #138, banned; TAT-C live) ·
doji 16T killed (0 leaks) · ai-trader+ disabled · pump-chain- 36T 22.2% = CONF_FLOOR+PROMOTE ·
pump-chain+ 45T 31.1% (conf<30 `-$1.24` vs conf>=30 `+$1.12`; 30d `+$1.88` NO-KILL) ·
ai-trader-pending CEO. 7d: bb-bounce 19T 36.8% · ai-trader-pending 15T 26.7%.

## SHADOW (2/6 answerable)
contrarian join re-run 819/547 + **control arm above** · gate_shadow now DISTINCT-trade
basis (only `WATCH: SHORT-RSI-HARD-FLOOR 61.1% n=18`, n>=50 bar fails) · shadow_trader
23,693 signals: CONFLUENCE-EXPIRY 11,182 @48% avg `-$0.12`, BTC-CRASH 123 @34% = gates
justified; exit A/B pm_trail `+$3,381` vs hard_max `-$4,969` = trail-or-nothing ·
oscillator FROZEN (24,598) / wyckoff 324 + floor_admit 2,021 PENDING join / rr ORPHANED.

## LAST-RUN VERIFY
#156 gate_shadow dedup WORKING (report re-based, LONG-RSI-BLOCK proposal correctly absent) ·
#155/#154/#153/#147 selfchecks PASS · #152 revert holding (diff = LOSERS only, PROFIT_MONSTER_BYPASS
pump-chain intact) · rsi_drift 29 stamps/48h · floor-45 0 violations (14 sub-45 SHORT opens 3d
all in 35-45 waiver band, min 35.95; knife <35 blocked 03:01 YGG 29.7) · kill flags 0 post-kill ·
size-reduce ABSENT = 1.0x · commit-msg hook 947B · 0 new component Tracebacks since Oct 24 08:50.

**DRIFT+1 (LOW/MED):** weekly `Self-healing test: FAIL - ModuleNotFoundError dispatcher.dispatcher`
03:00 Sun (Oct 11/18/25) — #137's health_monitor 83f99f71 SKIP branch still unverified →
**Nov 1 check queued.** session_brain dup drift **RESOLVED** (selfcheck 6/6 unique).
Carried LOW: `trades.regime` zero-variance, `signal_created_at` dead, `data_integrity_guard.py` never invoked.

24h 22T 59.1% `-$0.04` FLAT | 7d 131T 43.5% `-$0.84` | 14d 327T 37.9% `-$4.55` (gross `-$15.34`) | 30d 708T 44.2% `-$2.17`.

## READINESS — 2 open, both bracketed
- **BTC #16411 LONG continuum-osc+ @80065** conf 49.5, SL 79286.5 `-$1.02%` / TP 81274.6 `+1.51%`
  → hold to bracket; exit on sustained 15-30m 1m close back below EMA300.
- **CAKE bb-bounce-v2-long+ @2.0907** conf 100 → **would NOT open fresh** (worst live long
  family, 7d 19T 37% `-$0.59`, 15/19 mid-band); variant-C `BB_BOUNCE_TRAIL_ARM_TIMEOUT` owns it
  at age>=55m & pnl<0.

**Rules:** NO NEW LONG exposure until sustained 1m EMA300 reclaim **WITH volume** (LOW volume =
retest, not reclaim) · SHORTs only at rsi_exec >=45 (waiver lapses 2026-10-27T00:00Z), never
knife <35 · mid-band = no trade (compound block refuted, re-measure Oct 27) · trail-family first ·
size 1.0x (file absent). Regime sources disagree — cite the source: scanners btc_15m + btc_4h
SHORT_BIAS vs continuum AT EMA300 / ACCUMULATION / RECOVERY, volatility LOW.

## QUEUE
**2026-10-27T00:00Z waiver LAPSE** (support above) · **2026-10-27T17:12Z contrarian pump-chain-
PROMOTE** (control arm attached: orig 36.6% vs flip 64.6%, p<0.0001 both halves; btc-pump-rider+ do-not-flip) ·
Oct 27 mid-band re-measure (#139 — do not run early) · **Oct 30 scoped momentum time-stop BLIND run**
(bars locked) · Oct 31 short-supply re-measure · **Nov 1 coin_regime + self-healing SKIP verify** ·
Nov 8 gate scoreboard (distinct-trade basis) · Nov 15 floor_admit/wyckoff joins.
**CEO: fkB FAIL 29.1% ruling → CONF_FLOOR | D=0.20 GO | pump-chain+ kill close-out | identify the
02:19:30 constants writer | LOSERS set EMPTY (not a live safety layer) | NEW: guard's LOSERS
exception proven pre- AND post-stage, daily rewrite no longer accumulates drift.**
