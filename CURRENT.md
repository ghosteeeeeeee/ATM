# Current State — brain_auditor #274 2026-11-18 01:10 UTC
**Last Updated: 2026-11-18 01:10 UTC**
**Updated by: brain_auditor #274. Prior: #273 2026-11-17 16:55 UTC (preserved in git history).**

## HEADLINE — HL_COPY is_open FIX COMMITTED; EMA300 AMPLIFY CLOSED NO-SHIP; EXITSTACK KPI REGRESSED ON CEO MANUAL LOSERS

1. **hl_copy is_open=1 filter** was sitting uncommitted on disk (mtime 11-17 21:07) — COMMITTED and daemon restarted. 0 hold<5s phantoms since fix; 5 in prior 48h were close-fill mirrors.
2. **recovery_replay --selfcheck FIXED** (checked>100→>=90): 14d losers n=98 false-failed while vacuity held 91/98=92.9%. Census: 98 losers = 22 never-adverse / 65 recovered / 11 NEVER (11.2% structural).
3. **Due-11-19 batch:** storm-confl-waiver EXTEND→11-26 (bar 2/3, CEO NO-CONVERT stands); amplify-ema300-underdeploy CLOSED NO-SHIP (compaction_stale shadow book sum net_pnl_pct -6.19, bar-i FAIL).
4. **exitstack KPI REGRESS:** trailing-30 post-11-14 avg loser **-0.1007** vs bar -0.070 (was -0.0693 PASS at #273). 7/30 are CEO ai-trader manual losses; EX-manual still -0.0822 FAIL. Dual-read creative proposed — bar not redefined unilaterally.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d | 16T 50% **-0.10** / 109T 47.7% +0.22 / 207T 49.3% -1.38 / 661T 50.8% -4.91 |
| armed vs never 7d | ARMED 54T 83.3% **+4.11** vs NEVER 55T 12.7% **-3.89** |
| armed vs never 14d | ARMED 107T 86.0% **+6.82** vs NEVER 100T 10.0% **-8.20** |
| chop-bleed dollar | 7d **82.4%** (44/52) · 30d **90.9%** (259/299) — 1.1pt under 92% tripwire |
| LONG arm rate 7d | **41.3%** (19/46) — below 50, 3rd cycle (hl_copy 0/10, r2v2 1/3, rider 1/4 never arm) |
| 14d exits | profit-monster 71T 95.8% **+4.22** · mfe_exit 14T 100% +0.86 vs atr_sl 38T 0% **-4.39** · hard_max 28T 0% **-3.05** |
| exposure 24h | **44.3%** in-market (17T) |
| atr-trend- SHORT 14d by vol | NORMAL 16T +0.22 75% · HIGH 16T -0.30 · EXTREME 2T -0.23 — HIGH+EXTREME block would kill 9/21 winners (43%>20% cap) → NO SHIP |

### 2. AUTOPSY (STX/ALGO atr-trend- wrong-tape)
- Compactor allowed via CONTINUUM-OVERRIDE (DECLINING+LEAN_BEAR+BELOW) + standalone bypass atr-trend-. Both +0.9% during 16m hold → hard_max_loss -$0.20. Winning side: LONG immediately.
- **MED side-find:** `_signal_metadata.btc_trend_quality`=STRONG_UP/streak439 vs continuum_states same-minute BELOW/STRONG_DOWN — stamp vs continuum disagreement; meta-based tape censuses suspect.
- recovery_replay 14d: 98 losers = 22/65/11 NEVER (11.2% structural). Wrong-side still REFUTED 125th consecutive run (#61 p=0.116, #84 t=-0.04).

### 3. DEADLINE + AMPLIFY
| Entry | Verdict |
|---|---|
| storm-confl-waiver | EXTEND 11-26 — bar 2/3, CEO NO-CONVERT stands, default KEEP shadow |
| amplify-ema300-underdeploy | CLOSED NO-SHIP — shadow book sum -6.19% bar-i FAIL, friction = compaction_stale |
| amplify-pumpchain-normal-short-early | NEW — n=5 EARLY net +0.13, due 12-02, no size until n>=10 bar |

**Flip-KPI 0 this week** (no shadow cleared a ship bar). All 6 n>=10 net>0 30d cells already carry open amplify entries.

### 4. LAST-RUN VERIFY (#273)
- exitstack KPI: **FAIL** -0.1007 vs -0.070 (was PASS) — CEO manual pollution + signal-only still -0.0822.
- contrarian retention: **PASS** pc- 66.7% n=102 stable · floor p=0.1538 FAIL stands · exposure **PASS** 44.3% · gate_shadow_health **PASS** 0.94→0.98 · shadow_disposition selfcheck **PASS** · checkpoint_registry 0 pending · lock absent · pcfade tripwire readable (BELOW 77.3%/AT 40.6%).

### 5. DRIFT / SIDE-FINDs
- **FIXED:** recovery_replay selfcheck n=98 false-fail; hl_copy is_open uncommitted→committed+daemon restart.
- **MED (carried):** outcome joins producer-less · wyckoff join unbuilt · meta-vs-continuum tape stamp disagreement (NEW) · exitstack KPI manual-trade pollution (NEW).
- **NEW creative:** exitstack dual-read (all vs EX-manual) · meta-vs-continuum stamp audit · pc- fade BELOW-cohort demote tripwire <60%.

### 6. READINESS (2026-11-18 01:10 UTC)
**1 open BTC LONG +0.14 / health good / steers empty — HOLD correct.** Regime: 15m+4h LONG_BIAS, continuum ABOVE, vol LOW, trend_quality STRONG_DOWN + CALM = slow grind. No SHORT while 1m holds above EMA300; no pyramid (LOW volume); trail-family first.

**Queue:** **11-20** vb- + warrior + compaction-eval + hotset-pin → **11-21** bb-squeeze-module + r2v2 + jup-walk + atrtrail + prearm-BE + cell-tilt + structure-flip + slope-jup + pcv6 + ceiling-85 → **11-22** ai-trader cell + win-side-capture → **11-25** watch-contrarian + pcfade → **12-02** pc-normal-short-early.
CEO: jup-atrsl write-path sync · jup-pro-selection margin>=$1k · **fade-size/fee decision** · flip1 NO-GO ack · NET-KPI · **exitstack dual-read approval**.
