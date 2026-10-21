# bug_hunter verdict — all recent changes (last 24h audit)

**Auditor:** bug_hunter subagent (independent, fresh-eyes)
**Date:** 2026-10-21 21:45 UTC
**Scope:** commits 59b1aeec (chop SL floor), 4e24544f/d1fb3d74 (size-reduce guardrail), 8dd24778 (vacation mode switch), 55d6c8d1/847beba2 (guardrail pause-path fixes), plus live pipeline health, position-size floor, and protected-constants regression.

---

## VERDICT: ISSUES FOUND — no blockers, 1 HIGH (fix does not fix), 3 MED, 4 LOW

Nothing shipped in the last 24h can break the live pipeline, leak money below the HL notional floor, or unwind a guardrail pause. But the headline fix of the day (**59b1aeec, chop SL widening**) does **not** touch the code path that actually produced the stop-outs it cites — those were written by the `SOFT TRIGGER` engine in `position_manager.py`, which is untouched. Separately, the **size-reduce guardrail is currently inert on live position sizes** (structural bypass in `brain.py` + the $11 floor dominating at current account size).

---

## Checks

### 1. Chop SL widening (59b1aeec) — ⚠️ PASS (implementation) / FAIL (effectiveness vs stated goal)

| Sub-check | Result |
|---|---|
| Syntax (`py_compile`) | **PASS** |
| Condition `volatility_regime in ('FLAT', 'NORMAL')` correct | **PASS** — DB regime values are exactly `NORMAL/EXTREME/FLAT/HIGH` (7d census: 61/65/14/22), uppercase match |
| `ATR_SL_MIN_ACCEL` NOT changed | **PASS** — still `0.003`, hermes_constants.py:727 "do NOT change" respected |
| Diff scope | **PASS** — 7 lines added to tpsl_utils.py only, no live flag touched |
| Loaded without restart | **PASS** — `position_manager` is in `STEPS_EVERY_MIN` (run_pipeline.py:36), re-executed every cycle; new code active since 21:23 |
| **Fix actually widens the SL on the trades T cited** | **FAIL — see BUG-1** |

**Code-path trace (ran it, didn't read it):** A/B harness (`/tmp/ab/ab_run.py`, 42-scenario grid: LONG/SHORT × FLAT/NORMAL/HIGH/EXTREME × new-trade/in-profit small-peak/in-profit big-peak/in-loss/no-peak-tracking × trail-override, identical mocked ATR, old module from `git show 59b1aeec^`):

- 16/42 scenarios differ old→new; **14 of them differ only in the reported `eff_sl_pct` (0.56%→0.60%) — final `new_sl` byte-identical**.
- Only `est_in_profit_no_peak_tracking` (highest_price == 0) changes the real SL: 0.46%→0.50% from entry.
- Reason: for established trades with a tracked peak, the MIN GUARD (tpsl_utils.py:581-639) and POST-GATE (798-867) recompute `new_sl` from the **1.2% trail distance / 1.5% entry floor**, discarding `eff_sl_pct` entirely; and for tight per-trade trail overrides the BUG-031 cap (line 559, `max(min(eff, _trail_dist), 0.003)`) clamps the new 0.60% floor back down to the trail distance. Verified: `trailing_distance=0.4%` scenario is identical old vs new.

**Root cause of the cited stop-outs (log-proven, not inferred):** BTC #16342 SL 84365.64 = entry −0.31%; NEO #16344 −0.33%; SOL #16346 −0.23% (DB `stop_loss` queried directly). First writer in pipeline.log:

```
line 3068641: 2026-10-21 17:38:17 SOFT TRIGGER BTC LONG SL set to 84365.641500
  (was 84351.683500, 0.3% trail from 84619.500000, age=2.5h, pnl=-0.01%)
```

That is `position_manager.py:3518-3568` — the SOFT PEAK-EXIT TRIGGER, hardcoded `SOFT_TRAIL_PCT = 0.003` / `SOFT_TRIGGER_HOURS = 2.0`, which pins SL 0.3% from current price after 2h at pnl ≤ 0. Today it fired 14× on BTC + 1× on NEO. tpsl_utils' `MIN_SL_PCT` never governs those levels (at 18:48 the BTC line even shows `eff_sl=1.200%` while the stored SL stays at −0.31%, held by the ratchet).

**Net:** the change is safe and adds a 0.60% floor to one narrow branch, but the trades in the commit message would have stopped out identically. → BUG-1 (MED: no harm done, but the directive is unfulfilled and T will re-report it).

### 2. Size-reduce guardrail (4e24544f, d1fb3d74) — PARTIAL PASS

| Sub-check | Result |
|---|---|
| WR trigger writes size-reduce instead of pausing | **PASS** — vacation_guardrail.py:389-398, `size_reduce=True` only when 24h PnL OK |
| Hard pause still works for 24h PnL < −$3 | **PASS** — verified by driving the REAL `check_guardrails()`+`main()` through 10 metric scenarios with stubbed side-effects (`/tmp/ab/test_guardrail_logic.py`): 24h −3.50 → `pause_trading()` fires (alone and combined with WR breach); resume never fires while 24h below −3 |
| $11 floor — 3 layers | **PASS** — (1) `decider_run.py:266-267` floors after 0.5×; (2) call-site re-caps at `decider_run.py:822` (delayed path), `:2302` (main), `:2345` (post SL-zone reduce); (3) `brain.py:473-475` hard-rejects `< HL_MIN` and `brain.py:586` floors the `size_usdt_override` chain. Live test: raw base 10/11/20/21/25/100/300 → 11/11/11/11/12.5/50/150 — never below $11 |
| Flag currently active? | **ACTIVE** — `data/vacation_size_reduce.json`: `size_reduce=true`, `size_multiplier=0.5`, written 2026-10-20T14:57Z, reason "7d WR 34.9% < 35.0% AND pnl_7d $-2.80 < $-2.00 (169T)" |
| **Does the reduce actually reduce live size?** | **FAIL — see BUG-2** |

### 3. Vacation mode switch (8dd24778) — PASS with note

Syntax OK; switch file exists (`data/vacation_mode.json`, ON since 2026-10-16T19:58Z, rules: shadow_first / no_enforcement_flips / no_constants_change / no_signal_enable_disable / guardrails_active / moE_weekly / ceo_every_30min). `status/on/off` CLI correct. **Note (LOW):** no script anywhere in the repo reads `vacation_mode.json` — `grep -rn vacation_mode --include=*.py` returns only `vacation_mode.py` itself. The switch is a documentation/agent-directive flag, not an enforced mode. That matches how it's been used (prompts/audits reference it), but "rules are correct" only holds because humans/agents honor them.

### 4. Guardrail pause-path fixes (55d6c8d1, 847beba2) — PASS

- `disable_live_trading()` called on pause: **YES** — vacation_guardrail.py:167, with `ai-trader-manual` positions exempt (:152-167).
- Pipeline timers stopped: **YES** — marker written first (:122), then `hermes-watchdog.timer` (:129), then `hermes-pipeline.service` **and** `.timer` (:137-143); guardrail timer stays armed for auto-resume (:174-178).
- Watchdog respects `vacation_pause.json`: **YES** — pipeline_watchdog.py:39-42 (marker const), :56-58 (`check_pipeline_lock` returns ok), :193-194 (`restart_pipeline` refuses). Historical confirmation in `automation/error_alerts.md:1187/1192`: paused 04:08 and 07:08 UTC Oct 16, pipeline not restarted.
- **Edge (LOW):** `check_failed_services()` (pipeline_watchdog.py:206-235) restarts any *failed* hermes service with **no** PAUSE_MARKER guard — the same unwind class 847beba2 fixed for `restart_pipeline()`. `systemctl stop` lands in `inactive` (not `failed`), so today's path is safe, but a service that crashes into `failed` during a pause window would be silently restarted. Recommend skipping `hermes-pipeline.*` / `hermes-watchdog.*` while the marker exists.

### 5. Auto-clear size-reduce (d1fb3d74) — PASS

Condition at vacation_guardrail.py:364-365: `(not should_pause and marker and ((wr_7d >= 37 and pnl_7d >= -2) or pnl_7d >= 0))`. Verified with real code, controlled metrics:
- WR 37.5 / pnl7d −1.00 → **clears** ✓
- pnl7d +0.10 (WR still 34) → **clears** ✓
- WR 37.5 / pnl7d −2.50 → **does NOT clear** (aging-artifact guard works) ✓
- healthy + flag present → clears ✓
- flag correctly still active right now: current 7d WR 35.8% (<37) and pnl7d −$3.46 (<0) → no clear expected; file still present ✓

### 6. Live pipeline health — PASS

- `tail -200 logs/pipeline.log | grep -cE "Traceback|ERROR"` → **0**
- `systemctl is-active hermes-pipeline.timer` → **active** (cycle #251618 at 21:32, hotset/compactor/breakout/signals all rc=0)
- Trades last hour: **0 opens, 0 closes, 0 open positions** (quiet tape; last close 19:01 UTC). Last open was POL #16349 at 18:30.
- Kill switch coherent: `/var/www/hermes/data/hype_live_trading.json` = `live_trading: true`.
- Watchdog + guardrail timers both firing on schedule (guardrail last run 21:27:22, journal clean).

### 7. Position size floor — PASS

`_get_dynamic_position_size()` **cannot** return below $11 (tested live with patched base sizes, see check 2). `HL_MIN_NOTIONAL_USDT = 11.0` (hermes_constants.py:610), `DEFAULT_TRADE_SIZE_USDT = 11.0`. Every live trade since Oct 20 14:57 shows `amount_usdt` $11.10 or $22.10 (= base × 2.0 cluster/fav mult) — none below the floor, none at a halved size.

### 8. Regression check — PASS

`grep -E "CONFLUENCE_REQUIRED|LIVE_TRADING_ENABLED|CUT_LOSER_PNL|ATR_SL_MIN"` + import test:
- `LIVE_TRADING_ENABLED = True` (line 33) — unchanged in 7d
- `CONFLUENCE_REQUIRED = True` (line 3524) — unchanged in 7d
- `CUT_LOSER_PNL = -4.00` — last change Oct 15 (CEO), outside window
- `ATR_SL_MIN = 0.015`, `ATR_SL_MIN_INIT = 0.015` — last change Oct 16 (CEO), outside window
- `ATR_SL_MIN_ACCEL = 0.003` — **untouched**
- Constants touched in last 24h (diffed): FAVORITES/LOSERS sets (auto-updater), new `PRICE_SANITY_MAX_DRIFT_PCT = 0.5` (additive), `SHORT_RSI_*_PUMP_CHAIN` 40→45 (pre-registered auditor revert, documented trigger hit), `SHADOW_BYPASS_SIGNALS` registry (shadow-only, key/source fix from prior bug_hunter FAIL→fix cycle). **No protected flag altered.**

---

## Bugs

**BUG-1 — MED — Chop SL widening (59b1aeec) does not reach the stop-outs it cites.**
The −0.23%/−0.31%/−0.33% SLs were written by `SOFT TRIGGER` (`position_manager.py:3518-3568`, hardcoded `SOFT_TRAIL_PCT = 0.003`, fires at age ≥ 2h with pnl ≤ 0), not by `MIN_SL_PCT` in tpsl_utils. Log line 3068641 proves BTC's stop origin; DB rows 16342/16344/16346 confirm distances. Additionally, for peak-tracked established trades tpsl_utils' `eff_sl_pct` is overwritten by the 1.2%-trail MIN GUARD anyway, so the new 0.60% floor changes the real SL only when `highest_price/lowest_price == 0`.
*Fix:* widen `SOFT_TRAIL_PCT` (or make it regime-aware, 0.30%→0.60% in FLAT/NORMAL) — and move `SOFT_TRAIL_PCT`/`SOFT_TRIGGER_HOURS` into `hermes_constants.py` first (convention: no hardcoded constants). This needs CEO sign-off since it changes exit behavior.

**BUG-2 — HIGH (guardrail intent) — Size-reduce flag never reaches the HL order size.**
`decider_run._get_dynamic_position_size()` correctly halves `_trade_size` and floors it at $11 — but `brain.py add_trade` ignores the passed `amount_usdt` for sizing and recomputes `size_usdt_override = _get_trade_size_usdt() * _size_mult` (`brain.py:584-586`; `amount_usdt` is used only for the $11 rejection gate and DB signal-level bookkeeping — its own comment says "this chain bypasses every cap in decider_run"). `mirror_open` then skips its own sizing when the override is set (hyperliquid_exchange.py:1055-1056). So the 0.5× multiplier is discarded for **every** trade. Compounding this, at the current account size the reduce is impossible anyway: base = $11.10 → 0.5× = $5.55 → clamped back to the $11 floor (empirically: all trades since the flag are still full $11.10/$22.10).
*Fix:* apply the multiplier in the one place all paths converge — `hyperliquid_exchange._get_trade_size_usdt()` (or brain.py's `_precomputed_size`) — reading `vacation_size_reduce.json`. Note the guardrail can only bite once 7% of withdrawable ≥ ~$22 (account ≈ $315); below that, "reduce to minimum" is a no-op by definition. CEO decision needed on what "reduce" means at the floor (e.g., cut leverage instead of notional).

**BUG-3 — LOW — `check_failed_services()` can restart a paused pipeline.**
pipeline_watchdog.py:206-235 restarts failed hermes services with no `vacation_pause.json` check. Guard `hermes-pipeline.service`/`hermes-watchdog.service` behind the marker.

**BUG-4 — LOW — vacation_mode.json has no code consumer.**
The on/off switch changes nothing at runtime (see check 3). Either wire it into the guardrail/decider or document it as advisory-only so nobody assumes the rules are enforced.

**BUG-5 — LOW — docstring/constant drift in the size-reduce path.**
`_get_dynamic_position_size` docstring says "cuts position sizes to 30%"; the file writes `size_multiplier: 0.5`; the function default is `0.3` when the key is missing. Same flag, three different numbers.

**BUG-6 — LOW — hardcoded constants in position_manager soft trigger.**
`SOFT_TRIGGER_HOURS = 2.0`, `SOFT_TRAIL_PCT = 0.003` at `position_manager.py:3517-3518` violate the repo convention (all tunables in `hermes_constants.py`). Also flagged in BUG-1's fix.

**BUG-7 (observation) — LOW — vacation rule "no_constants_change" vs. actual 24h activity.**
`hermes_constants.py` changed 5× in 24h (FAVORITES/LOSERS auto-update, `PRICE_SANITY_MAX_DRIFT_PCT`, pump-chain RSI floor revert 40→45, SHADOW_BYPASS registry). Each is documented/pre-registered and none is a live-behavior flip except the pump-chain revert (tighter, trigger-backed). Worth stating explicitly in the vacation doc what "no constants change" exempts, to avoid the rule becoming noise.

---

## Current system state (2026-10-21 21:45 UTC)

- **Vacation mode:** ON (since Oct 16) — advisory only (BUG-4).
- **Size-reduce guardrail:** ACTIVE, 0.5× written Oct 20 14:57Z; currently *correct* not to clear (7d WR 35.8% < 37%, 7d PnL −$3.46 < 0); currently *ineffective* at execution (BUG-2).
- **Hard pause:** not triggered. 24h −$1.09 / 40T / 35.0% WR; 48h −$1.25 / 60T / 31.7% WR (**escalation alert firing every 30 min** — WARNING only, no action path; alert spam is bounded to last-50).
- **Live trading:** enabled (constant + kill-switch JSON both true), 0 open positions, 0 trades in the last hour.
- **Pipeline:** healthy — timer active, 0 Tracebacks/ERRORs in last 200 lines, cycle #251618.
- **Position sizing:** floor $11 everywhere; live base $11.10 (7% of withdrawable ≈ $158); sizes observed $11.10 / $22.10 (×2 mult).
- **Chop SL floor:** live since 21:23, no restart needed; effect ≈ nil except peak-untracked trades (BUG-1).

## Evidence / artifacts

- A/B scenario harness: `/tmp/ab/ab_run.py`, outputs `/tmp/ab/new.out`, `/tmp/ab/old.out`, pre-change module `/tmp/ab/old_tpsl_utils.py`
- Guardrail decision-logic test (10 scenarios, real `check_guardrails()`+`main()`, stubbed side-effects): `/tmp/ab/test_guardrail_logic.py`
- DB queries run against PostgreSQL `brain` (trades #16342/16344/16345/16346/16347/16348, guardrail metric SQL matching vacation_guardrail.py exactly)
- Log evidence: `logs/pipeline.log` lines 3033386-3040010 (TPSL trace), 3068641 (SOFT TRIGGER origin of BTC stop)
