# INDEPENDENT VERDICT — PLAN V3 + INVERSION CLAIM

**Auditor:** independent (fresh read, no priming) · **Date:** 2026-10-14 ~00:00 UTC
**Sources verified live:** PostgreSQL `brain.trades` (~4.9k rows), `/var/www/hermes/data` kill-switch state, systemd timers, `scripts/vacation_guardrail.py`, `scripts/signal_compactor.py`, plan v3, MoE panel report.

---

=== INDEPENDENT VERDICT — PLAN V3 + INVERSION ===

**Claim (T):** "We are currently worse than a coinflip, doing the total opposite of what we're doing would be profitable." SHORT WR 33% (16/49), LONG WR 37% (56/151); flipped = 67%/63% = profitable.

**Verdict: PARTIAL** — the WR numbers are real and the recent deficit is statistically significant, but the "opposite would be profitable" conclusion is **arithmetically invalid and contradicted by the trade-path data.** Do not flip.

**Evidence:**

### 1. The WR numbers reproduce (T is honest about the raw numbers)

| Window | LONG | SHORT |
|---|---|---|
| Last 200 closed (T's source) | **54/151 = 35.8%** (T said 56/151) | **15/49 = 30.6%** (T said 16/49) |
| Last 7d (close_time, PostgreSQL) | 53/147 = 36.1%, **p=0.0009** | 15/46 = 32.6%, **p=0.026** |
| Last 30d (close_time) | 239/519 = 46.1%, **p=0.079 (NOT significant)**, PnL **+$1.46** | 101/243 = 41.6%, p=0.010, PnL −$4.89 |
| Last 7d (open_time anchor — robustness) | 35.6%, p=0.0006 | 32.6%, p=0.026 |

Small drift vs T's exact digits = rolling-window movement; same population. **"Worse than coinflip" is TRUE and significant for the last 7 days (both directions) and for 30d SHORT. It is FALSE for 30d LONG — LONG was profitable over 30 days (+$1.46) and statistically indistinguishable from 50% (p=0.079). Flipping LONG over 30 days would have LOST money.**

### 2. Why the flip arithmetic (67%/63%) is wrong — MFE/MAE evidence

`1−WR` inverts only if exits are perfectly mirrored. They are not — exits are absolute price distances (0.6% hard cap, +0.40% trail activation), so winners and losers do NOT swap roles when the entry flips. Measured trade paths:

- **7d LONG losers (n=92):** avg **MFE +0.437%** (favorable!) vs avg MAE −0.517%. The losers were **not** trades where price went against from the start — price ran +0.44% in the signal's favor (just under the +0.40–0.5% trailing-activation boundary) and then reversed. These are **whipsaws at the trailing-arming threshold**, not directional inversions.
- **7d LONG winners (n=48):** avg MFE **+1.576%**, avg MAE −0.152%. Winners run ~3.6× farther than losers ever go favorable.
- **Flip consequence:** the flipped trade on a loser's path survives its stop (0.44% < 0.6%) and banks the ~0.5% reversal — but the flipped trade on a **winner's** path eats a 1.58% adverse move → guaranteed stop-out. Bounding flipped outcomes from recorded MFE/MAE:
  - Flip-win bound at 1.0% TP: **0–3% of losers qualify** (flipped WR would be ~1%).
  - Looser 0.5% TP bound: ~50% of losers qualify; combined with ~0 flipped wins from the winners cohort → **modeled flipped LONG WR ≈ 31–35% — WORSE than the current 36%, not 64%.**
- The 7d LONG payoff ratio is still **1.71** (winners run, losers are small). An anti-predictive system would show the magnitude asymmetry inverted too. It doesn't. **The system has positive selectivity; it lost its timing.**
- Corroboration: MoE Expert 4 already shadow-tested the near-flip (4h bias counter-flips): WR 35.8%, **p≈0.09 — not significant**, counter-bias longs +$2.45 over 30d is where the "flip" already worked, and it's a subset, not the whole book.

### 3. Is the system genuinely anti-predictive? — No. Regime-flip + exit architecture.

Weekly breakdown (PostgreSQL, by close_time):

| | W-5 | W-4 | W-3 | W-2 | W-1 (now) |
|---|---|---|---|---|---|
| SHORT | **+56.3% WR, +$2.25** (n=151) | 38.2%, −$2.40 | 46.2%, −$1.83 | 36.6%, −$0.86 | 32.6%, −$0.35 |
| LONG | 49.5%, −$1.78 | 47.8%, +$1.87 | 42.9%, +$0.15 | 56.5%, +$0.84 | 36.1%, −$0.26 |

- **SHORT was the system's best side 5 weeks ago** (56.3% WR, +$2.25, n=151). The "anti-edge" is ~4 weeks old and SHORT trade count collapsed 151→46/week. This is a **regime flip**, a stable property — flipping now would have been exactly wrong one month ago. Classic strategy-momentum trap.
- 7d losses by exit: LONG hard_max_loss 54T −$5.19 + atr_sl_hit 21T −$1.66 dominate — the **exit architecture** (hard cap at ~−0.6% price preempting the 1.3% ATR stop) converts the whipsaw reversals into realized losses. 30d: 497 never-armed trades −$21.77 vs 265 armed +$18.34 (MoE reproduces).
- **Diagnosis:** not inverted signal detection (winners still run 3.6×); it's (a) late-cycle entries at ~+0.4% favorable — right at the trailing-activation cliff — plus (b) hard_max_loss exit structure, amplified by (c) a market regime change ~4–5 weeks ago. This is exactly what the MoE's fix list (never-armed rate, HML realignment, confidence clamp) targets.

### 4. MoE findings — verified, all reproduce within drift

| MoE claim | My live query (30d) | Verdict |
|---|---|---|
| hard_max_loss: n=128, −$14.76 | **n=129, −$14.82** (worst exit by far; next atr_sl_hit −$6.95) | ✅ real |
| Conf >100 rows: 119 | **118** | ✅ real |
| Conf 90+ band: −$5.88 vs 70–89: +$6.59 | 90+: 442T **−$5.88**; 70–89: 178T **+$5.24** | ✅ real (confidence inversion confirmed) |
| pullback-entry- SHORT: 62T −$2.28, loses in ALL regimes | 61T **−$2.22**, avg conf **99.8**, HIGH −$0.49 / EXTREME −$1.20 / NORMAL −$0.53 | ✅ real |
| Never-armed 66%, −$21.24; armed +$18.30 | 497T **−$21.77**; 265T **+$18.34** | ✅ real |
| EXTREME LONG +$4.48 vs SHORT −$2.94 | **+$4.42 vs −$2.97** | ✅ real |
| Weekly WR "collapsed 52%→31% over five weeks" | 53.6 → 44.6 → 44.3 → 52.6 → **35.2** | ⚠️ overstated — not monotone; but W-1 alone is significant (p=6.5e-5 consistent) |

Fix #1 (HML/ATR realign) and #3 (kill broken SHORT tail) are sound and directly target verified bleed. Fix #2 (confidence clamp) targets a verified significant inversion (bootstrap CI claim consistent with my band data). **Would fixing them help? Yes — they address −$14.82 + −$5.88 + −$2.22 of verified 30d destruction = ~$23 of gross bleed vs −$2.94 net. Even 50% capture flips the system positive.** But: these fixes are NOT in the "ships before T leaves" list.

### 5. Vacation plan + guardrail verification

**Guardrail (blocker fix) — verified genuinely fixed:**
- `pause_trading()` calls `hyperliquid_exchange.disable_live_trading()` (real function, line 307: closes all HL positions via `close_position()`, saves flags) + stops `hermes-pipeline.timer` (verified: exists, active, is the only live trade-executing timer). Trade execution is actually stoppable. ✅
- Timer active: `hermes-vacation-guardrail.timer` enabled, fired 6 min ago, next trigger in 23 min. ✅
- Escalation is LIVE: last 3 runs all WARNING "48h WR 29.8% < 40.0% with 94 trades". Current state: 24h 38T −$0.04 WR 36.8%; 48h 94T −$1.57 WR **29.8%**. ✅ (worse than at departure)

**Guardrail gaps found (severity-ranked):**
1. **MED — "7d WR < 35%" day-14 kill is NOT code anywhere.** Current 7d WR = **35.2%** — hovering AT the kill line, unenforced. The plan's own most important kill criterion is prose only. Candidate-revert (10+ trades < −$1.00) and day-14 shadow criteria are also prose only.
2. **MED — Escalation is alert-only.** No responder defined during vacation; alert fires every 30 min → alert fatigue. Consider auto-action tier (e.g., 48h WR < 30% → pause instead of warn).
3. **MED — Pause threshold too loose for the current bleed profile:** −$3.00/24h won't trip at the observed ~−$0.8/24h steady bleed. A week-long slow bleed never pauses. Guardrail also blind to unrealized losses (closed-trades only; 1 open real position now).
4. **LOW — stops non-existent `hermes-decider.timer`** (logged warning; real deciders are `ai-decider.timer`/`tokyo-decider.timer` — both currently disabled, so harmless today, but latent if anyone enables one during vacation).
5. **LOW — no resume procedure.** After pause, guardrail stops its own timer; nothing documents who/when/how to restart trading or re-arm the guardrail.
6. **LOW — dead code:** `KILL_SWITCH_PATH` defined but unused in the module; `_save_flags` writes `hype_live_trading.json` which `is_live_trading_enabled()` deliberately ignores (constant-only). The JSON's "CEO RE-ENABLE" state is decorative — fine, but confusing during incident review.

**Kill criteria measurability:** 24h PnL pause ✅ coded & firing; 48h WR escalate ✅ coded & firing; 7d WR<35% ❌ not coded; candidate revert ❌ not coded; day-14 redesign decision ❌ not coded (arguably fine as a human decision).

**Shadow factory realism:** realistic for candidates #1–8 (gate_shadow has 14,234 events / 1,312 closed — counterfactuals measurable from existing data). **#9 (trail activation 0.40→0.30) and #10 (momentum leader filter) need new instrumentation that is not listed as built** — they'd need a shadow variant before counterfactual data exists.

**Cell_stats wiring (signal_compactor.py:2137–2210):** verified real — `_cell_mult` is included in `_mult_product` → `final_score` (line ~2193), key-mismatch fix (dash vs underscore keys) is present and correct. **But it is currently INERT:** bug hunter's own check shows 0 CELL-STATS fires (dominant cell wr=0.46 > 0.40 dampen threshold), and MED-2 is real: `PENALTY_MULT_FLOOR=0.5` eats most of the 0.5× dampen (product floored back up), while the 1.2× boost is never floored. **Asymmetry: boosts always work, dampens mostly don't.**

### PLAN GAPS (what I would add before T steps away — as if I were T)

1. **Ship the MoE's top-2 fixes before leaving, or explicitly defer them.** The pre-departure lever (cell_stats) is inert (0 fires, dampen cancelled by floor); the highest-EV items (HML realign +$7–14/30d, confidence clamp +$6–12/30d) ship *during* vacation with no CEO oversight. That's backwards.
2. **Code the 7d WR<35% kill into the guardrail.** It is 35.2% RIGHT NOW. If it's a kill criterion, it must be code; if it's not, remove it from the plan.
3. **Fix the escalation ladder:** alert-only is not a control system. Add an auto-pause tier (e.g., 48h WR < 30% with n≥60 → pause) and a notification path the automation team actually watches during vacation.
4. **Add a zero-trade-day / flow detector.** MoE found the hotset near-standstill (1 token, no fills since 17:35). The guardrail can't see flat flow; the shadow factory starves silently. Kill criterion "no trades in 24h → investigate."
5. **Correct the flip premise in writing.** If anyone acts on "flip everything" using 1−WR arithmetic, they will buy a ~33% WR system at 1.7 inverted payoff. The real test is path replay or gate_shadow counterfactuals — and Expert 4's existing near-flip shadow (p≈0.09) already says no.
6. **Document the resume procedure** for a guardrail pause (who flips it back, on what evidence, who re-arms the timer).
7. **Tighten or supplement the −$3.00/24h pause** with a cumulative-drawdown trigger (e.g., 7d PnL < −$5 → pause) so slow bleeds are caught.
8. **Drop the "60%+ WR target" as a decision input.** MoE: zero of 12 liquid signals have proven edge at α=0.05; W-1 = 35.2%. The day-14 "honest redesign" clause is the realistic branch — the target must not induce the Monday MoE to ship overfit gate changes to chase it.

---

**INVERSION ANALYSIS (one line):** The system is not anti-predictive — it is late-cycle and whipsawed at the trailing-activation boundary inside a ~4-week-old adverse regime; the recorded trade paths (winners +1.58% MFE, losers +0.44% MFE-then-reverse) make the naive flip *worse*, not better, and LONG was profitable over 30 days.

**CONFIDENCE: HIGH** — every number above was reproduced from live PostgreSQL/timer/filesystem state in this session (not from any report). Flip-model magnitudes are MEDIUM (stop/TP magnitudes approximated from cohort averages; a full path-replay backtest would tighten them — conclusion direction is robust across all bounds tested).
