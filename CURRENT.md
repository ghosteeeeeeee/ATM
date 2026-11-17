# Current State — brain_auditor #273 2026-11-17 16:55 UTC
**Last Updated: 2026-11-17 16:55 UTC**
**Updated by: brain_auditor #273. Prior: #272 2026-11-17 00:54 UTC (preserved in git history).**

## HEADLINE — 11-18 DEADLINE BATCH CLOSED: 8 DISPOSITIONS, 0 SHIPS, PC-FADE NEWER HALF DECAYED TO 51%

1. **8 due-11-18 dispositions adjudicated:** 2 EXTEND (watch-contrarian, pcfade → 11-25),
   5 CLOSED/NO-SHIP (xmirror, hml, clonehunt, ugb, jup-flat, grind), 1 NO-RE-PROMOTE (pcfade).
2. **3 shadow collectors were never built** — xmirror-giveback, hml-vol-atr-0.35 (and their
   bars were unreachable anyway) → closed with why-not, not silently drifted.
3. **pcfade newer half 63.2% → 51.0%** while overall stays 66.7% — aggregate hides decay;
   demote-tripwire pre-registered (creative #1). Fee gate NET -$0.209 still blocks re-promote.
4. **Clonehunt screen bug caught live:** row-level DISTINCT read n=295 vs true GROUP-BY
   token|day n=52 (5.7x) — dedup contract added as creative #2.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d | 21T 61.9% **+0.27** / 113T 48.7% +0.28 / 217T 49.8% -1.28 / 661T -4.72 |
| armed vs never 7d | ARMED 57T 84.2% **+4.31** vs NEVER 56T 12.5% **-4.03** |
| armed vs never 14d | ARMED 112T 85.7% **+7.14** vs NEVER 105T 11.4% **-8.42** |
| chop-bleed dollar | 7d **82.5%** (44/52, $4.28/$5.19) · 14d 87.2% — under 92% gate |
| 14d exits | profit-monster 71T 95.8% **+4.22** · mfe_exit 18T 100% +1.09 vs atr_sl 37T 0% **-4.25** · hard_max 33T 0% **-3.58** |
| 24h losers n=7 | SOL jup chase (-0.25% pre-entry) · STX+ALGO atr-trend- shorted into +0.6% strength · hl_copy phantoms · BTC ai-trader CEO |
| exposure KPI | 24h **30.4%** in-market (21 trades) |

### 2. DEADLINE BATCH (full text in data/shadow_disposition.json)
| Entry | Verdict |
|---|---|
| watch-contrarian-live | EXTEND 11-25 — 38 fills, NET -$0.209 fee-negative |
| amplify-pcfade-windowfix | NO-RE-PROMOTE + EXTEND 11-25 — bars i/ii PASS, iii/iv pending CEO |
| amplify-xmirror-giveback | CLOSED NO-CHANGE — collector never built, n unreachable |
| hml-vol-atr-mult-shadow | CLOSED keep-0.5 — collector never built, -32% HML drop confounded |
| amplify-atr-trend-short-clonehunt | NO-SHIP — n=52 PASS but would-win 69.2%/net +0.17/fk 30.8% all FAIL |
| amplify-ugb-bypass-armgap | CLOSED — n=6/30d, n=0/14d << 20 |
| amplify-jup-long-flat-cell | CLOSED noise — n=8<10 |
| amplify-grind-breakout-underdeploy | CLOSED shadow-noise — dedup n=2<<15 |

### 3. AUTOPSY + SHADOW
- **48h recovery_replay (adverse-first, ASSERT PASS): n=16 = 2 / 11 / 3 NEVER**
  (ALGO atr-trend- x2, WLD hl_copy) → **wrong-side REFUTED 124th consecutive run**
  (#61 p=0.116, #84 t=-0.04). 14d: 101 losers = 24/66/11 = 10.9% structural.
- **Contrarian join RE-RAN 16:31Z (mandate):** overall 46.1% n=1830 | **pc- 66.7% LIVE** |
  rider 44.7% do-NOT | het p=6e-35 → per-signal only.
- floor fresh 12:34Z p=0.1538 same_sign FAIL | shadow_trader 16:46Z pm_trail +17,330 vs
  hard_max -22,237 | oscillator archived / wyckoff PENDING / rr ORPHANED → 3/6.

### 4. AMPLIFY (weekly offense)
0 NEW — why-not: all 6 n>=10 net>0 30d cells already carry open amplify entries; early cells
covered or below +0.10; pc- SHORT contradicts live 66.7% fade. **Flip-KPI 0 this week**
(no shadow cleared a ship bar).

### 5. LAST-RUN VERIFY (#272)
- exitstack KPI still holds: trailing-30 post-11-14 avg loser **-0.0693** vs bar -0.070.
- disposition_deadline selfcheck PASS · exposure KPI present (30.4%) · retention guard
  PASS (66.7% stable) · constants diff = favorites_updater ZRO only (not mine) ·
  0 Tracebacks · checkpoint_registry 0 pending · lock absent · gate_shadow_health OK 0.94.

### 6. DRIFT / SIDE-FINDs
- **MED (carried):** outcome joins producer-less · entry_feature_split sample-shrink ·
  wyckoff join unbuilt · session_brain dup rebuild.
- **NEW creative:** pcfade demote-tripwire · gate_shadow GROUP-BY dedup contract ·
  HML drop DiD attribution.

### 7. READINESS (2026-11-17 16:38 UTC)
**0 open / 0 steers / health good — FLAT correct.** Regime: 15m SHORT_BIAS vs 4h LONG_BIAS
disagreement + continuum BELOW + vol LOW + trend STRONG_DOWN + market_phase RECOVERY =
**chop pin → no fresh counter-trend entries; trail-family first; SHORTs only under EMA300
with 4h aligned; size 1.0x.**

**Queue:** **11-20** vb- + warrior re-read → **11-21** bb-squeeze-module + r2v2 →
**11-22** ai-trader cell → **11-25** watch-contrarian + pcfade re-read → 12-01 jup-atrsl.
CEO: jup-atrsl write-path sync · jup-pro-selection margin>=$1k · **fade-size/fee decision
(blocks pcfade+watch)** · flip1 NO-GO ack · NET-KPI.
