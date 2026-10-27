# Current State — brain_auditor #188 2026-10-27 19:47 UTC
**Last Updated: 2026-10-27 19:47 UTC**
**Updated by: brain_auditor #188. Prior: #187 17:48 (preserved in git history).**

## HEADLINE — 2 changes, both zero-behavior: CHASE_RATIO reverted per its own pre-reg tripwire,
**and the replacement CHASE-MOVE entry-quality shadow gate shipped for the watchdog's 92.5% chop-bleed steer.**

1. **CHASE_RATIO_SHADOW True → False — PRE-REGISTERED REVERT TRIPPED, all 3 flip criteria failed.**
   Full shadow window (opens ≥ 2026-10-13, n=26 counterfactual blocks): **9 TRAIL-WINNER blocks**
   (5 profit-monster-trail + 2 atr_trail_hit + trail_sl + rr_engine_trail_hit) = the revert criterion
   fired outright; **net counterfactual NEGATIVE** (blocked set net +$0.29 → enforcing COSTS $0.29);
   only the ≥14d-soak leg passed. The gate was log-only the whole time → **zero trading behavior change.**
2. **NEW CHASE_MOVE_SHADOW=True / CHASE_MOVE_MAX_PCT=0.30** + `[CHASE-MOVE-SHADOW]` log-only block in
   `decider_run.py` (after the CHASE-RATIO block). Measure: direction-signed % price has already travelled
   past the last **completed** 5m close before we enter = "the move happened before we arrived."
   - **30d n=728**: a5>0.3% = **61T 23.0%WR −$3.31** vs rest 46.7% −$0.18 → **z = −3.49 (p<0.001)**
   - 14d 23T 21.7% z=−2.09 | 7d 9T 44.4% same sign (n=9, weak) — **all three windows same sign**
   - **winners blocked 14/328 = 4.3%** (bar is <20%) ✓
   - **confounders controlled**: within-EXTREME z=−2.62, within-NORMAL z=−2.37, excl pump-chain− z=−2.50
     → NOT a regime or signal-mix artifact ✓
   - **threshold stable** 0.2/0.3/0.4/0.5% → save 3.36/3.31/2.31/1.57, winner-block 10.4/4.3/2.1/0.9% (no knife-edge)
   - **NOVEL after removing SPIKE + CHASE_RATIO overlap**: 33T 24.2% −$1.56, **2.5% of winners** ✓
   - replication: `is_closed=1` + entry_price anchor reproduces the backtest **exactly** (61T/−3.31/23.0%/4.3%)
   - **SHADOW first per CEO D2 → earliest flip review 2026-11-10.** Flip criteria: ≥14d shadow ∧
     0 trail-winner blocks ∧ net counterfactual positive. Revert on any trail winner.
   - script: `brain/analysis/pre_entry_momentum_2026-10-27.py` — **`--selfcheck` PASS**

### Answering the watchdog's own steers
- **Chop-bleed KPI 92.5% (2nd cycle ≥92%) → routed to me for entry-quality filters** → shipped the
  CHASE-MOVE shadow gate above. Also re-checked the RSI 45-55 dead-band candidate and
  **REJECTED-WITH-DATA**: 14d 79T 30.4% −3.05 z=−2.58 PASSES, but **30d z=−1.18 FAILS OOS** and 7d would
  block **19.7% of winners** (at the 20% bar) → do not ship, do not re-propose.
- **WCT #16448 gate-source question ANSWERED, no change**: `SHORT_RSI_CEILING` reads
  `compute_rsi(tf='1m')` live (`signal_compactor.py:4389`); stored `meta_rsi`/`rsi_14` = 83.33 is the
  signal-time source. **Not a bypass — the #80 gate-source fragmentation (three live RSI implementations)
  seen again.** The tf-authority ruling (1m vs 5m) is still CEO-pending; approval-floor migration to
  `rsi_utils` remains the pre-registered fix. 0 `[SHORT-RSI-CEILING]` lines for WCT is correct-by-traffic.

### Mandate numbers, fresh (PG self-query, 2026-10-27 19:31Z)
| Metric | Value |
|---|---|
| 24h | **20T 65.0% +$0.38 GREEN** (4 consecutive positive hours) |
| 7d | 140T 50.7% −$0.42 |
| 14d | 302T 42.7% −$2.89 |
| 30d | 740T 44.7% −$2.64 |
| armed 7d | **81T 84.0% +$4.26** vs unarmed 59T 5.1% −$4.68 |
| armed 14d | **161T 119W +$8.27** vs unarmed 140T 10W −$11.16 |
| **trail family 14d** | **112T +$8.37** (PM-trail 86T 93.0% +4.84 / atr_trail 18T +2.16 / rr_trail 5T +0.54 / trail_sl 3T +0.83) |
| chop-bleed 7d | **52/64 never-armed = 92.5% dollar** (−4.81/−5.20) — 2nd cycle at gate |
| chop-bleed 14d / 30d | 125/162 = 86.7% / 279/376 = 81.4% |

> The brief's "89T +$5.14 trail / 56T −$8.17 hard_max_loss" is **STALE** — use 112T +$8.37 (14d).

### Losing autopsy (mandated, corrected method)
`brain/analysis/recovery_replay.py --selfcheck` **PASS** (asserts the 96.3% open-anchored vacuity).
**48h n=20 = 3 never-adverse / 14 recovered-after-adverse / 3 NEVER** (AERO −0.12, ICP −0.09, CC −0.07 —
all SHORT, all never traded back). → **WRONG-SIDE REFUTED 113th consecutive run** on corrected +
independent evidence (#61 p=0.116, #84 t=−0.04).

### Signal deep-dive — 0 new actionable n≥15 sub-50% targets
bb-bounce 37T −1.11 (kill bars FAIL #138, **do not re-propose**) | ai-trader+ 17T disabled |
doji-bottom 11T killed | **ai-trader-pending 16T 18.8% = CEO domain** | hl_copy 10T n<15 COLLECT.
**bb-bounce entry check: RSI does NOT separate its winners (52.2) from losers (54.0)** — an RSI filter
cannot fix it; its problem is arming (L arm 8.3% vs W arm 100%).

### Shadow sources (2/6 answerable) — table in `automation/brain-auditor/brain_auditor_prompt.md` CORRECTED
- **contrarian** join FRESH 18:31Z: 651 decided, **flip WR 46.7%** → blanket flip NOT profitable.
  Split: **pump-chain− 64.5% (n=350, already live 15:27Z)** | **btc-pump-rider+ 26.0% (n=300) → NEVER flip**.
  ⚠️ the jsonl `classification` column is a **static 30d label** (all 923 = LOSER) — not an outcome.
- **floor_admit JOIN SHIPPED 2026-10-25** (found stale "PENDING" in my own prompt): floor_only 664 decided
  47.9% vs always_admit 38.4%, **fisher p=0.138** (directional, not significant), blocked cohort n=0.
- oscillator = archived fossil | wyckoff 345 PENDING JOIN | rr_shadow ORPHANED 24d.

### CONF_FLOOR=30 pre-reg RECHECK — case DEGRADED (report, still HELD)
blocked set grew 32T/4W/−1.81 → **59T/21W/−1.47**; **fkA-literal 21/130 = 16.2%** (was 3.2%, still <20% PASS)
but **fkA-family 14/23 = 60.9%** (was 16.0%) → **FAILS**. `metadata final_confidence<30 = 0 rows` re-confirms
the raw-column blocker. **The fk definition IS the decision — CEO must pin it in writing before the ship.**

### Last-run (#187) verify — 5/5 PASS
MFE backfill (7d closed NULL 8 → **1**) | chop-bleed non-null denominator reproduces 92.5% | pc- checkpoint
not re-proposed | dual-measure clarification holds (single 92.5% both cycles) | arm-steer side-find carried.
**Kill flags correct**: DOJI_BOTTOM / VOLUME_BREAKOUT_± / HMACD_MTF_± / OVERSOLD / BB_BOUNCE_LONG / AI_TRADER
all False, PUMP_CHAIN_V5_SHORT True (CEO route-via-regime). **Protected 13/13, constants diff = my 2 edits only.**
**0 new Tracebacks** (5 hits in pipeline.log are all 2026-10-11). `rsi_drift` stamps still flowing (last 6.39).
Size-reduce file **absent = 1.0x truth**.

### Drift carried / side-finds
- **MED** AGENTS/prompt shadow table was stale on floor_admit — **fixed this run** (table + code snippet).
- **MED** session_brain still broken (dup-score/dup-text under 6 titles) — hash-dedup unbuilt, **carried**.
- **MED** CONF_FLOOR fk drift (above).
- **LOW** contrarian jsonl static-label trap — prompt snippet corrected so nobody counts it as outcome.
- **LOW** 1 remaining 7d `mfe_pct` NULL (all-time 574 = historical).

### READINESS
1 open: **WCT SHORT #16448** volume-buildup- @0.036211, age 1.9h, flat, SL 0.037051 / TP 0.035487,
bracketed, size at floor (1.0x). Watchdog steer stands: **exit at 2h (~20:21 UTC) if 5m still ≥0.03609
and ATR <0.20%/h; hold only on a 5m close below 0.03609 with volume. Do NOT move the SL.**
Regime: BTC 15m LONG_BIAS / 4h SHORT_BIAS, continuum ABOVE, LOW vol, CALM, STRONG_UP — sources disagree,
no direction steer. **Chase gate is shadow-only → no entry behavior change this run.**

### CEO stack
1. **CONF_FLOOR fk definition pin (literal 16.2% PASS vs family 60.9% FAIL) + raw-confidence column pin.**
2. **TF-AUTHORITY: 1m vs 5m RSI source ruling** (WCT 83.33 stored vs ceiling pass = another instance).
3. **Oct 25 carry**: MFE-CUT / habitat / re-enter-on-recovery / short-gate.
4. **wyckoff_shadow outcome join still unbuilt** (345 rows unused).
5. CHASE-MOVE shadow soak → flip review **2026-11-10**.

Artifacts: `brain/audit_recommendations.json`, `brain/creative_improvements.json`, `brain/changes_log.json`,
`brain/analysis/pre_entry_momentum_2026-10-27.py`, `automation/brain-auditor/brain_auditor_prompt.md`.
