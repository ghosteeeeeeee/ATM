# External Audit False Positives — 2026-06-12 (skillsmp.com)

External audit returned 8 bug claims for hl-sync-guardian.py. Manual verification in main session: **7 false positives, 1 true bug**.

## True Bug (Fixed)

| Bug | Location | Fix |
|-----|----------|-----|
| `range(3)` fill poll timeout too short | `_poll_hl_fills_for_close:932`, `_get_hl_exit_price:986` | `range(6)` = 30s window (was 15s) |

## False Positives (All NOT bugs — Already Fixed)

| Claim | Reality |
|-------|---------|
| Race-condition DB update (~line 2860) | NOT A BUG. All paths use single atomic UPDATE: `SET status='closed', guardian_closed=TRUE` in one statement. Verified at lines 1472, 1637, 1772, 2022, 3200. |
| `continue` after orphan trade update (~lines 925-962) | NOT A BUG (already fixed). Lines 1204-1213 close BOTH HL position AND paper trade before `continue` fires. |
| Missing `is_guardian_close` on orphan inserts (~line 571) | NOT A BUG (already fixed). Both `add_orphan_trade` calls set `is_guardian_close=TRUE, guardian_closed=TRUE` at lines 2627 and 2745. |
| Pre-check omission before orphan creation (~line 560) | NOT A BUG (already fixed). Full duplicate guard at lines 1163-1216 checks PostgreSQL before creating any orphan. |
| SQL injection in ai_decider.py (~lines 275-284) | NOT A BUG. All 4 f-string `execute()` calls use parameterized `?` placeholders. `placeholders = ','.join(['?' for _ in open_tokens])` only produces `?` chars, no user data in SQL string. |
| Duplicate-signal GROUP BY in `compact_signals()` | NOT A BUG. GROUP BY `combo_key` already exists at signal_compactor.py:433. |
| Missing confidence floor in `add_signal()` | NOT A BUG. signal_compactor enforces `confidence >= 60` at line 440; lower signals filtered before write. |
| `continue` leaves orphan HL position open | NOT A BUG. Already had full close logic (lines 1204-1213) before `continue`. |

## Pattern

External audits from third parties (skillsmp.com, arxiv, blog posts) tend to:
- Misread indentation/control flow
- Report "missing" flags that are already set
- Confuse commented-out code with live code
- Use outdated line numbers that shift as files evolve

**Always verify with grep+py_compile+read_file in main session regardless of source.**
