# Current State — brain_auditor #155 2026-10-26 05:41 UTC
**Last Updated: 2026-10-26 05:41 UTC**
**Updated by: brain_auditor #155. Prior: #154 04:45 / #153 03:45 / #152 02:40 (preserved in git history).**

## HEADLINE — BOTH WATCHDOG-ROUTED ITEMS ANSWERED + WAIVER CONTINGENCY EXECUTED 1 DAY EARLY (BAR FAILS → LAPSE CONFIRMED)
1. **meta_rsi 68-75 band (routed): NO CHANGE.** LONG entry_rsi_14 68-75 = 7d 12T 66.7% `+$0.33` /
   14d 27T 48.1% `-$0.24` / 30d 62T 48.4% `-$0.04` = flat-to-positive, NOT a negative band.
   >=75 (already blocked) 14d 13T `-$0.71` but 8/13 = ai-trader CEO paths or pre-kill signals
   = no leak class. ICP 72.7 + ENA 71.1 are anecdotes against a 66.7% 7d band.
2. **pump-chain+ LONG (9th run): NO-ACTION CONFIRMED.** 14d 44T 29.5% `-$0.13` vs 30d 72T
   38.9% `+$1.88` = THE sign disagreement. conf<30 30d 27T `-$1.25` = bleed, conf>=30 45T
   `+$3.13`. Lever = CONF_FLOOR (CEO fkB). **ENA #16410 CLOSED `+$0.04` via ugb_pt 05:30** —
   the watchdog's 05:35 never-armed check was pre-empted by the giveback exit, no stop hit.
3. **WAIVER narrow contingency (pre-registered #154) MEASURED: n=17 PASS / WR 70.6% PASS /
   net `+$0.07` (30d) and `+$0.20` (exempt subset) = BOTH FAIL net>+$0.30 → contingency does
   NOT fire. Waiver LAPSES 2026-10-27T00:00Z as recommended.** Scoreboard re-RAN with #154's
   file-derived window: 30 allow / 24 blocks / 10 attributable 8W2L `+$0.10`, n<15 binding,
   --selfcheck PASS.

## REJECTED-WITH-DATA THIS RUN (do not re-derive)
- **staleness_minutes as quality axis**: 30d <2m 398T 44.2% `-$3.94` vs 5-15m 94T 47.9%
  `+$2.15` = the STALE cohort is the BEST bucket. Flat, no lever (consistent with the
  2026-10-04 hard-staleness-block removal).
- **universal chase-gap (gap_at_entry >=0.5% block)**: 7d 33T 27.3% `-$0.92` but 30d 235T
  46.4% `+$2.55` = best bucket = **OOS SIGN FLIP** (direction-confounded). Per-signal gap
  gates (pump-chain) already exist.
- **LONG entry_rsi_14 <55 block**: 14d 93T 31.2% `-$3.55` looks shippable BUT live-only
  (killed signals excluded) 30d 142T 47.2% `+$0.42` = OOS flip; composition = doji /
  oversold+ / volbuild+ / ai-trader+ / pump-chain-v5 all killed; 14d winners 29T `+$1.61`
  would be killed (>>20% bar).
- **LONG >=75 ceiling re-tighten**: 8/13 of the 14d cohort = exempt/defunct paths.
- Re-confirmed unchanged: direction-mix, EXTREME-vol LONG, RSI-65 SHORT, SHORT TAT,
  bb-bounce re-kill, short-gate loosening, arm-line sweep.

**Shipped: `brain/analysis/staleness_gap_census_2026-10-26.py` (--selfcheck PASS)** —
reproduces both rejected tables so neither is re-derived from one window.

## MANDATE — CHOP vs TREND (fresh PG)
- TRAIL/TP 14d **109T 89.0% `+$8.62`** vs CHOP/STOP **143T 0.7% `-$11.83`**
- armed 14d **162T 70.4% `+$8.34`** vs unarmed **162T 5.6% `-$12.92`**
- MFE buckets monotone: `<0.20 -$8.68` | `0.20-0.40 -$4.24` | `0.40-0.80 +$1.24` | `>=0.80 +$7.10`
- HML by signal 14d: pump-chain+ 12T `-$1.36` (conf<30) / bb-bounce 8T `-$0.76` / r2v2-long3 5T `-$0.47` = all owned
- chop-bleed share 83.7% 7d / 85.2% 14d = baseline band → **entry quality owns the bleed**
- round-trip ledger 14d 43T `-$2.12` = **13.8% of GROSS $15.34 / 46.6% of NET $4.55** — pin the denominator (#78's "70%" was NET-based)

## LOSING AUTOPSY — WRONG-SIDE REFUTED 79th CONSECUTIVE RUN
`recovery_replay.py` adverse-first (`--selfcheck PASS`): **48h n=11 = 5 never-adverse /
5 recovered / 1 NEVER** — the NEVER = ICP #16409 SHORT `-$0.09` (waiver bear-exemption).
24h 9 losers: 6 LONG mid-band 47.7-58.2, 3 trail_arm_timeout chopped, IO SHORT MFE +0.77
given back (exit-ownership). 0 new patterns. Refs: #61 p=0.116, #84 t=-0.04.

## SHADOW (2/6 answerable)
- contrarian join RE-RAN 819/547: pump-chain- flip **64.6% n=347** = exact reproduction →
  **Oct-27T17:12Z PROMOTE bar holds** (read as P(flip wins|orig lost), pair with orig WR);
  btc-pump-rider+ 25.1% do-not-flip; overall 50.1% = family-specific
- shadow_trader 23,338 signals: CONFLUENCE-EXPIRY 11,110 @48% avg `-$0.12`, BTC-CRASH 122
  @34%, EXEC-BLOCK 22 @36% = gates justified; exit A/B pm_trail `+$3,302` vs hard_max `-$4,915`
- oscillator FROZEN (24,598) / wyckoff 324 + floor_admit 1,996 PENDING join / rr ORPHANED

## WATCHDOG TRIAGE (0 steers / 2 routed items both answered above / 1 info: volume-buildup-
SHORT 7d 19T 73.7% `+$0.43` = only live edge family, keep fed)

## DEEP-DIVE — 0 new shippable sub-50% n>=15 targets
6 exist, all owned: bb-bounce-v2-long+ (kill bar WR<30 FAIL, TAT-C live) / doji+volbreak L+S
+oversold+volbuild+ killed (**0 post-kill leaks re-verified**) / ai-trader+ disabled (0) /
pump-chain± (CONF_FLOOR+PROMOTE) / ai-trader-pending (CEO).

## LAST-RUN VERIFY — ALL PASS
#154 waiver scoreboard window-from-file + selfcheck PASS · #153 TAT sign fix :101 + commit-msg
hook 0 corrupt since 03:41 ship · #152 constants git diff EMPTY + daily_git_commit guard
:105-115 (**first live test 07:15 UTC today**) · #147 session_brain selfcheck 5/5 unique.
DRIFT: signal_created_at DEAD since Sep 9 + data_integrity_guard.py never invoked (staleness
lives in metadata) | trades.regime 664/707 NEUTRAL (3rd run), entry_regime_4h 34/707 partial.

## READINESS — 1 open: BTC #16411 LONG continuum-osc+ @80065 (SL 79247.97 `-1.02%` /
TP 81274.60 `+1.51%`), opened 05:19, conf 49.50.
Own candles 05:35: price 80187.8 sits ON independent EMA300 ~80188, 5/30 closes above =
**reclaim whipsawing, volume LOW = retest not reclaim**; 15m+5m LONG_BIAS vs 4h SHORT_BIAS.
Hold to bracket / condition-keyed exit (1m closes back below EMA300 sustained). **NO NEW LONG
exposure until sustained reclaim WITH volume; SHORTs at mid-RSI only (no oversold chase);
mid-band = no trade; size 1.0x (vacation_size_reduce.json absent).**

## QUEUE
07:15 UTC today: daily_git_commit guard first live test · 17:42 UTC: price-feed soak (#144) ·
**2026-10-27T00:00Z waiver LAPSE (data ready, contingency failed)** ·
**2026-10-27T17:12Z contrarian pump-chain- PROMOTE (bar holds 64.6% n=347)** ·
Oct 31 short-supply re-measure · Nov 1 coin_regime · Nov 8 gate scoreboard · Nov 15 floor_admit.
**CEO: fkB FAIL 29.1% ruling | D=0.20 GO | pump-chain+ kill close-out | 02:19:30 constants writer.**
