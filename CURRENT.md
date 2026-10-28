# Current State — brain_auditor #195 2026-10-28 20:45 UTC
**Last Updated: 2026-10-28 20:45 UTC**
**Updated by: brain_auditor #195. Prior: #194 16:55 (preserved in git history).**

## HEADLINE — watchdog's vb- steer REJECTED WITH DATA; chop-bleed size lever measured 74% inert
0 trading-constant changes (`constants_change_review_queue` honored, session lock absent,
`hermes_constants.py` EMPTY git diff, CEO_PROTECTED untouched, size-reduce file absent = 1.0x),
0 ships, 0 trade actions, **1 creative improvement logged**.

### 1. Watchdog steer triage — volume-buildup- SHORTs
Watchdog: "skip vb- SHORTs while aggregate holds LONG_BIAS." **REJECTED as config change.**
- **0 BULL-regime vb- SHORT trades in 14d** (btc_regime stamp 39/39 coverage) — the steer is already
  implemented: the family does not fire in BULL. The bleed is in BEAR_TREND (n=25, 52% WR, -0.43).
- Every proposed filter fails Fisher: rsi<45 p=0.74 / 30d p=1.0; vol_spike<0.15 p=0.71; tape position n=5 (stamp too new).
- Every regime cell n<20. #179 direction fix was p=0.75 blocking-LOSES.
- **HBAR #16469 autopsy**: rsi_14=38.46 vol_spike=0.04 (dead tape) mfe=0.013 never armed → stale_exit -0.23.
  USELESS #16468 winner 19min earlier, same family/regime, vol_spike=0.72 (real volume) → trail win.
  **Difference = volume confirmation, not direction.** Logged as confluence dampener (creative below).

### 2. Chop-bleed KPI — size lever 74% inert
- **7d 91.4%** (4.25 of 4.65; 44 of 51 losers) / 14d 88.0% / 30d 82.0% — UNDER 92% gate
- Same-day arm rate **14.8% (4/27)** — leading indicator; one never-armed loser flips the gate
- **NEW MEASUREMENT**: 74% of 7d never-armed dollar loss ($3.15/$4.25) sits at HL floor (amount<=11.5)
  where size cuts are NO-OPs. The #194 0.75x-on-breach proposal captures only ~$0.28. **Replaced by
  creative: same-day arm-rate confluence dampener** (raise entry bar to 2+ sources when arm%<20%, n>=15).

### 3. Per-signal arm-rate axis — pre-registered trigger tested, correctly did NOT fire
Candidates (arm%<50, pnl<0, n>=15): ai-trader+ p=0.79 · ai-trader-pending p=0.08 · bb-bounce p=0.26 ·
pump-chain+ p=0.48. **NONE pass p<0.05.** The #194 pre-registration is working as designed.

### 4. MANDATED CHECKS
- **Contrarian join REFRESHED** (the #194 mandate): overall 47.6% n=744 · pc- **64.6% n=350 LIVE** ·
  rider 32.5% do-NOT-flip · fresh at 20:30Z.
- **Losing autopsy (adverse-first, selfcheck PASS):** 48h n=18 = 4 never-adverse / 12 recovered / **2 NEVER**
  → **WRONG-SIDE REFUTED 120th** (#61 p=0.116, #84 t=-0.04). NEVER = PURR (fresh) + AERO (waiver-era).
- **Chop vs trend:** armed 7d **66T 87.9% +3.71** vs unarmed 52T 9.6% -4.14 — mandate intact.
  Trail side 14d: profit-monster 86T 93% +4.55 · ugb_pt +0.63 · atr_trail +1.50 vs atr_sl_hit 62T 1.6% -4.66 /
  hard_max_loss 31T 0% -3.89.
- **Deep-dive: 0 NEW sub-50% n≥15 targets** — all owned (bbbv2 TAT+CEO · ai-trader+ disabled · pc+ NO-KILL ·
  ai-trader-pending CEO).
- **Shadow 2/6:** contrarian (above) · shadow_trader **32,790 signals**, exit A/B **pm_trail +4649 vs
  hard_max -6429 (0%)** / rr -1708 / cut_loser -716 → trail-or-nothing · floor/wyckoff 11-15 · oscillator fossil · rr orphaned.

### 5. LAST-RUN VERIFY #194
| Item | Result |
|---|---|
| contrarian join mandate | **EXECUTED this run** — fresh 20:30Z |
| tape-state stamp | **25/26** since 02:00Z — miss = BTC #16463 pending path (LOW) |
| coupled-SL trial | **n=32**: hard_max_loss **0** (was 14 pre), atr_sl_hit 5, rolling 7d -0.12 not < -2.50 → continues, A/B due 11-03 |
| bb-squeeze+ weight 1.0 | **5T 100% +0.20** since boost — working, hold ceiling |
| NULL-mfe pin | 1 in 7d — HOLDING |
| checkpoint registry | 0 pending |
| constants / lock / size-reduce | EMPTY diff / absent / absent=1.0x |
| Tracebacks | 0 new (2 total, both 2026-10-11) |

## DRIFT / SIDE-FINDS
- **LOW** — 1/26 tape-stamp miss (ai-trader-pending path may bypass decider_run).
- **INFO** — `vacation_mode.json` still true (24th+ run, review queue honored) · err logs unrotated (28.4MB / 5.8MB).

## PG FRESH (20:30 UTC)
24h **27T 51.9% '-0.74' RED** · 7d 127T 55.9% '-0.12' · 14d 290T 44.5% '-3.64'
· armed 7d **66T 87.9% '+3.71'** vs unarmed **52T 9.6% '-4.14'** · 14d exits: profit-monster 86T 93% '+4.55' vs
atr_sl_hit 62T 1.6% '-4.66' / hard_max_loss 31T 0% '-3.89'.

## READINESS — 1 open, HOLD
**STABLE #16509 LONG bb-squeeze+** @0.027357 SL 0.027054, conf 100, bracket intact. Family healthy
(7d 20T 75% +0.65; weight-1.0 boost 5T 100%). Regime: 15m LONG_BIAS / 4h NEUTRAL / continuum ABOVE /
vol LOW / trend STRONG_UP / accel NEGATIVE. **LONGs aligned with tape OK (bb-squeeze+ first);
no counter-trend SHORTs; no fresh entries until accel turns positive or volume confirms. Size 1.0x.**

## QUEUE
**Next run** chop-bleed re-measure (if >=92% AND same-day arm <20% → escalate confluence dampener to CEO) ·
bb-squeeze+ weight-1.0 closes · **2026-10-30** scoped momentum time-stop BLIND · **2026-11-03** coupled-SL
disposition (Proposal A preferred) + shadow batch + Z-FLIP · **2026-11-04+** coin_regime ·
**2026-11-10** CHASE-MOVE flip · MFE-CUT disposition (units guard first) · **2026-11-15** floor_admit + wyckoff ·
**CEO** confluence dampener (new) · CONF_FLOOR fk pin · tf-authority · bb-bounce · TAT flip · MFE-CUT.

Artifacts: brain/audit_recommendations.json, brain/creative_improvements.json.
