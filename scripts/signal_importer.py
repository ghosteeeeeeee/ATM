"""
Import signals from various sources into unified signals DB
"""
import sys, json, time
sys.path.insert(0, '/root/.hermes/scripts')
sys.path.insert(1, '/root/.openclaw/workspace/scripts')
from signal_schema import add_signal, get_confluence_signals as schema_get_confluence, set_cooldown
import sqlite3

DB_PATH = '/root/.openclaw/workspace/data/signals.db'
LOG_FILE = '/root/.hermes/logs/signal-importer.log'

# ============================================
# Momentum Tracker Persistence
# ============================================
MOMENTUM_FILE = '/root/.openclaw/workspace/data/momentum_tracker.json'

# Track momentum state: tokens that crossed threshold but haven't entered yet
_momentum_tracker = {}

def _load_momentum():
    """Load momentum tracker from JSON file"""
    global _momentum_tracker
    try:
        with open(MOMENTUM_FILE) as f:
            _momentum_tracker = json.load(f)
    except:
        _momentum_tracker = {}
    return _momentum_tracker

def _save_momentum(data):
    """Save momentum tracker to JSON file"""
    try:
        with open(MOMENTUM_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

# Load momentum state on module import
_load_momentum()

# ============================================
# Z-Score Tier Logic
# ============================================
def get_zscore_tier(z):
    """Determine z-score tier based on momentum framework"""
    # Positive z-scores (LONG direction)
    if z >= 3.5:
        return "exhaustion_short_only"
    elif z >= 3.0:
        return "exhaustion"
    elif z >= 2.5:
        return "accelerating_long"
    elif z >= 2.0:
        return "momentum_tracking"
    elif z >= 1.5:
        return "decelerating_from_long"
    # Negative z-scores (SHORT direction)
    elif z <= -3.5:
        return "exhaustion_long_only"
    elif z <= -3.0:
        return "exhaustion_long"
    elif z <= -2.5:
        return "accelerating_short"
    elif z <= -2.0:
        return "momentum_tracking_short"
    elif z > -2.0 and z <= -1.5:
        return "decelerating_from_short"
    else:
        return "neutral"

# ============================================
# Momentum Tracking (Persisted)
# ============================================
def track_momentum(token, z_score, direction):
    """Track momentum state for delayed entry candidates"""
    key = token.upper()
    
    # Load fresh from file
    _load_momentum()
    
    if direction == 'LONG' and z_score > 2.0:
        if key not in _momentum_tracker or _momentum_tracker[key].get('direction') != 'LONG':
            _momentum_tracker[key] = {
                'direction': 'LONG',
                'peak_z': z_score,
                'crossed_at': time.time(),
                'z_tier': get_zscore_tier(z_score)
            }
        else:
            _momentum_tracker[key]['peak_z'] = max(_momentum_tracker[key]['peak_z'], z_score)
            _momentum_tracker[key]['z_tier'] = get_zscore_tier(z_score)
    
    elif direction == 'SHORT' and z_score < -2.0:
        if key not in _momentum_tracker or _momentum_tracker[key].get('direction') != 'SHORT':
            _momentum_tracker[key] = {
                'direction': 'SHORT',
                'peak_z': z_score,
                'crossed_at': time.time(),
                'z_tier': get_zscore_tier(z_score)
            }
        else:
            _momentum_tracker[key]['peak_z'] = min(_momentum_tracker[key]['peak_z'], z_score)
            _momentum_tracker[key]['z_tier'] = get_zscore_tier(z_score)
    
    # Check for deceleration
    if key in _momentum_tracker:
        tracker = _momentum_tracker[key]
        
        if tracker['direction'] == 'LONG' and z_score < 1.5 and tracker.get('peak_z', 0) > 2.0:
            result = {
                'action': 'decelerating_long',
                'tier': 'decelerating_short_opportunity',
                'peak_z': tracker['peak_z'],
                'current_z': z_score
            }
            _save_momentum(_momentum_tracker)
            return result
        
        if tracker['direction'] == 'SHORT' and z_score > -1.5 and tracker.get('peak_z', 0) < -2.0:
            result = {
                'action': 'decelerating_short',
                'tier': 'decelerating_long_opportunity',
                'peak_z': tracker['peak_z'],
                'current_z': z_score
            }
            _save_momentum(_momentum_tracker)
            return result
    
    # Save updated state
    _save_momentum(_momentum_tracker)
    return None

def get_momentum_state(token):
    """Get current momentum state for a token"""
    # Load fresh from file
    _load_momentum()
    return _momentum_tracker.get(token.upper())

# ============================================
# Signal Importers
# ============================================
def import_zscore_signal(token, z_score, price):
    """Import z-score signal with momentum tier tracking"""
    z_tier = get_zscore_tier(z_score)
    
    direction = 'SHORT' if z_score < 0 else 'LONG'
    momentum_info = track_momentum(token, z_score, direction)
    
    if z_score < -2.5 or z_score > 2.5:
        confidence = min(90, 70 + abs(z_score) * 5)
    elif z_score < -2.0 or z_score > 2.0:
        confidence = min(80, 60 + abs(z_score) * 4)
    else:
        confidence = 50
    
    kwargs = {
        'z_score': z_score,
        'z_score_tier': z_tier,
        'peak_z_score': abs(z_score),
        'momentum_state': momentum_info['tier'] if momentum_info else z_tier
    }
    
    return add_signal(
        token=token.upper(),
        direction=direction,
        signal_type='zscore',
        source='zscore-v9',
        confidence=confidence,
        value=z_score,
        price=price,
        **kwargs
    )

def import_fear_signal(fear_index, price):
    """Import fear & greed signal."""
    if fear_index <= 25:
        return add_signal(
            token='BTC',
            direction='LONG',
            signal_type='fear',
            source='fear-greed',
            confidence=85 if fear_index <= 20 else 70,
            value=fear_index,
            price=price,
            timeframe='daily'
        )
    return None

def import_rsi_signal(token, rsi, price, timeframe='1h'):
    """Import RSI signal."""
    if rsi < 30:
        return add_signal(
            token=token.upper(),
            direction='LONG',
            signal_type='rsi',
            source='rsi-oversold',
            confidence=min(90, 70 + (30 - rsi) * 2),
            value=rsi,
            price=price,
            rsi_14=rsi,
            timeframe=timeframe
        )
    elif rsi > 70:
        return add_signal(
            token=token.upper(),
            direction='SHORT',
            signal_type='rsi',
            source='rsi-overbought',
            confidence=min(90, 70 + (rsi - 70) * 2),
            value=rsi,
            price=price,
            rsi_14=rsi,
            timeframe=timeframe
        )
    return None

# ============================================
# Confluence - Use signal_schema version
# ============================================
def calculate_confluence():
    """
    DEPRECATED: Use signal_schema.get_confluence_signals() instead.
    This function kept for backward compatibility.
    """
    return schema_get_confluence(hours=24)

def get_confluence_signals(hours=24):
    """Get confluence signals from signal_schema"""
    return schema_get_confluence(hours=hours)

# ============================================
# Logging
# ============================================
def log(msg):
    """Log to file"""
    print(msg)
    try:
        import os
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(f"{msg}\n")
    except:
        pass

# ============================================
# Main
# ============================================
if __name__ == '__main__':
    # Test confluence calculation
    log("=== Signal Importer: Loading confluence ===")
    confluence = get_confluence_signals(hours=24)
    for c in confluence:
        log(f"{c['token']} {c['direction']}: {c['count']} signals, {c['final_confidence']:.1f}% confidence")
        log(f"  Signals: {c.get('signal_types', [])}")
    log(f"=== Done: {len(confluence)} confluence signals ===")
