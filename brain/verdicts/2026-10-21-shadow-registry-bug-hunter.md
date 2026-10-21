# Bug Hunter Verification: Shadow-Registry + Shadow-Bypass System

## Summary

Commit `6fee8ef8` is **safe** (zero live-flag changes, tag never corrupts context, shadow DB integrity intact) but **functionally dead**: the tagging matcher uses registry keys that match almost none of the real signal source names in the database, and the 12 disabled-signal entries can never fire anyway — so the shadow-bypass analysis will stay empty forever. Live proof: 8 `ichimoku_long` fires recorded immediately after deploy, 0 tagged.

## Verdict: FAIL

The plumbing works, but the feature collects **zero data** — its entire stated purpose. T's directive "turn on all our old signals in shadow-mode" was not implemented: nothing simulates disabled signals; shadow_trader only tags signals that actually fire, and almost none of the registry names match reality.

## Registry Verification

- ✅ **16 signals present** — Stage A=5, Stage B=4, Stage C=7 (hermes_constants.py:3125-3213)
- ✅ **All fields correct** — every entry has `reason`, `direction`, `stage`
- ✅ **Stages** are only A/B/C; **directions** are only LONG/SHORT
- ✅ **No protected flags** — registry uses signal *source names*; `CEO_PROTECTED_FLAGS` (line 2846) and `RESEARCH_FLAGS` (line 2867) hold *flag names* (`*_ENABLED`), different namespace. Mapped each entry to its flag (e.g. `bb-squeeze-` → `BOLLINGER_SQUEEZE_MINUS_ENABLED`) — none are CEO-protected or research-flagged
- ✅ **Zero live-flag changes** — diff is purely additive; `SHADOW_BYPASS_ENABLED=True` is a new flag; no existing flag value modified. Verified with `git show 6fee8ef8 --stat` (149 insertions, 0 deletions)
- ⚠️ Note (governance, low): `vel-hermes+/-` and `open-skies+` sit in `NEVER_REENABLE_FLAGS`. Shadow-only tagging doesn't re-enable them, so no actual violation — but if these ever collect positive data, re-enable pressure will collide with NEVER_REENABLE. Document the intent now.

## Tagging Logic Verification

- ✅ `record()` loads registry **once per run**, respects `SHADOW_BYPASS_ENABLED`, `except ImportError` degrades safely to no-tag (shadow_trader.py:308-315)
- ✅ Tag added to `ctx` only: `shadow_bypass`, `shadow_bypass_reason`, `shadow_bypass_stage` — no other context field touched (lines 323-334)
- ✅ `INSERT OR IGNORE` on `signal_id UNIQUE` — idempotent, re-record can't duplicate; `close`/`reclose` never overwrite `context`
- ✅ **No interference** — record of 36 new signals post-deploy ran clean in 0.7s; normal signal recording unaffected (EXECUTED/PENDING/EXPIRED rows all stored correctly)
- ✅ **Performance** — 16 substring checks per row, registry imported once: negligible (0.7s for 36 signals incl. all the DB/PG lookups)
- ❌ **Matching is broken against real data** — unit-tested the exact matcher logic against all 265 distinct sources in `signals_hermes_runtime.db` + live record run: **6/25 asserted cases FAIL**, including every high-volume signal (details in Findings 1-2)
- ⚠️ `bare_src = rstrip('+-')` is **dead logic** for the 7 suffixed keys (`bb-squeeze-`, `vel-hermes+` …): rstrip removes the very suffix the key requires, so those keys only match via the `bypass_key in src` fallback. Net matcher ≈ `key in src`. Works today by accident, misleading to maintainers
- ⚠️ Registry `direction` field is **never checked** against the actual trade direction `d` — decorative only

## Analysis Verification

- ✅ Section present at shadow_mode_analysis.py:225-243, executes without error
- ✅ `json_extract(context, '$.shadow_bypass') = 1` — **verified live**: Python `json.dumps(True)` → SQLite `json_extract` returns integer `1` (SQLite 3.45.1). Tested the exact query against an in-memory tagged row: stage, reason, WR, avg all extract correctly
- ✅ `GROUP BY source, direction, stage` + `ORDER BY stage` (text sort A→B→C) correct; empty result renders header-only without crashing
- ⚠️ Commit message claims the section "separates 'passed real gates' from 'would have passed if unblocked'" — **not implemented**; no `gate_blocked` split in the query (doc discrepancy, minor)

## Test Runs (all executed)

| Command | Result |
|---|---|
| `python3 -c "import hermes_constants"` | OK — 16 entries, enabled=True |
| `python3 scripts/shadow_trader.py --record` | ✅ `+36 signals (last_id=1683868 → 1683904)`, 0.7s, no errors |
| `python3 scripts/shadow_trader.py --report` | ✅ full report (8958 signals / 8522 closed) |
| `python3 scripts/shadow_mode_analysis.py` | ✅ full analysis; SHADOW BYPASS section renders **empty** |
| Shadow DB tag count | `SELECT COUNT(*) WHERE json_extract(context,'$.shadow_bypass')=1` → **0 of 8958** |
| systemd scheduling | `hermes-shadow-trader.service` runs `--record --close --report` — integration point intact, pipeline will keep running, but will never produce a tagged row |

## Findings

### CRITICAL — Registry keys don't match real signal source names: Stage B can never be tagged
- **Location**: hermes_constants.py:3166-3185 (Stage B entries) + shadow_trader.py:327-328 (matcher)
- **Issue**: The matcher compares keys against `src` (the `source` column) only. Actual data:
  - `ichimoku_long`/`ichimoku_short` are **signal_type** values; the actual sources are **`ichimoku+`** (414 fires/14d) and **`ichimoku-`** (1,424 fires/14d). Key never matches source → never tagged. Proven live: 8 `ichimoku+|ichimoku_long` rows recorded in the first post-deploy batch, 0 tagged.
  - `support_resistance_long`/`_short` — rs.py emits signal_type `support_resistance` with sources `rs-r78`, `rs-s84` etc. (503 fires/14d). Key matches nothing — neither source nor signal_type.
- **Impact**: The only two Stage B families that actually fire (thousands of rows per 2 weeks — exactly the "gate-blocked" data T wants) produce **zero** shadow-bypass data. Stage B is entirely non-functional.
- **Fix**: Match on `signal_type` + `direction` as well as `source`, and/or fix registry keys to real source names:
  ```python
  # shadow_trader.py record(), replace the matcher:
  bare_src = (src or '').rstrip('+-')
  norm_src = (src or '').replace('_', '-')
  for key, info in shadow_bypass.items():
      if (key in bare_src or key in norm_src
              or (st and key in (st or '').replace('_', '-'))
              or key == f"{st}_{d.lower()}" if st else False):
          ...tag...
  ```
  Simplest correct fix: change keys to `'ichimoku+'`, `'ichimoku-'`, `'support_resistance'` (+direction check via `d`), `'hmacd_mtf+'`/`'hmacd_mtf-'`.

### CRITICAL — 12 of 16 entries are disabled signals that can never fire: no simulation path exists
- **Location**: hermes_constants.py:3125-3213 (registry design) + shadow_trader.py:295-301 (record only reads real fires)
- **Issue**: `record()` snapshots `signals_hermes_runtime.db`, which only contains signals that **actually fired**. Stage A (5) + Stage C (7) entries all have `*_ENABLED = False` — their detectors never run, so no rows are ever written. Verified flags: `BOLLINGER_SQUEEZE_MINUS_ENABLED=False` (2897), `BB_BOUNCE_V3_LONG_ENABLED=False` (2943), `VOLUME_BREAKOUT_PLUS/MINUS_ENABLED=False` (3663-3664), `HMACD_MTF_PLUS/MINUS_ENABLED=False` (2826-2827), `DOJI_BOTTOM_ENABLED=False` (4581), `OPEN_SKIES*_ENABLED=False` (4431-4433), `SQUEEZE_CROSS*_ENABLED=False` (2889-2891), `RS_BROKEN*_ENABLED=False` (675-676), `VEL_HERMES*_ENABLED=False` (2083-2085). None of these 12 names appear in the 14-day runtime DB at all. The registry header comment says "we want shadow_trader to simulate what would happen if they fired" — **shadow_trader does not simulate anything at fire-detection time**; it only tags existing fires. Historical evidence: even the 2 names that do appear (`doji-bottom-long`, `volume-breakout-long+`) stopped firing when killed (last fire 2026-10-16 and 2026-10-13 respectively).
- **Impact**: 12/16 registry entries are inert. T's directive — collect shadow data on the old signals — is not delivered by this commit. The SHADOW BYPASS analysis section will print an empty header forever.
- **Fix**: To actually collect this data you need a shadow signal-generation path, e.g. (a) a `shadow_signals_runner` that runs the disabled detectors (their modules still exist in `scripts/signals/`: `squeeze_cross.py`, `open_skies.py`, `vel_hermes`, `rs.py`, `bb_bounce_v3_long.py`, `volume_breakout.py`, `hmacd.py`…) with their ENABLED flags force-overridden in-process, writes rows to a shadow-only table with `shadow_bypass=true`, then reuses the existing close/report engines; or (b) a replay/backtest harness over historical candles. Option (a) is cheaper and reuses all 7 exit-engine simulations. This is a build, not a patch — needs CEO re-scope.

### HIGH — Composite source strings tag LIVE signals as shadow_bypass (false positive)
- **Location**: shadow_trader.py:328 (`bypass_key in (src or '')`)
- **Issue**: `source` can be a comma-joined confluence string, e.g. the runtime DB contains `bb-squeeze+,volume-breakout-long+`. The key `volume-breakout-long` is a substring → the whole trade gets `shadow_bypass=true` even though `bb-squeeze+` is a **live enabled signal** (BOLLINGER_SQUEEZE_PLUS_ENABLED=True). 1 such row already exists in history.
- **Impact**: Violates the CEO's core requirement — "analysis cleanly separates 'passed real gates' from 'would have passed'". Live-signal trades would pollute the shadow-bypass cohort and corrupt any future re-enable decision built on it.
- **Fix**: Match per-composite-part: `parts = [p for p in (src or '').split(',')]; if any(k in p.rstrip('+-') or k in p for p in parts ...)` — and additionally require the tag only when the matched part is the *sole* source (true single-source bypass) or record which part matched.

### MEDIUM — hmacd registry key uses wrong separator spelling
- **Location**: hermes_constants.py:3143 (`'hmacd-mtf+'`)
- **Issue**: Actual sources in DB are `hmacd_mtf-+` / `hmacd_mtf--` (underscores, and a mangled double-suffix). Key `hmacd-mtf+` (hyphens) matches neither. Unit test confirms: tagged=False.
- **Impact**: Even if the signal were re-enabled it would never be tagged. Low urgency only because the signal is currently dead (Finding 2).
- **Fix**: Normalize separators in the matcher (`.replace('_','-')` on both sides) so registry keys are spelling-robust, and fix the key.

### LOW — Registry `direction` field never validated against actual direction
- **Location**: shadow_trader.py:327-334
- **Issue**: `bypass_info['direction']` is stored in the reason metadata but never compared to the row's `d`. A `squeeze-cross+` row recorded SHORT would still be tagged with the LONG entry.
- **Impact**: Mislabeled direction in the bypass cohort analysis (analysis groups by actual `direction` column, so the mismatch is visible but confusing).
- **Fix**: `if bypass_info.get('direction') and bypass_info['direction'] != d: continue`.

### LOW — `bare_src` rstrip is dead logic for suffixed keys
- **Location**: shadow_trader.py:324
- **Issue**: `rstrip('+-')` strips exactly the suffix that keys like `bb-squeeze-` / `vel-hermes+` require, so those keys can only ever match via the `key in src` fallback. For double-suffix sources (`hmacd_mtf--`) rstrip eats both characters (`→ hmacd_mtf`), which would false-match any future key `hmacd_mtf`.
- **Impact**: No current data corruption, but the code reads as if bare-normalization matters — it doesn't. Maintenance trap.
- **Fix**: Delete `bare_src` or replace with per-composite-part normalization (see HIGH fix).

### LOW (pre-existing, sideways find) — report() closing banner prints 60 log lines
- **Location**: shadow_trader.py:881 — `log("\n═" * 60)`
- **Issue**: Multiplication applies to the `"\n═"` string, producing 60 separate lines (visible at the bottom of every `--report` run). Line 831 does it correctly (`"═" * 60`).
- **Impact**: Cosmetic log noise only.
- **Fix**: `log("\n" + "═" * 60)`.

### INFO (doc) — Commit message overstates the analysis
- **Location**: commit 6fee8ef8 message; shadow_mode_analysis.py:225-243
- **Issue**: "Separates 'passed real gates' from 'would have passed if unblocked'" is not in the query — no `gate_blocked` split.
- **Fix**: Add `gate_blocked` to the SELECT/GROUP BY, or amend the claim.

## Verified Working

- hermes_constants.py imports cleanly; registry = 16 entries; master switch honored
- `shadow_trader.py --record` runs clean end-to-end (+36 rows, watermark advanced, no exceptions)
- `shadow_trader.py --report` and `shadow_mode_analysis.py` run clean end-to-end
- Tag never corrupts context JSON; other context fields intact; `INSERT OR IGNORE` idempotency; close/reclose don't touch context
- SQLite `json_extract` boolean handling (`true → 1`) verified on this box (SQLite 3.45.1)
- Analysis SQL correctness verified on an injected tagged row (stage, reason, WR, avg all correct)
- Zero live-flag changes — diff purely additive; no `*_ENABLED` value, gate, or blacklist modified
- Matching correctly does NOT tag live lookalikes: `bb-squeeze+`, `bb-bounce-v2-long+`, `volume-breakout-short-`, `doji-top-short`, `pump-chain+` all clean
- `hermes-shadow-trader.service` integration intact (`--record --close --report` on timer)
- Registry overlaps with CEO_PROTECTED_FLAGS / RESEARCH_FLAGS: none

## Recommendations

1. **Do not treat this feature as delivered.** It is safe but collects nothing. Report to CEO that "shadow-mode old signals" requires a shadow signal-*generation* path (Finding 2), not just tagging — that's the real build, and it should reuse the existing 7 exit-engine simulation stack via a `shadow_signals_runner` with in-process flag overrides. Shadow-only, zero live-flag changes remains achievable.
2. **Fix the Stage B matcher now (Findings 1 + 3 + 4)** — Stage B is the one part that could work today since those signals genuinely fire. Correct keys (`ichimoku+`/`ichimoku-`, `support_resistance` + direction, `hmacd_mtf`), match against `signal_type` too, split composite sources before matching, add the direction check. Small, testable patch.
3. **Add a self-test assertion to the analysis** — e.g. a sanity line: "registry entries that matched ≥1 row in 30d: N/16". Makes dead entries impossible to miss next time.
4. **Run the unit-test matrix in this verdict as a permanent test** (25 source-name cases incl. live lookalikes) under `scripts/tests/` or as a `--selftest` flag so future registry edits get validated against real source names.
5. **Document NEVER_REENABLE interaction** for `vel-hermes+/-` and `open-skies+` before any of that data lands.
6. Fix the two cosmetic items (banner multiply, commit-message overstatement) on the next touch of these files.

*Verification method: read full diff of 6fee8ef8, read all three modified files, queried `signals_hermes_runtime.db` (8,647 rows / 265 distinct sources, 2026-10-07→21) and `brain/shadow_trades.db` (8,958 rows), ran all three scripts live, and executed a 25-case unit test of the exact matcher logic. No code was modified by this verification.*
