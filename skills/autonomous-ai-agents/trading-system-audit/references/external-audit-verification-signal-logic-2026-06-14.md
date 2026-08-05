# External Audit Verification: signal-logic-review.md (2026-06-14)

**Source:** `/root/shared/signal-logic-review.md` — Dropbox external review of `accel_300.py` and `rs.py`

**Key lesson:** External audits cite line numbers and claim "missing" features that are already implemented in the current codebase. The review was against an older version of the files. **Always verify every claim against the actual deployed code before implementing.**

---

## Case Study: 13 Issues Reviewed

| # | Review Claim | Verification Method | Result |
|---|-------------|---------------------|--------|
| a1 | SHORT gap-growth sign-inverted | `grep -n "avg_gap_growth.*<=" accel_300.py` + read lines 365-375 | **TRUE BUG** — widening SHORT gaps rejected. Fixed. |
| a2 | SHORT stale-cross window=30, not 500 | `grep ACCEL_300_LOOKBACK_SHORT hermes_constants.py` | Already correct (ACCEL_300_LOOKBACK_SHORT=500). Review outdated. |
| a3 | SHORT min gap=0.20, not 0.25 | `grep ACCEL_300_MIN_GAP_PCT_SHORT hermes_constants.py` | Already correct (0.25). Review outdated. |
| a4 | SHORT growth=0.05, not 0.07 | `grep ACCEL_300_MIN_GAP_GROWTH_SHORT hermes_constants.py` | Already correct (0.07). Review outdated. |
| a5 | SHORT_BLACKLIST blocks LONG | Read scan loop (line 649) — checked before direction known | **TRUE BUG** — moved blacklist after direction. Fixed. |
| a6 | Stale gate bars>10, not ~60 | `grep STALE_BARS accel_300.py` | Already correct (STALE_BARS=60, STALE_BARS_SHORT=55). Review outdated. |
| — | "signal bar near latest bar" unimplemented | `grep bars_from_latest accel_300.py` (line 529) | Already implemented. Review outdated. |
| — | Gap expansion unimplemented | `grep MIN_GAP_EXPANSION accel_300.py` (line 507) | Already implemented. Review outdated. |
| — | Stale gap decay unimplemented | `grep STALE_GAP_DECAY accel_300.py` (line 574) | Already implemented. Review outdated. |
| — | Chop filter unimplemented | `grep CHOP_LOOKBACK accel_300.py` (line 579) | Already implemented. Review outdated. |
| r1 | Recency scoring inverted | `grep recency_score.*ancient rs.py` + read lines 382-395 | **TRUE BUG** — formula was `recent + K×ancient`. Fixed to `K×recent + ancient`. |
| r2 | Recency lookup after clustering fails | Read `_get_clustered_recency` (line 504) + callers at 531,541 | Already handled via nearest-raw-level lookup. Review outdated. |
| r3 | Level selection by distance, not recency | Read nearest level loop (lines 527-545) | Already uses `_get_clustered_recency`. Review outdated. |
| r4 | Bounce condition (a) dead code | Read `_bounce_confirmation` (lines 249-271) | **TRUE BUG** — `open==close` on synthesized candles. Fixed. |
| r5 | Level broken check direction-agnostic | Read `_level_recently_broken` (lines 315-340) | Already direction-aware (separate support/resistance logic). Review outdated. |
| r6 | `return 0` when disabled, not `(0,[])` | Read `scan_rs_signals` top (line 762) | **TRUE BUG** — bare `return 0`. Fixed to `return 0, []`. |
| — | RS_COOLDOWN_HOURS unused | `grep RS_COOLDOWN_HOURS rs.py` — only import at line 72 | **TRUE BUG** — imported but never applied. Fixed (added cooldown enforcement). |
| r7 | add_signal missing value/exchange/timeframe | Read `add_signal()` signature in signal_schema.py:361 + call at rs.py:815 | **TRUE BUG** — params missing. Fixed. |

**Net: 4 actual bugs fixed. 9 claims were already correct (outdated review).**

---

## External Audit Verification Protocol

1. **Read the review document** — understand all claimed issues
2. **Read the actual current code** — don't assume the review's line numbers are accurate
3. **Verify each claim with grep/search_files** in the actual deployed file at `/root/.hermes/scripts/`
4. **Mark items as: TRUE BUG / ALREADY FIXED / OUTDATED REVIEW**
5. **Fix only TRUE BUG items** — do not re-implement already-correct code
6. **Syntax check after every patch** — `python3 -m py_compile <file.py>`

### Common External Audit Failure Patterns
- **Line numbers shift** as files evolve — review citing "line 249" may reference different code
- **"Missing" constants** — flags ARE defined in hermes_constants.py but not in the older checkout the reviewer used
- **"Unimplemented" features** — already added in a later session the reviewer didn't see
- **Misread indentation** — continue/break statements that appear to skip guards actually have full logic above them
- **Confuse commented-out vs live code** — old workarounds remain commented in files but newer fixes exist elsewhere
- **Confuse SQLite vs PostgreSQL** — different parameterization styles between DBs
