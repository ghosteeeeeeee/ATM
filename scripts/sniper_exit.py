#!/usr/bin/env python3
"""
Sniper Exit Strategy — Proactive position closing on regime shifts.

When BTC trend shifts, sniper detects the new direction and closes ONLY
positions on the wrong side. Right-side positions ride the trend.

Runs every 3 minutes via systemd timer.

Usage:
    python3 sniper_exit.py              # live run
    python3 sniper_exit.py --dry-run    # detection only, no closes
    python3 sniper_exit.py --status     # show current state
"""

import sys
import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from paths import HERMES_DATA, RUNTIME_DB

LOG_FILE = os.path.join(os.path.dirname(HERMES_DATA), 'logs', 'sniper_exit.log')
STATE_FILE = os.path.join(HERMES_DATA, 'sniper_state.json')
TRAIL_STATE_FILE = os.path.join(HERMES_DATA, 'profit_monster_trail_state.json')
CLOSING_MARKERS_FILE = os.path.join(HERMES_DATA, 'sniper_closing_markers.json')

# ── Logging ────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [SNIPER] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('sniper')


# ═══════════════════════════════════════════════════════════════════════════
#  CONSTANTS (imported from hermes_constants when available)
# ═══════════════════════════════════════════════════════════════════════════

try:
    from hermes_constants import (
        SNIPER_ENABLED,
        SNIPER_CHECK_INTERVAL,
        SNIPER_MAX_CLOSES_PER_CYCLE,
        SNIPER_MAX_CYCLES,
        SNIPER_COOLDOWN,
        SNIPER_MIN_LOSS_THRESHOLD,
        SNIPER_BTC_VELOCITY_THRESHOLD,
        SNIPER_SIGNALS_FOR_L1,
        SNIPER_SIGNALS_FOR_L2,
        SNIPER_SIGNALS_FOR_L3,
    )
except ImportError:
    # Defaults if constants not yet added
    SNIPER_ENABLED = True
    SNIPER_CHECK_INTERVAL = 180
    SNIPER_MAX_CLOSES_PER_CYCLE = 2
    SNIPER_MAX_CYCLES = 6
    SNIPER_COOLDOWN = 600
    SNIPER_MIN_LOSS_THRESHOLD = -0.5
    SNIPER_BTC_VELOCITY_THRESHOLD = 0.15
    SNIPER_SIGNALS_FOR_L1 = 1
    SNIPER_SIGNALS_FOR_L2 = 2
    SNIPER_SIGNALS_FOR_L3 = 3


# ═══════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS — Read data from existing SQLite tables
# ═══════════════════════════════════════════════════════════════════════════

def _db_query(db_path, query, params=(), one=True):
    """Run a query against a SQLite DB with proper cleanup."""
    import sqlite3
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, params)
        return cur.fetchone() if one else cur.fetchall()
    except Exception as e:
        log.warning(f"DB query error ({db_path}): {e}")
        return None
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def get_btc_wave_phase():
    """Read BTC wave_phase from token_speeds table.
    Returns: 'accelerating', 'decelerating', 'bottoming', 'falling', or 'neutral'
    """
    row = _db_query(RUNTIME_DB, "SELECT wave_phase FROM token_speeds WHERE token='BTC'")
    return row['wave_phase'] if row else None


def get_btc_velocity():
    """Read BTC 30m price change from token_speeds (fresh data).
    Returns: float (percentage) or None
    """
    row = _db_query(RUNTIME_DB, "SELECT price_change_30m FROM token_speeds WHERE token='BTC'")
    return row['price_change_30m'] if row else None


def get_btc_momentum_state():
    """Read BTC momentum_state from momentum_cache.
    Returns: 'bullish', 'bearish', 'neutral', or None
    NOTE: momentum_cache may be stale — caller should check age.
    """
    row = _db_query(RUNTIME_DB, "SELECT momentum_state FROM momentum_cache WHERE token='BTC'")
    return row['momentum_state'] if row else None


def get_momentum_cache_age_minutes():
    """Check how old the BTC momentum_cache entry is.
    Returns: age in minutes, or 9999 if unknown/stale
    """
    row = _db_query(RUNTIME_DB, "SELECT updated_at FROM momentum_cache WHERE token='BTC'")
    if row and row['updated_at']:
        try:
            age = (time.time() - float(row['updated_at'])) / 60
            return max(0, age)
        except (ValueError, TypeError):
            return 9999
    return 9999


def get_btc_slope_15m():
    """Read BTC 15m avg_z (slope proxy) from momentum_cache.
    Returns: float or None
    """
    row = _db_query(RUNTIME_DB, "SELECT avg_z FROM momentum_cache WHERE token='BTC'")
    return row['avg_z'] if row else None


def volatility_regime_changed():
    """Check if BTC volatility regime changed in last 4 hours.
    Uses state file to track previous regime.
    Returns: True if changed
    """
    try:
        state = _load_state()
        prev_regime = state.get('last_volatility_regime')

        # Read current regime from regime_5m.json
        regime_file = '/var/www/hermes/data/regime_5m.json'
        if os.path.exists(regime_file):
            with open(regime_file) as f:
                data = json.load(f)
            # Find BTC in the regime data
            for token_data in data.get('tokens', []):
                if token_data.get('token') == 'BTC':
                    current_regime = token_data.get('regime', 'NEUTRAL')
                    if prev_regime and current_regime != prev_regime:
                        state['last_volatility_regime'] = current_regime
                        _save_state(state)
                        return True
                    state['last_volatility_regime'] = current_regime
                    _save_state(state)
                    return False
    except Exception as e:
        log.warning(f"volatility_regime_changed error: {e}")
    return False


# ═══════════════════════════════════════════════════════════════════════════
#  STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def _load_state():
    """Load sniper state from JSON file."""
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_state(state):
    """Save sniper state to JSON file."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        log.warning(f"Failed to save state: {e}")


def _load_trail_state():
    """Load profit_monster trail state. Keys are STRINGS."""
    try:
        with open(TRAIL_STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# ═══════════════════════════════════════════════════════════════════════════
#  MUTUAL EXCLUSION — Closing markers
# ═══════════════════════════════════════════════════════════════════════════

def write_closing_marker(token):
    """Write a marker indicating sniper is closing this token."""
    markers = {}
    try:
        with open(CLOSING_MARKERS_FILE) as f:
            markers = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    markers[token] = time.time()
    try:
        with open(CLOSING_MARKERS_FILE, 'w') as f:
            json.dump(markers, f)
    except Exception:
        pass


def clear_closing_marker(token):
    """Remove closing marker after close completes."""
    markers = {}
    try:
        with open(CLOSING_MARKERS_FILE) as f:
            markers = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    markers.pop(token, None)
    try:
        with open(CLOSING_MARKERS_FILE, 'w') as f:
            json.dump(markers, f)
    except Exception:
        pass


def is_token_being_closed_by_sniper(token):
    """Check if sniper is currently closing this token.
    Used by profit_monster and cut_loser to avoid double-close.
    """
    try:
        with open(CLOSING_MARKERS_FILE) as f:
            markers = json.load(f)
        return token.upper() in {k.upper() for k in markers.keys()}
    except (FileNotFoundError, json.JSONDecodeError):
        return False


# ═══════════════════════════════════════════════════════════════════════════
#  SHIFT DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def detect_shift():
    """Detect market shift and determine direction.
    Returns: (shift_level, shift_direction) or None

    Uses majority voting — not strict agreement. CRITICAL crash = 2 votes.
    All helper functions read from existing SQLite tables.
    """
    signals = 0
    direction_votes = {'BEARISH': 0, 'BULLISH': 0}

    # ── Fast signals (1-5 min) — crash filter ──
    try:
        from btc_crash_filter import check_crash
        crash_result = check_crash()

        if crash_result.blocked:
            severity = crash_result.severity
            if severity == 'EMERGENCY':
                return (3, 'BEARISH')  # Crashes are always bearish
            elif severity == 'CRITICAL':
                signals += 2
                direction_votes['BEARISH'] += 2
            elif severity == 'WARNING':
                signals += 1
                direction_votes['BEARISH'] += 1

        # Multi-alt divergence — check raw dict (only populated when Layer 6 fires)
        weak_alt_count = 0
        if hasattr(crash_result, 'raw') and isinstance(crash_result.raw, dict):
            weak_alt_count = crash_result.raw.get('weak_alt_count', 0)
        if weak_alt_count >= 3:
            signals += 1
            direction_votes['BEARISH'] += 1

    except ImportError:
        log.warning("btc_crash_filter not available — skipping crash signals")
    except Exception as e:
        log.warning(f"Crash filter error: {e}")

    # ── Medium signals (5 min) — velocity + wave phase ──
    btc_wave = get_btc_wave_phase()
    if btc_wave == 'falling':
        signals += 1
        direction_votes['BEARISH'] += 1
    elif btc_wave in ('accelerating', 'bottoming'):
        signals += 1
        direction_votes['BULLISH'] += 1

    btc_vel = get_btc_velocity()
    if btc_vel is not None:
        if btc_vel < -SNIPER_BTC_VELOCITY_THRESHOLD:
            signals += 1
            direction_votes['BEARISH'] += 1
        elif btc_vel > SNIPER_BTC_VELOCITY_THRESHOLD:
            signals += 1
            direction_votes['BULLISH'] += 1

    # ── Slow signals (15 min - 4 hours) — momentum state ──
    cache_age = get_momentum_cache_age_minutes()
    if cache_age < 30:  # Only use if fresh
        mom_state = get_btc_momentum_state()
        if mom_state == 'bearish':
            signals += 1
            direction_votes['BEARISH'] += 1
        elif mom_state == 'bullish':
            signals += 1
            direction_votes['BULLISH'] += 1
    else:
        log.info(f"  momentum_cache stale ({cache_age:.0f}min) — skipping momentum signal")

    # Volatility regime change
    if volatility_regime_changed():
        signals += 1
        slope = get_btc_slope_15m()
        if slope is not None and slope < 0:
            direction_votes['BEARISH'] += 1
        else:
            direction_votes['BULLISH'] += 1

    # ── Decision ──
    if signals < SNIPER_SIGNALS_FOR_L1:
        return None

    bearish = direction_votes['BEARISH']
    bullish = direction_votes['BULLISH']

    if bearish == 0 and bullish == 0:
        return None

    if bearish > bullish:
        direction = 'BEARISH'
    elif bullish > bearish:
        direction = 'BULLISH'
    else:
        return None  # Tied — uncertain

    if signals >= SNIPER_SIGNALS_FOR_L3:
        level = 3
    elif signals >= SNIPER_SIGNALS_FOR_L2:
        level = 2
    else:
        level = 1

    return (level, direction)


# ═══════════════════════════════════════════════════════════════════════════
#  POSITION QUERIES
# ═══════════════════════════════════════════════════════════════════════════

def get_open_positions():
    """Get all open Hermes positions from PostgreSQL."""
    conn = None
    try:
        import psycopg2
        from _secrets import BRAIN_PASSWORD, BRAIN_HOST
        conn = psycopg2.connect(
            host=BRAIN_HOST, dbname="brain", user="postgres",
            password=BRAIN_PASSWORD, connect_timeout=10
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, direction, entry_price, current_price,
                   pnl_pct, open_time, signal
            FROM trades
            WHERE server = 'Hermes' AND status = 'open'
              AND entry_price > 0 AND current_price > 0
            ORDER BY open_time DESC
        """)
        rows = cur.fetchall()
        return [
            {"id": r[0], "token": r[1], "direction": r[2],
             "entry_price": float(r[3]), "current_price": float(r[4]),
             "pnl_pct": float(r[5]), "open_time": r[6], "signal": r[7] or ""}
            for r in rows
        ]
    except Exception as e:
        log.error(f"DB query error: {e}")
        return []
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════
#  CLOSE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def is_position_on_hl(token):
    """Check if token still has an open position on Hyperliquid."""
    try:
        from hyperliquid_exchange import get_exchange, MAIN_ACCOUNT_ADDRESS
        ex = get_exchange()
        addr = getattr(ex, 'account_address', None) or MAIN_ACCOUNT_ADDRESS
        state = ex.info.user_state(addr)
        for p in state.get('assetPositions', []) or []:
            item = p.get('position') or {}
            if item.get('coin') == token.upper() and abs(float(item.get('szi') or 0)) > 0:
                return True
        return False
    except Exception as e:
        log.warning(f"HL check failed for {token}: {e}")
        return False


def is_token_being_closed_by_guardian(token):
    """Check if guardian closing markers include this token."""
    try:
        markers_path = Path("/root/.hermes/data/guardian-closing-markers.json")
        data = json.loads(markers_path.read_text())
        markers = data.get('tokens', {}) if isinstance(data, dict) else data
        return token.upper() in {k.upper() for k in markers.keys()}
    except Exception:
        return False


def sniper_close_position(pos, reason, dry_run=False):
    """Close a position on HL then update DB.
    Returns True on success.
    """
    trade_id = pos['id']
    token = pos['token']
    direction = pos['direction']
    current_price = pos['current_price']
    pnl_pct = pos['pnl_pct']

    if dry_run:
        log.info(f"  [DRY RUN] Would close {token} {direction} @ {pnl_pct:+.2f}% — {reason}")
        return True

    # Check guardian marker
    if is_token_being_closed_by_guardian(token):
        log.info(f"  Guardian closing {token} — skipping")
        return False

    # Check HL
    if not is_position_on_hl(token):
        log.info(f"  {token} not on HL — already closed, skipping")
        return False

    # Close on HL
    hl_fill_price = None
    try:
        from hyperliquid_exchange import is_live_trading_enabled, close_position as hl_close
        if is_live_trading_enabled():
            result = hl_close(token.upper())
            if result.get("success"):
                log.info(f"  HL close OK: {token}")
                try:
                    statuses = result.get("result", {}).get("response", {}).get("data", {}).get("statuses", [])
                    for s in statuses:
                        avg_px = s.get("filled", {}).get("avgPx")
                        if avg_px:
                            hl_fill_price = float(avg_px)
                            break
                except Exception:
                    pass
            else:
                log.warning(f"  HL close failed for {token}: {result.get('error', result.get('message', 'unknown'))}")
                return False
    except Exception as e:
        log.error(f"  HL close error for {token}: {e}")
        return False

    # Update DB via brain.py
    exit_price = f"{hl_fill_price:.8f}" if hl_fill_price else f"{current_price:.8f}"
    import subprocess
    import sys as _sys
    BRAIN_CMD = "/root/.hermes/scripts/brain.py"
    cmd = [_sys.executable, BRAIN_CMD, "trade", "close", str(trade_id), exit_price,
           "--notes", f"sniper({pnl_pct:+.2f}%)",
           "--close-reason", reason,
           "--skip-hl"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            log.info(f"  Closed id={trade_id} {token} {direction} — {pnl_pct:+.2f}% — {reason}")
            return True
        else:
            log.warning(f"  DB close failed for {token}: {result.stderr[:200]}")
            return False
    except Exception as e:
        log.error(f"  DB close error for {token}: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════

def sniper_check(dry_run=False):
    """Main entry point. Run every 3 minutes.

    Detect shifts and close wrong-side positions.
    Right-side positions ride the trend.
    """
    if not SNIPER_ENABLED:
        return

    state = _load_state()

    # ── Cooldown check ──
    cooldown_until = state.get('cooldown_until', 0)
    if time.time() < cooldown_until:
        remaining = (cooldown_until - time.time()) / 60
        log.info(f"  Cooldown active — {remaining:.1f}min remaining")
        return

    # ── Max cycles check ──
    cycle_count = state.get('cycle_count', 0)
    if cycle_count >= SNIPER_MAX_CYCLES:
        log.info(f"  Max cycles ({SNIPER_MAX_CYCLES}) reached — entering cooldown")
        state['cooldown_until'] = time.time() + SNIPER_COOLDOWN
        state['cycle_count'] = 0
        _save_state(state)
        return

    # ── Detect shift ──
    result = detect_shift()
    if result is None:
        # Reset cycle count if no shift
        if cycle_count > 0:
            log.info(f"  Shift ended — resetting cycle count")
            state['cycle_count'] = 0
            state['closed_this_shift'] = []
            _save_state(state)
        return

    shift_level, shift_direction = result

    # ── Get open positions ──
    positions = get_open_positions()
    if not positions:
        log.info("  No open positions")
        return

    # ── Identify wrong-side positions ──
    if shift_direction == 'BEARISH':
        wrong_side = [p for p in positions if p['direction'] == 'LONG']
        right_side = [p for p in positions if p['direction'] == 'SHORT']
    else:  # BULLISH
        wrong_side = [p for p in positions if p['direction'] == 'SHORT']
        right_side = [p for p in positions if p['direction'] == 'LONG']

    if not wrong_side:
        log.info(f"  No wrong-side positions (all {shift_direction}-aligned)")
        return

    # ── Filter out already-closed-this-shift ──
    closed_ids = set(state.get('closed_this_shift', []))
    wrong_side = [p for p in wrong_side if p['id'] not in closed_ids]

    if not wrong_side:
        log.info(f"  All wrong-side positions already closed this shift")
        return

    # ── Categorize wrong-side positions ──
    trail_state = _load_trail_state()

    tier1 = [p for p in wrong_side
             if p['pnl_pct'] > 0
             and str(p['id']) not in trail_state]

    tier2 = sorted(
        [p for p in wrong_side
         if p['pnl_pct'] < -SNIPER_MIN_LOSS_THRESHOLD
         and p.get('open_time') is not None],
        key=lambda p: p['open_time'],
        reverse=True  # LIFO — most recent first
    )

    tier3 = [p for p in wrong_side
             if p['pnl_pct'] > 0
             and str(p['id']) in trail_state]

    # ── Select closes based on shift level ──
    closes = []

    if shift_level >= 1:
        closes.extend(tier1[:SNIPER_MAX_CLOSES_PER_CYCLE])

    if shift_level >= 2:
        remaining = SNIPER_MAX_CLOSES_PER_CYCLE - len(closes)
        closes.extend(tier2[:remaining])

    if shift_level >= 3:
        # Emergency — close all wrong-side (including trailing)
        closes = tier1 + tier2 + tier3

    # Deduplicate
    seen_ids = set()
    deduped = []
    for p in closes:
        if p['id'] not in seen_ids:
            seen_ids.add(p['id'])
            deduped.append(p)
    closes = deduped[:SNIPER_MAX_CLOSES_PER_CYCLE]

    if not closes:
        log.info(f"  No positions to close (shift L{shift_level} {shift_direction})")
        return

    # ── Execute ──
    log.info(f"  🔫 SNIPER L{shift_level} {shift_direction} — closing {len(closes)} wrong-side position(s)")

    closed_count = 0
    for pos in closes:
        # Write closing marker BEFORE close
        write_closing_marker(pos['token'])

        reason = f"SNIPER-L{shift_level}-{shift_direction}"
        try:
            success = sniper_close_position(pos, reason=reason, dry_run=dry_run)
            if success:
                closed_count += 1
                closed_ids.add(pos['id'])
        except Exception as e:
            log.error(f"  Failed to close {pos['token']}: {e}")
        finally:
            clear_closing_marker(pos['token'])

    # ── Update state ──
    state['last_shift_time'] = time.time()
    state['shift_level'] = shift_level
    state['shift_direction'] = shift_direction
    state['cycle_count'] = cycle_count + 1
    state['closed_this_shift'] = list(closed_ids)
    _save_state(state)

    # ── Log right-side positions (riding) ──
    for p in right_side:
        log.info(f"  📈 Riding {p['token']} {p['direction']} | "
                 f"PnL: {p['pnl_pct']:+.2f}% (aligned with {shift_direction})")

    # ── Cooldown after full cycle ──
    if cycle_count + 1 >= SNIPER_MAX_CYCLES:
        state['cooldown_until'] = time.time() + SNIPER_COOLDOWN
        state['cycle_count'] = 0
        _save_state(state)
        log.info(f"  Max cycles reached — entering {SNIPER_COOLDOWN/60:.0f}min cooldown")


def show_status():
    """Show current sniper state and data freshness."""
    state = _load_state()
    print("=== SNIPER STATUS ===")
    print(f"Enabled: {SNIPER_ENABLED}")
    print(f"State: {json.dumps(state, indent=2, default=str)}")
    print()

    # Data freshness
    cache_age = get_momentum_cache_age_minutes()
    print(f"Momentum cache age: {cache_age:.0f} min ({'FRESH' if cache_age < 30 else 'STALE'})")

    wave = get_btc_wave_phase()
    vel = get_btc_velocity()
    mom = get_btc_momentum_state()
    print(f"BTC wave_phase: {wave}")
    print(f"BTC velocity (30m): {vel}")
    print(f"BTC momentum_state: {mom}")
    print()

    # Trail state
    trail = _load_trail_state()
    print(f"PM_TRAIL active: {len(trail)} position(s)")
    for tid, info in trail.items():
        print(f"  id={tid}: peak_pnl={info.get('peak_pnl', '?')}%")

    # Closing markers
    try:
        with open(CLOSING_MARKERS_FILE) as f:
            markers = json.load(f)
        if markers:
            print(f"\nClosing markers: {markers}")
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    print()
    print("=== END STATUS ===")


# ═══════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    status_only = '--status' in sys.argv

    if status_only:
        show_status()
    elif dry_run:
        log.info("=== SNIPER DRY RUN ===")
        sniper_check(dry_run=True)
        log.info("=== END DRY RUN ===")
    else:
        log.info("=== SNIPER CHECK ===")
        sniper_check()
        log.info("=== END CHECK ===")
