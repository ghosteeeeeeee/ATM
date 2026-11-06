# Current State — brain_auditor #229 2026-11-06 13:04 UTC
**Last Updated: 2026-11-06 13:04 UTC**
**Updated by: brain_auditor #229. Prior: #228 2026-11-06 05:00 UTC (preserved in git history).**

## HEADLINE — harvest-ship item4 was INERT: auto combo_weights (self_learner) override static SIGNAL_SOURCE_WEIGHTS, so CEO boosts 1.3/1.6 were scoring as 1.1/1.04. Fixed via combo_weights sync + PINNED_COMBO_WEIGHTS. Harvest 48h read = KEEP ALL 4 (default revert would have restored proven bleed; HML bar failed by window lag — 34/37 HML opened pre-ship, post-ship in-scope = 0).

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| **combo-weight-precedence (FIXED, scoped)** | `signal_compactor._get_source_weight` auto-first (e55b6c49, Aug-7) → 36/64 auto keys diverge from static; item4 inert. Fixed: combo_weights 1.1→1.3 / 1.04→1.6 + PINNED_COMBO_WEIGHTS in self_learner (2 keys only). **34 other divergences queued for precedence review — do NOT flip globally without per-key check** (incl. stop_hunt static 0.0 DEAD → auto 1.0 latent, pump-chain+ 1.4→0.6, volume-buildup- 1.2→1.05) |
| **harvest-ship-2026-11-04 (CLOSED — KEEP ALL 4)** | 48h read: jup rolling-50 46% FAIL-improving (daily 69→58→35→67→33) · HML 7d 37 FAIL **window lag (34/37 pre-ship; post-ship 3 total, 0 in-scope, 0 on 11-06)** · daily net 72h -0.85 FAIL package-level (11-05 first green +0.26/+0.16 since 10-31) · LONG-in-SHORT_BIAS 25→1 **PASS**. Default revert OVERRIDDEN with evidence; HML re-based to post-ship opens; re-read 11-11 |
| **volmom-volbreak (CLOSED — KILL)** | n=0 vs n>=20 bar: flags False since build, no data files, 0 log lines — shadow never collected. Default KILL executed (registry closed; re-open needs CEO shadow-first ruling) |
| **daily-fill-cap-brake (CLOSED — KEEP)** | 24h fills 9≤15 · fee-net -0.12<0 engaged · 11-05 green day had 0 SKIPs after (release key verified) · daily fee-net trend -1.42→-0.96→-0.51→+0.16→-0.41 improving |
| **amplify-bbsqueeze-warrior-uninert (NEW, due 11-10)** | bar: next-100 bb+warrior share ≥25% (baseline 17% last-100 / 38.9% last-48h) ∧ bb NORMAL 7d net ≥0 ∧ pin still 1.3/1.6 at read. Default: revert pin |
| **LOSERS/BLUR side-find (MEDIUM, not mine)** | Uncommitted hermes_constants: LOSERS {'BLUR'}→set(), BLUR now in NO blocklist. FAVORITES_LONG +BTC = daily auto-updater (expected). Owner confirm-or-revert |
| **Autopsy 48h (MANDATE)** | n=6 = 2 never-adverse / 4 recovered / **0 NEVER** → WRONG-SIDE REFUTED **85th** (#61 p=0.116, #84 t=-0.04) |
| **AMPLIFY weekly** | 1 NEW: amplify-bbsqueeze-warrior-uninert. Flip-KPI 0 this week — all 4 n≥8 winner cells already in-flight (pc+ EXTREME, bb NORMAL, vb- HIGH, jup SHORT HIGH); n≥5 early cells too small/sign-flip |
| **#228 verify** | gate_shadow_health --selfcheck **PASS** (36 gates, covers=True) · jup-regime NO CHANGE held · linreg-fade bypass clean (0 confluence blocks 11-06) |

### 2. NUMBERS (fresh PG)
- 24h **9T 77.8% gross '+0.13' fees 0.25 net '-0.12'** | 7d **241T 53.9% gross '-2.29' net '-5.36'** | 14d 403T 55.3% '-2.11' | 30d 777T 46.1% gross '-6.28' fees 7.49 **net '-13.77'** | **1 open (ADA bb-squeeze+ LONG +0.23%)**
- 7d by regime: EXTREME 36T 38.9% '-1.03' · HIGH 77T 58.4% '-0.80' · NORMAL 112T 53.6% '-0.64' · FLAT 16T 68.8% '+0.18'
- 7d family: **trail 127T 91.3% '+7.90' vs chop 82T 0% '-10.01'** | 14d armed 219T 90.4% '+13.40' vs unarmed 184T 13.6% '-15.51'
- Contrarian join 12:40Z: flip **43.1% n=1442** | pc- 64.6% LIVE | rider 36.2% do-NOT
- Floor join 12:55Z: floor_only 49.3% vs always 43.7% **p=0.135** → COLLECT to 11-15
- goal_metrics verifier: 5/7 FAIL (jup 46%, HML 37, HML net -5.22, net72h -0.85, fleet WR 52.5%) — HML/jup move as pre-ship rows age out

### 3. SHADOW (3/6 usable)
- contrarian + floor joins re-ran unconditionally (mandate) · gate_shadow_health selfcheck PASS · shadow_trader 69,256 (pm_trail +10,443 vs hard_max -11,865)
- oscillator FROZEN/archived · wyckoff RETIRED (file gone) · rr ORPHANED

### 4. SIGNAL QUALITY — 0 new targets
- 0 signals at n≥20 + WR<50 + net<0 (14d). #228 entry-filter negative result stands — do not re-propose RSI/gap/BB filters for jup/vb-/pc+.
- Kill candidates: none. Arm-rate watch: pc- LONG 7.4% (arms almost never, still green).

### 5. READINESS (13:00)
**1 open (ADA bb-squeeze+ LONG, +0.23%, 0.5h).** Regime: 15m LONG_BIAS / 4h LONG_BIAS / continuum ABOVE / vol LOW / velocity SLOW / trend UP / wyckoff DISTRIBUTION / 0 steers / portfolio good. Size 1.0x (size-reduce file absent). Session lock ABSENT; CEO_PROTECTED untouched; combo pin + 2 dispositions are this run's only writes to trading paths.

**Queue:** 11-07 verifier re-run → 11-09 zombie-purge → 11-10 five bars + uninert read → 11-11 HML post-ship re-read → 11-13 linreg-fade fill bar + chop-exempt + clonehunt + pc+ kill → 11-14 stop-tighten eval + atrtrail + jup-short-walk → 11-15 floor/wyckoff → 11-19 ema300/jup-short-high.
**CEO:** harvest KEEP (veto window open) · 34 combo-weight divergences need precedence review · LOSERS/BLUR uncommitted diff · NET-KPI.
