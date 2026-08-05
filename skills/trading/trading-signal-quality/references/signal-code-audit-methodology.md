# Signal Code Audit Methodology + Findings Index

Use this reference when auditing a signal script in `/root/.hermes/scripts/signals/`
against its docstring. Captures the audit procedure and a running log of
documented bugs/gaps discovered across audits.

## When to run a signal audit

- Signal fires fewer/more times than expected and a code review is the next step.
- Constants in `hermes_constants.py` look like they've drifted from docstring claims.
- A new finding (e.g., "LONG fires but SHORT never fires") needs root-cause via
  code path analysis, not just parameter tuning.

## Audit procedure (do these in order)

1. **Read the ENTIRE signal file in one read_file call.** Don't skim — bugs hide
   in 800-line files (accel_300.py is 806 lines). Use offset/limit only if the
   file is too large for a single read.

2. **Pull every `SIGNALNAME_*` constant from `hermes_constants.py` in one
   search_files call.** Cross-reference each constant against the docstring and
   the inline detection comments. Drift between docstring text and the actual
   constant value is a first-class finding.

3. **Trace each docstring condition end-to-end through the code.** For each of
   the N conditions in the docstring, find the gate code and answer:
   - What variable stores the gate result?
   - Is the variable ever set to a value that makes the gate silently pass?
   - Are there code paths where the gate is unreachable / dead code?
   - Does the gate's ORDER in execution match its semantic role? (e.g., a
     "fresh cross" check that runs AFTER the cross-bar finder can read stale
     cross_bar = None.)

4. **Look for duplicate / shadowed flags.** Bugs where two variables track the
   same state (e.g., `was_above_recently` and `was_ever_above_in_window` both
   set in the identical conditional) silently disable intended branches.

5. **Look for ordering bugs in the early-exit chain.** `continue` inside
   nested ifs is fine, but if a later check depends on a variable set inside
   a previously-skipped branch, downstream gates operate on stale state.

6. **Build a docstring-vs-implementation matrix.** Table with one row per
   docstring condition, columns: {docstring claim | code location | match?}.
   This is the single most useful artifact — paste it into the report.

7. **MANDATORY: Trace live signals against bar-level state.** This step is
   what catches the class of bug the docstring/implementation matrix MISSES.
   For each of ~10-50 recent signals of this type, run a replica of the
   detection logic against price_history, find which bar `i` would be
   returned, then check:
   - Is the bar's price-vs-EMA consistent with the recorded direction?
   - How old is bar `i` relative to the signal timestamp? (minutes_stale)
   - Is the CURRENT bar's price-vs-EMA consistent with the recorded direction?
   The CRITICAL question: "at the moment the trade would open, is price
   on the correct side of EMA?" — if not, the signal fires directionally
   wrong even though every gate "passes."

   In accel_300.py (2026-06-23), this trace revealed 31% of signals
   (1112/3537) had direction INVERTED vs. current bar — the docstring-vs-
   implementation matrix found zero such bugs because every gate was
   technically wired correctly. The bug was in the SCAN PATTERN itself:
   a forward scan with `break`-on-first-match returns the OLDEST
   qualifying bar, not the most recent. See references/accel-300-stale-
   bar-break-bug-2026-06-23.md for the full reproduction.

8. **Categorize findings by severity:**
   - CRITICAL: gate is a no-op, or always-passes, for an entire direction
   - CRITICAL: scan pattern returns wrong bar (oldest vs. most recent,
     off-by-one in scan range) — only visible via live-signal trace (step 7)
   - MEDIUM: gate is permissive in a way the docstring doesn't mention,
     ordering bug, drift between docstring text and constant values
   - MINOR: dead code, cosmetic duplication, docstring typos

9. **Sanity-check imports.** Signal scripts import from `signal_gen`,
   `signal_schema`, `position_manager`, `hyperliquid_exchange`. If the
   scanner block imports a function, verify the function exists in that
   module. accel_300.py imports `set_cooldown` from `signal_gen` — it's
   re-exported there, which works, but a future refactor could break this
   silently.

## Known audit findings — accel_300.py (audit date 2026-06-23)

### CRITICAL

- **Condition 1 is a no-op for SHORT.** Lines 286-326 of
  `/root/.hermes/scripts/signals/accel_300.py`. The variables
  `was_above_recently` and `was_ever_above_in_window` are set in identical
  conditionals inside the lookback loop (lines 294-301), making the
  `else: continue` branch at line 326 unreachable for SHORT. Net effect:
  any bar where price is currently below EMA passes the fresh-cross gate
  for SHORT regardless of whether price was ever above EMA in the 500-bar
  lookback. The "implied_cross_bar" fallback becomes the only SHORT path,
  even when a real cross was within the window.

- **Forward scan with `break`-on-first-match returns OLDEST qualifying bar,
  not most recent (2026-06-23).** Line 619 of accel_300.py:
  ```
  signal_bar = {...}
  break
  ```
  combined with line 267 `for i in range(PERIOD + LOOKBACK, len(closes) - 1):`
  walks forward through all 700+ bars and exits on the FIRST bar that
  passes all gates. The comment at lines 608-610 claims this returns the
  MOST RECENT match — it does not. Result: signals fire on bars up to
  300+ minutes old (verified in production), recorded `direction` matches
  bar `i`'s price-vs-EMA, but `price` written to the signal row is the
  scanner's CURRENT price which has often reversed through the EMA.
  **Measured impact: 1112/3537 accel_300 signals (31%) today had direction
  INVERTED vs. price-vs-EMA at signal time.** Fix: scan backward from
  `len(closes) - 2`. See references/accel-300-stale-bar-break-bug-2026-06-23.md.
  Audit-class lesson: every detection loop should be checked for scan
  direction vs. intended "most recent" semantics — this bug pattern is
  silent in code review and only visible via live-signal trace (step 7).

### MEDIUM

- **Staleness gate is permissive.** Lines 525-536. The gate allows
  detection up to 400 bars behind the latest bar (`ACCEL_300_STALE_LOOKBACK`).
  Combined with `bars_since_cross <= 60`, a signal can fire on a bar up to
  459 bars old that captured a fresh cross. The fix comment at lines
  530-533 acknowledges this. Document the actual semantic: "fresh cross
  captured within 60 bars, on a bar no older than 400 bars."

- **Chop filter skipped when cross_bar < 50.** Lines 582-606. Gated by
  `cross_bar >= ACCEL_300_CHOP_LOOKBACK`. When the cross is recent
  (bars_since_cross < 50), the chop filter is entirely skipped. Interacts
  with the timing fix at line 540 — early-breakout signals pass without
  chop validation.

- **Duplicate SHORT_BLACKLIST check contradicts its own comment.** Line 669
  blocks ALL signals for SHORT-blacklisted tokens regardless of direction.
  Line 700-701 then claims to apply the blacklist direction-aware. The
  comment at line 697-699 says LONG should still be allowed. Pick one.

- **SHORT never earns gap-growth confidence bonus.** Lines 710-712. The
  bonus uses `sig['gap_growth'] - 0.05` directly — for SHORT,
  `gap_growth` is negative, so `max(0, negative - 0.05) == 0` always.
  Fix: `max(0, abs(sig['gap_growth']) - 0.07)` (using the SHORT growth
  threshold).

### MINOR

- `MIN_GAP_EXPANSION = 0.01` (line 481) is signed but applied with
  ± tolerance — actual semantic is "allow up to 0.01% contraction." Rename
  or tighten the constant name.
- Line 506-508: duplicate comment header for the gap-expansion gate.
- Line 308-309: dead `if cross_bar is not None: pass` block.
  cross_bar is initialized to None at line 286 and not set until line 397.
- Line 489: `'implied_cross_bar' in dir()` is fragile; `implied_cross_bar`
  is unconditionally initialized to None at line 285, so the dir() check
  is redundant with a direct None check.
- Detection docstring at lines 213-223 describes 5 conditions; top
  docstring at lines 14-26 describes 10. Detection docstring is stale.
- Line 502: `max_expansion = ACCEL_300_MIN_GAP_PCT_SHORT * 3` hardcodes
  a constant-derived threshold. If `MIN_GAP_PCT_SHORT` changes, this
  silently changes too.

## Findings index — what was checked, what to look at next

| Signal | Last audited | Known issues |
|---|---|---|
| accel_300.py | 2026-06-23 | See CRITICAL/MEDIUM sections above |
| gap_300.py | not yet | (likely similar pattern: detect gap > N% above EMA300) |
| phase_accel | not yet | (per trading-signal-quality triggers: "phase_accel not appearing in hot-set") |
| zscore-momentum | not yet | (per trading-signal-quality triggers: "zscore-momentum tuner sweeps 0 tokens") |

When auditing a new signal, add a row to this table.