# Bug-Hunter Verdict: Vacation Guardrail Size-Reduce (commit 4e24544f)

**Date:** 2026-10-17 17:15 UTC
**Scope:** `scripts/vacation_guardrail.py`, `scripts/decider_run.py` — WR-triggered pause → 30% position-size reduction
**VERDICT: ✅ SAFE** — 1 medium + 1 low finding (neither blocks live trading; both in safe direction)

## Critical question: can position size ever go below $11?

**NO.** Enforced at three independent layers:

| Layer | Mechanism | Evidence |
|---|---|---|
| 1. Base sizing | `_get_dynamic_position_size()` floors at `HL_MIN_NOTIONAL_USDT` after multiplier; falls back to `DEFAULT_TRADE_SIZE_USDT=11.0` on any error/missing-JSON/corrupt-JSON | Extracted production function via `ast` and swept dynamic $5–$400 × multipliers 0.01–2.0: **0 cases returned < $11** (13/13 assertions pass) |
| 2. Decider callers | Both execution paths re-cap after ALL multipliers: `max(_trade_size, HL_MIN_NOTIONAL_USDT)` at decider_run.py:822 (delayed entry) and :2302 + :2345 (main path incl. SL-zone shrink) | Code read + test |
| 3. brain.py gate | `add_trade` rejects `amount_usdt < HL_MIN_NOTIONAL_USDT` outright (brain.py:470) | Code read |

## Checks

1. **Syntax** — **PASS**. `ast.parse` clean on both files.
2. **Size-reduce logic / edge cases** — **PASS** (13/13). Tested the REAL function text (ast-extracted, mocked account):
   - dynamic=$12 ×0.3 → **$11.00** (floor) ✓ | dynamic=$50 ×0.3 → **$15.00** ✓ | dynamic=$10 ×0.3 → **$11.00** (DEFAULT, reduce block skipped) ✓
   - JSON missing → full dynamic, no crash ✓ | JSON corrupted → full dynamic, no crash ✓ | empty file (write race) → no crash ✓
   - `size_reduce:false` → full size ✓ | multiplier missing → defaults 0.3 ✓ | multiplier=0 / negative → floor $11 ✓ | multiplier='abc' → full size, no crash ✓ | API error → DEFAULT $11 ✓
3. **Pipeline running** — **PASS**. `hermes-pipeline.timer` active (last run 17:10, next cycle confirmed); watchdog timer also active (was restored after the earlier pause).
4. **Size-reduce flag exists** — **PASS**. `data/vacation_size_reduce.json`: `size_reduce: true`, `size_multiplier: 0.3`, freshly rewritten by the 17:08:28 guardrail run.
5. **Guardrail no longer pauses on WR** — **PASS**. Functional test (real module, mocked DB): WR-trigger-only → `write_size_reduce` called, `pause_trading` NOT called. Confirmed live in journalctl: 17:08:28 run logged "📉 SIZE REDUCED to 30% (not paused)" while 24h PnL ($-0.92) was above -$3.
6. **Resume clears both markers** — **PASS**. REAL `resume_trading()` (mocked subprocess/kill path): removed BOTH `vacation_pause.json` and `vacation_size_reduce.json`, restarted both timers, rewrote kill JSON. BUT see finding BH-SR-1 — resume is unreachable in size-reduce-only mode.
7. **Live pipeline log** — **PASS**. Zero errors/tracebacks/`dynamic sizing failed` since 16:57. No trades have opened since the change (decider: 0 entered, 1 skipped), so no real fill to inspect yet. Instead I ran the ast-extracted production function against the LIVE account: base=$11.00 → returned **$11.00** (0.3× floored), flag present and absent both ≥$11.
8. **Regression: hard-pause intact** — **PASS**. 24h PnL=-$5 only → hard pause (real `pause_trading`: writes marker first, stops watchdog→pipeline.service→pipeline.timer, closes non-manual HL positions). Both breaches → pause wins over size-reduce. Boundary pnl=-$3.00 exactly → no pause (strict `<`, as designed).

Guardrail routing suite: **12/12 scenarios PASS** (`/tmp/bughunter_guardrail_test.py`, `/tmp/bughunter_size_test.py`).

## Findings

### BH-SR-1 — MEDIUM (functional, not safety): size-reduce flag NEVER auto-clears
`should_resume` (vacation_guardrail.py:89) requires `os.path.exists(PAUSE_MARKER)`. Size-reduce-only mode never writes a pause marker, and `resume_trading()` is the ONLY code that removes `vacation_size_reduce.json`. So when WR recovers (≥37% or pnl_7d ≥0), the flag persists **indefinitely** — sizing stays at 30% forever unless a hard pause later happens and auto-resumes, or it's deleted manually. The live system is in exactly this state right now (flag on, no pause file). Direction is safe (never oversized), but it silently caps profits and defeats the recovery intent.
**Suggested fix:** in `main()`, if `SIZE_REDUCE_MARKER` exists and metrics recovered (`wr_7d >= WR_7D_RESUME or pnl_7d >= 0`) and not `should_pause`, remove the marker + log. (Same hysteresis as pause-resume.)

### BH-SR-2 — LOW: non-atomic write + fail-open read
`write_size_reduce()` truncates then writes (`open('w')`). A decider read in the truncate window (or after a crash mid-write) sees empty/partial JSON → `json.JSONDecodeError` → inner `except: pass` → **full size** for that run, silently. Probability is tiny (rewrite every 30 min vs ms read window), impact = one run unsuppressed — floor still holds at $11.
**Suggested fix:** write to `tmp` + `os.replace()` (atomic); log a WARN when the flag file is unreadable instead of silent pass.

## Notes for T / CEO
- **The 30% cut is currently inert.** Live account base size is exactly **$11.00** (7% of withdrawable ≤ $11), so 0.3× = $3.30 → floored back to $11. Trades are already at the minimum; the multiplier only starts biting when base > ~$36.67 (withdrawable ≳ $524). At today's balance the guardrail adds no extra loss mitigation beyond the floor — by design of the floor, not a bug.
- Current metrics at check time: 24h 13T WR 23.1% $-0.92 | 48h 63T WR 39.7% $-1.48 | 7d 209T WR 34.4% $-2.71 → WR trigger correctly active, PnL pause correctly NOT active.
- Kill switch JSON coherent (`live_trading: true`, resume reason recorded); manual CEO BTC trade exempt and still open.

*Tests: `/tmp/bughunter_size_test.py` (13 assertions + 8 multiplier sweeps), `/tmp/bughunter_guardrail_test.py` (12 scenarios incl. real pause/resume functions with mocked subprocess). No live system state was modified — all timers/DB/kill-switch paths mocked; live flag file moved aside and restored byte-identical during the account test.*
