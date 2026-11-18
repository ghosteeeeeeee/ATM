# Current State — brain_auditor #275 2026-11-18 04:55 UTC
**Last Updated: 2026-11-18 04:55 UTC**
**Updated by: brain_auditor #275. Prior: #274 2026-11-18 01:10 UTC (preserved in git history).**

## HEADLINE — #274 FIXES VERIFIED LIVE; LONG-ARM TRIPWIRE 4TH CYCLE; IOTA TRAIL-ARM SOURCE DISCREPANCY

1. **#274 verify ALL PASS:** recovery_replay selfcheck exit=0 (14d 20/61/11) · hl_copy is_open fix = 0 hold<5s post-fix vs 5 prior · contrarian join re-ran 04:31Z mandate · shadow_disposition selfcheck PASS · constants EMPTY · lock absent · size-reduce 1.0x · 0 Tracebacks.
2. **LONG arm-rate tripwire BOTH LEGS again:** 7d LONG **44.7%** (21/47) <50 AND SHORT **55.7%** >55 — CEO FLAG with leaderboard (ai-trader -0.29 / rider -0.21 / r2v2 -0.19 unarmed), NO auto-config (4th cycle).
3. **IOTA #16970 MED side-find:** candle MFE **+0.60%** (>=0.40 arm) but `highest_price`=+0.27% and `trailing_activated=False` — PM feed vs candle disagree; 05:15Z exit steer may false-fire. HOLD per candle-armed logic; verify trail state before 05:15Z.
4. **exitstack KPI still FAIL:** trailing-30 avg loser **-0.1007** vs bar -0.070; EX-manual -0.0879 (worse than #274's -0.0822). Dual-read awaits CEO.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d | 14T 57.1% **+0.16** / 108T 49.1% +0.46 / 207T 49.3% -1.38 / 660T 50.8% -4.90 |
| armed vs never 7d | ARMED 55T 83.6% **+4.19** vs NEVER 53T 13.2% **-3.73** |
| armed vs never 14d | ARMED 103T 86.4% **+6.55** vs NEVER 95T 10.5% **-7.61** |
| chop-bleed dollar | 7d **81.4%** (41/49) · 14d **87.4%** · 30d **90.9%** (259/299, +10.3pt vs baseline) |
| LONG arm rate 7d | **44.7%** (21/47) — tripwire trip; prior7d was 50.0% |
| 14d exits | profit-monster 67T 95.5% **+3.82** · mfe_exit 14T 100% +0.84 vs atr_sl 36T 0% **-4.16** · hard_max 24T 0% **-2.61** |
| trail+mfe family 14d | **87T 94.3% +5.12** |
| 24h losers | **6/6 LONG**, mid-band, 5/6 atr_sl_hit, 5/6 never-armed |
| sub-50 14d n>=15 | only ai-trader-pending 36T 33.3% net **+0.19** (CEO) — 0 kill candidates |

### 2. AUTOPSY (24h cluster + recovery_replay)
- recovery_replay 14d selfcheck PASS: 92 losers = 20 never-adverse / 61 recovered / **11 NEVER (11.9%)** → WRONG-SIDE REFUTED **126th** (#61 p=0.116, #84 t=-0.04).
- GRASS LONG #16967: entered against btc_trend_quality=STRONG_DOWN, rsi 46.3, EXTREME vol → price 0.394→0.390 after exit. Winning side SHORT. Coin-regime counter already COLLECT p=0.126 (#179).
- 24h all-LONG mid-band never-armed = same chop class as standing tripwire.

### 3. DEADLINE + AMPLIFY
| Entry | Verdict |
|---|---|
| amplify-vb-high-short-underdeploy | **CLOSED NO CHANGE early** — gate_shadow: major blockers all negative would_pnl = quality filters; cell healthy 20T +0.49; underdeploy = fire-rate not plumbing |
| amplify-warrior-sr-normal-long | PRE-READ: still n=6<10, 2d to deadline → default NO SHIP |
| compaction-stale / hotset-pin | CEO-owned, due 11-20 |

**Flip-KPI 0 this week** (no new shadow cleared a ship bar). All 6 n>=10 net>0 30d cells already carry open amplify entries — why-not logged.

### 4. LAST-RUN VERIFY (#274)
- recovery selfcheck **PASS** exit=0 | hl_copy hold<5s **0 post-fix** vs 5 prior | contrarian join **04:31Z fresh** (overall 45.8%) | floor **FAIL p=0.1538 stands** | shadow_disp selfcheck **PASS** | checkpoint_registry **0 pending** | lock **absent** | constants **EMPTY** | size-reduce **1.0x** | gate_shadow_health **OK 0.98** | exitstack dual-read **NOT implemented** (CEO pending).

### 5. DRIFT / SIDE-FINDs
- **MED (new):** IOTA PM highest_price vs candle MFE disagreement (trail-arm source).
- **MED (carried):** exitstack KPI manual pollution · outcome joins producer-less · wyckoff join unbuilt · meta-vs-continuum stamp · freq_deviation orphan.
- **NEW creative:** PM/candle MFE reconcile · freq_deviation→watchdog steer · LONG arm leaderboard rotation.

### 6. READINESS (2026-11-18 04:55 UTC)
**1 open IOTA LONG r2v2-long3 #16970, candle MFE +0.60% armed-by-candle, PM not armed — HOLD, verify trail before 05:15Z.** Regime: BTC BELOW EMA300 (-0.18%, 64464 vs 64581), 15m SHORT_BIAS aggregate / 4h LONG_BIAS, vol LOW, continuum AT→BELOW. No fresh mid-band LONGs while below EMA300; trail-family first; size 1.0x.

**Queue:** **05:15Z IOTA trail verification** → **11-20** vb-disposed(done) + warrior + compaction-eval + hotset-pin → **11-21** bb-squeeze-module + r2v2 + jup-walk + atrtrail + prearm-BE + cell-tilt + structure-flip + slope-jup + pcv6 + ceiling-85 → **11-22** ai-trader cell + win-side-capture → **11-25** watch-contrarian + pcfade → **12-02** pc-normal-short-early.
CEO: **LONG arm 4th-cycle flag** · exitstack dual-read · slippage BUILD #1 (14th) · hl_copy over-fire · fade-size/fee.
