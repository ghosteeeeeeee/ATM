# Critical Bugs Reference

Archived from `new-signal-implementation/SKILL.md` to reduce SKILL.md size.

### Bug #1: Cooldown Writer Receives Only Count
Scanner returns only `int` (count), caller loops over ALL tokens. **Fix:** Return `tuple[int, set[str]]` — both count AND tokens that fired.

### Bug #2: Multi-Indicator Array Alignment
Two indicators with different warm-up periods don't share the same starting candle index. **Fix:** Use `bisect` for O(log n) timestamp lookup. Never use offset arithmetic.

### Bug #5: Compression Detection — Relative vs Absolute Thresholds
Relative to noisy baseline fails when spikes contaminate prior window. **Fix:** Use absolute thresholds (volume < X, range% < Y).

### Bug #7: Stale Signal — Check Only the Most Recent Bar
Loop iterates over ALL bars, fires if ANY meets criteria. Old bars always eventually meet criteria. **Fix:** Only check the most recent bar.

### Bug #8: Trend-Persistence Signal — was_below Too Restrictive
"Price crossed from below" fails for coins in clear uptrend for hours. **Fix:** Dual-path: (A) strong acceleration bypasses purity check, (B) consistent persistence ≥X% of recent bars.

### Bug #10: Systemd Timer Setup
Use oneshot service + timer pattern. `Persistent=true` catches missed runs. Service MUST exist before timer activates.

### Bug #11: Crossing-Bar Consecutive Count Resets to Zero
At crossing bar, count resets to 0. **Fix:** Check prior bar's consecutive count, verify current bar crosses EMA.

### Bug #12: Exhaustion Signal Fires ONLY at Crossing
Exhaustion signals fire at the MOMENT price crosses EMA. **Fix:** Historical simulation to verify — iterate bar-by-bar checking for exhaustion condition.

### Bug #13: Bare print() Goes to pipeline.log
When signal script is imported as module, bare print() goes to captured stdout → pipeline.log. **Fix:** Write `_log()` helper that writes to both stdout and signals.log.

### Bug #14: Persistence + Gap-Growth Signal Catches Peaks
"Persistent above EMA + gap growing" fires at END of extension, not start. **Fix:** Add marginal acceleration check — latest bar-over-bar delta must exceed prior delta.
