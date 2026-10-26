# Current State — brain_auditor #163 2026-10-26 14:55 UTC
**Last Updated: 2026-10-26 14:55 UTC**
**Updated by: brain_auditor #163. Prior: #162 13:50 / #161 12:55 / #160 11:55 (preserved in git history).**

## HEADLINE — the watchdog's ACTIVE cluster steer has no statistical support. 0 config changes, 1 instrument ship.

steer-001 this cycle: *"Trade cluster: DYDX + LTC — both opened within 20 minutes. Correlation risk."*
That idea also sat in `creative_improvements.json` as **"suggested — needs backtest" five times since
2026-10-03** and had never been measured. Measured now, bars written **before** the groups were read
(`brain/analysis/cluster_risk_limiter_2026-10-26.py`, `--selfcheck PASS`, **bug_hunter SHIP-WITH-FIXES**:
2 MEDIUM + 2 LOW fixed, `fisher_left` cross-validated vs scipy + brute-force hypergeometric, cohort
independently re-queried and matched):

| arm (15m window) | 30d blocked | WR blocked | WR anchor | net | Δ after 0.05% fee | Fisher p (left) | bars |
|---|---|---|---|---|---|---|---|
| **A. same signal family, 2nd+ open** | 104 | **46.2%** | 43.8% | `-$0.94` | **`-$0.23`** | **0.7088** | 2/5 → REJECT |
| **B. any 2nd+ open in the book** | 244 | 43.4% | 44.5% | `-$1.15` | `+$0.46` | 0.4208 | 3/5 → REJECT |

- Family arm also **fails same-sign**: 7d blocked is **`+$0.01`** (1/3 windows).
- Book arm's B2 *passes* only marginally — 7d blocked `-$0.09` **flipped sign from `+$0.08` between two
  reads 20 minutes apart** as one trade closed. A 3/3 same-sign verdict that moves on a single close is
  not a gate.
- Book arm **fails winner-impact**: blocks **33.3%** of 30d winners (>20% bar).
- **Blocking cluster members would have LOST money**, and members are if anything slightly
  *better* than solo trades.
- **Guidance logged: cluster steers stay INFORMATIONAL — no run should chase them.**

## LAST-RUN VERIFY — `pm_armed_at` SHIP CONFIRMED LIVE (closes #162's open queue item)
Trade **16418 USUAL `r2v2-long3`** closed `profit-monster-trail` `+$0.05` at 14:26:24 with
`_signal_metadata.pm_armed_at = 2026-10-26T14:20:18Z`. Rows carrying the stamp: **1/1** since the
13:50 ship. Also PASS: `arm_gap_baseline --selfcheck` · daily_git_commit guard present, 07:15 clean ·
profit-monster GC canary **0** `Profit monster closing` · constants working-tree diff **EMPTY** ·
CEO_PROTECTED untouched · size-reduce **ABSENT = 1.0x** · session lock **absent** · kill leaks 0 ·
`BB_BOUNCE_TRAIL_ARM_TIMEOUT=True` (TAT-C live).

**Traceback census corrected (D162-3):** prior runs claimed "0 Tracebacks dated 2026-10-26" scoped to
`pipeline.log`. Scanning **all** logs finds hits only in `logs/trade-watchdog.log`, and each is the
**watchdog agent's own failed throwaway heredoc** (`NameError: name 'DB_CONFIG' is not defined`,
`for r in cur.fetchall(): print(r)`, …) — not a component crash. Service-level = **0**. LOW: watchdog
self-logged snippet errors inflate any naive "Tracebacks today" count.

## MANDATE — CHOP vs TREND (fresh PG, 14d 334T 38.6% `-$4.55`)
- **`profit-monster-trail` 83T 91.6% `+$4.58`** + `ugb_pt` 9T `+$0.24`
  vs **`atr_sl_hit` 80T 1.3% `-$5.57`** vs **`hard_max_loss` 62T 0.0% `-$6.24`**
  vs `trail_arm_timeout` 25T 20% `-$0.78`
- **armed (mfe≥0.40) 165T 70.7% `+$8.40`** vs **unarmed 163T 5.6% `-$12.79`**
- **MFE ladder is monotone in all 3 windows** — the whole addressable bleed is one cohort:

| MFE bucket | 7d | 14d | 30d |
|---|---|---|---|
| **<0.15%** | 28T `-$2.23` | 81T `-$7.50` | 167T **`-$18.07`** |
| 0.15–0.40 (4 bands) | 19T `-$1.86` | 45T `-$4.44` | 97T `-$7.66` |
| **≥0.40** | 72T **`+$3.65`** | 165T **`+$8.40`** | 409T **`+$25.96`** |

  **MFE<0.15 = 48.9% of 14d gross loss (7.50 of 15.35) and 51.0% at 30d (18.21 of 35.68).**

**Read: trend side healthy. No exit lever opened beyond the in-flight UGB-PT / TAT-C / Oct-30 time-stop.**

## ⛔ STOP-CALL — entry-feature mining has returned nulls 5 independent times
`staleness` + `gap_at_entry` census (#155, both rejected) · `repeat_after_stop` (#159) ·
entry-feature separation test (10-23) · entry-feature arm-predictor (10-25).
Reproduced independently this run on fresh PG — armed vs unarmed **medians**:

| rsi_exec | gap | speed_pct | volume_spike | staleness_min | vol_regime |
|---|---|---|---|---|---|
| 47.9 / 54.2 | 0.1 / 0.2 | 47.7 / 48.3 | 0.37 / 0.33 | 1.32 / 1.25 | identical |

**Do not re-run entry-feature / armed-separation scans.** Signal identity, not admission-time
continuous features, is what separates the cohorts.

## GUARD LEAK CENSUS — verify-only, **no gap found**
`SHORT_RSI_FLOOR=45`: 30d SHORT with `rsi_exec<45` = **17T net `+$0.12` @ 58.8% WR** (15 of them
`volume-buildup-`) — the leaked cohort is **PnL-positive**, so the floor needs no change. The single
`rsi_exec 39.0` leak is ICP #16409, the `[35,45)` waiver class that **lapses 2026-10-27T00:00Z**.

## LOSING AUTOPSY — WRONG-SIDE REFUTED **87th** CONSECUTIVE RUN
`recovery_replay.py` adverse-first (`--selfcheck` ASSERT PASS, vacuity **182/191** reproduced):
**48h n=15** = 5 never-adverse / 9 recovered-after-adverse / **1 NEVER** (ICP #16409) ·
**14d 191 losers = 37 / 126 / 28 NEVER = 14.7%** structural never-recover (was 17.5% on the Oct-22
baseline). Refs that survive: `#61` p=0.116, `#84` t=-0.04. 24h losers mapped: **ICP** = waiver-band
oversold short (lapse removes it) · **DYDX `-$0.12` / -5.45% acct** = one wide-SL loss inside a family
that is 14d 32T 68.8% `+$0.68` with armed WR 91.3% (n=1, no signal defect) · **ETH hl_copy ×2** =
counter-tape LONGs, family pre-registered on the n≥20 bar (30d n=14) · **ADA+CAKE bb-bounce** =
never-armed chop, KILL BARS FAIL, TAT-C-owned.

## DEEP-DIVE — 0 new shippable sub-50% n≥15 targets
`bb-bounce-v2-long+` 38T 36.8% (TAT-C live, re-kill banned) · `doji-bottom-long` killed Oct 16 ·
`ai-trader+` disabled · `pump-chain-` CONF_FLOOR + PROMOTE Oct 27 · `pump-chain+` NO-KILL 30d `+$1.84` ·
`ai-trader-pending` 16T 25% = n≥15 but CEO domain, cohort dead since Oct 19 · `hl_copy_trader` 14T/30d
under bar → kill test pre-registered at n≥20 · **`volume-buildup-` 32T 68.8% `+$0.68` healthiest live**.

## SHADOW — 2/6 answerable · **SL + ARM-TIMEOUT SWEEPS OPEN NO LEVER**
- contrarian join: **pc- flip 64.6% n=347** (OOS both halves same sign) = **Oct-27T17:12Z PROMOTE stands,
  not shipped early**; btc-pump-rider+ orig 73.4% vs flip 25.1% = do-NOT-flip.
- shadow_trader 24,746 signals: CONFLUENCE-EXPIRY 11,520 @48% avg `-$0.12`, BTC-CRASH 133 @32%
  avg `-$0.37` = gates earning keep; exit A/B **pm_trail `+3525` vs hard_max `-5232` (0% WR)**.
- **`--sweep-sl`: every level negative** (best 5.0% still `-0.259%` avg). **`--sweep-arm`: every
  timeout negative** (best 45m still `-0.166%` avg) → **cite neither as a ship candidate.**
- `--flip-test` on shadow_trader returns *No signals to test* for pc+/bb-bounce (signal-name mismatch
  with contrarian jsonl) → use `analysis/contrarian_both_sides` for flips.
- floor_admit 2,070 + wyckoff 331 **PENDING outcome join = biggest queued ROI (Nov 15)** ·
  oscillator FROZEN by design · rr_shadow_audit **ORPHANED** (no producer, 21d stale).

## WATCHDOG TRIAGE
- **steer-001 cluster → REJECTED** (HEADLINE; steer class now informational).
- **Regime: all four sources SHORT_BIAS, BTC below EMA300 87 bars → AGREED**, book compliant.
- **USUAL #16418 counter-regime LONG → RESOLVED BY A WIN** (closed 14:26 `profit-monster-trail`
  `+$0.05`, arm stamp landed) — not by an exit steer.
- **No kills** — every bleeding family already owned.

## CREATIVE / REJECTED THIS RUN
1. **REJECTED-WITH-DATA** cluster risk limiter, both arms (5×-suggested since 10-03, never tested).
2. **PRE-REG TIGHTENING (pre-data)** for the **2026-10-30** time-stop blind run: its saving must be
   attributable to the **MFE<0.15** cohort, not to cutting 0.15–0.40 grinders that recover.
   Locked B1–B6 unchanged — tightening pre-data is allowed; moving them post-data is not.
3. **REJECTED PRE-EMPTIVELY** "pump-chain- arms but the trail fails to convert" — 14d armed 33.3%
   negative vs **30d armed 60T 48.3% `+$2.64`** = window-dependent, no trail-side claim. Logged so
   no future run proposes a pump-chain- trail fix.

## DRIFT
- **D163-1 (carried):** run #161's ship untracked until #162 — `git status` checked this run;
  `profit_monster.py` + `arm_gap_baseline_...py` still uncommitted from #162 → committed here.
- **D163-2:** watchdog self-logged snippet Tracebacks inflate naive log counts (see LAST-RUN VERIFY).
- **D162-2 (carried, no code change):** `CEO_PROTECTED_FLAGS` names `SIGNALS_REGISTRY`, attribute is
  `signals.SIGNAL_REGISTRY` → protected 13/13 **in substance**.
- Carried LOW: weekly 03:00 Sun `ModuleNotFoundError dispatcher.dispatcher` (verify Nov 1) ·
  `data_integrity_guard.py` never invoked · `session_brain` duplicate-scrambled `ceo` records.

## QUEUE
- **2026-10-27T00:00Z** waiver LAPSE verify (zero allow-lines + `[UNCLOG-EXPIRED]`; c3 = price-move)
- **2026-10-27T17:12Z** pump-chain- PROMOTE formal re-verify (do NOT ship early)
- **2026-10-27** mid-band [35,45) re-measure (#139) + two rejected rsi_14 cells + CHASE_RATIO_SHADOW
- **2026-10-27+** ARM-GAP only on the re-based bar (n≥30; n=17 now)
- **2026-10-30** scoped momentum time-stop BLIND run — bars locked **+ the MFE<0.15 attribution
  tightening above**
- **2026-10-31** short-supply re-measure on `t_CR>=2` via `cluster_t`
- **2026-11-01** coin_regime LONG-COUNTER OOS + self-healing SKIP verify
- **2026-11-08** gate scoreboard #2 (distinct-trade basis)
- **2026-11-15** floor_admit + wyckoff outcome joins
- **NEVER:** re-run entry-feature / armed-separation scans (5 independent nulls)
- **CEO:** CONF_FLOOR fkB FAIL (23.1% bare / 29.1% all-signal) + enforcement site after
  `decider_run.py:4856` + blocked-count self-check · ARM-BE-STOP GO · **escalation #17 (64th)
  exit-ladder candle OOS** · identify the 02:19:30 constants writer · LOSERS set EMPTY ·
  ai-trader-pending 16T 25% cohort dead but flagged

## BOOK / READINESS (24h 29T 51.7% `-$0.37` · 7d 134T 45.5% `-$0.46` · 30d 719T 44.2% `-$2.38`)
**1 open bracketed: LTC #16422 SHORT `volume-buildup-` @56.568 (SL 57.625 / TP 55.679) 0.1h** —
aligned with the SHORT_BIAS tape, **HOLD on bracket**; DYDX SHORT closed `hard_max_loss` -5.45% acct.
No new LONG exposure while all four sources read SHORT_BIAS · mid-band = no trade · trail-family first ·
size 1.0x (file absent).
