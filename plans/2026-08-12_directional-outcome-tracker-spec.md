# Directional Outcome Tracker ("Weather Vane") — Spec v2

**Date:** 2026-08-12
**Author:** T + opencode
**Status:** PROPOSED (CEO reviewed: APPROVE WITH MODIFICATIONS)
**CEO Report:** `automation/ceo/ceo_report.md`

---

## Problem

When SHORT signals that were on a winning streak start losing in clusters, it means the market regime has shifted (bearish → bullish). The current regime detection system is too slow:

1. **4h_regime_scanner** — runs every 4 hours, linear regression of closes (lagging)
2. **15m_regime_scanner** (actually 5m) — runs every 15 minutes, still lagging
3. **Regime penalty** in signal_compactor — only applies 0.5x if regime_conf > 50 and direction contradicts regime

By the time the scanners register the shift, the system has already eaten 3+ losses.

**"Ships in the water" problem:** Even if we suppress NEW signals, existing open positions are still exposed. A SHORT opened at 18:30 during bearish regime is still open at 20:20 when regime flips bullish — it's a sitting duck.

## Insight

Trade outcomes are a LEADING indicator of regime shifts. Slope-based scanners are LAGGING. A cluster of losses on one direction IS the weather change, detected instantly from trade results.

## Solution: Weather Vane (3 Components)

```
┌─────────────────────────────────────────────────────────────────┐
│                    WEATHER VANE SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Component 1: SIGNAL GATE                                       │
│  Suppress new signals in losing direction                       │
│  Location: signal_compactor.py (scoring stage)                  │
│                                                                 │
│  Component 2: POSITION SHIELD                                   │
│  Protect open counter-regime positions                          │
│  Location: position_manager.py (new function)                   │
│                                                                 │
│  Component 3: RECOVERY                                          │
│  Rolling window auto-recovers when losses age out               │
│  No explicit reset needed                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component 1: Signal Gate

### Mechanism

```
Rolling window: last 5 trades per direction, 30 minutes
Trigger: 3+ losses in last 5 trades within 30 minutes
Action: suppress ALL new signals in that direction (0.7x score multiplier)
Recovery: rolling window — old losses age out naturally
```

### Parameters (hermes_constants.py)

```python
# ── Weather Vane: Directional Outcome Tracker ────────────────────────────
# Detects regime shifts by monitoring trade outcomes per direction.
# Fires when 3+ of last 5 trades in same direction are losses within 30min.
# Faster than regime scanners (leading indicator vs lagging slope).
DIRECTIONAL_OUTCOME_ENABLED = True
DIRECTIONAL_OUTCOME_WINDOW = 5            # last N trades per direction
DIRECTIONAL_OUTCOME_TIME_WINDOW = 30      # minutes (rolling window)
DIRECTIONAL_OUTCOME_LOSS_THRESHOLD = 3    # N losses in window to trigger
DIRECTIONAL_OUTCOME_WR_THRESHOLD = 40     # backup: WR below this also triggers
DIRECTIONAL_OUTCOME_PENALTY = 0.7         # score multiplier (milder for first deploy)
DIRECTIONAL_OUTCOME_MIN_TRADES = 3        # minimum trades before activating
```

### Integration: signal_compactor.py

After `reg_mult` calculation (line ~365), before `final_score`:

```python
# Weather vane: directional outcome penalty
dir_outcome_mult = 1.0
if DIRECTIONAL_OUTCOME_ENABLED:
    losses, total, wr = get_directional_outcome(direction)
    if total >= DIRECTIONAL_OUTCOME_MIN_TRADES:
        # Trigger on cluster detection (3+ losses in 5) OR low WR (< 40%)
        if losses >= DIRECTIONAL_OUTCOME_LOSS_THRESHOLD or wr < DIRECTIONAL_OUTCOME_WR_THRESHOLD:
            dir_outcome_mult = DIRECTIONAL_OUTCOME_PENALTY
            log(f"  🌊 [WEATHER-VANE] {token} {direction}: "
                f"{losses}/{total} losses in {DIRECTIONAL_OUTCOME_WINDOW}T "
                f"(WR={wr:.0f}%) → {dir_outcome_mult}x penalty")

final_score = score * survival_bonus * staleness_mult * reg_mult * dir_outcome_mult * source_mult * speed_mult
```

### Data Source

```sql
-- get_directional_outcome() query
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN is_win = 0 THEN 1 ELSE 0 END) as losses,
    ROUND(100.0 * SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as wr
FROM signal_outcomes
WHERE direction = ?
  AND created_at > datetime('now', '-{TIME_WINDOW} minutes')
ORDER BY created_at DESC
LIMIT {WINDOW};
```

---

## Component 2: Position Shield ("Ships in the Water")

### The Problem

When Weather Vane detects a regime shift (3+ SHORT losses), existing SHORT positions are at risk. Currently:
- ATR trailing SL protects against normal pullbacks (0.80% trailing distance)
- But in a regime shift, price can grind against the position for extended time
- The trailing SL may be too wide to protect against a sustained directional move

### Mechanism

When Weather Vane triggers for a direction:
1. Query all open positions in that direction from PostgreSQL
2. For each counter-regime position:
   - **If losing (PnL < 0):** tighten trailing stop from 0.80% to 0.30%
   - **If winning (PnL > 0):** leave alone (trailing already protecting)
3. Set max_hold_minutes for counter-regime positions (30min)
4. Log: `"WEATHER-VANE: tightened SHORT TIA stop 0.80%→0.30%"`

### Parameters

```python
# ── Weather Vane: Position Shield ────────────────────────────────────────
# Tightens stops on open counter-regime positions when regime shift detected.
WEATHER_VANE_SHIELD_ENABLED = True
WEATHER_VANE_SHIELD_TRAILING_PCT = 0.0030   # 0.30% — tightened from 0.80%
WEATHER_VANE_SHIELD_MAX_HOLD_MIN = 30       # close counter-regime positions after this long
WEATHER_VANE_SHIELD_LOSING_ONLY = True      # only tighten LOSING positions (winners are OK)
```

### Integration: position_manager.py

New function `apply_weather_vane_shield()`:

```python
def apply_weather_vane_shield(losing_direction: str) -> int:
    """
    Tighten stops on open positions in the losing direction.
    Returns number of positions affected.

    Called by signal_compactor when weather vane triggers.
    """
    if not WEATHER_VANE_SHIELD_ENABLED:
        return 0

    affected = 0
    open_trades = get_open_positions()  # existing function

    for trade in open_trades:
        if trade['direction'] != losing_direction:
            continue

        token = trade['token']
        pnl_pct = trade.get('pnl_pct', 0)

        # Only tighten LOSING positions — winners are already protected by trailing
        if WEATHER_VANE_SHIELD_LOSING_ONLY and pnl_pct >= 0:
            continue

        # Tighten trailing distance
        new_trailing = WEATHER_VANE_SHIELD_TRAILING_PCT
        old_trailing = trade.get('trailing_distance', TRAILING_DISTANCE_PCT)

        if new_trailing < old_trailing:
            _update_trailing_distance(trade['id'], new_trailing)
            affected += 1
            log(f"  🛡️  [WEATHER-VANE SHIELD] {token} {losing_direction}: "
                f"trailing {old_trailing*100:.2f}% → {new_trailing*100:.2f}% "
                f"(PnL={pnl_pct:+.2f}%)")

    return affected
```

### How Stops Get Updated

The trailing distance is stored in the `trades` table (`trailing_distance` column). When the Weather Vane tightens it:
1. UPDATE trades SET trailing_distance = 0.003 WHERE id = ?
2. On next guardian cycle, tpsl_utils.py reads the new trailing_distance
3. Trailing SL now uses the tighter 0.30% distance instead of 0.80%

No need to push a new SL order to HL immediately — the guardian's next ATR update cycle will apply the tighter trailing.

### Edge Case: False Alarm

If the regime shift was false (3 losses was just variance):
- The tight stop (0.30%) means the position exits quickly if price continues against us
- If price reverses (false alarm), the position was already at a loss and the tight stop minimizes further damage
- The 30min max_hold prevents "hoping" a losing counter-regime trade turns around
- Once the weather vane recovers (old losses age out), normal trailing distance (0.80%) is restored for new positions

---

## Component 3: Recovery

### Rolling Window Recovery

The weather vane naturally recovers — no explicit reset needed:

```
20:03 CFX SHORT loss    → window: [L] (1/1)
20:07 TIA SHORT loss    → window: [L,L] (2/2)
20:19 ZK SHORT loss     → window: [L,L,L] (3/3) → TRIGGER (3+ losses in 5)
20:33 CFX loss ages out → window: [L,L] (2/3) → still triggered
20:35 NEW SHORT wins    → window: [L,L,W] (2/4) → still triggered (50% WR)
20:40 NEW SHORT wins    → window: [L,W,W] (2/5) → still triggered (60% WR > 40%)
20:45 TIA loss ages out → window: [W,W] (1/3) → RECOVERED (losses aged out)
```

### Shield Recovery

When weather vane recovers:
- No explicit action needed for new positions — they get normal trailing distance (0.80%)
- Existing tightened positions keep their tight stop until:
  - They hit the tight stop (exit)
  - They recover to breakeven and trailing takes over
  - They hit the 30min max_hold (close)

---

## Data Flow

```
Trade closes → signal_outcomes table updated
    ↓
get_directional_outcome() queries last 5 trades per direction
    ↓
3+ losses detected in 30min window?
    ├─ YES → TRIGGER
    │   ├─ Signal Gate: dir_outcome_mult = 0.7x in compactor scoring
    │   ├─ Position Shield: tighten stops on open counter-regime LOSING positions
    │   └─ Alert: log "🌊 WEATHER-VANE: SHORT regime shift detected"
    │
    └─ NO → normal operation
        ↓
Rolling window recovers (old losses age out, new wins come in)
    ↓
dir_outcome_mult = 1.0 (unsuppressed)
    ↓
New positions get normal trailing distance (0.80%)
```

---

## Interaction with Existing Systems

| System | Relationship |
|--------|-------------|
| Regime scanners (4h/5m) | Weather vane is FASTER (real-time vs lagging). Both can coexist — regime scanners provide structural context, weather vane provides tactical response. |
| Loss cooldown (per-token) | Independent layer. Token cooldown blocks re-entry on same token. Weather vane blocks ALL signals in losing direction. |
| Wrong-side learning | Complementary. Wrong-side tracks per-token historical win rate. Weather vane tracks per-direction recent outcomes. |
| Self-learner | Independent. Self-learner adjusts params daily (slow). Weather vane responds in real-time (fast). |
| Context gate | Weather vane feeds into compactor scoring, which feeds into context gate decisions. No direct interaction. |
| Profit monster | No conflict. Profit monster closes winning positions. Weather vane (Phase 2) would tighten stops on LOSING positions. Different targets. |
| ATR trailing | Phase 1: no interaction (signal gate only). Phase 2: would need tpsl_utils.py modification to support per-trade trailing override (currently uses global constant). |

---

## Edge Cases

### 1. Cold Start
System just started, no trade history in window → skip weather vane (MIN_TRADES not met). Normal operation.

### 2. Mixed Direction Losses
Both LONG and SHORT losing simultaneously → market is choppy/ranging, not directional shift. Both directions suppressed → fewer trades overall (correct behavior — reduce exposure in choppy market).

### 3. Fast Recovery
3 SHORT losses at 20:03-20:19, then 2 SHORT wins at 20:35-20:40 → window shows 60% WR (3/5) → unsuppress. The rolling window handles this naturally.

### 4. Token vs Direction
Token X has loss cooldown, but SHORT overall is fine → independent layers. Both can be active simultaneously. Token cooldown blocks re-entry on X. Weather vane blocks all SHORT signals.

### 5. Regime Scanner Disagreement
Weather vane says SHORT is losing, but 4h regime says SHORT_BIAS → Weather vane wins. It's real-time, regime scanner is lagging. Trust the leading indicator.

### 6. Shield on Winning Positions
Weather vane triggers but all open SHORT positions are in profit → WEATHER_VANE_SHIELD_LOSING_ONLY=True means no tightening. Winners are already protected by normal trailing.

### 7. Multiple Triggers in Window
Weather vane triggers at 20:19, triggers again at 20:25 (still in loss cluster) → no double-penalizing. The dir_outcome_mult is recalculated each compaction round — it's either 0.7x or 1.0x, never 0.7x twice.

---

## Implementation Plan

### Phase 1: Signal Gate (signal_compactor.py) — CEO APPROVED
1. Add params to `hermes_constants.py`
2. Add `get_directional_outcome()` helper (in signal_compactor.py or new file)
3. Add `dir_outcome_mult` in compactor scoring (after `reg_mult`)
4. Test: verify it triggers on simulated loss clusters

### Phase 2: Position Shield — CEO REJECTED (integration bug) → FIXED 2026-08-12

**Blocker (now fixed):** `tpsl_utils.py` used the global `TRAILING_DISTANCE_PCT` constant everywhere:
- Line 528: `trail_floor = round(highest_price * (1 - TRAILING_DISTANCE_PCT), 8)`
- Line 551: `trail_ceil = round(lowest_price * (1 + TRAILING_DISTANCE_PCT), 8)`
- Line 501: `eff_sl_pct = max(min(eff_sl_pct, TRAILING_DISTANCE_PCT), ATR_SL_MIN)`

It never read the per-trade `trailing_distance` column from the DB. Updating that field was a no-op.

**Fix applied:** Added `trailing_distance: Optional[float] = None` parameter to `compute_atr_sl_tp()`. Uses per-trade value when set, falls back to global constant when None. Caller (`position_manager.py`) passes `pos.get('trailing_distance')`. Edge case: `trailing_distance=0` guarded with `> 0` check.

**Bug hunter reviewed:** PASS — all 8 functional uses replaced, default behavior identical, no regressions.

**Status:** Phase 2 is now unblocked. Can proceed with Position Shield implementation.

### Phase 3: Recovery & Monitoring
1. Add weather vane status to dashboard (hotset or signal_outcomes view)
2. Monitor: does it trigger on real regime shifts? Does it recover properly?
3. Tune: adjust LOSS_THRESHOLD, WR_THRESHOLD, PENALTY based on live data

### Files to Modify

| File | Change | Status |
|------|--------|--------|
| `scripts/hermes_constants.py` | Add Weather Vane params | PENDING (Phase 1) |
| `scripts/signal_compactor.py` | Add `get_directional_outcome()` + `dir_outcome_mult` in scoring | PENDING (Phase 1) |
| `scripts/tpsl_utils.py` | Add `trailing_distance` param to `compute_atr_sl_tp()` | DONE (2026-08-12) |
| `scripts/position_manager.py` | Pass `pos.get('trailing_distance')` to compute_atr_sl_tp | DONE (2026-08-12) |

---

## Testing

1. **Unit test:** Simulate 5 trades with 3 losses → verify trigger fires
2. **Recovery test:** Simulate 5 trades with 3 losses, then 2 wins → verify trigger clears
3. **Shield test:** Create open trade, trigger weather vane → verify trailing_distance updated
4. **Backtest:** Query signal_outcomes for last 7 days, simulate weather vane, compare WR with/without
5. **Paper trade:** Enable with PENALTY=0.85 (very mild) for 48h, observe behavior

---

## Risk

| Risk | Mitigation |
|------|-----------|
| Over-suppression | MIN_TRADES=3 and 30min time window limit false triggers. 0.7x penalty (not 0.0) — signals still fire, just ranked lower. |
| Shield false alarm | Tight stop (0.30%) on losing positions is aggressive but correct — if position is losing AND regime shifted, getting out fast is right. |
| Missed entries | If weather vane suppresses SHORT and regime stays bearish, we lose valid trades. But 0.7x penalty means top-quality SHORT signals still survive (88 conf × 0.7 = 61.6, above MIN_EXEC_CONFIDENCE of 50). |
| Performance | One extra SQL query per compaction round (5 trades, simple query). Negligible. |
