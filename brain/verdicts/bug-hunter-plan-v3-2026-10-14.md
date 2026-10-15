# Bug Hunter: Plan v3 + MoE Panel Final Pre-Departure Verification

**Date:** 2026-10-15 (00:30–01:10 UTC)
**Scope:** Vacation plan v3, MoE panel 20261014T182556Z, guardrail pause path, cell-stats wiring, T simulator, inversion claim, conf>100 rows.
**Method:** All numbers reproduced live against PostgreSQL (`brain.trades`, anchored to the panel's synthesis time 2026-10-14T18:25:56Z where applicable), SQLite DBs, systemd, and logs. Dry-run of the pause path with mocked side effects. No results from memory.

---

# VERDICT: SAFE TO DEPART — after one NEW BLOCKER found & fixed in-session (`847beba2`)

The v3 plan, the MoE panel numbers, and the `55d6c8d1` guardrail fix all hold up under independent verification. But verification uncovered a **new blocker**: the 55d6c8d1 pause was silently undone ~6 minutes later by `pipeline_watchdog.py`, which re-armed the pipeline timer when the heartbeat went stale — resuming LIVE trading while the guardrail's own timer was stopped. Fixed, tested, committed as `847beba2`. With that fix, the guardrail is now a real hard stop.

---

## Check Results

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | MoE claims vs PostgreSQL | **PASS** | Anchored 30d window (2026-09-14T18:25:56Z → 2026-10-14T18:25:56Z): n=**767**, net **-$2.94** — exact. `hard_max_loss` n=**128**, **-$14.76**, 0 wins — exact. conf 95+ band n=394/395*, **-$5.88**, WR 44.4% (MoE's 44.3%) — matches. conf 70–84 band n=158/159*, **+$6.74** (MoE +$6.59), WR 51.3% — matches. *±1 trade boundary drift vs panel's live snapshot; PnL identical. |
| 1b | "0/12 signals have proven edge" | **PASS (with nuance)** | Independent binomial test, 12 liquid signals (n≥10), anchored window: **0/12 significant at α=0.05 two-sided**. Best: bb-squeeze+ 62.0% n=71, p_two=0.0568 (MoE quoted 0.057 — correct). **Nuance:** one-sided p=0.0284 — bb-squeeze+ IS significant one-sided. MoE's claim is true for the conventional two-sided test; bb-squeeze+ deserves the shadow-scale to n≥100 they recommended. |
| 2 | Inversion claim (SHORT 33%, LONG 37%) | **PARTLY — numbers ~real, conclusion FALSE (see below)** | User's denominators (151 LONG, 49 SHORT) are an exact match for `trades.json` rolling-200 (not a strict 7d window; covers Oct 7–14). My live read: trades.json LONG 54/151=35.8%, SHORT 15/49=30.6% (user read it minutes earlier: 56/151, 16/49). PostgreSQL true 7d: LONG 53/147=36.1%, SHORT 15/46=32.6%. **System is NOT anti-predictive — proof below.** |
| 3 | Guardrail pause path (55d6c8d1) | **FAIL → FIXED (`847beba2`)** | 55d6c8d1 itself works: `disable_live_trading()` exists, importable, closes HL positions + writes flags; timers stop. BUT: (a) **`pipeline_watchdog.py` re-armed the paused pipeline ~6 min later** (heartbeat >300s stale → CRITICAL → `systemctl restart hermes-pipeline.timer`) → decider resumed **LIVE** (constant stays True) with nothing to re-pause; (b) `hermes-decider.timer` **does not exist** (stop returns rc=5; decider_run is a pipeline step — harmless but shows the fix targeted a phantom unit); (c) stopping the timer alone doesn't stop an in-flight `hermes-pipeline.service` run. All three fixed; dry-run verified order (watchdog → pipeline.service → pipeline.timer → positions closed), marker written, live system untouched. |
| 4 | Cell-stats wiring | **PASS** | SQL valid, parameterized, exact-key-first fix (`0ebfd16b`) verified material: `pump-chain+` LONG EXTREME = 45.9% WR/85T (loser) vs `pump_chain` = 63.6%/22T (tradeable) — hitting the wrong row would have BOOSTED a loser. `finally: _cs_conn.close()` present. Multiplier math correct (1.2/0.5/neutral). **CELL-STATS tag IS firing** — 33× today 17:43–23:34 (`losing cell pump-chain+ wr=37% n=30 → 0.5x` for APT/IOTA/JUP/BABY/ICP LONG). The plan's "firing: 0 / all neutral" is **stale** (written before 17:43). |
| 5 | Plan consistency | **PASS (doc drift noted)** | All 8 cited commits exist (`12f14b88`, `0ebfd16b`, `32266d59`, `a907936c`, `84a38707`, `d43afbc0`, `21a20ced`, `55d6c8d1`). Kill criteria are specific + measurable (7d WR<35%, 24h PnL<-$3.00, 10T/-$1.00, day-14 n≥30). Drift: plan doesn't reference `a9f4b2cb` (7d WR criterion added 00:03) or `847beba2`; gate_shadow stats stale (plan 14,234/1,312 → now 16,123/14,433); candidate #3 (CONFLUENCE relaxation) now looks **negative** (see below). |
| 6 | conf>100 rows | **CONFIRMED** | Anchored 30d: **119 rows (15.5%)**, all-time **315**, max **499.4**. Breakdown: pump-chain- 25 (avg 109.6), pump-chain+ 17 (avg 171.0), pullback-entry- 16 (avg 102.9 despite file cap 88; 113 all-time rows >88), volume-breakout-long+ 9, bb-bounce-v2-long+ 9, ai-trader+ 5 (avg 168.2 — matches MoE), +~20 singletons. **Live proof during verification: MNT LONG conf=162.9 EXECUTED 00:29:20, trade is OPEN right now with confidence 162.90 in brain.trades.** MoE's SYRUP conf=162.19 line at 18:46:57 also verified verbatim in pipeline.log. |
| 7 | T simulator | **PASS** | 74 vectors indexed, dim=384; `list` and `search` both run clean; search for "should we disable a losing signal" returned 3 relevant past decisions — including the 2026-04-06 **WR flip test FAILED** decision (see below). No handle leaks. |

---

## Bugs

### 🔴 BLOCKER-1 (FIXED in-session, `847beba2`) — Watchdog silently un-pauses the guardrail
- **Where:** `scripts/pipeline_watchdog.py:45-71` (lock check) + `:190-197` (restart) × `scripts/vacation_guardrail.py:93-100` (pause).
- **What:** 55d6c8d1 stopped `hermes-pipeline.timer`. The heartbeat stops updating → `pipeline_watchdog.py` (every 2 min via `hermes-watchdog.timer`) flags heartbeat >300s as CRITICAL → `restart_pipeline()` → `systemctl restart hermes-pipeline.timer`. The restarted decider runs `paper = not is_live_trading_enabled()` which reads **only the static constant** (=True) → **LIVE trading resumes ~6 min after the "pause"** — and the guardrail stopped *its own* timer, so nothing re-pauses. A CRITICAL alert says "TRADING PAUSED" while real orders flow: the exact failure mode the first blocker fix was meant to prevent.
- **Also fixed in the same commit:** pause now writes `data/vacation_pause.json` (watchdog checks it in both the lock check and `restart_pipeline`); stops `hermes-watchdog.timer` before the pipeline; stops `hermes-pipeline.service` (in-flight run) not just the timer; removed the nonexistent `hermes-decider.timer` from the stop list.
- **Verified:** py_compile OK; functional tests (marker present → lock-check 'ok', restart refused; marker absent → restart proceeds, no regression); full dry-run with mocked `subprocess.run` + `disable_live_trading` → correct call order, marker written/removed; live system confirmed untouched afterwards (all timers active, no marker).
- **Resume procedure for T/automation:** delete `/root/.hermes/data/vacation_pause.json`, then `systemctl start hermes-pipeline.timer hermes-watchdog.timer hermes-vacation-guardrail.timer`.

### 🟠 MEDIUM-1 — Guardrail is 0.1 pp from auto-pausing right now
Live check at 00:08 UTC: 7d WR = **35.1%** vs `WR_7D_PAUSE = 35.0` (added `a9f4b2cb` at 00:03), n=194. One more losing close trips the pause. That's the kill criterion working as designed — but T should expect the system may be PAUSED (and stay paused, post-fix) shortly after departure. 24h PnL is -$0.08 (far from -$3.00); 48h WR 29.8% escalation is active (alerts every 30 min).

### 🟡 LOW-1 — Plan text stale on CELL-STATS
Plan lines 38/160 say "CELL-STATS firing: 0 / all signals resolve neutral". It has fired 33× today since 17:43 (pump-chain+ LONG HIGH cell, wr=36.7%<40%, n=30). The wiring is live and dampening. Update plan text.

### 🟡 LOW-2 — Shadow candidate #3 (CONFLUENCE-GATE relaxation) weakened
gate_shadow now: closed-with-outcome n=312, WR **50.6%**, aggregate **-$1.71**. Relaxing the confluence gate to let single-source pump-chain+ through would, on current data, ADD losses. Recheck before enforcing. (Candidates #1/#2 hold: SHORT-CONTINUUM 32.5% WR/-$5.58 — relax is wrong; SHORT-NEUTRAL 66.7%/+$2.58 — relax looks good.)

### 🟡 LOW-3 — MoE minor number drift
MoE "pump-chain+ avg conf 146" doesn't reproduce (I measure 171.0 for conf>100 pump-chain+; 164 incl. composites). Doesn't affect the conclusion (>100 conf exists and is executing). Also Expert 2 says "125 hard_max_loss exits" in one place vs the correct 128 elsewhere. Cosmetic.

### 🔵 INFO — 30d exit distribution (Expert 3 verified)
profit-monster-trail 225T +$11.39 | atr_sl_hit 221T -$6.81 | **hard_max_loss 129T -$14.82** | hard_sl 49T -$3.13. HML is 16.9% of all trades, 0% WR by construction. `CUT_LOSER_PNL=-3.00` → -0.6% price @lev5 vs `SL_PCT_MIN=1.3%` — the ATR stop never governs, exactly as the MoE's Risk expert said.

---

## Is the inversion claim real? — **NO. Do not flip.**

**The numbers are approximately real** (they're a `trades.json` rolling-200 snapshot ≈ last 7 days: SHORT ~31–33%, LONG ~36–37%). **The conclusion — "the system is anti-predictive, flip it" — is wrong.** Four independent proofs:

1. **Gross (pre-fee) PnL is POSITIVE.** 7d: +$1.14 gross (LONG +$1.01, SHORT +$0.14) → net -$0.61 after $1.75 fees. 30d: +$2.46 gross → net -$3.43 after $5.89 fees. An anti-predictive system loses BEFORE costs. This one earns a small directional edge and pays it to fees. **Flipping inverts the +$1.14 gross to -$1.14 and keeps the same fees → ≈ -$2.89/7d. Flipping loses ~4.7× more.**
2. **The "67%/63% if flipped" arithmetic is invalid.** Flip direction and the payoff asymmetry flips too: 7d LONG avg win $0.1385 / avg loss $0.0894 (payoff 1.55, breakeven WR 39.2%). Flipped: avg win $0.0894 / avg loss $0.1385 → breakeven WR **60.8%**. You'd need 61%+ just to break even before fees. Low WR + payoff >1 is a coherent trailing-stop structure, not a wrong-side signal.
3. **WR is dominated by an exit-structure artifact, not direction.** 30d WR **including** `hard_max_loss` exits = 44.6%; **excluding** them = **53.8%**. HML is 16.9% of trades, 0% WR *by construction* (forced loss exit at -0.6% price @lev5). The headline WR is largely the HML bill, which MoE fix #1 (realign HML with the ATR stop) attacks directly.
4. **T already tested this exact hypothesis.** `brain/DECISIONS.md` 2026-04-06: *"WR flip test FAILED — signal direction not systematically inverted… Flip deployed 2026-04-05, ran 2 trades, both failed… Historical 79% SHORT-wrong finding did NOT replicate in live trading. Focus on signal quality improvements instead."* Revisit condition: WR <30% on a larger sample — 7d is 35.1%, not met.

**What the low WR actually means:** the system is in a significant losing *regime* (7d WR 35.4%, p=6.5e-5 vs 50%, per MoE — reproduced), fees eat the gross edge (~$0.009/trade), and the HML left tail plus the broken-SHORT tail destroy the rest. The fixes are the MoE's ranked list (#1 HML realign, #2 clamp confidence, #3 kill broken tail) — not flipping.

---

## MoE panel quality

The panel's numbers reproduce to the dollar on an anchored window — this is one of the most reliable MoE outputs to date. Confidence 0.75 is fair. The confidence-inversion finding is **live and worse than historical**: a trade executed at conf=163 **during this verification session** (MNT LONG, still open). Fix #2 (clamp `final_confidence ∈ [0,100]` at the execution boundary) is the highest-leverage code change queued and should ship early in week 1.

## Files changed this session

- `scripts/vacation_guardrail.py` — pause marker, watchdog stop, service stop, phantom unit removed (commit `847beba2`)
- `scripts/pipeline_watchdog.py` — pause-marker awareness in lock check + restart (commit `847beba2`)
- This verdict file.
