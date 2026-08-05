---
name: trading-system-audit
description: Full codebase audit of the Hermes trading system — syntax, imports, calculations, API consistency, DB safety, error handling, and security.
category: autonomous-ai-agents
---

# trading-system-audit

Run a full health check and code quality audit of the Hermes trading system.

## When to Use
After any significant code change (weights, signal flow, API calls, DB schema). Covers:
1. Python syntax — py_compile each key script
2. Import integrity — all imports resolve, no circular dependencies
3. Calculation logic — sign flips, None handling, zero-division guards
4. API call consistency — hype_cache usage vs direct requests.post for Hyperliquid
5. Database consistency — SQL injection risks, connection leaks, NULL handling
6. Signal flow — source weights in ONE place only
7. Error handling — bare excepts, silent failures, missing fallbacks
8. Security — hardcoded secrets, exposed ports, credential leaks
9. Concurrency — lock file handling, race conditions
10. Completeness — dead code paths, unfinished TODOs

## Overlap Note
- `code-audit` has been MERGED into this skill (2026-04-27). `code-audit` is deprecated — do not use.
- `multi-pass-signal-audit` (software-development) focuses specifically on signal script data freshness — trading-system-audit is broader (full pipeline, all layers). Keep both but use trading-system-audit for cross-layer audits.
- `cooldown-tracker-ms` (trading) is tightly related — cooldown store mismatch bugs are the most common source of phantom re-entry. Load cooldown-tracker-ms alongside this skill when auditing runner scripts.
- `ai-engineer` (autonomous-ai-agents) is the correct persona to LOAD when starting an audit — the subagent is defined there. Use `trading-system-audit` as the methodology reference. For cross-layer pipeline audits, prefer delegating to `ai-engineer` with `trading-system-audit` as the handoff spec.

## Architecture Updates (2026-05-08)

**Pipeline (2026-05-06 onward):**
```
run_pipeline.py → signal_compactor.py → breakout_engine.py → signals_runner.py (BACKGROUND) → signals/*.py
                                                                                 ↓
                                                                           hotset.json
                                                                                 ↓
                              decider_run.py → position_manager.py / hl-sync-guardian.py
```

- `signal_gen.py` — **REMOVED** from pipeline (2026-05-06). Inline signal orchestrator replaced by `signals_runner.py` + `signals/` module registry.
- `ai_decider.py` — **DEFUNCT** since 2026-04-16. Do not use or audit.
- `signals_runner.py` runs in BACKGROUND via `run_bg(step)` — non-blocking. Pipeline continues synchronously while signals generate in parallel. This means signals_runner output may not align with the main pipeline.log cycle timing.
- `breakout_engine.py` — NEW in pipeline (2026-05-06), 60s timeout.
- Canonical execution path: `hl-sync-guardian.py` (NOT decider_run for HL position management)
- Hot-set path: `/var/www/hermes/data/hotset.json`

## Git Workflow — Uncommitted Changes Are the Danger Zone

**Critical rule (2026-05-08 incident):** Uncommitted disk changes are the PRIMARY source of P0 incidents. `git status --short` shows modified files that are LIVE in the running system but NOT in git. These changes:
- Are not visible in `git diff` until `git diff HEAD` is run
- Are not revertable without `git checkout -- file`
- Can break the system silently while appearing to work in git log

**Always check uncommitted changes FIRST when debugging:**
```bash
cd /root/.hermes && git status --short  # shows M/D/?? files
cd /root/.hermes && git diff HEAD -- scripts/hl-sync-guardian.py  # shows uncommitted disk changes
```

The incident root cause: 5 files had uncommitted changes (`hl-sync-guardian.py`, `brain.py`, `decider_run.py`, `signal_compactor.py`, `run_pipeline.py`) plus 1 untracked file (`archive-trades.py`). All changes were LIVE but not in git. The orphan creation block at hl-sync-guardian.py:3638-3678 and closing marker system were uncommitted — they were running in production but invisible to git bisect/revert.

**Fix protocol:**
1. `git status --short` first — always
2. If file shows `M` (modified): check `git diff HEAD -- file` before touching
3. If file shows `??` (untracked): verify it's not a production script (especially if it has DELETE/DB write logic)
4. Revert with `git checkout -- file` (unstaged) or `git revert --no-commit <commit>` (if already staged)
5. Never assume "it was working yesterday" means the file on disk matches git HEAD

## Architecture Breaks (2026-05-08 — P0 Incidents)

### BREAK 1: Confluence Gate Blocking All Signals (INTENTIONAL — per T instruction)
**File:** `signal_compactor.py` lines 467-501 (UNCOMMITTED)
**Rule:** 2+ unique signal types required. Single-source signals blocked with no bypass. This is INTENTIONAL per T's explicit instruction — single source signals are NOT allowed to pass through confluence gate.
**Symptom:** All single-source signals blocked → hot-set empty → no trades execute.
**Action:** Do NOT change this behavior. It is correct per user instruction.

### BREAK 2: Guardian Orphan Creation Block Creates Phantom Records (P0 — UNCOMMITTED)
**File:** `hl-sync-guardian.py` lines 3638-3678 (UNCOMMITTED)
**What:** New `else:` block in orphan close path creates `guardian_orphan_insert` record with `trade_id = lev * 1000000`, then calls `_close_orphan_paper_trade_by_id()` which searches by `id` (auto-increment) not `trade_id`. The query `WHERE id = lev*1000000` finds nothing → returns False → `_clear_closing_marker()` never called → stale marker blocks token permanently.
**Symptom:** 48 stale entries in `guardian-closing-markers.json` all with `trade_id: null`. decider_run skips all tokens with "SKIP: {token} — guardian closing in progress (race guard)".
**Fix:** Remove the orphan creation block at lines 3638-3678. The ORPHAN GUARD at line ~1145 already handles this case with a `continue`. The new block is structurally dead code and creates phantom records.

### BREAK 3: Guardian Closing Marker System (P0 — UNCOMMITTED)
**File:** `hl-sync-guardian.py` lines 351-408 + decider_run.py `_is_guardian_closing()` (UNCOMMITTED)
**What:** `_save_closing_marker()` writes to `guardian-closing-markers.json` BEFORE market_close. `_is_guardian_closing()` in decider_run checks the file before executing any trade. Stale markers (from failed orphan closes) permanently block tokens.
**Fix:** If the orphan creation block (BREAK 2) is removed, the closing marker system loses its primary trigger. Clear `guardian-closing-markers.json`. Consider removing the closing marker system entirely or adding a TTL (<5 min) with automatic expiry.

### BREAK 4: archive-trades.py DELETE Risk
**File:** `/root/.hermes/scripts/archive-trades.py` (NOT in git — created May 8 03:16)
**What:** `--apply` flag archives to JSON AND DELETEs from PostgreSQL via `DELETE FROM trades WHERE id IN (...)`.
**Risk:** If run with `--apply`, all PostgreSQL trade history is wiped. Was NOT auto-run, but the file exists and could be triggered manually.
**Fix:** Remove the DELETE — archive to JSON only, never delete from PostgreSQL. The DELETE capability should not exist.

### BREAK 5: Pipeline Architecture Redesign (P1 — UNCOMMITTED)
**File:** `run_pipeline.py` (UNCOMMITTED)
**What:** `STEPS_EVERY_MIN` changed from `['price_collector', '4h_regime_scanner', 'signal_gen', 'hermes-trades-api', 'decider_run', 'position_manager']` to `['signal_compactor', 'breakout_engine', 'signals_runner', 'decider_run', 'position_manager', 'hermes-trades-api']`. `signals_runner` runs in background. `signal_gen` removed. `ai_decider` removed.
**Assessment:** Architecture change is correct — `signals_runner` replaces `signal_gen`, `ai_decider` is correctly defunct. This change is NOT the breaking part.
**Fix:** Keep this change. It is correct.

## Critical audit target — `name_to_module` in `signals/__init__.py` Every signal in `SIGNAL_REGISTRY` must appear in `name_to_module` with the correct module name. Mismatches here cause the wrong signal script to execute silently (e.g. `r2_rev`/`r2_trend` swap). Also verify every registered `run` function actually exists in the target module — `_run_signal` looks for `mod.run`, not `scan_*`.

## Subagent Orchestration

**Constants-first rule (NON-NEGOTIABLE):** Always check hermes_constants.py FIRST before delegating anything. The highest-value finding (`SIGNAL_SOURCE_BLACKLIST = {}`) was missed for 3 audit cycles because heavy subagents timed out before reaching constants. Do this in the main session:
```bash
grep -n "SIGNAL_SOURCE_BLACKLIST\|CONFLUENCE_REQUIRED\|ATR_TP_K_MULT\|CASCADE_FLIP_ENABLED\|MIN_ATR_PCT\|MAX_SL\|MIN_TP\|MAX_TP\|ATR_SL_MAX\|ATR_TP_MIN" /root/.hermes/scripts/hermes_constants.py
```

**Timeout hazard:** Workers given 600s timeout still timed out. 3 of 5 subagents timed out on the 2026-05-08 full pipeline audit (too many files per worker).

**Workload limits that work:**
- Max ~8-10 signal scripts per worker (not all 27 at once)
- Constants + signal_schema audit: LIGHTWEIGHT — always do in main session
- Recommended revised layer split (6 workers):
  1. **Constants + signal_schema** — hermes_constants.py, signal_schema.py (LIGHTWEIGHT — main session)
  2. **Signals A-L** (accel_300 through hmacd) — 10 scripts max
  3. **Signals M-Z** (hzscore through volume_hl) — 10 scripts max
  4. **Signal Runner** — signals_runner.py, signals/__init__.py
  5. **Compactor + Decider** — signal_compactor.py, decider_run.py
  6. **Guardian + Position Manager** — hl-sync-guardian.py, position_manager.py

**Timeout fallback:** If a worker times out, do NOT re-delegate — execute the checks directly in the main session. Direct execution is faster for targeted checks.

```
delegate_task with role='orchestrator' + tasks=[layer1, layer2, layer3...]
```

**Recommended layer split** (5 parallel workers, max_concurrent_children=5):
1. **Signal Generation** — all scripts under signals/, signals_legacy/ — signal type accuracy, data source correctness, timestamp-key merges, EMA seeding consistency
2. **Signal Compaction** — signal_compactor.py, blacklist enforcement (especially SIGNAL_SOURCE_BLACKLIST), scoring math, hotset.json schema, survival_round tracking
3. **Trade Execution / Guardian** — hl-sync-guardian.py, position_manager.py, order placement, API error handling, cooldown guard checks, pending_retry logic
4. **Constants & Cross-File Consistency** — hermes_constants.py drift, ATR_UPPER_LIMIT / MIN_PRICE / PULLBACK_THRESHOLD scattered, staleness thresholds, MAX_POSITIONS/MAX_OPEN sync
5. **Position Tracking & Data Layer** — trades.json schema, trailing_stops.json orphan accumulation, pnl calculation, HL vs DB sync, phantom trades

Each subagent gets a **structured handoff document** with:
- Exact file paths (not glob)
- T's trading rules (tight stops, fast exits, first candle against us = out)
- Known gotchas (zscore_momentum is MOMENTUM not mean-reversion, CASCADE_FLIP_ENABLED=False, hot-set path=/var/www/hermes/data/hotset.json)
- The full audit checklist (syntax, logic errors, null guards, race conditions, etc.)
- A directive: DO NOT change anything, only report findings with file:line:issue:fix

**After all subagents return**, consolidate findings into a single priority-ordered bug table:
- P0: Crashers + direct financial loss
- P1: Logic errors + data corruption
- P2: Signal quality issues
- P3: Minor/hardcoded values
- P4: Cleanup/dead code

## External Audit Verification Protocol

External audits (arxiv, skillsmp.com, blog posts, third-party reviewers) MUST be verified the same way as ai-engineer subagent claims — grep+py_compile+read_file in main session before implementing.

**2026-06-12 case study (skillsmp.com):** 8 bug claims → 7 false positives, 1 true bug (fill poll timeout `range(3)`→`range(6)`). Common failure patterns in external audits:
- Misread indentation/control flow (continues that appear bare but are preceded by full close logic)
- Report "missing" flags that are already set
- Confuse commented-out code with live code
- Use outdated line numbers that shift as files evolve
- Confuse SQLite vs PostgreSQL parameterization styles (e.g., `?` vs `%s`)

**2026-06-14 case study (signal-logic-review.md):** 13 bug claims → 9 false positives (already correct in current code), 4 true bugs fixed. Key lesson: external reviews are often against an older version of the code. Always verify every claim against the actual deployed files at `/root/.hermes/scripts/` before implementing. See `references/external-audit-verification-signal-logic-2026-06-14.md` for the full case study.

**ai-engineer subagent audit reliability (2026-06-12):** Of ~40 bug claims across 2 batch audits, 34 were false positives. Common subagent failure patterns:
- Reports loss cooldown "missing" when it IS present (reads wrong code path, wrong indentation level)
- Reports "column never set" when it IS set in both UPDATE statements in the same function
- Reports `_clear_reconciled_token` unreachable — only true if code was not yet fixed (batch 2 verified it had been fixed in batch 1)
- Reports `pending_gone` confusion — subagent misread the function name vs the variable
- Reports `_record_trade_outcome` never called — correct for guardian, wrong for position_manager (different file)
- Times out at 600s on large files (4,200+ line files), leaving sections unaudited

**Subagent timeout rule:** When a delegated audit task times out at 600s, do NOT re-delegate — execute the remaining checks directly in the main session. Direct execution is faster for targeted checks and avoids redundant re-checking of already-audited sections. The skill rule is "do NOT re-delegate" specifically to prevent this pattern.

**Always:**
1. grep for the exact variable/function in the ACTUAL deployed file at `/root/.hermes/scripts/`
2. python3 -m py_compile on the file
3. Read the specific lines cited to confirm the bug description matches reality
4. Check if the "fix" makes the bug better or introduces a new problem

## Post-Audit: Systematic Bug Fixing Workflow

**Critical discipline: verify EVERY patch before moving on.** Introducing new bugs while fixing old ones is the most common failure mode in multi-fix sessions.

After the audit report, fix bugs **one by one** in priority order:
1. Read the specific file/line in context (read surrounding 10-20 lines) — do NOT assume you know the code without looking
2. Apply the fix with `patch()` — one bug per patch, name the bug in the old_string comment
3. **Verify syntax before touching anything else:** `python3 -m py_compile <file.py> && echo OK`
4. If compile fails: revert, re-read, fix properly — never pile fixes on top of a broken state
5. Update the bug table in `/root/.hermes/brain/trading.md` (mark FIXED, add date)
6. Move to next bug — never fix two unrelated bugs in the same patch session

## Known Bug Patterns in Hermes (2026-04-02 through 2026-06-12)

### BREAK 1: Confluence Gate Hard-Block (P0 — LIVE)
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| Single-source signals hard-blocked | All tokens failing silently. pipeline.log: `{accel-300+}` (1 type) blocked at 17:09:00. No trades reaching Hyperliquid despite valid signals. | signal_compactor.py:467-501 | Remove strict 2-type requirement or add high-confidence bypass. CONFLUENCE_REQUIRED=True is dead code — never checked. |
| `CONFLUENCE_REQUIRED` flag unused | Flag set to True in hermes_constants.py:450 but signal_compactor.py gate logic never checks it | hermes_constants.py:450, signal_compactor.py:467 | Either wire the flag to the gate or remove it |

### BREAK 2: Guardian Closing Markers Stalling Decider (P0 — LIVE)
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| 48 stale closing markers block all trades | `guardian-closing-markers.json` has 48 entries (May 6–May 8 20:22), all with `trade_id: null`. Decider_run skips every token with "SKIP: {token} — guardian closing in progress (race guard)". | hl-sync-guardian.py:351-408, decider_run.py:~120 | Clear `guardian-closing-markers.json`. Implement marker TTL + startup cleanup. |
| Orphan close block creates unfindable records | New `else:` block (lines 3638-3678) creates `guardian_orphan_insert` with `trade_id = lev * 1000000`. `_close_orphan_paper_trade_by_id()` searches by `id` (auto-increment), not `trade_id` — structural mismatch. All 48 markers have `trade_id: null`. | hl-sync-guardian.py:3638-3678 | Remove dead orphan creation block. OR fix `_close_orphan_paper_trade_by_id()` to search by `trade_id`. |

### BREAK 3: Regime Path Mismatch (P1)
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| `get_regime_5m()` reads non-existent path/column | Renamed from `get_regime_15m` (reads `regime_15m.json` + `regime_15m` DB col). Now reads `regime_5m.json` (doesn't exist) + `regime_5m` col (doesn't exist). Falls back to `regime_15m` DB col returning NEUTRAL for all tokens → all signals de-escalated. | signal_compactor.py | Restore `get_regime_15m` with correct path/column, or create missing regime_5m infrastructure |
| Freshness threshold too tight | Changed from <900s to <300s — regime considered stale faster | signal_compactor.py | Revert to <900s or implement regime caching |

### BREAK 4: archive-trades.py DELETE Risk (P0)
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| `--apply` flag DELETEs from PostgreSQL | `DELETE FROM trades WHERE id IN (...)` — wipes all trade history if run manually | archive-trades.py:502-510 | Remove DELETE — archive to JSON only, never touch PostgreSQL |

### BREAK 5: Opposing Penalty Over-Counting (P1 — re-introduced)
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| Opposing penalty doubled | Changed from -15%/source to -30%/source, floor 70%→65%. Opposing combo now applies `5 × 30% = 150%` penalty (capped). Previously fixed (BUG-NEW-5) to count `len(opp_sources)`. | signal_compactor.py:239-279 | Count `len(opp_sources)` (1 per opposing direction pair), not `sum(len(p) for p in opp_parts)` |

### BREAK 6: Pipeline Architecture Changes (P1)
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| `signals_runner` runs in background | Non-blocking background fork — output timing misaligned with pipeline.log cycle. Harder to debug signal gaps. | run_pipeline.py:116-139 | Run `signals_runner` synchronously if timing issues persist, or add explicit sequencing |

### BREAK 7: New Signal Source Weights Untested (P2)
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| `macd_accel_short/long` added to SIGNAL_SOURCE_WEIGHTS | New entries with unknown weight values. Opposing penalty increase also untested. | signal_compactor.py | Audit all SIGNAL_SOURCE_WEIGHTS values, run backtest before production |

### BREAK 8: Loss Cooldown in Brain.py (P1)
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| Loss cooldown helpers added with FileLock | `_load_cooldowns`, `_save_cooldowns`, `_record_loss_cooldown` added at lines 15-44. Potential for cooldowns not being written if process crashes mid-write. | brain.py:15-44 | Verify FileLock is released on all code paths (exception handling). Add unit tests for crash scenarios. |

### BREAK 9: 14 New Signal Parameter Fields (P2)
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| `brain.py add_trade()` signature expanded | z_score, rsi_14, macd_hist, momentum_state, test_sl_variant, and 9 others added. All calls to `brain.py trade add` in decider_run must be updated. | brain.py:450-524, decider_run.py:602-675 | Audit all `brain trade add` calls for arg count mismatches. Missing args = early exit with no trade recorded. |

### BREAK 10: Stale Orphan Check in brain.py (P1)
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| New stale orphan check at lines 413-431 | Rejects trades if DB has "zombie open trade with no HL position." Could block valid re-entries if HL position exists but not yet cached. | brain.py:413-431 | Verify HL position check uses fresh cache (not stale hype_cache). Add logging for rejected trades. |

### P0 — Crashers + Direct Financial Loss
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| `SIGNAL_SOURCE_BLACKLIST` fully commented out | All entries in `{}` — nothing is ever blocked. pct-hermes-, vel-hermes-, pattern_scanner all flow to hot-set. | hermes_constants.py:87-101 | Restore active set members |
| STALE_ROTATION bypasses `_close_paper_trade_db` — 3 bugs in 1 | (a) Uses stale pre-close `pnl_pct` not actual close PnL; (b) Never records loss cooldown → immediate re-entry allowed; (c) Never clears reconciled token → re-reconciliation blocked. Direct UPDATE in `_check_stale_rotation` instead of `_close_paper_trade_db`. | hl-sync-guardian.py:~2026-2045 | Replace direct UPDATE with `_close_paper_trade_db(trade_id, token, exit_price, 'STALE_ROTATION')` |
| STALE_ROTATION `rate_data` possibly unbound | If rate_file read raises exception before `rate_data = {}` assignment, `_update_rate()` call raises `NameError`. Variable initialized inside try block. | hl-sync-guardian.py:~1997 | Move `rate_data = {}` before the try block |
| PHANTOM_CLOSE backfill never triggers | `_get_hl_exit_price` NEVER returns 0 (polls ×6, then falls back to current market price). The SELECT `WHERE exit_price = 0` and UPDATE `AND exit_price = 0` are always false for guardian-closed trades. | hl-sync-guardian.py:495,541 | Remove `AND exit_price = 0` from both WHERE clauses |
| `ema20_50` source tags inverted | `SOURCE_LONG='em2050-'`, `SOURCE_SHORT='em2050+'` — LONG writes wrong tag | signals/ema20_50.py:60-61,338 | Swap constants: `SOURCE_LONG='em2050+'`, `SOURCE_SHORT='em2050-'` |
| `guppy.py` undefined constants | `MIN_GROUP_SLOPE` and `SLOW_TREND_LOOKBACK` used but never defined — NameError if called | signals/guppy.py:144,146,350 | Define at top of file |
| `_record_trade_outcome` never called | Function defined but zero call sites in guardian — `signal_outcomes` SQLite DB never written | hl-sync-guardian.py:2683 | Add calls after every `conn.commit()` in all close paths |
| `accel-300+` signal source blacklisted | accel_300_signals.py emits `'accel-300+'` but SIGNAL_SOURCE_BLACKLIST in hermes_constants.py line 142 blocks it — signals can never execute | hermes_constants.py:142, accel_300_signals.py:260 | Change source name to unblocked name (e.g. `'accel-300'`) OR remove from blacklist |
| `gap-300` and `gap300-5m` sources entirely blacklisted | gap300_signals.py writes `gap-300+`/`gap-300-`; gap300_5m_signals.py writes `gap300-5m+`/`gap300-5m-` — ALL four are in SIGNAL_SOURCE_BLACKLIST (hermes_constants.py lines 150-152). Both signal families are dead — generated but immediately blocked at signal_compactor line 679. | gap300_signals.py:40-41, gap300_5m_signals.py:39-40, hermes_constants.py:150-152 | Either unblacklist all variants (if signals are valid) or rename sources to unblocked names |
| `CASCADE_FLIP_ENABLED` undefined in counter_flip_signal.py | counter_flip_signal.py line 282 checks `if not CASCADE_FLIP_ENABLED:` but the constant is never imported from hermes_constants. Python treats as NameError or undefined-false, so counter-flip exits silently in CLI mode. | counter_flip_signal.py:281-284 | Import CASCADE_FLIP_ENABLED from hermes_constants, or remove the CLI guard check |
| hotset.json empty (0 bytes) | Pipeline writes hot-set but file is empty — decider operates on invalid state, all tokens skipped | /var/www/hermes/data/hotset.json | Check signal_compactor.py atomic write (tempfile+fsync+replace), verify cron is writing to correct path |
| k_tp double-k formula in position_manager | `_collect_atr_updates()` does `ATR_TP_K_MULT * _dr_atr()` where `_dr_atr` already returns `k*atr_pct` — effectively `1.25*k*k*atr_pct` | position_manager.py:1579 | Use `k_tp * atr_pct` (same as guardian.py line 2941: `k_tp * atr_pct = k*1.25*atr_pct`) |
| `r2_rev`/`r2_trend` name swap in `name_to_module` | `name_to_module` maps `r2_rev`→`r2_trend` and `r2_trend`→`r2_rev` — both execute `r2_rev.py` (which imports both functions), so `r2_rev` silently runs `scan_r2_trend_signals` and vice versa | signals/__init__.py:303-304 | Remove the swap: `r2_rev`→`r2_rev`, `r2_trend`→`r2_trend` |
| `guppy` signal silently returns None | Registry registers `guppy` with `_guppy_run = scan_all_tokens` but `_run_signal` looks for `mod.run` which doesn't exist — returns `(sig_name, None)` with no error | signals/__init__.py:110-113, 195, 266 | Add a `run(prices_dict=None)` wrapper to guppy.py, or update `_run_signal` to also check `scan_all_tokens` |

### P1 — Logic Errors (Data Corruption / Financial Loss)
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| ATR caps don't match spec | `ATR_SL_MAX=1.0%` (spec=2.0%), `ATR_TP_MIN=1.5%` (spec=0.75%) — unnecessarily restricts valid trades | hermes_constants.py:248-251 | `ATR_SL_MAX=0.020` (2.0%), `ATR_TP_MIN=0.0075` (0.75%) |
| guppy runs full universe | No hot-set gate — runs on all `prices_dict.keys()` (150 tokens) | signals/guppy.py | Add hot-set filter like other signals |
| macd_accel uses stale candles.db | Reads from `candles.db/candles_1m` with no freshness guard — stale MACD signal | signals/macd_accel.py:273+ | Switch to `price_history` with `MAX(timestamp)` freshness check |
| `trailing_active` always False | Dead skip code never executes — `not trailing_active` always True | position_manager.py:2481-2499 | Remove dead code or wire `trailing_active = True` when trailing SL active |
| Opposing penalty over-counts source components | `_get_opposing_penalty` in signal_compactor.py counts every source PART as a separate opposing signal (`opp_source_count += len(opp_parts)`). A 5-source opposing combo applies `5 × 15% = 75%` penalty. Should count opposing signals as 1 per `(token, direction)` pair. | signal_compactor.py:239-279 | Count `len(opp_sources)` (number of opposing rows), not `sum(len(p) for p in opp_parts)` |
| SQL column index fragility | signal_compactor.py lines 465-466 use raw integer indices (`row[8]`, `row[10]`) for `compact_rounds` and `combo_key`. Fragile if SELECT column order ever changes. | signal_compactor.py:465-466 | Use named column access via `cursor.description` or dict unpacking |
| SQL parameter format mixing | signal_gen.py line 1364 uses `?` placeholders (SQLite) but DB connection configured for `%s` syntax — queries silently fail | signal_gen.py:1364 | Use consistent `%s` placeholders OR ensure connection uses `?` format |
| breakout exception in confluence gate | signal_gen.py line 1292: `breakout` exception may incorrectly accept signals that should be filtered | signal_gen.py:1292 | Verify breakout logic — signals with breakout=True but low confidence should still be gated |

### P2 — Signal Quality
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| PUMP_SL_PCT/PUMP_TP_PCT hardcoded | pump hunter TP/SL hardcoded in signal_gen.py instead of hermes_constants.py — drift risk | signal_gen.py | Move to hermes_constants.py |
| Missing scripts | hl_regime_4h.py, mtf_macd.py, rsi_regime.py, gap_300_5m.py, momentum_score.py listed in spec but NOT found at /root/.hermes/scripts/ | — | Confirm renamed/consolidated or restore |

### P2 — Signal Runner / Registry Bugs
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| `_run_signal` silently returns None for missing `run` | Signals with no `run` function (e.g. guppy) return `(sig_name, None)` with no logging — hard to debug | signals/__init__.py:263-265 | Return `f'ERROR: no run function in signals.{module_name}'` instead |
| `co_argcount == 0` branch never executes | `accel_300.run(prices_dict=None)` has 1 arg so the zero-arg branch is dead — all signals always receive `get_all_latest_prices()` | signals/__init__.py:266 | Remove the branch; all signals take prices |
| `counter_flip` missing from `name_to_module` | Falls through to signal name → `__import__('signals.counter_flip')` works by accident | signals/__init__.py:306 | Add `'counter_flip': 'counter_flip'` to name_to_module |
| `r2_rev` missing from `name_to_module` | `r2_rev` not in map → uses `signal['name']` = `'r2_rev'` → `__import__('signals.r2_rev')` (works) | signals/__init__.py | Add `'r2_rev': 'r2_rev'` to name_to_module |
| Duplicate `SIGNAL_REGISTRY` docstring | Lines 171-174 repeat the same comment block verbatim | signals/__init__.py:171-174 | Delete one duplicate block |

### P3 — Minor / Housekeeping
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| Stale `ai_decider` comments in decider_run.py | ~1100-1400 range has old references to ai_decider (DEFUNCT since 2026-04-17) | decider_run.py:~1100-1400 | Clean up stale comments |

### Stage-Specific Audit Checklist (2026-04-28)

Use this 6-stage framework for every audit:

**STAGE 1 — Signal Generation Scripts**
Compile every signal script: `python3 -m py_compile /root/.hermes/scripts/SCRIPT.py`
Check for: NameError (undefined vars), AttributeError (wrong module), IndexError (empty list access), SQL injection (unparameterized queries), race conditions (shared state without locks), API error handling (no try/except on requests), None checks (missing null guards).

**STAGE 2 — Signal Compaction (Hot-Set)**
- hot-set path: `/var/www/hermes/data/hotset.json` (NOT `/root/.hermes/data/hotset.json`)
- signal_compactor.py reads from HOTSET_FILE (paths.py), writes to same path
- Verify atomic write: `tempfile.mkstemp()` + `json.dump()` + `os.fsync()` + `os.replace()`
- SIGNAL_SOURCE_BLACKLIST enforced at `signal_schema.py:add_signal()` (line 860)
- Check for empty hot-set: `ls -la /var/www/hermes/data/hotset.json`

**STAGE 3 — Decision Engine (decider_run.py)**
- ai_decider.py is DEFUNCT — decider_run.py is ACTIVE
- Hot-set staleness check: 20-min threshold
- Regime filters applied correctly
- Cooldowns enforced (cooldown-tracker-ms for deep dive)
- Scoring/selection deterministic

**STAGE 4 — Guardian (hl-sync-guardian.py)**
- DRY mode: `--apply` flag required for live execution (default is DRY)
- Hard stops and TP set correctly
- k_tp formula: `k * ATR_TP_K_MULT * atr_pct` (verify against position_manager)
- Position tracking (long vs short)
- PnL calculation: use `net_pnl` not `pnl_usdt`
- Partial fills handled
- Loss cooldown recorded on ALL loss paths
- Self-close breach cooldown check

**Stage 5 — Hyperliquid Exchange**
- API credentials in `_secrets.py` not hardcoded
- Order types correct (market vs limit)
- Order sizing (notional value correct)
- **HL_MIN_NOTIONAL_USDT check (P0 — found 2026-05-21):** `brain.py:432` rejects trades where `amount_usdt < HL_MIN_NOTIONAL_USDT` (11.0). This gate is NOT in the signal/approval layer — it fires at the Hyperliquid API integration layer AFTER decider_run fires. Pipeline can show "EXEC: brain.py trade add" followed by "REJECTED: amount_usdt=3.5 < HL_MIN=11.0" — the signal flow is working, the block is at HL minimum. Always check pipeline.log for this rejection pattern before auditing upstream signal flow.
- Rate limit handling (429 backoff)
- Response parsing correct

**STAGE 6 — Data Integrity**
- ATR parameters consistent: MIN_ATR_PCT=0.50%, MAX_SL=2.0%, MIN_TP=0.75%, MAX_TP=5.0%
- ATR_TP_K_MULT=1.25 (k_tp = k * 1.25)
- CASCADE_FLIP_ENABLED = False
- SIGNAL_SOURCE_BLACKLIST = ['hzscore+', 'hzscore-', 'hzscore', 'pattern_scanner']
- Price data: live vs stale (check CANDLES_STALENESS_SEC)
- Blacklist/whitelist mechanisms working

**Key Constants Cross-Reference (verify ALL match across files):**
```python
# In hermes_constants.py — these MUST be consistent everywhere:
MIN_ATR_PCT = 0.50    #%
MAX_SL = 2.0          #%
MIN_TP = 0.75         #%
MAX_TP = 5.0          #%
ATR_TP_K_MULT = 1.25  # k_tp = k * 1.25
CASCADE_FLIP_ENABLED = False
SIGNAL_SOURCE_BLACKLIST = ['hzscore+', 'hzscore-', 'hzscore', 'pattern_scanner']
CONFLUENCE_REQUIRED = False   # MUST be True in production — single-source signals bypass hot-set gate when False
```
Verify: grep these values across ALL .py files in /root/.hermes/scripts/ — any deviation is a bug.

**Compile Check Pattern (run on every audit):**
```bash
cd /root/.hermes/scripts
for f in signal_gen.py accel_300_signals.py zscore_pump_hunter.py ma_cross_5m.py pattern_scanner.py signal_compactor.py decider_run.py hl-sync-guardian.py position_manager.py hyperliquid_exchange.py; do
  python3 -m py_compile "$f" && echo "OK: $f" || echo "FAIL: $f"
done
```

**Hot-Set Freshness Check:**
```bash
ls -la /var/www/hermes/data/hotset.json
# Should be non-zero bytes, modified recently
cat /var/www/hermes/data/hotset.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'tokens: {len(d)}')"
```

**Recent Logs Check:**
```bash
tail -100 /root/.hermes/logs/pipeline.log
tail -100 /root/.hermes/logs/sync-guardian.log
tail -100 /root/.hermes/logs/signal-compactor.log
```

**Signals DB Query:**
```bash
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT source, direction, symbol, created_at FROM signals ORDER BY created_at DESC LIMIT 20;"
```

### P0 — Crashers + Direct Financial Loss
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| Breach-close lock path uses undefined var | Lock file `/tmp/hermes-close-lock-.lock` (empty suffix for ALL coins) — no per-coin mutual exclusion | hl-sync-guardian.py:3108 `{token}` | Use `{tok}` (the defined variable) |
| Breach-triggered HL close no cooldown | Trade closes via HL but `_record_loss_cooldown()` never called — immediate re-entry | hl-sync-guardian.py:3175, 3026 | Add `_record_loss_cooldown(token, direction)` after DB commit |
| Wrong DB column names in breach UPDATE | `hl_exit_price`/`realized_pnl` → silent DB write failure | hl-sync-guardian.py:3000, 3008 | Use `exit_price` and `hype_realized_pnl_usdt` |
| `_record_trade_outcome` in both branches | Double cooldown on dedup'd HL losses (called once in each branch) | hl-sync-guardian.py:2617-2618 | Move inside `else` branch only |
| MAX_HYPE_POSITIONS shadow | Local `MAX_HYPE_POSITIONS = 5` shadows `hermes_constants` import — wrong limit used for breach decisions | hl-sync-guardian.py:2078 | Remove local def; use imported constant |

### P1 — Logic Errors (Data Corruption / Financial Loss)
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| Non-atomic hotset.json write | Crash mid-write leaves truncated/corrupted hotset — causes empty hot-set | signal_compactor.py:783-789 | Use `tempfile.mkstemp()` + `json.dump()` + `os.fsync()` + `os.replace()` |
| Stale rotation reads hotset without lock | Read-while-write race — stale or corrupted data used for rotation decision | hl-sync-guardian.py:1792 | Wrap read in `FileLock('hotset_json')` |
| R² mean-reversion logic inverted | LONG=falling knife (downtrend+buy), SHORT=momentum fade (uptrend+sell) | r2_rev_5m_signals.py:114-117 | LONG: `slope>0` + price below line; SHORT: `slope<0` + price above line |
| Mixed timeframe data in signal | 5m candle close used where 1m price was intended — wrong entry price | r2_rev_5m_signals.py:157,249 | Use `close_price: closes[-1]` in signal dict; pass to `add_signal()` |
| Stale winner/loser timeouts swapped | Losers held 30min (dead money), winners cut at 15min (cuts winners early) | position_manager.py:49-50 | Losers=15min (`STALE_LOSER_TIMEOUT_MINUTES`), winners=30min (`STALE_WINNER_TIMEOUT_MINUTES`) |
| Win/loss uses gross pnl | After-fee `net_pnl` not used — small wins after fees = WIN incorrectly | position_manager.py:687-690 | Use `net_pnl if net_pnl is not None else pnl_usdt` |
| Missing loss cooldown after self-close breach | Self-triggered breach close (`_close_breach_position`) doesn't record cooldown | hl-sync-guardian.py:3026 | Add `_record_loss_cooldown()` call |

### P2 — Signal Quality
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| Price_history freshness not checked | Stale `price_history` (API gap) used for signal — phantom signals | volume_hl_signals.py:67-68 | Check `MAX(ts) > CANDLES_STALENESS_SEC` before merge; return `[]` if stale |
| Hardcoded staleness instead of constant | `900` seconds hardcoded — drift from `CANDLES_STALENESS_SEC=120` | r2_rev_5m_signals.py:186 | Use `CANDLES_STALENESS_SEC` from hermes_constants |
| Staleness threshold drift across files | `volume_hl` allows 900s stale; `volume_1m` uses 120s | volume_hl_signals.py:73 vs volume_1m_signals.py:61 | Both should use `CANDLES_STALENESS_SEC` |
| Volume SMA wrong formula | `mean(vol) * mean(price)` instead of `mean(vol * price)` | volume_1m_signals.py:115-126 | Compute per-bar USD volume first |
| Wilder vs SMA EMA seed | macd_1m seeds with Wilder smoothing; others use SMA seed — systematic divergence | macd_1m_signals.py:47-54 | Use SMA seed; prepend `data[0]` to output |

### P3 — Minor / Housekeeping
| Pattern | Symptom | Files | Fix |
|---------|---------|-------|-----|
| Hardcoded timeout in condition | `>= 30` hardcoded instead of `STALE_WINNER_TIMEOUT_MINUTES` | position_manager.py:489 | Use named constant |
| Trailing stops file orphan growth | `active:false` entries accumulate — file grows unbounded | trailing_stops.json | Run clean-up skill periodically; keep only `active:true` |
| Cooldown over-write | Cooldowns written for ALL filtered tokens, not just signaled | run_ma_fast_signals.py, run_r2_trend_signals.py, etc. | Track actual signaled tokens; only write for those |

### FALSE POSITIVES (Not Bugs — Verified 2026-04-26)
| Claim | Reason It's Correct |
|-------|---------------------|
| "rs_signals.py synthesizes OHLCV from price_history" | `candles_1m` table in `candles.db` is 200+ min stale for BTC. Synthesized OHLCV from live `price_history` (updated 1/min) is the CORRECT design for live signal ATR |
| "gap300/r2_trend no local blacklist check" | `add_signal()` already checks SHORT_BLACKLIST, LONG_BLACKLIST, and SIGNAL_SOURCE_BLACKLIST before DB write. Local checks are redundant |
| "bare hzscore check after blacklist" | Belt-and-suspenders for prev-hotset preservation path. `add_signal()` blocks hzscore via SIGNAL_SOURCE_BLACKLIST, but the bare check catches edge case of hzscore from prev-hotset |

### P0/P1 Bugs Fixed (2026-04-26 through 2026-04-28)
| Bug | File | Fix |
|-----|------|-----|
| BUG-20 | hl-sync-guardian.py | Removed local `MAX_HYPE_POSITIONS = 5` shadow |
| BUG-24 | trailing_stops.json | 60 orphaned `active:false` entries removed |
| BUG-26 | position_manager.py | `>=30` → `STALE_WINNER_TIMEOUT_MINUTES` |
| BUG-30 | r2_rev_5m_signals.py | `CANDLES_STALENESS_SEC` import confirmed |
| BUG-31 | r2_rev_5m_signals.py | `close_price: closes[-1]` in signal dict, used in `add_signal()` |
| BUG-32 | r2_rev_5m_signals.py | Swapped `slope < 0 ↔ slope > 0` for LONG/SHORT conditions |
| BUG-33 | hl-sync-guardian.py | `{token}` → `{tok}` in breach-close lock path |
| BUG-34 | hl-sync-guardian.py | `_record_loss_cooldown()` added after breach HL close |
| BUG-35 | hl-sync-guardian.py | `hl_exit_price` → `exit_price`, `realized_pnl` → `hype_realized_pnl_usdt` |
| BUG-39 | signal_compactor.py | Atomic write: `tempfile.mkstemp()` + `os.replace()` + `fsync()` |
| BUG-40 | hl-sync-guardian.py | Hotset read wrapped in `FileLock('hotset_json')` |
| BUG-41 | position_manager.py | Swapped stale timeouts: losers=15, winners=30 |
| BUG-42 | position_manager.py | `net_pnl` used for win/loss classification |
| BUG-43 | hl-sync-guardian.py | `_record_trade_outcome` moved inside `else` branch |
| BUG-44 | volume_hl_signals.py | Freshness check on `price_history` MAX(ts) |
| BUG-45/47 | r2_rev_5m_signals.py | Hardcoded `900` → `CANDLES_STALENESS_SEC` |
| BUG-NEW-1 | hermes_constants.py:142 | `accel-300+` must be removed from SIGNAL_SOURCE_BLACKLIST OR accel_300_signals.py source name changed |
| BUG-NEW-2 | /var/www/hermes/data/hotset.json | Verify atomic write path in signal_compactor.py is working; check cron job is running |
| BUG-NEW-3 | position_manager.py:1579 | k_tp double-k fix: `_dr_atr` already returns `k*atr_pct`, multiply by ATR_TP_K_MULT only |
| BUG-NEW-4 | counter_flip_signal.py:281-284 | `CASCADE_FLIP_ENABLED` not imported — NameError in CLI, silent skip when imported as module |
| BUG-NEW-5 | signal_compactor.py:239-279 | `_get_opposing_penalty` counts source parts not opposing signal rows — should count `len(opp_sources)` |
| BUG-NEW-6 | signal_compactor.py:465-466 | Column index fragility for `compact_rounds` (row[8]) and `combo_key` (row[10]) — use named access |
| BUG-NEW-7 | hermes_constants.py:315 | `CONFLUENCE_REQUIRED=False` — single-source signals bypass hot-set gate. Must be True in production. |

## Key Files
**CRITICAL ARCHITECTURE (2026-05-08):**
- `ai_decider.py` is DEFUNCT — `signal_compactor.py` is the ACTIVE hot-set compactor
- `signal_gen.py` is REMOVED — `signals_runner.py` is the ACTIVE signal runner
- Source weights are in `signal_compactor.py`, NOT in ai_decider
- `decider_run.py` reads hot-set from `signal_compactor` output
- Guardian (`hl-sync-guardian.py`) is the REAL execution path — not decider_run
- `signals_runner.py` runs in BACKGROUND (non-blocking) — timing may misalign with pipeline.log
- `signal_schema.add_signal()` checks `SHORT_BLACKLIST`, `LONG_BLACKLIST`, and `SIGNAL_SOURCE_BLACKLIST` — signal scripts do NOT need local blacklist checks
- hot-set path: `/var/www/hermes/data/hotset.json` (NOT `/root/.hermes/hot-set.json`)
- The canonical DB schema for trades: `exit_price` (not `hl_exit_price`), `hype_realized_pnl_usdt` (not `realized_pnl`), `net_pnl_usdt`
- **k_tp formula**: `k_tp = k * ATR_TP_K_MULT` where `ATR_TP_K_MULT=1.25`. TP pct = `k_tp * atr_pct`. Verify all three files agree: `decider_run.py:182`, `position_manager.py:1579`, `hl-sync-guardian.py:2941`
- **`accel-300+` blacklisted**: hermes_constants.py line 142 has `'accel-300+'` in SIGNAL_SOURCE_BLACKLIST, but accel_300_signals.py emits signals with source `'accel-300+'`. Either unblock or rename the signal source.
- **`CONFLUENCE_REQUIRED` is dead**: Set to True in hermes_constants.py:450 but NEVER checked in signal_compactor.py gate. The gate uses hardcoded 2+ types logic.
- `archive-trades.py` — NOT in git, created May 8 03:16. `--apply` DELETEs from PostgreSQL. Never auto-run.

```
/root/.hermes/scripts/
  run_pipeline.py         — pipeline orchestrator (STEPS_EVERY_MIN = signal_compactor, breakout_engine, signals_runner, decider_run, position_manager, hermes-trades-api)
  signal_compactor.py     — ACTIVE compactor (writes hot-set.json ~1/min)
  signals_runner.py       — ACTIVE signal runner (runs signals/ registry, BACKGROUND via run_bg())
  signals/__init__.py     — signal registry (27 signal scripts)
  signals/*.py            — individual signal scripts
  decider_run.py          — hot-set approval + trade placement (checks guardian-closing-markers.json)
  hl-sync-guardian.py    — DB/HL reconciliation + closing marker system (UNCOMMITTED CHANGES)
  position_manager.py     — trade execution + position tracking + cooldowns
  brain.py                — PostgreSQL brain (loss cooldown helpers, 14 new signal params)
  hype_cache.py           — centralized HL API cache (THE canonical source)
  hyperliquid_exchange.py — HL API wrapper
  hyperliquid_utils.py    — HL utilities
  signal_schema.py        — add_signal() with blacklist checks
  hermes_constants.py    — ALL numeric constants centralized here
  candles.py              — candle data collection
  paths.py                — path constants (HOTSET_FILE, CANDLES_DB, etc.)
  archive-trades.py       — NOT in git — archive to JSON + DELETE from PostgreSQL (DANGEROUS)
  hl_regime_4h.py         — 4h regime scanner (standalone timer, NOT in STEPS_EVERY_MIN)
  trailing_stops.json     — ATR trailing stop state (purge orphans regularly)

  # MISSING (2026-04-28) — confirm if renamed or removed:
  # mtf_macd.py, rsi_regime.py, gap_300_5m.py, momentum_score.py
```

## Audit Script
Save and run from `/root/.hermes`:
```python
#!/usr/bin/env python3
"""Quick audit runner — paste into terminal."""
import subprocess, sys, os

REPO = "/root/.hermes"
SCRIPTS = f"{REPO}/scripts"

def sh(*cmd):
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    return r.stdout, r.stderr, r.returncode

KEY_FILES = [
    "decider-run.py", "ai-decider.py", "signal_gen.py",
    "unified_scanner.py", "position_manager.py", "hyperliquid_exchange.py",
    "hype_cache.py", "hl-sync-guardian.py", "wasp.py", "brain.py", "run_pipeline.py"
]

print("=== 1. SYNTAX ===")
for s in KEY_FILES:
    path = f"{SCRIPTS}/{s}"
    status = "OK" if os.path.exists(path) and sh("python3","-m","py_compile",path)[2]==0 else "FAIL"
    print(f"  {s}: {status}")

print("\n=== 2. IMPORTS ===")
for mod in ["ai_decider", "hype_cache", "signal_gen", "position_manager", "hyperliquid_exchange"]:
    out, err, rc = sh("python3","-c",f"import sys;sys.path.insert(0,'{SCRIPTS}');import {mod}")
    print(f"  {mod}: {'OK' if rc==0 else 'FAIL'}")

print("\n=== 3. SOURCE WEIGHTS — ONE PLACE ONLY ===")
out, _, _ = sh("grep","-rn","SOURCE_WEIGHT\\|source_weight\\|source_mult","--include=*.py",SCRIPTS)
for line in out.splitlines():
    fname = line.split(":")[0].replace(SCRIPTS+"/","")
    if fname not in ["ai-decider.py","decider-run.py"]:
        print(f"  !! OUTSIDE ai-decider: {line}")
    else:
        print(f"  {line}")

print("\n=== 4. DIRECT HL API (should use hype_cache) ===")
for fname in KEY_FILES:
    out, _, _ = sh("grep","-n","requests\\.post.*hyperliquid\\|requests\\.post.*allMids\\|exchange\\.info\\.all_mids",f"{SCRIPTS}/{fname}")
    tag = "!!" if out.strip() else "  "
    print(f"  {tag} {fname}: {'direct calls found' if out.strip() else 'clean'}")

print("\n=== 5. PIPELINE SYNC CHECK ===")
sys.path.insert(0, SCRIPTS)
try:
    from hype_cache import get_allMids
    from hyperliquid_exchange import get_open_hype_positions_curl
    import psycopg2
    mids = get_allMids()
    hl = get_open_hype_positions_curl()
    conn = psycopg2.connect(host='/var/run/postgresql',dbname='brain',user='postgres',password='Brain123')
    cur = conn.cursor()
    cur.execute("SELECT token,status FROM trades WHERE status='open'")
    db_tokens = set(r[0] for r in cur.fetchall())
    cur.close(); conn.close()
    hl_tokens = set(k for k,v in hl.items() if v.get('size',0)!=0)
    diff = (db_tokens ^ hl_tokens)
    print(f"  hype_cache mids: {len(mids)} | HL: {len(hl_tokens)} | DB: {len(db_tokens)}")
    print(f"  Sync: {'OK' if not diff else 'MISMATCH: '+str(diff)}")
except Exception as e:
    print(f"  !! Sync check failed: {e}")

print("\n=== 6. ERROR HANDLING ===")
out, _, _ = sh("grep","-rn","except:$","--include=ai-decider.py","--include=decider-run.py",SCRIPTS)
print(f"  Bare excepts in ai-decider+decider-run: {len(out.splitlines())}")

print("\n=== AUDIT COMPLETE ===")
```

## Audit Checklist (consolidated from code-audit)

### Syntax Check
```bash
cd /root/.hermes
python3 -m py_compile scripts/decider-run.py scripts/ai-decider.py scripts/signal_gen.py \
  scripts/unified_scanner.py scripts/position_manager.py scripts/hyperliquid_exchange.py \
  scripts/hype_cache.py scripts/hl-sync-guardian.py scripts/wasp.py scripts/brain.py
```

### `***` Placeholder Corruption Check
The git diff sanitization tool corrupts `token=?` → `token=***`. Check:
```bash
grep -c 'token=\\\\*\\\\*\\\\*' scripts/signal_gen.py scripts/ai-decider.py scripts/unified_scanner.py
```
Expected: 0 in all files.

### SQL Parameter Check
```bash
grep -c 'WHERE token=\\\\*\\\\*\\\\*' scripts/*.py  # should be 0
```

### Import Check
```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
import ai_decider, hype_cache, signal_gen, position_manager, hyperliquid_exchange
```

### Source Weights Check
Source weights must ONLY be in `ai-decider.py`:
```bash
grep -rn "SOURCE_WEIGHT\|source_weight\|source_mult\|SOURCE_MULT" scripts/ \
  --include=*.py | grep -v ai-decider.py
```
Should be empty.

### HL API Consistency
Direct `requests.post` to Hyperliquid is ONLY allowed in:
- `hype_cache.py` (canonical cache writer)
- `price_collector.py` (cache feeder)
- `hyperliquid_exchange.py` (SDK-level calls)
- `hyperliquid-trader.py` (separate trader)

All other scripts MUST use `hype_cache.get_meta()`, `hype_cache.get_allMids()`, or `hype_cache.get_user_context()`.

Search for violations:
```bash
grep -n "requests\.post.*hyperliquid\|requests\.post.*allMids\|requests\.post.*meta" \
  scripts/decider-run.py scripts/ai-decider.py scripts/unified_scanner.py \
  scripts/hl-sync-guardian.py scripts/wasp.py 2>/dev/null
```
Should return nothing (except in hype_cache.py, price_collector.py, hyperliquid_exchange.py).

### DB Sync Check
```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hype_cache import get_allMids
from hyperliquid_exchange import get_open_hype_positions_curl
import psycopg2

mids = get_allMids()
hl = get_open_hype_positions_curl()
conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
cur = conn.cursor()
cur.execute("SELECT token, status FROM trades WHERE status='open'")
db_tokens = set(r[0] for r in cur.fetchall())
cur.close(); conn.close()
hl_tokens = set(k for k,v in hl.items() if v.get('size',0)!=0)
diff = db_tokens ^ hl_tokens
print(f"hype_cache mids: {len(mids)} | HL: {len(hl_tokens)} | DB: {len(db_tokens)}")
print(f"Sync: {'OK' if not diff else 'MISMATCH: '+str(diff)}")
```

### Error Handling Check
```bash
grep -rn "except:$" scripts/ai-decider.py scripts/decider-run.py
```
Count bare excepts — should be minimal and have logging.

### Security Check
```bash
grep -rn "password.*=" scripts/brain.py  # should use _secrets.py fallback
grep -rn "Bearer \|api_key\|secret.*=" scripts/*.py | grep -v "#\|_ \|password"
```

## Critical Historical Bugs (2026-04-02)

| # | File | Line | Severity | Issue | Status |
|---|------|------|----------|-------|--------|
| 1 | `ai-decider.py` | 313 | HIGH | `clear_ab_cache()` refs undefined `token` (should be `coin`) | FIXED |
| 2 | `unified_scanner.py` | 30, 179 | MEDIUM | Direct `requests.post` to HL `/info` bypasses shared hype_cache | FIXED |
| 3 | `hyperliquid_exchange.py` | 875 | MEDIUM | `mirror_open()` returns undefined `mid_price` (should be `live_price`) | FIXED |
| 4 | `signal_gen.py` | ~1570 | HIGH | 10x `token=***` placeholder bugs in confluence loop | FIXED |
| 5 | `ai-decider.py` | multiple | HIGH | 10x SQL `WHERE token=***` placeholder bugs | FIXED |

## Pitfalls Found So Far (2026-04-02 through 2026-04-28)
- **`accel-300+` permanently blocked**: hermes_constants.py SIGNAL_SOURCE_BLACKLIST includes `'accel-300+'`, but accel_300_signals.py emits signals with this exact source name. Signals generate but can NEVER reach hot-set or execute.
- **`gap-300` and `gap300-5m` entirely dead**: Both signal families are generated with source names that are in SIGNAL_SOURCE_BLACKLIST. gap300_signals.py writes `gap-300+`/`gap-300-` (both blacklisted lines 152). gap300_5m_signals.py writes `gap300-5m+`/`gap300-5m-` (both blacklisted lines 150-151). Every signal from both generators is blocked at signal_compactor.py line 679 before reaching hot-set.
- **k_tp triple formula problem**: Three different TP pct formulas in three files. Always cross-reference `decider_run.py:182`, `position_manager.py:1579`, and `hl-sync-guardian.py:2941` when auditing or fixing TP/SL parameters.
- **CONFLUENCE_REQUIRED=False**: When False, single-source signals bypass the hot-set gate entirely. This significantly changes the risk profile — one bad indicator can trigger a trade without any confluence. Must be True in production. **NOTE**: The flag is True but NEVER CHECKED in signal_compactor.py gate — it's dead code.
- **hotset.json can be 0 bytes**: Even with atomic writes in place, the file can be empty if signal_compactor.py fails before the write or if cron job isn't running. Always check file size.
- **`***` WIP placeholders** in decider-run.py SQL — always verify all SQL is complete
- **Phantom DB entries** from hl-sync-guardian not closing deleted HL positions
- **Symlink `ai_decider.py → ai-decider.py`** required for underscore import — do NOT remove
- **CloudFront blocks `/exchange` endpoint** for clearinghouseState — use `/info` endpoint
- **Symlinks break `git archive`** — allow `ai_decider.py` in update-git.py symlink check
- **`clear_ab_cache(coin=...)` referenced undefined `token`** — parameter was renamed, body wasn't
- **`mirror_open mid_price` NameError** — always use `live_price` in that scope
- **`unified_scanner.py` direct HL API calls** bypassing hype_cache — now fixed to use `get_meta()`
- **`candles_1m` in `candles.db` is 200+ min stale** — synthesized OHLCV from live `price_history` is the CORRECT design, not a bug
- **`signal_schema.add_signal()` is the blacklist authority** — signal scripts do NOT need local blacklist checks (defense-in-depth OK but not required)
- **Loss cooldown MUST be recorded on ALL loss paths in guardian** — breach-triggered HL closes, self-close breaches, and orphan paper closes all need `_record_loss_cooldown()`
- **`guardian-closing-markers.json` stale entries**: 48 tokens permanently blocked from trading if markers not cleared. Always check for stale entries after guardian restarts or after any orphan close event. Marker TTL should be < 5 minutes.
- **`signals_runner` background timing**: `run_bg()` makes signals_runner non-blocking — pipeline.log entries may appear after the main cycle completes. When debugging signal gaps, check signals_runner output separately (grep pipeline.log for signal_runner lines).
- **`DECIDER-LOOP` pipeline.log entry is the primary single-source indicator**: The `[DECIDER-LOOP]` line shows actual execution-time state. `src=accel-300+` (no comma) = single-source. `conf=80.0` is secondary indicator (vs ~98 when multi-source). `src=accel-300+,rs-s236` = two sources (correct). Grep: `grep "DECIDER-LOOP" /root/.hermes/logs/pipeline.log | grep "src=accel-300+"`
- **`get_regime_5m` wrong path**: Renamed function reads non-existent `regime_5m.json` + `regime_5m` DB column. Regime always returns NEUTRAL → signals de-escalated. Verify regime function reads correct path (`regime_15m.json`, `regime_15m` column) or that regime infrastructure exists before using.
- **archive-trades.py DELETE is irreversible**: The `--apply` flag does `DELETE FROM trades WHERE id IN (...)` — this CANNOT be undone. Archive to JSON only unless explicitly directed by T. Check systemd timers and cron before assuming it's not auto-run.
- **`_close_orphan_paper_trade_by_id` searches wrong column**: Searches by `id` (auto-increment) but orphan records created with `trade_id = lev * 1000000`. Orphan block at hl-sync-guardian.py:3638-3678 creates records that `_close_orphan_paper_trade_by_id` can never find.
- **Loss cooldown MUST be recorded on ALL loss paths in guardian** — breach-triggered HL closes, self-close breaches, and orphan paper closes all need `_record_loss_cooldown()`
