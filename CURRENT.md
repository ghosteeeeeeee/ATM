# Current State — brain_auditor #143 2026-10-25 16:55 UTC
**Last Updated: 2026-10-25 16:55 UTC**
**Updated by: brain_auditor #143. Prior: #142 15:42 (preserved in git history).**

## HEADLINE — 0 config changes (nothing passed bars), 1 analysis ship + 1 doc-drift fix
**DRIFT FIXED: CEO queue item "post-arm floor D=0.20 GO" was STALE** — that floor is
ALREADY LIVE: UGB-PT enforced on every non-PM-armed trade at +0.40 (CEO GO Oct 24, ship
#130) and PM-managed armed trades trail at D=0.20 (verified live: `[TRAIL] HYPER floor=0.65
dist=0.20` from peak 0.85). Residual tightening UGB_PT_DISTANCE_PCT 0.30→0.20 measured FRESH
this run on the exact bypass cohort (#136 scope): 30d `+2.368` vs `+2.247` = `+0.12` = NOISE
(14d `+1.323` vs `+1.318`) → MONITOR, no change. Escalation #17 = CLOSED (superseded by
live UGB-PT), no longer "awaiting GO". hermes_constants.py EMPTY git diff.

## CREATIVE #1 — PRE-ENTRY DISPLACEMENT GATE: REJECTED-WITH-DATA
Mandate hypothesis (trend entries move first, chop entries don't) measured on every closed
trade, 6 1m candles strictly `ts < open_time`, direction-adjusted, price-move % vs pnl_usdt:
- 14d: no-disp 153T 34.6% `-3.59` vs >0.15 103T 38.8% `-0.15` — **Fisher p=0.510**
- 30d: no-disp 311T 41.5% `-4.06` vs >0.15 220T 44.5% `+0.08` — **Fisher p=0.533**
- Winner impact: **42.7% / 42.4% of winners killed** (bar <20%) = destroys `+4.37`/`+12.14`
- Family-confounded both ways (doji/bb-bounce no-disp BETTER; bb-squeeze disp better)
→ fails significance, fails fk, kills winners. **Not shipping.**
Script `brain/analysis/pre_entry_displacement_2026-10-25.py` — first cut had a
MIS-PARAMETRIZED Fisher (reported p=0.106); independent brute-force cross-check caught it;
rewritten with `FISHER_SELFCHECK` assertions (0.5101/1.0/0.001093) PASS.

## CREATIVE #2 — CONTRARIAN FLIP-POOL NARROWED (zero code)
Fresh outcome join 541/813: pump-chain- flip-WR 64.1% n=344 (Oct 27 PROMOTE recheck);
**btc-pump-rider+ flip-WR 25.0% n=196 = flipping LOSES 75%** → excluded with data;
hmacd_mtf-+ n=1 dead. Pool overall 49.8% = flip is family-specific, not generic.
Oct 27 evaluates **pump-chain- only**.

## LOSING AUTOPSY 48h — WRONG-SIDE REFUTED 67th CONSECUTIVE RUN
`recovery_replay.py` adverse-first (selfcheck PASS, open-anchored vacuity reproduced
181/190=95.3%): n=5 = 2 never-adverse / 2 recovered-after-adverse / **1 NEVER**
(BTC #16377 manual_sl_hit `-0.08`, immaterial). Winning side for all 5: flat or
already-short. Valid refs: #61 p=0.116, #84 fwd t=-0.04.

## MANDATE — CHOP vs TREND (fresh)
- 7d: armed (mfe>=0.40) 61T 72.1% `+3.25` vs never-armed 61T 18.0% `-3.66`
- 7d exits: profit-monster-trail 45T 40W `+2.70` · hard_max_loss 14T 0W `-1.80`
  · atr_sl_hit 25T 0W `-1.40` · stale_exit 3T 0W `-0.64`
- 14d: armed 155T 69.7% `+8.52` vs unarmed 172T 9.3% `-12.58`
- chop-bleed KPI 7d 83.8% / 14d 85.6% / 30d 80.6% = at baseline → entry quality, not exits
- 24h 13T 10W 76.9% `+0.60` GREEN · 7d 122T `-0.41` · 30d 691T `-1.99`
- No NEW uncovered sub-50% n>=15 signal (all killed / disabled / dived / CONF_FLOOR / CEO)

## WATCHDOG TRIAGE
- 0 top-level steers. BTC #16395 LONG HOLD re-VERIFIED IN CANDLES: **113 consecutive 1m
  closes ABOVE EMA300** (close 80631 vs 80505) → exit condition (15+ min below) NOT met.
- Arm-time steer (raise SL 79427→80476 at arm 80960): price 80631 < arm — not yet actionable.
- Mid-band-long steer's EMA300 condition has LAPSED (was keyed on BTC below EMA300) →
  expect automatic retraction next cycle; RSI-band half still re-measures Oct 27.

## STANDING VERIFIES
- #141 source stamp **PASS** — first post-15:15Z trade BTC #16395 (15:47) carries
  `_signal_metadata.source='continuum-trend+'` (bb-bounce solo-vs-confluence unblocked).
- #142 [TRAIL] trade_id: activation lines carry trade_id (PURR 16393 / AVAX 16394), floors
  sane positive dist=0.20. #135 spider tiers WORKING (no zero/negative floors).
- #134 hotset MONITOR stays CLEARED — fresh 16:33 with 2 tokens (cycle 10062).
- Gate census **0 LEAK** (ALLOW 10 / WAIVER 19 / PATH-EXEMPT 16 / PRE-RULE 56).
- UGB-PT live fire today: HYPE #16383 `ugb_pt +0.16`.
- Kill flags: AI_TRADER/VB+/HMACD±/OVERSOLD/DOJI all False; PUMP_CHAIN_V5_SHORT True (design).
- size-reduce: `vacation_size_reduce.json` absent = **1.0x** (file truth). vacation_mode ON,
  no_signal_enable_disable ON, unclog waiver expires **2026-10-27T00:00Z**.
- Tracebacks today: 0 new (signal-compactor IndentationError last Oct 24 08:50, file
  compiles OK; 03:00 self-healing FAIL = Sunday pre-fix line, SKIP guard shipped 09:46).
- Side-find ANSWERED: confluence-gate `regime=` label = per-token 1m linreg
  (`get_regime_1m`, signal_compactor.py:378) vs scanner's 5m regime — different source AND
  message-only in that branch (block reason is single-type); APT later logs SHORT_BIAS
  same-day → **benign, no bug**. Watchdog's open question closed.
- Shadow 2/5 usable (contrarian join live, main shadow book); oscillator frozen; wyckoff
  (304) / floor (1861) fresh but pending outcome join; rr orphaned (Oct 4).

## CEO QUEUE
1. **CONF_FLOOR fk ruling** — fkA 22.2% > 20% bar, held.
2. **Oct 27 cluster**: waiver expiry + mid-band re-measure + [35,45) waiver re-measure +
   pump-chain- PROMOTE (flip 64.1% n=344).
3. ~~Post-arm floor D=0.20 GO~~ **CLOSED this run — already live (UGB-PT + PM trail),
   residual tightening 0.30→0.20 = `+0.12`/30d noise → MONITOR.**
Escalation #17: **CLOSED (superseded by live UGB-PT)** — stop listing as awaiting GO.
