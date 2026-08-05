# Subagent Timeout → False Positives (2026-05-19)
**Date:** 2026-05-19
**Context:** Delegated full trading system audit to ai-engineer subagent. Subagent timed out at 600s with 40 API calls completed.

## What Happened

1. Subagent delegated audit of Hermes trading system (brain.py, hl-sync-guardian.py, hermes-trades-api.py, position_manager.py, hyperliquid_exchange.py, signal_compactor.py, decider_run.py)
2. Subagent timed out after 600s
3. Main session tried to verify findings with search_files tool — returned empty results for actual deployed constants
4. Switched to `grep` via terminal — found the constants were actually deployed correctly
5. Subagent's "findings" were likely false positives caused by tool errors during timeout

## Key Finding: search_files Returns Empty on Live Code

The `search_files` MCP tool (Ripgrep-backed) returned ZERO matches for `DEFAULT_TRADE_SIZE_USDT` across all .py files in `/root/.hermes/scripts/`, even though:
- The constant IS imported in 11 files (brain.py, cascade_flip.py, position_manager.py, hl-sync-guardian.py, etc.)
- The constant IS used in 22 locations across 8 files

**Root cause:** search_files was running from wrong context or the file paths were different than expected. `grep -rn` via terminal returned correct results immediately.

**Lesson:** When search_files returns empty for a constant that should exist, DO NOT trust the empty result as evidence the constant is missing. Use `grep -rn` via terminal as the verification tool for constant existence checks.

## Also Found: `HL_MIN_NOTIONAL_USDT = 11.0` is Dead Code

- Defined in `hermes_constants.py:252` — but ZERO imports anywhere in the codebase
- Actual HL minimum enforced by `MIN_TRADE_USDT = 10.0` + `MIN_ORDER_BUFFER = 0.10` in `hyperliquid_exchange.py:706-707`
- Per T's instruction, kept in hermes_constants as documentation
- Subagent would have reported this as "unused constant" if it had completed

## Updated (2026-05-20): Task-Type-Aware Timeout

Today a focused 3-4 bug fix task (hyperliquid_exchange.py mirror_open/batch/close bugs) completed in ~394s with 20 API calls — subagent completed successfully, no timeout. The 600s timeout ceiling is task-type-dependent:
- Full pipeline audit (10+ files, 35+ API calls): times out at 600s
- Focused fix task (3-4 bugs, 20 API calls): completes in ~400s

**Rule:** Don't assume timeout from prior experience with a DIFFERENT task type. When giving a subagent a focused fix task, allow 400-450s and monitor for completion. Only re-delegate if the subagent explicitly times out.

## Diagnostic Pattern for Future Delegations

Before trusting any subagent finding about "X is not defined" or "Y constant not found":
```bash
# Always verify in main session FIRST before accepting subagent conclusion
grep -rn "CONSTANT_NAME" /root/.hermes/scripts/ 2>/dev/null | head -20
```

If grep finds it and subagent says it doesn't exist → subagent tool malfunction, not a real bug.

## Files Involved

- `/root/.hermes/scripts/hermes_constants.py:252` — HL_MIN_NOTIONAL_USDT definition (dead code)
- `/root/.hermes/scripts/hyperliquid_exchange.py:706-707` — MIN_TRADE_USDT + MIN_ORDER_BUFFER (actual HL minimum)