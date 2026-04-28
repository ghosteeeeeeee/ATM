#!/usr/bin/env python3
"""
counter_flip_signal.py — Counter-flip signal for open positions.

Fires when the market reverses against an open position — all TFs flip
against us, MACD turns, or cascade entry fires in the opposite direction.

This signal enters the normal signal pipeline → signal_compactor → hot-set.
If it survives compaction and the original direction trade was in the hot-set,
the opposing counter-flip signal penalizes it via the existing opp_penalty logic.

Architecture (independent of cascade_flip engine in position_manager.py):
  open positions (PostgreSQL) + HL candles → reversal detection
  → signal_schema.add_signal() → signals_hermes_runtime.db
  → signal_compactor → hotset.json → guardian → HL

Three detection paths:

  1. MTF ALIGNMENT FLIP (conf 95):
     All TFs (4H, 1H, 15m) flip opposite to our position direction.
     LONG open + all bearish → counter-flip SHORT
     SHORT open + all bullish → counter-flip LONG

  2. CASCADE DIRECTION FLIP (conf 90):
     Uses cascade_entry_signal() from macd_rules.py.
     Cascade is ACTIVE and direction opposes our position.

  3. MACD RULES ENGINE FLIP (conf 85):
     Uses macd_rules.get_macd_exit_signal() — MACD histogram
     has turned against our position with enough conviction.

This script does NOT:
  - Close positions
  - Execute trades
  - Write to HL
  - Set cooldowns

It only writes a signal to the DB via add_signal(), which then flows through
the normal compaction pipeline like every other signal.

Architecture:
  price_history + HL candles → cascade logic
  → signal_schema.add_signal() → signals_hermes_runtime.db
  → signal_compactor → hotset.json → guardian → HL
"""

import sys, os, sqlite3, time
from datetime import datetime, timezone
from typing import Optional, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from signal_schema import add_signal
from macd_rules import cascade_entry_signal, get_macd_exit_signal
from macd_rules import compute_mtf_macd_alignment, Regime

# ── Paths ──────────────────────────────────────────────────────────────────────
_RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'
_PRICE_DB   = '/root/.hermes/data/signals_hermes.db'

# ── Signal constants ───────────────────────────────────────────────────────────
SIGNAL_TYPE_LONG  = 'counter_flip_long'   # counter to SHORT position
SIGNAL_TYPE_SHORT = 'counter_flip_short'  # counter to LONG position
SOURCE_LONG       = 'counter-flip+'       # appears in hot-set source field
SOURCE_SHORT      = 'counter-flip-'


# ═══════════════════════════════════════════════════════════════════════════════
# Detection path 1: MTF MACD alignment flip
# ═══════════════════════════════════════════════════════════════════════════════

def _check_mtf_alignment_flip(token: str, position_dir: str) -> Optional[Dict]:
    """
    MTF alignment flip: all TFs (4H, 1H, 15m) have flipped against position_dir.
    
    Returns {direction, conf, source, reason} if flip detected, else None.
    Conf = 95 (ultra-confirmed).
    """
    try:
        mtf = compute_mtf_macd_alignment(token)
        if mtf is None:
            return None
        
        tf_states = mtf.get('tf_states', {})
        s15 = tf_states.get('15m')
        s1h = tf_states.get('1h')
        s4h = tf_states.get('4h')
        
        if not all([s15, s1h, s4h]):
            return None
        
        if position_dir == 'LONG':
            # All bearish = counter to LONG
            if not s15.macd_above_signal and not s15.histogram_positive \
               and not s1h.macd_above_signal and not s1h.histogram_positive \
               and not s4h.macd_above_signal and not s4h.histogram_positive:
                return {
                    'direction': 'SHORT',
                    'conf': 95.0,
                    'source': 'mtf_macd_alignment',
                    'reason': 'all_tfs_reversed',
                }
        else:  # SHORT
            if s15.macd_above_signal and s15.histogram_positive \
               and s1h.macd_above_signal and s1h.histogram_positive \
               and s4h.macd_above_signal and s4h.histogram_positive:
                return {
                    'direction': 'LONG',
                    'conf': 95.0,
                    'source': 'mtf_macd_alignment',
                    'reason': 'all_tfs_reversed',
                }
        return None
    except Exception as e:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Detection path 2: Cascade direction flip
# ═══════════════════════════════════════════════════════════════════════════════

def _check_cascade_direction_flip(token: str, position_dir: str) -> Optional[Dict]:
    """
    Cascade direction flip: cascade_entry_signal() says cascade is ACTIVE
    and its direction opposes our position.
    
    Returns {direction, conf, source, reason} if flip detected, else None.
    Conf = 90.
    """
    try:
        cascade = cascade_entry_signal(token)
        if not cascade.get('cascade_active'):
            return None
        
        cascade_dir = cascade.get('cascade_direction')
        if cascade_dir is None:
            return None
        
        if cascade_dir == position_dir:
            return None  # Cascade agrees with our position, not opposing
        
        return {
            'direction': cascade_dir,
            'conf': 90.0,
            'source': 'cascade_direction',
            'reason': f'cascade_{cascade_dir.lower()}_confirmed_blocking_{position_dir}',
        }
    except Exception as e:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Detection path 3: MACD rules engine flip
# ═══════════════════════════════════════════════════════════════════════════════

def _check_macd_rules_flip(token: str, position_dir: str) -> Optional[Dict]:
    """
    MACD rules engine flip: macd histogram has turned against our position.
    
    Returns {direction, conf, source, reason} if flip detected, else None.
    Conf = 85.
    """
    try:
        macd_result = get_macd_exit_signal(token, position_dir)
        if macd_result is None:
            return None
        
        if not macd_result.get('should_flip'):
            return None
        
        reasons = macd_result.get('reasons') or []
        primary_reason = reasons[0] if reasons else 'macd_reversal'
        
        opposite_dir = 'SHORT' if position_dir == 'LONG' else 'LONG'
        
        return {
            'direction': opposite_dir,
            'conf': 85.0,
            'source': 'macd_rules_engine',
            'reason': primary_reason[:80],
        }
    except Exception as e:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Open position reader
# ═══════════════════════════════════════════════════════════════════════════════

def _get_open_positions() -> Dict[str, str]:
    """Read open positions from PostgreSQL brain DB. {TOKEN: direction}."""
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("SELECT token, direction FROM trades WHERE status = 'open'")
        positions = {row[0].upper(): row[1].upper() for row in cur.fetchall()}
        conn.close()
        return positions
    except Exception as e:
        print(f"  [counter-flip] Failed to read open positions: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════════════════════════

def scan_counter_flip_signals(prices_dict: dict = None) -> int:
    """
    Called by signal_gen.run() every pipeline run.
    
    For each open position, run three cascade-flip detection paths.
    If any path fires, write a counter_flip signal to the DB.
    
    The signal flows through compaction normally. If the original direction
    trade is in the hot-set, the counter_flip signal penalizes it via the
    existing opp_penalty logic in signal_compactor.
    
    Returns: number of counter_flip signals written.
    """
    open_pos = _get_open_positions()
    if not open_pos:
        return 0
    
    written = 0
    
    for token, pos_dir in open_pos.items():
        flip_result = None
        
        # Try each detection path in order of strength
        flip_result = _check_mtf_alignment_flip(token, pos_dir)
        if flip_result is None:
            flip_result = _check_cascade_direction_flip(token, pos_dir)
        if flip_result is None:
            flip_result = _check_macd_rules_flip(token, pos_dir)
        
        if flip_result is None:
            continue
        
        counter_dir = flip_result['direction']
        conf = flip_result['conf']
        source = flip_result['source']
        reason = flip_result['reason']
        
        sig_type = SIGNAL_TYPE_LONG if counter_dir == 'LONG' else SIGNAL_TYPE_SHORT
        sig_source = SOURCE_LONG if counter_dir == 'LONG' else SOURCE_SHORT
        
        # Get current price for the signal
        price = None
        if prices_dict:
            price = prices_dict.get(token, {}).get('price')
        
        result = add_signal(
            token=token,
            direction=counter_dir,
            signal_type=sig_type,
            source=sig_source,
            confidence=conf,
            price=price,
            exchange='hyperliquid',
            timeframe='1h',
            momentum_state=f'counter_flip:{reason}',
        )
        
        if result is not None:
            print(f"  [counter-flip] 🚫 {token} {counter_dir} conf={conf:.0f}% "
                  f"(counter to {pos_dir}, src={source}, reason={reason})")
            written += 1
        else:
            print(f"  [counter-flip] {token} write returned None (blocked by add_signal)")
    
    if written > 0:
        print(f"  [counter-flip] Wrote {written} counter_flip signals to DB")
    
    return written


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print(f"[counter-flip] CASCADE_FLIP_ENABLED={CASCADE_FLIP_ENABLED}")
    if not CASCADE_FLIP_ENABLED:
        print("[counter-flip] Exiting: CASCADE_FLIP_ENABLED is False")
    else:
        written = scan_counter_flip_signals()
        print(f"[counter-flip] Done. {written} signals written.")
