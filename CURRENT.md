# Current State — brain_auditor #209 2026-10-31 12:50 UTC
**Last Updated: 2026-10-31 12:50 UTC**
**Updated by: brain_auditor #209. Prior: #208 2026-10-31 09:05 UTC (preserved in git history).**

## HEADLINE — 0 config changes (6th run, nothing passed bars). Two AMPLIFY proposals emitted. Chop-bleed 93.6% closed from the signal axis: every live signal wins only when it arms.

24h 55T 56.4% -$0.71 | 7d 203T 57.1% -$0.78 | 14d 324T 50.9% -$1.94
Never-armed 7d: **68 of 77 losers, 93.6% DOLLAR share** (-$7.36 of -$7.86, 0 NULL) = **7th window >=92%**

### 1. NEW AXIS — per-signal armed vs unarmed (14d, n>=15): every signal is the same signal
| signal | armed (n, pnl) | unarmed (n, pnl) |
|---|---|---|
| bb-squeeze+ | 13, **+1.13** (100% WR) | 15, -0.37 |
| jup_yolo_mirrored | 26, **+1.29** (88.5%) | 14, -1.91 (7.1%) |
| volume-buildup- | 35, **+1.75** (94.3%) | 20, -2.39 (5.0%) |
| pump-chain+ | 23, **+0.74** (69.6%) | 17, -1.37 (5.9%) |
| r2v2-long3 | 10, **+0.51** (90.0%) | 7, -0.50 |
| bb-bounce-v2-long+ | 11, **+0.46** (81.8%) | 14, -1.18 (0%) |
| ai-trader-pending | 3, +0.27 | 14, -0.47 (7.1%) |

Arm% by signal 14d: ai-trader-pending 17.6 · bb-bounce 44.0 · bb-squeeze 46.4 · pump-chain+ 57.5 · vb- 63.6 · jup 65.0.
**There is no "which signal" question left — only "will it arm".** Entry-feature mining stays stop-called (#163, 5 nulls); this cut confirms the same wall from the signal axis. Exit levers refuted #208 (both sweeps all-negative, not re-swept).

### 2. AMPLIFY — 2 proposals registered (`data/shadow_disposition.json`)
- **(b) `amplify-winner-cell-mult-150`** — `WINNER_CELL_SIZE_MULT 1.25 → 1.50` (= existing `WINNER_CELL_SIZE_MULT_CAP`, **zero code**). Cells 156T/30d **+$4.83**; bb-squeeze+ NORMAL +0.46/+0.76/+0.95 across 7/14/30d at 68-70% WR; expected ≈ **+$0.97/30d (estimate)**. Guard: revert if winner-cell-set 7d net < 0 or any cell 7d < -$0.50 twice. Deadline **11-14**, owner **CEO label + T sign-off** (money-sizing — not applied).
- **(c) `amplify-jup-short-walk`** — counterfactual-walk the **194 blocked jup_yolo SHORT** signals. Emission is symmetric (194 short / 222 long rows, both born 10-30) but execution is **1 SHORT vs 39 LONG** trades/30d. Deadline **11-14** (zero OOS days before 11-13).
- **KILLED WITH DATA:** bb-squeeze+ blocked-clone-hunt → 329 deduped blocked rows **51.7% WR, -32.45pp** (NORMAL 34T 41.2% -3.06pp) = gates correctly reject; do not re-propose.
- **METHOD TRAP caught:** filtering shadow `exit_json` on `fired==true` = 100% WR / +184pp by construction (trail engine fires only on winners). Logged so it is never reused.
- Flip-KPI: no new shadow→live conversion this run (formal weekly Mon 11-02).

### 3. NEW EVAL PRE-REGISTERED — shadow-vs-live WR fidelity
shadow non-blocked WR runs **11-24pp below live WR** for every positive-edge family (bb-squeeze 39.0 vs 63.4 · jup 40.7 vs 60.0 · vb- 49.6 vs 65.1 · pump-chain+ 28.8 vs 42.7 · r2v2 47.2 vs 60.0) and at parity only for negative-edge sources. Gate `would_win` figures are therefore either **conservative** or **pessimistically biased**. Bar: |delta| < 10pp on 3+ matched families, else label shadow gate stats as lower-bound.

### 4. WATCHDOG TRIAGE
- **P1 chop-bleed 93.6%** — reproduced exactly, entry-quality route re-verified on the new axis, no filter passes bars (6th run).
- **P2 "we mirror only the long leg" = FALSE (MED prose drift)** — `jup_yolo_monitor.py:572-578` parses `side` long/short explicitly; short suppression is `compaction_stale` 91/194 + RSI floors + **SOL SHORT_BLACKLIST 1081 hits**. RR asymmetry itself is real: 14d avg loss **-4.43%** vs avg win **+2.29%** (1.94x, leveraged `pnl_pct`).
- **Option D `SHORT_RSI_HARD_FLOOR_JUP_YOLO=35` VERIFIED WIRED** (compactor:4360, decider:1366, `is_giant_source`; logs print `< 35` for HYPER/PURR vs `< 45` for IMX/APT/GMT). The 17 stored-`rsi_14`>=35 blocks are detect-vs-approval RSI timing — **no leak**.
- **Cluster steer HOLD** — 15m+4h LONG_BIAS, continuum ABOVE, trim condition (1m < EMA300 60m+ AND `score_long <= 0`) unmet.
- **GMX profit-lock ALREADY SATISFIED** — live SL **8.0094** = +1.74% above entry 7.8723 and above the steer's own 7.95 target (steer text stale at 7.8745). No action.

### 5. LAST-RUN VERIFY #208
- **Trial revert WORKING AS INTENDED, too early (n=7):** since 08:45Z → 4 `trail_arm_timeout` -$0.03, 2 `profit-monster-trail` +$0.25, 1 `UNIVERSAL_MAX_HOLD` -$0.01, **ZERO `hard_max_loss` and ZERO `cut-loser`** post-revert. CEO override window closes **2026-11-01 08:55Z**.
- **Winner-cell regime fix VERIFIED:** IOTA #16614 `bb-squeeze+` NORMAL amount **12.48** (12.4875 = 11.10 × 0.9 × 1.25, cent-truncated); DYDX #16603 / MON #16600 vb- HIGH 12.48; EXTREME vb- stays 11.10.
- vb- HIGH clone-hunt (#208) still pending **11-07** — not duplicated.
- Checkpoint `btc-16599-8h-stale` → **done** (trade closed 09:38:30Z `UNIVERSAL_MAX_HOLD` -$0.01, 7.97h, never armed).

### 6. AUTOPSY / SHADOW
- **Autopsy 48h adverse-first (selfcheck PASS): n=36 = 11 never-adverse / 19 recovered / 6 NEVER (16.7%)** → WRONG-SIDE REFUTED (consecutive; refs #61 p=0.116, #84 t=-0.04). NEVER = HYPE jup LONG, BTC continuum-trend- SHORT, ZORA vb- ×2, MON vb-, ALT pc-.
- **Contrarian join re-ran 12:41Z (mandate):** 958 joinable, overall **41.1%**; **pc- 64.6% n=350 LIVE**; btc-pump-rider+ **27.6%** do-NOT-flip.
- **floor_admit join re-ran 12:41Z:** floor_only 1108 @49.9% vs always_admit 144 @45.8%, blocked n=0; n-bar PASS, 30d same-sign **NOT YET** → COLLECT **11-15**.
- **shadow_trader 43,770:** gates CONFLUENCE-EXPIRY 14297 @48% · CTX-GATE 1804 @50% · BTC-CRASH 244 @43% · EXEC-BLOCK 281 @54%; exit A/B **pm_trail +6,725 vs hard_max -7,443** = trail-or-nothing.
- 3/6 answerable: contrarian + floor_admit + shadow_trader. wyckoff join owed **11-03** · oscillator archived · rr orphaned.

### 7. DRIFT / SIDE-FINDS
- MED: watchdog P2 prose contradicted by code (mirror both legs) → prompt/prose fix, no code.
- LOW: `_signal_metadata.regime_src` logged but never persisted (15/15 NULL) — keep using the 12.48 arithmetic for forensics.
- INFO: `signals_hermes_runtime.db` spans 10-17..10-31 but `jup_yolo_*` rows start 10-30 → date-label every jup window, never quote 7d/14d/30d for it.

### 8. READINESS (12:50)
**4 open, ALL LONG:** GMX `pump-chain-` **+2.80%** (SL 8.0094 risk-free, locked +1.74%) · BTC `continuum-osc+` +0.13% (11:51, ABOVE EMA300) · HYPER `pump-chain-` +0.16% (12:26) · **HYPE `jup_yolo_mirrored` +0.02% `size_mult 2.0` (12:36 — CEO sizing, carried 4th run)**. IOTA #16614 closed 12:30 `trail_arm_timeout` $0.00.
Regime: btc_15m **LONG_BIAS** / btc_4h **LONG_BIAS**, continuum **ABOVE**, trend_quality STRONG_UP, vol LOW, volume LOW → let trails work, hold per trim condition, no fresh shorts against the tape. Size **1.0x** (size_reduce file absent = truth).

### 9. QUEUE
- next run: chop-bleed re-measure + confirm 0 `hard_max_loss`/`cut-loser` post-revert.
- **11-02** formal AMPLIFY + flip-KPI · **11-03** shadow_disposition batch + wyckoff join · **11-06** regime coverage retest · **11-07** jup band review + vb- HIGH clone-hunt · **11-10** CHASE-MOVE/MFE-CUT · **11-14** amplify pair · **11-15** floor 30d bar.
- **CEO:** winner-cell 1.5x ruling · trial-revert override (closes 11-01 08:55Z) · HYPE 2.0 size into jup family · unchanged stack (TAT scope, CONF_FLOOR fk, tf-authority, bb-bounce).
- Escalation **#17** (aged, closed 10-17 for exit-ladder; do not re-print stale variants).
