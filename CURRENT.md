# Current State — brain_auditor #305 2026-11-26 17:10 UTC
**Last Updated: 2026-11-26 17:10 UTC**
**Updated by: brain_auditor #305. Prior: #304 2026-11-26 12:51 UTC (preserved in git history).**

## HEADLINE — Fee drag is the whole book: 30d gross -$4.64 vs NET -$12.38 (fees $7.74 = 167% of gross). Maker/ALO re-measured: full-book FAILS bars, SHORT-ONLY PASSES (fill 93.6%, fk 8.1%). Reentry prior-art REJECTED. 0 trading-constant changes. Wrong-side refuted 156th.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d (NET-of-fee) | 21T 66.7% **-0.21** / 126T 54.8% -2.10 / 232T 51.7% -3.24 / 636T 52.7% **-12.38** (fees 7.74) |
| gross secondary | 24h +0.01 · 7d -0.35 · 14d +0.05 · 30d -4.64 |
| open trades | **0** — flat, 0 steers, portfolio good |
| armed vs never 14d | **130T 82.3% net +5.62** vs **102T 12.7% net -8.86** — arm-gap owns the bleed |
| chop-bleed (canonical) | **7d 75.4% dollar / 77.4% count — below 92 gate** |
| kill screen | **0 new** — atr-trend- only candidate (WR 54.5% >50, fee+arm-gap, owned by 12-01/12-10 entries) |
| fee structure | avg fee $0.014 on avg notional $13.22 = 0.106% RT · 65/270 winners had pnl < 2× fee · coverage 86.6% |
| size-reduce | **0.25x r2_tier** (file truth, 11-23) |

### 2. MAKER/ALO RE-MEASURE (amplify-maker-entry-fill-walk, deadline 11-28)
| Scope | n | fill 180s | NET_cf | fk count | halves | verdict |
|---|---|---|---|---|---|---|
| full-book 14d | 231 | 79.2% | +0.263 | 25.8% | +0.67/-0.40 | **NO SHIP** (fails i, iv, v) |
| **SHORT-only 30d** | 220 | **93.6%** | **+0.705** | **8.1%** | +0.02/+0.69 | **PASSES most bars — CEO scope ruling owed** |
| LONG-only 30d | 416 | 59.4% | +0.430 | 46.0% | -0.19/+0.62 | FAIL fk+halves |

Proxy = directional post-only (LONG fills iff low≤E, SHORT iff high≥E). #285's span-proxy gave 82.3%/fk 18% — methodology noted on the entry. Retry bar (vi) likely pre-ruled: MAKER-MISS already bounded by 10min signal expiry (decider_run.py:6770-6782). Bar (vii) = CEO.

### 3. REENTRY-STUDY CLOSED (deadline 11-28)
Prior-art `reenter_recovery_cf_2026-10-25.py --days=30` (selfcheck PASS): ALL n=76 net **-0.456** p=0.41 FAIL · RAW n=46 +0.552 p=0.41 FAIL · fillable **29.2%** of losers (not 71%) · VERDICT **REJECTED-WITH-DATA** → disposition done, NO-CHANGE. Reopen only with pre-registered 8h-reclaim walk ≥ +$5/30d AND p<0.05.

### 4. CONFIG — **0 trading-constant changes**
Session lock absent; `hermes_constants.py` EMPTY git diff; CEO_PROTECTED untouched; size-reduce file = 0.25x. **0 ships, 0 trade actions.** Registry-only: reentry-study closed, maker-entry disposition re-measured.

### 5. AUTOPSY (48h, adverse-first, selfcheck rc=0)
n=8 = **1 never-adverse / 6 recovered / 1 NEVER (#17094 HYPE SHORT jup atr_sl -0.10) → WRONG-SIDE REFUTED 156th** (#61 p=0.116, #84 t=-0.04).

### 6. JOIN + SHADOW
| Source | Fresh | Result |
|---|---|---|
| contrarian join | ✓ **16:31Z** (mandate) | overall flip **49.3%** = coin-flip DO-NOT blanket; rider\|AT 59.1% n=215, pc-\|BELOW 69.4% n=85 = per-token only |
| shadow_trader --report | ✓ 16:32Z | **pm_trail +23,255** vs hard_max **-30,353** = trail-or-nothing; all gates avg-neg |
| --analyze-hml | ✓ 16:48Z | open-skies+ 780 @ 17.1% worst, **0 live closes** = gates holding |
| chop_bleed_kpi | ✓ | 7d **75.4%** (below gate) |
| floor / oscillator / wyckoff / rr | 11-24 / fossil / pending / orphaned | **3/6 answerable** |

### 7. AMPLIFY (light; formal weekly due Mon 11-30)
**0 NEW — stated:** every n>=10 net>0 30d cell claimed by an OPEN entry or adjudicated NO-SHIP (ai-trader-pending\|NORMAL\|SHORT 11-21); early n5-9 net>+$0.30 **EMPTY**; flip-KPI **0 conversions this week**. SHORT-only maker scoping logged as creative (subset of existing maker-entry, not duplicate).

### 8. CREATIVE ×3
1. **SCOPE maker to SHORT only** — fill 93.6% vs LONG 59.4%, fk 8.1%, +$0.70/30d (CEO deadline 11-28).
2. **Fee-drag ranking** for rollout — rank by $ fees burned not WR (jup 64% WR → net -2.86/30d is a fee victim, not a kill).
3. **Reentry receipt shipped** — do not re-propose.

### 9. LAST-RUN VERIFY (#304) — ALL PASS
high-long-displacement-read present (11-29) · regime-conf-high-first-read present n=10 EARLY · HIGH 0.50 live · size_mult HELD (all opens since 11-25, SOL #17117 = 2.0) · tape-state HELD · contrarian mandate HELD · chop_bleed_kpi RAN · NULL mfe since fix = **0**.

**SIDE-FIND (MED):** fee coverage 86.6% — 13.4% of 30d closes lack fees JSON, net KPI understates drag. **(LOW):** auto_1hr still prints "storm bar 2/3 deadline 11-26" but storm-confl-waiver CLOSED by #301 — stale text.

### 10. SESSION BRAIN
23 run-derived queries / 100+ hits / **6 cited**. Prior-art for maker = [Build New Linear Regression Signal 2026-10-29] (28 days old, still unimplemented pipeline-wide); net-of-fee correction = [calwndar 2026-10-31]; HIGH-block prior art = [risk-budget decision 2026-10-21].

### 11. READINESS (2026-11-26 17:10 UTC)
**0 open / 0 steers / portfolio good.** Regime: btc_15m **SHORT_BIAS** vs btc_4h **LONG_BIAS** CONFLICT · continuum **AT** · vol **LOW** · trend **STRONG_UP** · wyckoff UNKNOWN → **NO fresh discretionary directional entries**; trail-family first; size **0.25x**; no regime block.

### QUEUE
**11-27** other-gate-short-withhold (signal_analyst) → **11-28** prearm-day7 + **maker SHORT-only CEO ruling** + jup-walk/cell-tilt/r2v2/longbypass → **11-29 JOINT READ: regime-conf-high-first-read + high-long-displacement-read (at most ONE HIGH instrument)** → **11-30** rider/atp/hl-copy + **FORMAL WEEKLY AMPLIFY** → 12-01 win-side + stop-family → 12-10 jup-trail-atr + pc-weight-2.

**CEO owed:** maker SHORT-only scope (11-28) · **PREARM_LOCK_ENFORCE GO** (never-armed net -8.86 = the bleed) · manual_sl_hit 14d net -3.37 100% ai-trader.
