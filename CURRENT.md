# Current State — brain_auditor #201 2026-10-30 04:45 UTC
**Last Updated: 2026-10-30 04:45 UTC**
**Updated by: brain_auditor #201. Prior: #200 2026-10-30 00:45 UTC (preserved in git history).**

## HEADLINE — Watchdog 'overbought longs bleed' partially REFUTED (65-75 LONG positive);
## real bleed 45-55 LONG fails block bars (already owned); chop-bleed run 2 at 94.8%;
## contrarian join verified; 1 bugfix commit (decider ctx guard)

0 trading-constant changes (hermes_constants.py EMPTY diff, CEO_PROTECTED 13/13,
size-reduce absent = 1.0x), **1 bugfix commit (decider_run.py ctx.get AttributeError
guard — uncommitted F3-1 fix found in working tree, defensive isinstance, zero trading
behavior), 2 creative entries.**

### 1. RSI BAND ANALYSIS — WATCHDOG PATTERN CORRECTED
14d bands: 65-75 LONG = 43T 55.8% **+0.44 (POSITIVE)** — bb-squeeze+ drives it (17T
+0.43). Real bleed = **45-55 LONG 62T -2.30 37.1%** (biggest band) and 55-65 LONG
55T -1.41. Block counterfactual for 45-55 LONG: 7d Fisher p=0.62 FAIL, 30d p=0.34
FAIL, halves sign-flip (old +1.11 / new -2.29) → **ALREADY OWNED by
eval-midband-long-4564** (self_learner, deadline 11-03). Do NOT re-propose.
Money band confirmed: 35-45 SHORT 40T 55% +0.59 (CRV grind-breakout- RSI 42.9
+0.75 tonight = the template).

### 2. CHOP-BLEED RUN 2 OF NEW STREAK — 94.8%
7d: 52/60 losers never armed (-5.44 of -5.74) = 94.8%. Was 95.0% at #200 (run 1).
Checkpoint registered for run 3 at 08:30Z: if breached again, present #194 0.75x size
proposal WITH fresh #195 74%-inert measurement (pre-registered protocol #196).
Root cause unchanged: never-armed chop entries — owned by MFE-CUT/TAT/CONF_FLOOR stack.

### 3. CONTRARIAN JOIN VERIFIED (re-ran 04:30Z, fresh)
pump-chain- flip-WR **64.6%** (226/350 decided) STANDS. btc-pump-rider+ 26.7% (136/510)
= do NOT flip. Overall 42.0% n=861. Oct-27 PROMOTE verified with fresh data.

### 4. WINNER CELLS + DRIFT
All n>=10 validated cells already at 1.25x (WINNER_CELLS_VALIDATED).
pump-chain+ EXTREME 14d drift **WORSENED -0.39 → -0.88** (30d still +2.58). 11-10 bar
(>=+$1.00 delta) will judge. T sign-off stands — do NOT revert unilaterally.
bb-squeeze+ NORMAL recovering: week of Oct 26 = 20T 75% +0.45 (best since Oct 11 RSI
filter). The 1.25x winner-cell will amplify a recovering signal.

### 5. LOSING AUTOPSY (adverse-first, ASSERT PASS)
48h n=18 = 4 never-adverse / 12 recovered / **2 NEVER** (BTC continuum-trend- SHORT
cut-loser -0.18, NXPC volume-buildup- SHORT cut-loser -0.14) → **WRONG-SIDE REFUTED
126th consecutive run** (#61 p=0.116, #84 t=-0.04 stand).

### 6. CREATIVE x2
1. Clone-hunt: gate_shadow blocked setups matching bb-squeeze+ NORMAL winner profile
   (CONFLUENCE-EXPIRY blocks 13873 at 48% would-win — free offense, no config risk)
2. pump-chain+ EXTREME auto-revert trigger at 11-10 deadline (prevent amplifying
   decaying cell)

### 7. COMMITTED
decider_run.py ctx.get AttributeError guard (uncommitted F3-1 fix found in working
tree, defensive isinstance checks, compile PASS, zero trading behavior) +
bb-squeeze candidate backtest stat refresh (auto-regen 03:20Z). Commit 7f3c6c4a.

### READINESS
Open: CAKE pump-chain+ LONG entry RSI 70.83 EXTREME (overbought-long pattern —
watchdog's exact class). SL 1.871 TP 1.932. Monitor trail arm. Regime: chop pin
(15m LONG_BIAS vs 4h NEUTRAL), LOW vol, CALM. No fresh mid-band directional entries.
Size 1.0x. Escalation #17: CEO-GO-blocked (settled). eval-midband-long-4564 due 11-03.
