# Spec: Temporal Confluence — Signal Accumulation Window

**Date:** 2026-10-13
**Status:** SPEC — awaiting CEO approval
**Author:** CEO agent

## Problem

The confluence gate requires **spatial confluence** (2+ different signal types at the same moment). Single-source signals are blocked unless they're in `STANDALONE_BYPASS_SIGNALS`.

This creates a blind spot: a signal that fires **repeatedly** for the same token+direction is strong evidence the setup is real, but each fire is treated as an isolated single-source event and blocked.

**Evidence (2026-10-12/13):**
- 40+ SHORT signals fired during BTC dump (21:02–21:50). `return_exhaustion-short` fired 3+ times for 8 tokens (SYRUP, SUPER, IO, GMX, FIL, ALT, WCT, ZORA). All blocked as single-source. 0 trades.
- 22 PENDING signals at 01:30. `return_exhaustion-short` × 8, `wyckoff-` × 1, `pump-chain-` × 12. Hotset empty.
- GRASS SHORT: 5 fires in 30 minutes, all expired as PENDING.

**Current signal lifecycle:**
1. Signal fires → INSERT into `signals` DB as PENDING
2. Next cycle: query PENDING signals
3. If combo_key in top-10 hotset → APPROVED
4. If not in top-10 and age > 5 min → EXPIRED

Signals expire individually. Repetition is never counted as evidence.

## Proposal

**Temporal confluence:** If the same token+direction accumulates N signal fires within a time window, treat that repetition as confluence and bypass the single-source block.

This is **not** removing any filter. It adds a new evidence path alongside the existing spatial confluence.

## Design

### Where in the pipeline

In `signal_compactor.py`, the confluence gate (Step 2, lines 3247–3318). Add a new bypass branch **before** the final `else` block that currently sets `gate_msg = 'only N unique types — need 2+'`.

The check fires only when:
- `CONFLUENCE_REQUIRED = True`
- `unique_signal_types == 1` (single-source)
- Signal is NOT in `STANDALONE_BYPASS_SIGNALS`
- No other bypass path matched

### Counting fires

Query the `signals` DB for recent fires matching token+direction:

```sql
SELECT COUNT(*) FROM signals
WHERE token = ? AND direction = ?
  AND created_at > datetime('now', ?)
  AND decision IN ('PENDING', 'EXPIRED')
```

The `?` for time is a SQLite modifier string like `'-30 minutes'`.

**⚠️ CRITICAL: Do NOT use `executed = 0` in this query.** When signals expire, they get `executed = 1`. Using `executed = 0` returns 0 for most tokens (verified: GRASS SHORT has 20 fires but all have `executed = 1`). The `decision IN ('PENDING','EXPIRED')` filter correctly counts all fires that were detected but not traded.

**What counts as a fire:**
- Any signal row for the same token+direction within the window
- Regardless of source (pump-chain-, volume-breakout-short-, etc. all count)
- PENDING and EXPIRED both count (expired signals still represent real detections)
- EXECUTED signals are excluded (already traded — no need for confluence bypass)

**What doesn't count:**
- Opposite direction (LONG fires don't count toward SHORT threshold)
- Different token
- Signals older than the window

### Constants

Add to `hermes_constants.py`:

```python
# ── Temporal Confluence ─────────────────────────────────────────────────────
# Repetition of the same token+direction signal within a window = confluence.
# Bypasses single-source confluence gate. Does NOT bypass any other filter
# (RR engine, penalty gate, RSI floors/ceilings, HALL-SHAME, etc.).
# Spec: plans/temporal-confluence-spec.md
TEMPORAL_CONFLUENCE_ENABLED = True
TEMPORAL_CONFLUENCE_WINDOW_MIN = 30     # minutes to count fires
TEMPORAL_CONFLUENCE_MIN_FIRES = 3       # fires needed to qualify
```

**Defaults rationale:**
- `WINDOW_MIN = 30`: Signals expire at 5 min. 30 min = 6 expiration cycles. Long enough to accumulate, short enough to stay relevant.
- `MIN_FIRES = 3`: Conservative. 2 fires could be noise. 3 fires across 30 min = the setup persisted through 3 detection cycles.
- `ENABLED = True`: Ships live. The bypass only affects the confluence gate — all downstream filters still apply. Risk is low.

### Code placement

In `signal_compactor.py`, inside the confluence gate block, add before the final `else`:

```python
# ── Temporal Confluence Bypass ──────────────────────────────────────────
# Repetition = evidence. If this token+direction fired N+ times in the
# window, the setup is persistent enough to treat as confluence.
elif (TEMPORAL_CONFLUENCE_ENABLED
      and unique_signal_types == 1
      and _temporal_confluence_count(token, direction) >= TEMPORAL_CONFLUENCE_MIN_FIRES):
    pass_gate = True
    gate_msg = f'temporal confluence ({_tc_count} fires in {TEMPORAL_CONFLUENCE_WINDOW_MIN}min)'
```

Helper function:

```python
def _temporal_confluence_count(token: str, direction: str) -> int:
    """Count recent signal fires for token+direction within the temporal window.
    
    NOTE: Uses decision IN ('PENDING','EXPIRED') — NOT executed = 0.
    Expired signals have executed = 1 but represent real detections.
    Using executed = 0 would return 0 for most tokens (verified with GRASS/CHIP).
    """
    try:
        from hermes_constants import TEMPORAL_CONFLUENCE_WINDOW_MIN
        _conn = sqlite3.connect(RUNTIME_DB, timeout=3)
        try:
            _cur = _conn.cursor()
            _cur.execute("""
                SELECT COUNT(*) FROM signals
                WHERE token = ? AND direction = ?
                  AND decision IN ('PENDING', 'EXPIRED')
                  AND created_at > datetime('now', ?)
            """, (token.upper(), direction.upper(),
                  f'-{TEMPORAL_CONFLUENCE_WINDOW_MIN} minutes'))
            _row = _cur.fetchone()
            return _row[0] if _row else 0
        finally:
            _cur.close()
            _conn.close()
    except Exception:
        return 0  # fail-open: no temporal bypass on error
```

### Interaction with existing filters

**What temporal confluence BYPASSES:**
- Single-source confluence gate only

**What temporal confluence does NOT bypass (all still apply):**
- RR engine (grade C/D penalties)
- Penalty gate (exec_conf < 40%)
- HALL-SHAME (30d WR < 55%)
- RSI floors/ceilings (LONG_RSI_CEILING, SHORT_RSI_HARD_FLOOR, etc.)
- CONTINUUM-BLOCK (bearish structure)
- SLOPE-FILTER
- CHASE-BLOCK
- VOL-GATE-BYPASS
- Blacklists
- All other safety filters

This is intentional. Temporal confluence is an **evidence path**, not a safety bypass. A signal that fires 5 times but has grade F R:R still gets blocked by the RR engine.

### What about confidence boost?

**Not in v1.** The initial implementation only bypasses the gate. A future enhancement could multiply confidence by fire count (e.g., 3 fires = 1.2x confidence), but that requires separate backtesting.

### Logging

Every temporal confluence bypass logs:

```
✅ [TEMPORAL-CONFLUENCE] {token} {direction} — {count} fires in {window}min, bypassing single-source block
```

This makes it easy to audit how often the bypass fires and whether the resulting trades win.

### Shadow mode option

If CEO prefers caution, ship with `TEMPORAL_CONFLUENCE_ENABLED = False` and add a shadow log:

```python
if not TEMPORAL_CONFLUENCE_ENABLED:
    _tc_shadow_count = _temporal_confluence_count(token, direction)
    if _tc_shadow_count >= TEMPORAL_CONFLUENCE_MIN_FIRES:
        log(f"  📊 [TEMPORAL-CONFLUENCE-SHADOW] {token} {direction} — would bypass ({_tc_shadow_count} fires), flag OFF")
```

This collects counterfactual data without changing behavior.

## Relationship to Existing `signal_confluence`

There is already a `signal_confluence` meta-signal (`scripts/signals/signal_confluence.py`) that does something similar. The two are **complementary, not overlapping**:

| Aspect | `signal_confluence` (existing) | Temporal Confluence (proposed) |
|--------|-------------------------------|-------------------------------|
| Window | 30 min | 30 min |
| What it counts | **Unique source types** (different signals) | **Total fires** (same source OK) |
| Threshold | `MIN_COMPOUND = 3` unique sources | `MIN_FIRES = 3` total fires |
| Price confirmation | Required — price must move in favor | Not required |
| Persistence | Required — price must not reverse | Not required |
| Action | Fires a **new signal** (confluence+/−) | **Bypasses the gate** for the existing signal |
| Cooldown | Per token+direction | None |

**The gap `signal_confluence` doesn't cover:** If `return_exhaustion-short` fires 5 times for GRASS but no other signal type fires, `compound_count = 1` (below `MIN_COMPOUND = 3`). The confluence signal never fires. The 5 individual signals each expire as single-source PENDING.

This is exactly the 2026-10-12/13 scenario: `return_exhaustion-short` fired repeatedly for 8 tokens, `pump-chain-` fired repeatedly for 12 tokens. Same source, multiple fires, no other signal types agreeing. `signal_confluence` saw `compound_count = 1` and stayed silent.

**The two approaches catch different things:**
- `signal_confluence`: "Three different signals agree AND price confirms" → high-conviction second chance
- Temporal confluence: "One signal won't shut up about this coin" → persistent setup

**They coexist without conflict.** `signal_confluence` runs as a slow signal (every 5 min, `_SLOW_SIGNALS`). Temporal confluence runs in the compactor (every cycle). A token could trigger both — the confluence signal adds a new signal, temporal confluence lets the original signal through.

**Potential interaction:** If temporal confluence bypasses the gate for a single-source signal, and `signal_confluence` later fires a confluence+ signal for the same token, both would be in the hotset. The deduplication by token+direction (Step 8) would keep the higher-scored one. This is acceptable — it means the market had both temporal and spatial confluence, which is stronger evidence.

## Risk Analysis

**Risk 1: Same bad signal fires repeatedly → repeated losses**
- Mitigation: Downstream filters still apply. A signal with bad R:R, low WR, or overbought RSI still gets blocked. Temporal confluence only bypasses the "single-source" check.

**Risk 2: Signal fires rapidly due to data glitch → false confluence**
- Mitigation: `executed = 0` filter. Also, the signals DB has a unique index on `combo_key WHERE decision='PENDING' AND executed=0` — duplicate combo_keys are already deduplicated.

**Risk 3: Accumulated signals are stale by the time threshold is met**
- Mitigation: 30-minute window is short. Also, the signal that triggers the bypass is the current cycle's signal — it's fresh. The historical fires just provide the evidence.

## Expected Impact

Based on 2026-10-12/13 data:
- `return_exhaustion-short`: 8 tokens × 3+ fires = 8 trades that would have passed confluence
- `pump-chain-`: 12 tokens with 3+ fires = 12 trades
- Total: ~20 additional trades over 24h

Whether these trades win depends on downstream filters. The point is they get a **chance** to be evaluated instead of being auto-blocked.

## Verification Plan

1. **Shadow mode first (recommended):** Ship `ENABLED = False`, log would-bypass events for 48h. Count how many would have fired and check their hypothetical outcomes.
2. **Live with revert trigger:** If enabled, monitor: temporal-confluence cohort n≥10 with WR < 40% or PnL < −$1 → revert to False.
3. **Independent backtest:** Run own-conclusions auditor on the shadow data before flipping ON.

## Files Changed

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | Add 3 constants |
| `scripts/signal_compactor.py` | Add `_temporal_confluence_count()` helper + bypass branch in confluence gate |
