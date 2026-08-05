---
name: python-gotchas
description: Python source code bugs and pitfalls specific to Hermes development — duplicate function shadowing, closure scoping, and patch-file pitfalls.
---

# Python Gotchas — Hermes Source Code Bug Patterns

These three skills capture Python bugs that appear repeatedly when patching or writing Hermes source files.

## Reference Files

- `references/python-duplicate-function-shadowing.md` — duplicate function definitions
- `references/python-nested-function-scoping-gotcha.md` — closure scoping bugs
- `references/patch-pitfalls.md` — patch file pitfalls
- `references/patch-pitfalls-v2.md` — write_file destruction, global-before-assignment SyntaxError, signal module import paths
- `references/python-call-signature-mismatch.md` — silent TypeError in bare except blocks
- `references/python-call-signature-mismatch.md` — silent TypeError in bare except blocks
- `references/multi-file-import-refactor.md` — safe sequence for moving constants paths→hermes_constants

## Centralizing Inline Computations — Refactoring Pattern

When the same calculation (PnL math, fee math, direction logic) is copy-pasted across 3+ files, centralize it:

**Step 1 — Audit:** `grep -rn "LONG.*SHORT\|pnl_pct.*=.*current\|entry.*\*.*100" /root/.hermes/scripts/*.py | grep -v __pycache__ | grep -v pnl_utils | grep -v backtest`

**Step 2 — Create module:** Write `/root/.hermes/scripts/pnl_utils.py` with one function per unique calculation. Keep direction as `str` (accept `"LONG"`/`"SHORT"` strings), not a strict enum, since callers pass mixed types.

**Step 3 — Compile test:** `python3 -m py_compile pnl_utils.py` before any caller is updated.

**Step 4 — Patch callers one at a time:** Import the new module in each file, replace inline logic with the function call, compile after each patch.

**Step 5 — Verify:** Re-run the grep from step 1 — no raw inline calculations should remain outside `pnl_utils/` and `backtest/`.

**Key pitfalls:**
- Patch import BEFORE patching the call sites (otherwise the first patch breaks the import)
- When replacing inline LONG/SHORT if/else blocks, verify the replacement function returns the same shape: `(pnl_pct, pnl_usdt, net_pnl)` vs just `pnl_pct`
- `compute_close_pnl` already handles fees internally — do not double-apply fees in the caller
- `unrealized_pnl != 0` guards skip breakeven price updates — remove them when centralizing PnL sync

**See:** `references/pnl-utils-centralization.md` — full step-by-step including all files patched in the 2026-05-20 session.

---

## Quick Reference

### 0.0 Is Falsy — Never Use `if float_var` for Null Checks
```python
# WRONG — 0.0 treated as falsy, falls back to wrong value
calc_notional = float(hl_notional_usdt) if hl_notional_usdt else amount_usdt

# CORRECT — only None triggers fallback, 0.0 is a real value
calc_notional = float(hl_notional_usdt) if hl_notional_usdt is not None else amount_usdt
```
`float(x) if x else y` → `0.0` falls back to `y`. `float(x) if x is not None else y` → `0.0` stays as `0.0`.
This caused PnL inflation ~5x when `hl_notional_usdt=0.0` (legacy trades) or when HL notional was `NULL` — fell back to signal-level $50 instead of actual HL ~$7-10.

## All Instances Found in Session (2026-05-20)

| File | Line | Pattern | Effect |
|------|------|---------|--------|
| brain.py | 637 | `if hl_notional_usdt` | PnL ~5x inflated |
| brain.py | 640 | `or DEFAULT_TRADE_SIZE_USDT` | phantom $50 for 0.0 |
| position_manager.py | 883 | `or DEFAULT_TRADE_SIZE_USDT` | deflated pnl_pct |
| position_manager.py | 884 | `if row['hl_notional_usdt']` | wrong PnL calc |
| position_manager.py | 1096 | `or DEFAULT_TRADE_SIZE_USDT` | inflated fee base |
| hl-sync-guardian.py | 696 | `if parts[5]` | phantom $50 for '0' |
| hl-sync-guardian.py | 2694 | `or DEFAULT_TRADE_SIZE_USDT` | phantom $50 in orphan close |
| hl-sync-guardian.py | 2696 | `if row[2]` | wrong denominator in pnl_pct |

Fix all with: `if x is not None else default` pattern.

**String parsing variant** (pipe-output from subprocess): when the parsed value is a string, check for both `None` and empty string:
```python
# WRONG — '0' string is truthy but becomes 0.0 when converted; empty string falsy
amount_usdt = float(parts[5]) if parts[5] else DEFAULT_TRADE_SIZE_USDT

# CORRECT — only non-empty string becomes a float
amount_usdt = float(parts[5]) if parts[5] is not None and parts[5] != '' else DEFAULT_TRADE_SIZE_USDT
```

See `references/python-falsy-float-bug.md` for full analysis.
## Quick Reference

### Duplicate Function Shadowing
Last definition wins. Grep for the function name, check all occurrences.

### Closure Scoping Gotcha
Variables assigned in nested `def` shadow outer scope → `UnboundLocalError`. Fix: pass as parameter or use default argument.

### Patch Pitfalls
- `except:` catches everything (IndentationError included → syntax disaster)
- Scope references in new code blocks
- `replace_all` can hit unintended matches
- String patterns spanning multiple indentation levels

### Call-Site / Signature Mismatch (Silent Failure)
`mirror_close(token, direction, exit_price=None)` — if caller passes only `token`, Python raises `TypeError` inside a bare `except Exception:` block. Rollback silently fails, HL position stays open, orphan forms. See `references/python-call-signature-mismatch.md`.

### Chained Comparison with Negative Thresholds
`min_pct <= live_pnl <= max_pct` where both are negative (e.g. `LOSS_MIN_PCT=-3.0`, `LOSS_MAX_PCT=-0.5`) always returns False for losses in the range (-0.5, 0). Python chains `(a <= b) and (b <= c)`, and `-0.35 <= -0.5` is False. Fix: use `(live_pnl <= max_pct) and (live_pnl >= min_pct)`. See `references/python-chained-comparison-negative.md`.

### Greedy Regex Captures Code as Concepts (Hermes markdown seeders)

Pattern that breaks: `\*\*([^*]+)\*\*` (bold) or `/root/\.hermes/[^\s]+\.(?:py|json|...)` (file paths) — both have unbounded quantifiers that capture multi-line code blocks when markdown contains `**...code...**` wrapping or path-like substrings inside code.

Real failure (2026-06-24 hebbian_learner.py): a single doc ended up creating a node containing the entire `hl-sync-guardian.py` body as a "file" concept (4250 lines). Same for code paths mid-sentence.

Fix rules for any text-extraction regex in Hermes:
- Bold: `\*\*([^*\n=]{2,60})\*\*` — exclude newlines, exclude `=` (filters assignments), bound to 60 chars
- File paths: require a recognizable extension as the terminator (`\.py|\.json|\.md|\.db|\.log`) AND exclude single/double quotes (`'` and `"`) so trailing-quote artifacts don't end up in DB nodes
- Always test the regex against real source files (`grep -o` on `/root/.hermes/scripts/*.py` or `/root/.hermes/brain/*.md`) before shipping

### Don't Strip Underscores in Concept Normalizers

`re.sub(r'[`*_~<>]', '', name)` looks like a safe "remove markdown decoration" pattern but turns `/root/.hermes/scripts/signal_compactor.py` into `/root/.hermes/scripts/signalcompactor.py`. Underscores are part of every Python file path (`signal_compactor`, `hl-sync-guardian`, `accel_300_signals`, `decider_run`). After normalization, recall by exact filename misses because the underscore was stripped.

Fix: strip markdown decoration but NOT underscores: `re.sub(r'[`*~<>]', '', name)`. Or, if you need to strip decoration, do it BEFORE the path is captured (don't normalize paths at all if they're already from a clean source like inline code).

### Verify "Defunct" Labels Before Acting on Them

Hermes scripts can be marked defunct in SOUL.md or memory but actually still be live. The naming convention `signal_<topic>.py` covers `signal_compactor.py`, `signal_run.py`, `accel_300_signals.py` — all alive. Only `signal_gen.py` and `ai_decider.py` are truly defunct (replaced by `signal_compactor.py`). Before adding ANY script to a DEAD/DEFUNCT exclusion list:

```bash
# Verify the script actually exists
ls -la /root/.hermes/scripts/<name>.py

# Check for actual imports / live callers
grep -rn "from <module>\|import <module>" /root/.hermes/ --include="*.py" 2>/dev/null | head -5
```

If `grep` returns nothing, the script is truly dead. If it returns hits, it's still in use regardless of what SOUL.md says.

### Delete Polluting Functions Completely, Not Stub Them

When removing a polluting function (`seed_decisions_log`, `learn_from_decisions_log`, anything that writes bad data), do NOT leave a stub:

```python
# WRONG — footgun, hasattr() still returns True, dir() still lists it
def bad_function():
    # removed in Fix X
    return 0
```

Future code that does `if hasattr(module, 'bad_function')` will think it exists, and someone might accidentally call it.

```python
# RIGHT — completely gone, including signature
# (function deleted entirely, comment block documents the removal)
```

Verification: `grep -rn "bad_function" /root/.hermes/scripts/*.py | grep -v .bak` should be EMPTY. If the grep returns anything in non-backup files, the deletion is incomplete.
