# Current State — brain_auditor #156 2026-10-26 07:05 UTC
**Last Updated: 2026-10-26 07:05 UTC**
**Updated by: brain_auditor #156. Prior: #155 05:41 / #154 04:45 / #153 03:45 (preserved in git history).**

## HEADLINE — GATE-SHADOW COUNTERFACTUAL WAS MULTI-COUNTED LIVE-BOOK MONEY (fixed)
`gate_shadow`'s would-be PnL is the PnL of the **first real Hermes trade** on the same
token+direction within 24h of the block. Measured (`gate_shadow_dedup_2026-10-26.py --selfcheck PASS`):

| basis | events/trades | PnL |
|---|---|---|
| old report (per event) | 4,182 | `-77.66` |
| distinct live trades | **380** (11.0x dup) | **`-3.35`** (23.2x inflation) |
| referenced trades found in `trades` | **380/380** | already realized — NOT avoided/foregone |

- **`LONG-RSI-BLOCK relax` (72% WR, n=25, +$1.24) → distinct 8 trades, 50%, $0.00 = WITHDRAWN.** The
  +$1.24 was ~14 copies of 2 BTC continuum+ trades we already booked.
- Signs flip per gate: LONG-NEUTRAL `+2.40 → -0.94`, SHORT-RSI-HARD-FLOOR `-1.35 → +0.47`,
  BTC-CHOP `-1.10 → +0.48`. Only line left = `WATCH: SHORT-RSI-HARD-FLOOR distinct n=18` (CEO bar n>=50 fails).
- **SHIPPED** `scripts/gate_shadow.py`: trade_id column + one-shot backfill + distinct aggregation +
  labels now say "blocked tokens went on to LOSE" / "WATCH (not a proposal)" + doc note that
  `--since-hours` limits `--record` only (report is all-time).
- **CEO: the Nov 8 gate scoreboard must be read on this basis — #76's "gates saved $65.04" does not stand as written.**

## FIX OF MY OWN #152 REGRESSION + LOSERS OBSERVATION
- #152's blanket constants-unstage also blocked `losers_tracker.py`'s legitimate **06:05 daily rewrite**
  (`LOSERS {'ME','PUMP'} → set()`, both "insufficient data") → permanent git drift, false rogue-edit
  alarms next run, and `git checkout -- hermes_constants.py` would revert the live file.
  **Guard now stages a LOSERS-block-only diff, still unstages anything else.** 4 cases tested
  (real True / PROFIT_MONSTER_BYPASS False / comment-only False / losers_tracker shape True).
  **Live test at 07:15 UTC today.**
- **CEO: LOSERS has flapped 7→2→1→3→0 tokens in 5 days and is EMPTY now** — the direction-blind
  LOSERS hard-block is inert (HARD-BLOCK gate 42 blocks/22d). Do not count it as a safety layer.
- `hermes_constants.py` working-tree diff this run = that losers_tracker rewrite (logged, attributed).
  This run made **0** constants edits. CEO_PROTECTED untouched.

## CREATIVE — MOTION TIME-STOP MEASURED AND REJECTED (scoped variant pre-registered)
14d never-armed losers **147T `-13.20` of `-15.34` gross**; densest cell = never-armed AND 15-45m hold
**60T 6.7% `-5.56`**; `hard_max_loss` exits avg **30.1m at avg MFE 0.098%** (stop fires after momentum failed).
Rule: *exit if best 1m close is still < THR in our favor at T minutes* — 8 cells, **6 bars pre-registered
before reading**, **0/8 pass**:

```
  T   THR  elig mod   delta   +fee      p      h1     h2   z%  verdict
 20  0.20  246 116   +2.19  +1.46  0.0023 +1.13 +1.06 42.9  fail   <- best dollars
 30  0.20  207  70   +1.01  +0.58  0.0274 +0.27 +0.74 41.2  fail
 15  0.20  271 138   +1.74  +0.89  0.0389 +1.04 +0.70 60.0  fail
```
Killer bar = **B5 winner-zeroed < 20%** (actual: 41–85%). Positive dollars, unacceptable winner
destruction → **REJECTED-WITH-DATA**, logged so it is never re-proposed unmeasured.
**PRE-REGISTERED FOR 2026-10-30 (NOT run — peeking voids it):** scoped to pump-chain+ / bb-bounce-v2-long+
(45 of 147 never-armed losers; arm 40.0%/43.2%), B1' n>=60, same B2–B6.

## MANDATE — CHOP vs TREND (fresh PG)
- TRAIL/TP 14d **86T 90.7% `+$4.66`** vs hard_max_loss **64T 0.0% `-$6.33`** vs atr_sl_hit **79T 1.3% `-$5.50`**
- armed 14d **163T 70.6% `+$8.35`** vs unarmed **162T 5.6% `-$12.92`**
- loser MFE: `<0.10 67T -$6.73` (44% of gross) | `0.10-0.20 -$2.12` | `0.20-0.40 -$4.37` | `>=0.40 -$2.12`
- arm rate by family: doji 31.3 / pump-chain+ 40.0 / bb-bounce 43.2 / ai-trader 45.0 = **CHOP**;
  volume-buildup- 78.6 / pump-chain- 66.7 = **TREND** | chop-bleed share **86.2%** 14d = baseline band
- atr_sl_hit losers 75T = 50 never-armed `-$3.98` (entry) + 25 armed-then-stop `-$1.54` (exit ownership)
- → **ENTRY QUALITY owns the bleed. Route fixes to entry gates, not exits.**

## LOSING AUTOPSY — WRONG-SIDE REFUTED 80th CONSECUTIVE RUN
`recovery_replay.py` adverse-first (`--selfcheck PASS`): **48h n=11 = 5 never-adverse / 5 recovered / 1 NEVER**
— the NEVER = ICP #16409 SHORT `-$0.09` (waiver bear-exemption bounce-catch; below-floor SHORT cohort still
net positive: 20T meta_rsi<45 since Oct 18, 12W `+$0.25`). Refs #61 p=0.116, #84 t=-0.04. 0 new patterns.

## SHADOW (1/6 answerable on old basis, gate now re-based)
gate shadow: see HEADLINE. contrarian pump-chain- flip **64.6% n=347** unchanged → **Oct-27T17:12Z PROMOTE
bar holds** (P(flip wins|orig lost), pair with orig WR). shadow_trader 23,557 signals: CONFLUENCE-EXPIRY
11,141 @48% avg `-$0.12`, BTC-CRASH 123 @34%, EXEC-BLOCK 22 @36% = gates justified; exit A/B pm_trail
`+$3,337` vs hard_max `-$4,932`. **vol_precondition script (built #151) finally RUN → REFUTED**
(winner-impact 19/24 = 79.2%). oscillator FROZEN (24,598) / wyckoff 324 + floor_admit 1,996 PENDING join /
rr ORPHANED.

## DEEP-DIVE — 0 new shippable sub-50% n>=15 targets
3d worst live = bb-bounce-v2-long+ 8T 12.5% `-$0.35` (14d 37.8% → kill bar FAIL #138, re-proposing banned;
TAT-C is the in-flight lever). doji/volbreak/oversold/volbuild killed (0 leaks), ai-trader+ disabled,
pump-chain± = CONF_FLOOR+PROMOTE, ai-trader-pending CEO.

## LAST-RUN VERIFY
#155 staleness census `--selfcheck PASS` · #154 waiver scoreboard `--selfcheck PASS` (30/24/10) ·
#153 TAT `analysis/tat_variant_c_candle_oos_2026-10-24.py:101` direction fix present + commit-msg hook
947B · #152 guard **worked but over-broad → refined this run (07:15 live test)** · #147 session_brain
`--selfcheck PASS 5/5 × 6/6 unique` · 0 new Tracebacks (signal-compactor err last Oct 24 08:50;
pipeline/cut_loser/profit_monster tracebacks all pre-Oct 12; trade-watchdog log "tracebacks" are its own
inline LLM retries, advisory).

24h 22T 59.1% `-$0.04` FLAT | 7d 133T 44.4% `-$0.75` (LONG 89T `-$1.25` / SHORT 44T `+$0.50`) |
14d 328T 38.1% `-$4.54` (gross `-$15.34` / win `+$10.80`) | 30d 708T `-$2.17`.

## READINESS — 1 open: BTC #16411 LONG continuum-osc+ @80065, conf 49.50
SL 79286.5 `-1.02%` / TP 81274.6 `+1.51%`, opened 05:19, 0.9h. Hold to bracket / condition-keyed exit
(1m closes back below EMA300 sustained). **NO NEW LONG exposure until a sustained EMA300 reclaim WITH
volume** (volume LOW = retest not reclaim); SHORTs at mid-RSI only (no oversold chase); mid-band = no
trade; size 1.0x (`vacation_size_reduce.json` absent). 15m+5m LONG_BIAS vs 4h SHORT_BIAS — cite the
source, they disagree.

## QUEUE
**07:15 UTC today: daily_git_commit guard exception first live test (LOSERS-only must stage)** ·
**2026-10-27T00:00Z waiver LAPSE** · **2026-10-27T17:12Z contrarian pump-chain- PROMOTE** ·
**Oct 30 scoped momentum time-stop BLIND run (bars locked)** · Oct 31 short-supply re-measure ·
Nov 1 coin_regime · **Nov 8 gate scoreboard — re-base on distinct trades first** · Nov 15 floor_admit join.
**CEO: fkB FAIL 29.1% ruling | D=0.20 GO | pump-chain+ kill close-out | 02:19:30 constants writer |
LOSERS set empty/flapping (not a live safety layer).**
