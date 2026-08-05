# ai-engineer Subagent False Positives (2026-05-20)

## Why This Matters
T called ai-engineer 3 times this session (brain.py, decider_run, position_manager). Each time it found bugs that were wrong, partially wrong, or severity-inflated. ALL findings were verified in main session before implementing. The rule: **grep + py_compile in main session, never trust subagent reports alone.**

## False Positives by Audit

### brain.py Audit (2026-05-20)
| Bug # | Claimed | Reality |
|-------|---------|---------|
| Bug 1 DRY bypass | CRITICAL — guardian orphan INSERT runs in DRY mode | **REAL but severity inflated** — DRY=True means paper-only mode, no live HL positions affected; still worth fixing for data cleanliness |
| Bug 3 phantom detection | My LIMIT 1 fix was counterproductive | **REAL** — reverted my wrong fix, applied correct fix (direction filter + ORDER BY) |
| Bug 4 away_detector | CRITICAL — split-brain on live_trading flag | **REAL** — fixed |
| Bug 5 paper flag | CRITICAL — paper flag always True, no live trades possible | **WRONG** — `paper = not is_live_trading_enabled()` IS correct; when constant=False, paper=True, which is correct paper mode |

### decider_run.py Audit (2026-05-20)
| Bug # | Claimed | Reality |
|-------|---------|---------|
| Bug 4 (live_trading redundant) | Medium — `live_trading=not paper` redundant with is_live_trading_enabled() | **NOT A BUG** — logic is correct, harmless redundancy |
| Bug 3 phantom execution | Phantom signals go undetected | **WRONG direction** — compactor has phantom detection, this was already fixed before audit |
| Bug 1 DRY bypass | DRY path increments entered counter | **NOT A BUG** — cosmetic counter only, no functional impact |

### position_manager.py Audit (2026-05-20) — Worst False Positive Rate
Told to audit live file at `/root/.hermes/scripts/position_manager.py` but instead compared two archive exports (`/root/hermes-archive-v3-export/position_manager.py` vs `/root/hermes-archive-hermes-export/position_manager.py`). All 18 bugs reported were based on comparing archives, not the live file.

| Bug # | Claimed | Reality |
|-------|---------|---------|
| MAX_LEVERAGE mismatch | CRITICAL — v3 has 5, hermes-export has 10 | **FALSE** — live file at `/root/.hermes/scripts/position_manager.py` has MAX_LEVERAGE=5; subagent compared archive files |
| pnl_usdt missing in UPDATE | CRITICAL — hermes-export:655 omits pnl_usdt | **PARTIALLY WRONG** — `refresh_current_prices()` (a different function) DOES write pnl_usdt; the position_manager close path is separate |
| No `is_live_trading_enabled()` gate | MEDIUM — file has no live-trading gate | **FALSE** — live file imports and calls `is_live_trading_enabled()` at line 1042 before `mirror_close` |
| No mirror_open/mirror_close | MEDIUM — these functions don't exist | **FALSE** — live file imports `mirror_open, mirror_close` at line 64 and uses them |
| Bug 3 duplicate close race | HIGH — no FOR UPDATE lock | **PARTIALLY TRUE** — guardian and position_manager can close same trade; result is DB returns False, hype-sync reconciles |

## Patterns of Failure
1. **Archive vs live file confusion** — subagent looks at similar-named files in archive directories instead of the actual deployed file
2. **Severity inflation** — Bug 1 (DRY bypass) and Bug 1 (MAX_LEVERAGE) were both labeled CRITICAL when their actual impact was minimal
3. **Architecture mismatch claims** — reported functions as "missing" when they exist under different names or in different files
4. **Comparison between two wrong versions** — when two archive versions disagree, the subagent assumes one is correct and one is buggy without checking which matches the live deployment

## Verification Protocol
Before acting on ANY ai-engineer finding:
1. grep for the exact variable/function in the ACTUAL deployed file
2. python3 -m py_compile on the file
3. Read the specific lines cited to confirm the bug description matches reality
4. Check if the "fix" makes the bug better or introduces a new problem