# bug_hunter verdict — 2026-11-11 fix round: NULL-signal orphans + `cut_loser` label

**Verifier:** bug_hunter (adversarial, read-only — no fixes applied)
**Target commit:** `c0aaef88` — "fixes: NULL-signal orphan trades (CEO bug report) + 'cut_loser' label on plain stops" (2026-11-11 15:50:29 UTC)
**Files in commit:** `scripts/hl-sync-guardian.py` (1 hunk, `@@ -864,11`), `scripts/position_manager.py` (1 hunk, `@@ -3769,9`)
**Verified at:** 2026-11-11 ~17:15 UTC

## Harnesses (rerunnable, /tmp — SELECTs + mocks only, no live writes)

| Harness | Command | Result |
|---|---|---|
| A — INSERT alignment (static + mocked functional) | `python3 /tmp/bh/verify_A_orphan_insert.py` | **34/34 PASS** |
| B — orphan/NULL-signal creation paths | `python3 /tmp/bh/verify_B_orphan_paths.py` | **15/15 PASS** |
| C — label-fix scope + 4-case logic + spy | `python3 /tmp/bh/verify_C_label_fix.py` | **28/28 PASS** |
| D — regression | `python3 analysis/test_manual_exit_manager.py` | **20/20 passed, 0 failed (rc=0)** |
| D — py_compile + fresh import | `python3 -m py_compile scripts/hl-sync-guardian.py scripts/position_manager.py`; `python3 -c "import position_manager"` | **OK / OK** |

## Verdict table

| # | Check | Verdict | Evidence |
|---|---|---|---|
| A1 | INSERT column list ↔ SELECT value list paired 1:1 (24/24) | **PASS** | Parsed from current source: `… stop_loss, target, server, signal, status, open_time …` ↔ `… %s, %s, 'Hermes', 'guardian_orphan', 'open', NOW() …` (harness A1, full pair dump) |
| A2 | `signal` ↔ `'guardian_orphan'` | **PASS** | position 11 of 24 (A2) |
| A3 | `status` ↔ `'open'`; `server` ↔ `'Hermes'` | **PASS** | positions 12 / 10 (A3, A4) |
| A4 | `stop_loss`/`target` land on params, no shifted literal | **PASS** | positions 8/9 both `%s`; explicit `stop_loss=1900, target=2200` reconstructed into the right columns (A30/A31); `signal` still `guardian_orphan` (A32) |
| A5 | `%s` count == params == 12, param order unchanged | **PASS** | 12 `%s` (11 in SELECT list + 1 in `WHERE NOT EXISTS … token=%s`), tuple `(token, direction, amount_usdt, entry_price, entry_price, stop_loss, target, leverage, signal_z_score, vol_regime, _orphan_meta, token)` (A10, A11, A15, A16) |
| A6 | Functional: mocked `get_db_connection`, `add_orphan_trade('BTC','SHORT',74000,11.1,5)`, DRY off | **PASS** | captured `(sql, params)`; reconstructed row: `signal='guardian_orphan'`, `server='Hermes'`, `status='open'`, `stop_loss=None`, `target=None`, `entry_price=hl_entry_price=74000`, `amount_usdt=11.1`, `leverage=5`, `pnl_usdt/pnl_pct=0`, `volatility_regime` from param, `_signal_metadata` json (A12–A29); DRY short-circuits with 0 executes (A34); all 24 columns exist in `information_schema` (jsonb/boolean types compatible) |
| B1 | Every `INSERT INTO trades` site in `scripts/` classified (9 sites / 7 distinct) | **PASS** | `brain.py:843` (signal param), `cascade_flip_helpers.py:206` (param), `continuum_trader.py:671/674` (`'continuum_engine'` param), `pump_hunter.py:365` (`'pump_hunter'` literal), `hl-sync-guardian.py:866` (fixed), `hl-sync-guardian.py:1728` (**no signal — DEAD**), symlink duplicate `hl_sync_guardian.py` → same file |
| B2 | No reachable NULL-signal creator | **PASS (with LOW caveats)** | only no-signal site is `_check_and_execute_flip()` which `return`s unconditionally at `hl-sync-guardian.py:1614`; `add_orphan_trade` has exactly 1 live caller (`:1534`, reconcile path); no `UPDATE … status='open'` reopen path exists |
| B3 | Historical NULL rows closed | **PASS** | 27/27 `signal IS NULL` rows are `status='closed'`; 0 open NULL/empty rows; #16869 closed 15:37:16, #16837 closed 2026-11-09 (5 rows carry `_signal_metadata.source='orphan_recovery'`, all closed) |
| B4 | Tagged orphans still match guardian/PM queries (`signal IS NULL OR signal NOT IN ('pump_hunter')`) | **PASS** | evaluated in SQL: `guardian_orphan`→true, `NULL`→true, `pump_hunter`→false, bare `NULL NOT IN (…)`→NULL (why the `OR` exists) — `hl-sync-guardian.py:774/801`, `position_manager.py:357/381/428` |
| C1 | **Scope: is `direction` bound before the relabel block?** | **PASS (risk ruled out)** | AST control flow: `check_and_manage_positions` → `for pos in positions:` at `position_manager.py:3034`, `direction = str(pos.get("direction","UNKNOWN")).upper()` at **:3043** (2nd statement, no `continue`/`return` before it), no `del`/rebind between :3043 and block :3770-3799, block not inside any nested scope. So `or direction` can never raise NameError in the real loop (C1a–C1f, C1i) |
| C1' | Hypothetical: `direction` unbound | **PASS (diagnostic)** | exact shipped expr `_dir = str(pos.get('direction') or direction or '').upper()` raises `NameError` **inside** the try → would be swallowed → relabel silently dead (C1g-1); but the same scenario then dies **loudly** at the log line `:3791` which sits *outside* the try (C1g-2). With `pos.direction` present the `or` short-circuits (C1h). Unreachable anyway per C1f |
| C2 | 4-case logic (SHORT/LONG × loss/profit side) | **PASS** | SHORT stop>entry → `manual_sl_hit`; SHORT stop<trail → `manual_trail_hit`; LONG mirrors; managed+exception → `cut_loser`; managed+missing SL → `manual_sl_hit` (edge); lowercase/`pos.direction`-missing handled (C2-1…C2-11) |
| C3 | Spy on `close_paper_position` — reason + exit_detail asserted | **PASS** | reasons received verbatim; `exit_detail='cut_loser_pct=-1.23%'` unchanged; pipeline log line **byte-identical** to pre-fix (`"  CUT_LOSER ETH SHORT -2.50%"`); managed log line `"  MANUAL_SL_HIT (stop breach) …"` (C3a–C3d) |
| C4 | Pipeline trades unaffected (no `ai-trader-*` tags) | **PASS** | `is_managed_signal` False for `bb_bounce_v2_long`, `rr-struct+`, `pump-chain+`, `hl_copy_trader`, `guardian_orphan`, `continuum_engine`, `pump_hunter`, `delayed-entry` (C4b); profit-side stop on a pipeline trade still → `cut_loser` (C2-7) |
| D | Regression: tests, py_compile, fresh import, pipeline log | **PASS** | 20/20; both files compile; fresh-process `import position_manager` OK; **79/79** `position_manager: done … (rc=0)` cycles after 15:50:29; **0** `Traceback` in `logs/pipeline.log`; 0 non-zero rc post-fix; `logs/sync-guardian.err.log` untouched since 14:34 |
| E | Phantom-close root chain claimed STILL OPEN — fix must not touch it | **PASS (claim holds)** | commit has exactly **one** hunk in the guardian (the INSERT, `@@ -864,11`); no close/fallback edits; worktree clean for both fix files. Chain live in code: `_get_hl_exit_price()` `hl-sync-guardian.py:1124-1156` (6 polls → `:1147` "no HL close fills found … using fallback"), Step8 `:5004-5030` still closes `HL_CLOSED` off `bool(hl_entry_price)` (entry-time flag, not a liveness check), grace guard `:4948-4968` **fails open** (`except Exception: pass  # fail open`), 2-miss guard pre-satisfied by stale `data/guardian-missing-tracking.json` (BTC `first_seen 2026-10-16`, cycles 16). Chain reproduced same-day pre-fix: **#16868** (BTC SHORT `ai-trader-pending`, opened 14:33:57) → 14:34:44 `Step8 closing … reason=HL_CLOSED` *after* "no HL close fills found after 6 polls (30s) — using fallback" → 14:35:45 orphan adoption created **#16869** (`signal=NULL`, pre-fix) → continuum exemption blocked the HL close → later ATR-killed |
| F | Live proof after fix timestamp | **AWAITS FIRST LIVE EXERCISE** | `signal='guardian_orphan'` rows: **0**; trades opened after 15:50:29: **0**; trades closed after 15:50:29: **0**; `cut_loser`/`manual_*` closes after 15:50:29: **0**. Nothing to verify yet — stated honestly, not inferred |

## Findings

### HIGH-1 — NULL-signal fix is **not deployed**: the guardian daemon is running pre-fix code
- `hermes-hl-sync-guardian.service` MainPID **652629 started 2026-11-08 19:16:48 UTC** (`systemctl show … ActiveEnterTimestamp=Sun 2026-11-08 19:16:49 UTC`; `ps -o lstart` confirms; `pgrep` shows exactly one guardian process).
- `scripts/hl-sync-guardian.py` mtime **2026-11-11 15:43:45**, commit at 15:50:29. `Type=simple` daemon loads source once at start; **93 guardian cycles have run since the edit with no restart**.
- Consequence: the only code path that creates orphans (`add_orphan_trade`, `hl-sync-guardian.py:866`) is still executing the **pre-fix INSERT without the `signal` column** → the next HL orphan will again be `signal=NULL`, i.e. the CEO-visible symptom persists until `systemctl restart hermes-hl-sync-guardian`.
- Not repaired here (verifier must not change live state). The `position_manager` half **is** live — `run_pipeline.py` spawns each step via `subprocess.Popen`, so the label fix reloads every minute (79/79 rc=0 since commit).

### MEDIUM-1 — Phantom-close root chain: confirmed still open (as claimed), with the concrete gaps named
- Unfixed by design (commit touches only the INSERT). Evidence chain in `logs/sync-guardian.log`: `:562413` (14:34:44 close `HL_CLOSED` with fallback exit despite no close fill), `:562425` (14:35:45 orphan #16869 created with NULL signal), `:562427-28` (continuum exemption → HL position kept).
- Two specific weaknesses that make it recur: (a) `hl-sync-guardian.py:4948-4968` the 5-minute grace guard **fails open** on any exception (that is why a 47-second-old trade was closable); (b) `has_hl_confirmation = bool(hl_entry_price)` (`:5004`) is an *entry-time* flag, never a *current-liveness* check, and the 2-miss counter is fed by stale state (`guardian-missing-tracking.json`: BTC `first_seen 2026-10-16`).

### LOW-1 — Second NULL-signal INSERT survives as dead code (`hl-sync-guardian.py:1728-1743`)
- Inserts `status='open'` with **no `signal` column**; unreachable only because `_check_and_execute_flip()` returns at `:1614` (`[DEFUNCT-2026-04-17]`). If that path is ever re-enabled the bug returns verbatim. Suggest tagging or deleting on cleanup.

### LOW-2 — `brain.py add_trade` can still produce a NULL-signal open row
- `signal: str = None` (`brain.py:335`), `--signal` optional (`:1503`), column nullable with **no default** (information_schema). All three in-repo callers pass `--signal` (`decider_run.py:1175`, `:3305`, `trade_watchdog.py:1594`) so no live automated path today — but there is no defensive coalesce (`signal or 'manual'`), so a manual `brain.py trade add` without `--signal` recreates the exact symptom.

### LOW-3 — New labels widen HL order-cancellation to a new close site
- `close_paper_position` cancels **all open HL orders** for the token when reason ∈ {`atr_sl_hit`,`atr_tp_hit`,`manual_sl_hit`,`manual_tp_hit`,`manual_trail_hit`} (`position_manager.py:1445-1457`). Managed-signal stop breaches labeled `cut_loser` previously skipped that cleanup; now they won't. Consistent with the ATR path for the same labels (and desirable for stale triggers), but an armed pending order on the same token would now be cancelled at close.

### INFO
1. **Silent swallow** — `position_manager.py:3787-3788` `except Exception: pass` has no logging; any future failure silently degrades to the pre-fix `cut_loser` label (fail-safe, but undiagnosable).
2. **Stale comment** — `signal_compactor.py:6569` claims orphans use `'guardian_orphan_insert'`; actual tag is `'guardian_orphan'`. Comment-only; no functional reference found.
3. **`exit_conditions` prefix** — managed closes store `"manual_sl_hit cut_loser_pct=-1.23%"` (`:3789`); grep-for-`cut_loser` over `exit_conditions` over-matches (canonical `close_reason`/`exit_reason` are correct).
4. **Stats denominators shift** — `signal IS NOT NULL` consumers (`hermes-trades-api.py:901`, `reputation.py:98/161/242/265`, `data_migration_sync.py:221/275`) exclude the 27 historical NULL rows (7 in last 90d) but will now count tagged orphans. Nothing breaks; a small intended denominator change.
5. **Log direction vs pos direction** — the new log line prints the loop `direction` (`:3791`) while the relabel prefers `pos.direction`; in the real loop both come from the same `pos` (`:3043`), so they always agree — noted only because the harness deliberately desynced them.

## Overall verdict

**Code-correct, deployment-incomplete → NOT FULLY SHIPPED.**

- Fix 1 (NULL-signal INSERT): **correct** — 34/34 static+functional alignment checks pass, 12/12 placeholders, row reconstruction exact. **But the fix is not in effect**: the guardian daemon predates the edit (HIGH-1) and needs a restart before the next orphan can be trusted.
- Fix 2 (`cut_loser` label): **correct and live** — the NameError hypothesis is ruled out (`direction` bound at `:3043`, block in same scope), 4-case logic + spy + pipeline-parity all pass (28/28), regression clean (20/20, py_compile, fresh import, 79/79 rc=0, zero Tracebacks).
- Root phantom-close chain: **honestly claimed open, and it is open** — untouched by this commit, with two concrete weak points documented for the follow-up bug_hunter.
- Live behavior of both fixes: **awaits first live exercise** (0 orphans, 0 closes since 15:50:29 UTC).
