# cut_loser v2 — Full Spec

Mirror image of profit_monster. Two-tier loss cutting + trailing loss tier. Cuts losers fast before they bleed to ATR SL.

## Problem

Current cut_loser.py:
- No systemd timer (dead since May 18, 2026)
- Single flat tier (-0.5% to -3.0%), too slow (5-18 min fire windows)
- No safety checks (HL position, guardian markers)
- Doesn't record to signal_outcomes (exits invisible to stats)
- Not integrated with position_manager (commented out at line 2684)
- No trailing loss logic (no peak-worst tracking)

Result: vortex_break_long losses bleed 50-260 min before ATR SL catches them. All exits are `atr_sl_hit` — no early exit fires.

## Architecture

```
cut_loser.py (every 1min via systemd timer)
  ├─ Tier 1 (Quick Cut): -0.3% to -1.0%, fires 1-3 min
  ├─ Tier 2 (Deep Cut):  -1.0% to -3.0%, fires 3-6 min
  └─ Trailing Loss:       track worst point, cut on recovery failure

position_manager.py (every pipeline run)
  └─ should_cut_loser(): SL breach check (immediate, not probabilistic)

guardian (independent)
  └─ Emergency exits: flip, hard SL at -5% (untouched)
```

Three complementary layers, no overlap:
1. **position_manager** — immediate SL breach (deterministic)
2. **cut_loser** — probabilistic cutting in loss zones (two-tier + trailing)
3. **guardian** — emergency exits (flip, hard stop at -5%)

## Constants (hermes_constants.py)

```python
# ── cut_loser v2 — mirror of profit_monster ──────────────────────────────────
# Tier 1: Quick Cut — catch small losses fast
CL_TIER1_MIN_PCT      = -1.0    # floor (don't cut deeper than this in T1)
CL_TIER1_MAX_PCT      = -0.3    # ceiling (don't cut tiny drawdowns)
CL_TIER1_MAX_CLOSE    = 2       # max positions to close per wake
CL_TIER1_SKIP_BOTTOM_PCT = 10   # don't touch bottom 10% worst losers
CL_TIER1_FIRE_WINDOWS = {"A": (1, 3), "B": (3, 6)}   # minutes

# Tier 2: Deep Cut — handle bigger losses
CL_TIER2_MIN_PCT      = -3.0    # floor
CL_TIER2_MAX_PCT      = -1.0    # ceiling (T1 handles above this)
CL_TIER2_MAX_CLOSE    = 1       # max positions to close per wake
CL_TIER2_SKIP_BOTTOM_PCT = 20   # don't touch bottom 20% — let ATR SL handle catastrophic
CL_TIER2_FIRE_WINDOWS = {"A": (3, 6), "B": (6, 12)}  # minutes

# Trailing Loss — mirror of PM_TRAIL
CL_TRAIL_ENABLED        = True
CL_TRAIL_ACTIVATE_PCT   = -0.3   # start tracking at -0.3% loss
CL_TRAIL_RECOVER_PCT    = 0.15   # cut if price recovers 0.15% from worst then drops back
CL_TRAIL_MIN_HOLD       = 2      # minimum minutes before trailing activates
CL_TRAIL_FIRE_WINDOWS   = {"A": (0.5, 1), "B": (1, 2)}  # check every 30-60s

# Legacy constants (keep for guardian compatibility)
CUT_LOSER_PNL = -2.0   # guardian hard-stop — DO NOT CHANGE
```

## cut_loser.py — Full Implementation

### File structure

```python
#!/usr/bin/env python3
"""
Cut Loser v2 — Two-tier loss cutting + trailing loss.
Mirror image of profit_monster.py.

Tier 1 (Quick Cut): -0.3% to -1.0%, fires frequently. Catches small losses fast.
Tier 2 (Deep Cut):  -1.0% to -3.0%, fires less frequently. Handles bigger bleeds.
Trailing Loss:       Track worst point, cut if recovery fails.

All params tunable via hermes_constants.py (CL_TIER1_*, CL_TIER2_*, CL_TRAIL_*).
"""
```

### Functions (mirror of profit_monster.py)

| cut_loser v2 | profit_monster equivalent | Purpose |
|-------------|--------------------------|---------|
| `load_config()` | `load_config()` | Load JSON config |
| `should_fire()` | `should_fire()` | Random timer check |
| `get_losing_positions()` | `get_all_open_positions()` | Query DB, order by pnl ASC |
| `filter_by_pnl()` | `filter_by_pnl()` | Filter to loss range |
| `select_positions()` | `select_positions()` | Skip bottom X%, pick random subset |
| `is_position_on_hl()` | `is_position_on_hl()` | Safety: skip if already closed |
| `is_token_being_closed_by_guardian()` | `is_token_being_closed_by_guardian()` | Safety: skip if guardian handling |
| `is_token_being_closed_by_profit_monster()` | — | Safety: skip if PM is closing (race prevention) |
| `close_position()` | `close_position()` | HL close + DB update + signal_outcomes |
| `run_tier()` | `run_tier()` | One tier: fire check → filter → select → close |
| `run_trail()` | `run_trail()` | Trailing loss tier |
| `_load_trail_state()` | `_load_trail_state()` | Load trailing state JSON |
| `_save_trail_state()` | `_save_trail_state()` | Save trailing state JSON |
| `run()` | `run()` | Main entry point |

### Key implementation details

#### get_losing_positions()

```python
def get_losing_positions():
    """Return list of dicts for open positions with pnl_pct < 0, ordered worst first."""
    # Same query as profit_monster but ORDER BY pnl_pct ASC (worst losers first)
    # This ensures Tier 1 skips bottom X% correctly (worst are at top of list)
```

#### filter_by_pnl()

```python
def filter_by_pnl(positions, min_pct, max_pct):
    """Filter positions to those within loss range.
    
    min_pct is more negative (floor), max_pct is less negative (ceiling).
    Example: T1 range is min_pct=-1.0, max_pct=-0.3
    """
    # Uses pnl_utils.compute_live_pnl() — same as profit_monster
    # Sets pos["live_pnl_pct"] for downstream use
```

#### select_positions()

```python
def select_positions(positions, max_close, skip_bottom_pct, trail_state=None):
    """Select positions to close: skip worst losers + trailed, pick random subset.
    
    skip_bottom_pct: skip the worst X% of losers (let them recover or hit ATR SL)
    trail_state: skip trades being trailed by trailing loss tier
    """
    # Mirror of profit_monster but skips BOTTOM instead of TOP
    # Random selection prevents always cutting the same position
```

#### Safety checks

```python
def is_token_being_closed_by_profit_monster(token: str) -> bool:
    """Check if profit_monster closing markers include this token."""
    # Read profit_monster_trail_state.json + check recent closes
    # Prevents race: if PM is closing, don't also cut_loser close
```

#### close_position()

```python
def close_position(trade_id, token, direction, pnl_pct, current_price, dry_run, tier):
    """Close position: safety checks → HL close → DB update → signal_outcomes.
    
    Same structure as profit_monster.close_position() but:
    - Tier label is "CL-T1" or "CL-T2" or "CL-trail"
    - close_reason is "cut-loser-T1", "cut-loser-T2", "cut-loser-trail"
    - Records to signal_outcomes with signal_type from trades table
    """
    # 1. Safety: check guardian markers, HL position, profit_monster state
    # 2. HL close (if live trading)
    # 3. DB update via brain.py trade close
    # 4. Record to signal_outcomes (same as profit_monster)
```

#### Trailing Loss tier (run_trail)

```python
def run_trail(positions, dry_run):
    """Trailing loss tier: track worst point, cut on recovery failure.
    
    Mirror of profit_monster.run_trail() but inverted:
    
    profit_monster trail:
      - Activates at +0.30% profit
      - Tracks PEAK (highest pnl)
      - Cuts when pnl drops 0.15% below peak
    
    cut_loser trail:
      - Activates at -0.30% loss
      - Tracks WORST (lowest pnl / most negative)
      - Cuts when pnl recovers 0.15% from worst then drops back
    
    Logic:
    1. When trade hits CL_TRAIL_ACTIVATE_PCT → mark as trailing, record worst_pnl
    2. On each check: if worst_pnl improved (less negative), update worst
    3. If current_pnl > worst_pnl + CL_TRAIL_RECOVER_PCT → cut (recovery failed)
    4. If trade recovers above activation threshold → clear state (recovered)
    """
```

State file: `/root/.hermes/data/cut_loser_trail_state.json`
Format: `{trade_id: {worst_pnl, activated_at, token}}`

#### run_tier()

```python
def run_tier(tier_name, min_pct, max_pct, max_close, skip_bottom_pct, fire_windows, positions, dry_run, trail_state=None):
    """Run one tier: check fire timing, filter positions, close picks.
    
    Same structure as profit_monster.run_tier() but:
    - skip_bottom_pct instead of skip_top_pct
    - Trail state skips trades being trailed (trail tier handles those)
    """
```

#### Main run()

```python
def run(dry_run=False):
    # 1. Load config, check enabled
    # 2. Get all open positions (once, shared across tiers)
    # 3. Run trailing loss tier first (catches early losses)
    # 4. Load trail state for T1/T2 to skip trailed trades
    # 5. Run Tier 1 (quick cut)
    # 6. Re-fetch positions if T1 closed any
    # 7. Run Tier 2 (deep cut)
    # 8. Log totals
```

## position_manager.py changes

### Uncomment should_cut_loser (line 2684)

Current state:
```python
# ── 5. Cut loser (DISABLED — guardian handles all emergency exits) ──
# if not trailing_active and should_cut_loser(live_pnl, pos):
#     reason = f"cut_loser_{live_pnl:+.2f}%"
#     close_paper_position(trade_id, reason)
```

New state:
```python
# ── 5. Cut loser — immediate SL breach only ──────────────────────────────
# Only fires when actual stop_loss price is breached (Priority 1 in should_cut_loser).
# Probabilistic cutting is handled by cut_loser.py (two-tier + trailing).
# Race prevention: check guardian markers before closing.
if should_cut_loser(live_pnl, pos):
    reason = f"cut_loser_{live_pnl:+.2f}%"
    close_paper_position(trade_id, reason)
    closed_count += 1
    log(f"  CUT_LOSER {token} {direction} {live_pnl:+.2f}%")
```

### should_cut_loser() stays as-is (line 320)

Already correct:
- Priority 1: actual stop_loss price breach (deterministic)
- Priority 2: sl_distance from A/B test
- Priority 3: global CUT_LOSER_PNL (-2.0%)

No changes needed to the function itself.

## systemd files

### /etc/systemd/system/cut-loser.service

```ini
[Unit]
Description=Cut Loser v2 — auto-close losing positions (oneshot)

[Service]
Type=oneshot
User=root
WorkingDirectory=/root/.hermes/scripts
ExecStart=/usr/bin/python3 /root/.hermes/scripts/cut_loser.py
StandardOutput=append:/root/.hermes/logs/cut_loser.log
StandardError=append:/root/.hermes/logs/cut_loser.log
```

### /etc/systemd/system/cut-loser.timer

```ini
[Unit]
Description=Cut Loser timer — fires every minute

[Timer]
OnBootSec=30
OnUnitActiveSec=1min
Persistent=true

[Install]
WantedBy=timers.target
```

## Constants to remove (hermes_constants.py)

```python
# REMOVE these (replaced by CL_TIER1/CL_TIER2):
LOSS_MIN_PCT           = -3.0   # → CL_TIER2_MIN_PCT
LOSS_MAX_PCT           = -0.5   # → CL_TIER1_MAX_PCT
CUT_LOSER_MAX_CLOSE    = 1      # → CL_TIER1_MAX_CLOSE / CL_TIER2_MAX_CLOSE
SKIP_BOTTOM_PCT        = 0      # → CL_TIER1_SKIP_BOTTOM_PCT
CUT_LOSER_FIRE_WINDOWS = {...}  # → CL_TIER1_FIRE_WINDOWS / CL_TIER2_FIRE_WINDOWS
```

Keep: `CUT_LOSER_ENABLED = True` (rename to `CL_ENABLED` if desired, but keep backward compat)

## Expected behavior

### vortex_break_long example (from today's data)

| Token | Loss | Current exit | New T1 exit | New T2 exit | Trailing exit |
|-------|------|-------------|-------------|-------------|---------------|
| PNUT | -0.65% | ATR SL (50min) | ~10-15min | — | — |
| MNT | -0.32% | ATR SL (261min) | ~5-10min | — | — |
| TNSR | -1.22% | ATR SL (117min) | — | ~20-30min | — |
| UMA | -0.88% | ATR SL (62min) | ~10-15min | — | — |
| TNSR | -0.71% | ATR SL (66min) | ~10-15min | — | — |
| ME | -0.38% | ATR SL (145min) | ~5-10min | — | — |
| AVNT | -0.76% | ATR SL (70min) | ~10-15min | — | — |

All losses cut in 5-30 min instead of 50-260 min. Avg loss reduced by ~60-70%.

## Implementation order

1. Add constants to hermes_constants.py (CL_TIER1, CL_TIER2, CL_TRAIL)
2. Rewrite cut_loser.py (mirror profit_monster structure)
3. Uncomment should_cut_loser in position_manager.py
4. Create systemd files
5. Enable and start timer
6. Test with --dry-run
7. Monitor logs for 24h
8. Tune fire windows based on results

## Files to change

| File | Action |
|------|--------|
| `scripts/hermes_constants.py` | Add CL_TIER1/2/TRAIL constants, keep old ones for now |
| `scripts/cut_loser.py` | Full rewrite |
| `scripts/position_manager.py` | Uncomment should_cut_loser (line 2684) |
| `/etc/systemd/system/cut-loser.service` | Create |
| `/etc/systemd/system/cut-loser.timer` | Create |
| `plans/cut-loser-v2-spec.md` | This file |

## Risk assessment

- **Race with profit_monster**: Both close positions. Safety checks (guardian markers, HL check) prevent double-close.
- **Race with guardian**: Guardian handles emergency exits (flip, hard SL at -5%). cut_loser handles medium losses (-0.3% to -3%). No overlap.
- **Race with position_manager should_cut_loser**: position_manager fires on SL breach (deterministic). cut_loser fires probabilistically. If both fire, the first one closes and the second finds the position already closed (safety check skips it).
- **Over-cutting**: Random selection + skip_bottom_pct prevents always cutting the same position. Fire windows prevent cutting too frequently.
- **Signal outcomes noise**: cut_loser exits will show in signal stats. This is intentional — we want to see which signals produce losers that get cut early.
