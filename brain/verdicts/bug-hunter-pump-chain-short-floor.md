# Bug Hunter: pump-chain SHORT RSI Floor 45→40 (1ac1c92a)

## Verdict: ISSUES FOUND

The constant and both enforcement points are **syntactically correct and crash-safe**, but the change is **functionally a no-op**. A second, unmodified guard (`SHORT_RSI_FLOOR = 45`) fires immediately after the new pump-chain hard floor and blocks the exact 40–45 RSI band the change was meant to open. The intended win band (19T 63.2%WR +$0.48) will still be 100% blocked at both the context gate and exec time.

## Issues Found

### 1. CRITICAL — `SHORT_RSI_FLOOR = 45` collision makes the change a no-op
The commit lowers the **hard floor** to 40 for pump-chain, but a **second, softer floor** (`SHORT_RSI_FLOOR = 45`, `hermes_constants.py:898`) runs directly after it and has **no pump-chain variant**. Runtime gate-order simulation (`python3`, exact code order):

```
RSI= 38.0 | ctx=SKIP(hard)               | exec=BLOCK(hard)              <- both floors block (intended)
RSI= 40.0 | ctx=SKIP(SHORT_RSI_FLOOR)    | exec=BLOCK(SHORT_RSI_FLOOR)   <- intended PASS, actually BLOCKED
RSI= 42.0 | ctx=SKIP(SHORT_RSI_FLOOR)    | exec=BLOCK(SHORT_RSI_FLOOR)   <- intended PASS, actually BLOCKED
RSI= 44.9 | ctx=SKIP(SHORT_RSI_FLOOR)    | exec=BLOCK(SHORT_RSI_FLOOR)   <- intended PASS, actually BLOCKED
RSI= 45.0 | ctx=PASS                     | exec=PASS
```

- Context gate: `decider_run.py:1146` computes `_hard_floor = 40` for pump-chain → passes. Then `decider_run.py:1183-1186` (`_live_rsi_floor < SHORT_RSI_FLOOR` = 45) → `return ('SKIP', ...)` — **no pump-chain carve-out, no bearish override**.
- Exec time: `decider_run.py:2040` computes `_exec_hard_floor = 40` → passes. Then `decider_run.py:2048-2050` (`_exec_rsi < SHORT_RSI_FLOOR` = 45) → `return False` — **no pump-chain carve-out**.

Result: every pump-chain SHORT in the RSI 40–45 band is still killed. The commit's stated benefit ("40-45 band = 19T 63.2%WR +$0.48") cannot be realized. This is not a crash — it is a silent dead feature.

**Severity: HIGH (functional no-op). Not a money-losing bug — it blocks trades that were already blocked. But the change delivers zero of its intended edge and the revert criterion (`7d n>=5 WR<45%`) will never trigger because n will be 0.**

### 2. MEDIUM — `_ctx_bearish_override` is computed but never used (dead code / possible refactor leftover)
`decider_run.py:1159-1181` computes `_ctx_bearish_override` by opening `continuum.db`, but grep shows it is only ever assigned (lines 1159, 1179) — **never read**. The SHORT_RSI_FLOOR checks at 1183-1186 ignore it entirely. This looks like the remains of the 2026-10-06 removal of the exec bear override (`c4097276`). Every pump-chain/SHORT gate call pays an unnecessary SQLite round-trip. Low impact, but dead code in a live trading path should be cleaned up.

### 3. LOW — signal_compactor.py also uses the global `SHORT_RSI_HARD_FLOOR` with no pump-chain variant
`signal_compactor.py:4013,4032-4033` blocks SHORT approval when `RSI < SHORT_RSI_HARD_FLOOR` (45) — no pump-chain carve-out. This is a **third** enforcement point the commit did not touch. In practice it is currently masked because pump-chain is in `STANDALONE_BYPASS_SIGNALS` and skips compactor entirely (confirmed: `'pump-chain-'` is in the tuple). But the moment pump-chain is removed from the bypass list, compactor will re-block 40-45 and silently undo the fix again. Worth noting for consistency.

## Collision Check

**Yes — collision confirmed and fatal to the change's intent.**
`SHORT_RSI_FLOOR = 45` (raised 40→45 by CEO/T 2026-10-06) is the *non-hard* oversold floor and is checked **after** the hard floor at both enforcement points, with no pump-chain variant. Because 45 > 40, the 40–44.9 band is caught by `SHORT_RSI_FLOOR` before the loosened hard floor ever matters. The hard floor only becomes the binding constraint below RSI 40 — which is exactly the region that should stay blocked. As written, the commit changes nothing about which trades pass.

## Recommendation

**Fix first — do not ship as-is (it is currently inert, so shipping it causes no harm, but it also delivers none of its value and creates a false sense that the 40-45 band is open).**

To make the change real, one of these is required:
1. **Preferred:** add a matching pump-chain carve-out to the `SHORT_RSI_FLOOR` checks at `decider_run.py:1183-1186` (context gate) and `decider_run.py:2048-2050` (exec time), e.g. `_floor = SHORT_RSI_FLOOR_PUMP_CHAIN if 'pump-chain' in (source or '') else SHORT_RSI_FLOOR` with a new `SHORT_RSI_FLOOR_PUMP_CHAIN = 40` constant. This is the only path that actually opens the 40-45 band.
2. Or revert the commit and redo the analysis knowing `SHORT_RSI_FLOOR` (not `HARD_FLOOR`) is the true binding gate for pump-chain.

Also confirm with the auditor which floor their 19T/63.2% backtest was measured against — if it was measured against the *hard* floor only, the number is still valid but currently unreachable. If they were unaware of `SHORT_RSI_FLOOR`, re-validate the band against the real binding constraint before loosening it.

**Verify, don't trust:** all numbers above come from `git show 1ac1c92a`, direct file reads, and a live Python simulation of the exact gate ordering in this session — not from memory.
