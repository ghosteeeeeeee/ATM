#!/usr/bin/env python3
"""
speed_tracker.py — Token speed tracking for Hermes trading system.

Computes price velocity (5m, 15m), price acceleration (2nd derivative),
and momentum percentile for all tokens. Updated every pipeline run (~1 min).

Speed data is persisted to the `token_speeds` table in signals_hermes_runtime.db
and cached in-memory for fast access during the pipeline run.

Key concepts:
  - price_velocity_5m:  % change over last 5 minutes
  - price_velocity_15m: % change over last 15 minutes
  - price_acceleration: 2nd derivative — rate of change of velocity (momentum of momentum)
  - speed_percentile:   rank of this token's velocity vs universe (0-100)
  - is_stale:           True if velocity near zero for 15+ min (flat/uninteresting)
  - last_move_at:       timestamp of last significant price move (>0.2% in 5m)
"""

import sys, os, time, sqlite3, statistics
from typing import Dict, Optional, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_RUNTIME_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           os.pardir, 'data', 'signals_hermes_runtime.db')

# Thresholds for stale detection
_STALE_VELOCITY_THRESHOLD = 0.002  # <0.2% change over 5m = stale
_STALE_MINUTES = 15                # stale for 15+ min
_LAST_MOVE_THRESHOLD = 0.002       # >0.2% change = significant move

# ─── In-memory cache ─────────────────────────────────────────────────────────
# Updated every pipeline run, keyed by token uppercase
_token_speeds: Dict[str, Dict] = {}
_cache_updated_at: float = 0
_CACHE_TTL = 90  # seconds — force refresh after 90s

# ─── DB helpers ─────────────────────────────────────────────────────────────

def _get_conn():
    return sqlite3.connect(_RUNTIME_DB, timeout=10)


def _ensure_table():
    """Create token_speeds table if it doesn't exist."""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS token_speeds (
                token TEXT PRIMARY KEY,
                price_velocity_5m REAL DEFAULT 0,
                price_velocity_15m REAL DEFAULT 0,
                price_acceleration REAL DEFAULT 0,
                speed_percentile REAL DEFAULT 50,
                is_stale INTEGER DEFAULT 0,
                last_move_at TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()


# ─── Price history helpers ──────────────────────────────────────────────────

def _fetch_price_history_cached(token: str, lookback_minutes: int = 60) -> List[Tuple[int, float]]:
    """
    Fetch price history for a token from signal_schema's static DB.
    Returns list of (timestamp, price) sorted ASC.
    Falls back to empty list on error.
    """
    try:
        from signal_schema import get_price_history as _get_ph
        rows = _get_ph(token, lookback_minutes=lookback_minutes)
        return [(int(r[0]), float(r[1])) for r in rows] if rows else []
    except Exception:
        return []


def _get_current_price(token: str) -> Optional[float]:
    """Get the most recent price for a token."""
    try:
        from signal_schema import get_latest_price
        price = get_latest_price(token)
        return float(price) if price else None
    except Exception:
        return None


def _get_all_current_prices() -> Dict[str, float]:
    """Get all latest prices from signal_schema."""
    try:
        from signal_schema import get_all_latest_prices
        data = get_all_latest_prices()
        return {t.upper(): float(v['price']) for t, v in data.items() if v.get('price')}
    except Exception:
        return {}


# ─── Core speed computation ────────────────────────────────────────────────

def _compute_velocity(prices: List[float], minutes: int) -> float:
    """
    Compute % price change over the last `minutes`.
    Prices should be sorted oldest→newest.
    Returns 0 if not enough data.
    """
    if len(prices) < 2:
        return 0.0
    # Number of bars needed (assuming ~1 bar per minute)
    bars_needed = min(minutes, len(prices) - 1)
    if bars_needed < 1:
        return 0.0
    old_price = prices[-1 - bars_needed]
    new_price = prices[-1]
    if old_price <= 0:
        return 0.0
    return ((new_price - old_price) / old_price) * 100.0


def _compute_acceleration(velocity_5m: float, velocity_15m: float) -> float:
    """
    Compute price acceleration: 2nd derivative.
    acceleration ≈ velocity_5m - velocity_15m (how much velocity is increasing)
    Positive = gaining momentum, Negative = losing momentum.
    """
    # Acceleration = rate of change of velocity
    # Using difference between short-term and medium-term velocity as proxy
    return velocity_5m - velocity_15m


def _detect_stale(velocity_5m: float, minutes_stale: int) -> Tuple[bool, str]:
    """
    Determine if a token is stale (flat/uninteresting).
    Returns (is_stale, reason).
    """
    if abs(velocity_5m) < _STALE_VELOCITY_THRESHOLD and minutes_stale >= _STALE_MINUTES:
        return True, f"flat_5m_{minutes_stale}min"
    if abs(velocity_5m) < _STALE_VELOCITY_THRESHOLD / 2 and minutes_stale >= 5:
        return True, f"very_flat_{minutes_stale}min"
    return False, ""


def _compute_single_token_speed(token: str, prices: List[Tuple[int, float]],
                                 current_price: float) -> Dict:
    """
    Compute speed metrics for a single token.
    prices: list of (timestamp, price) sorted by timestamp ASC.
    """
    if len(prices) < 5 or current_price is None or current_price <= 0:
        return {
            'token': token,
            'price_velocity_5m': 0.0,
            'price_velocity_15m': 0.0,
            'price_acceleration': 0.0,
            'speed_percentile': 50.0,
            'is_stale': False,
            'last_move_at': None,
        }

    price_values = [p for _, p in prices]

    vel_5m = _compute_velocity(price_values, minutes=5)
    vel_15m = _compute_velocity(price_values, minutes=15)
    accel = _compute_acceleration(vel_5m, vel_15m)

    # Determine last significant move time
    last_move_at = None
    now = time.time()
    for ts, px in reversed(prices[-30:]):  # check last 30 bars
        if len(price_values) > 1:
            idx = prices.index((ts, px))
            if idx > 0:
                prev_px = price_values[idx - 1]
                if prev_px > 0 and abs((px - prev_px) / prev_px) >= _LAST_MOVE_THRESHOLD:
                    last_move_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
                    break

    if last_move_at is None:
        # Check if current price differs significantly from earliest in window
        if price_values[0] > 0:
            pct = abs((current_price - price_values[0]) / price_values[0]) * 100
            if pct >= _LAST_MOVE_THRESHOLD * 10:
                last_move_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(prices[0][0]))

    # Stale detection: how long since last meaningful price change
    stale = False
    stale_reason = ""
    if last_move_at is None:
        stale, stale_reason = _detect_stale(vel_5m, minutes_stale=15)
    else:
        try:
            from datetime import datetime
            last_move_dt = datetime.strptime(last_move_at, '%Y-%m-%d %H:%M:%S')
            last_move_ts = last_move_dt.timestamp()
            minutes_stale = int((now - last_move_ts) / 60)
            stale, stale_reason = _detect_stale(vel_5m, minutes_stale)
        except Exception:
            stale, stale_reason = False, ""

    return {
        'token': token,
        'price_velocity_5m': round(vel_5m, 4),
        'price_velocity_15m': round(vel_15m, 4),
        'price_acceleration': round(accel, 4),
        'speed_percentile': 50.0,  # temporarily 50, updated after universe calculation
        'is_stale': stale,
        'last_move_at': last_move_at,
        'stale_reason': stale_reason,
    }


# ─── SpeedTracker class ─────────────────────────────────────────────────────

class SpeedTracker:
    """
    Tracks price speed (velocity, acceleration, percentile) for all tokens.
    Updated every pipeline run, persists to SQLite.
    """

    def __init__(self):
        _ensure_table()
        self._speeds: Dict[str, Dict] = {}
        self._updated_at: float = 0
        self._load_from_cache_or_compute()

    def _load_from_cache_or_compute(self):
        """Load from in-memory cache if fresh, else compute all."""
        global _token_speeds, _cache_updated_at
        now = time.time()
        if _token_speeds and (now - _cache_updated_at) < _CACHE_TTL:
            self._speeds = _token_speeds
            self._updated_at = _cache_updated_at
            return
        self._compute_all_speeds()

    def _compute_all_speeds(self):
        """Compute speed for all tokens with available price data."""
        global _token_speeds, _cache_updated_at
        now = time.time()

        # Get all tokens with prices
        all_prices = _get_all_current_prices()
        if not all_prices:
            self._speeds = {}
            return

        tokens = list(all_prices.keys())

        # Compute speed for each token
        speeds = {}
        for token in tokens:
            prices = _fetch_price_history_cached(token, lookback_minutes=60)
            current = all_prices.get(token)
            if current is None:
                continue
            speed_data = _compute_single_token_speed(token, prices, current)
            speeds[token] = speed_data

        # Compute percentile rank across universe
        if speeds:
            # Use velocity_5m as the primary ranking metric
            velocities = [(t, s['price_velocity_5m']) for t, s in speeds.items()]
            velocities.sort(key=lambda x: abs(x[1]), reverse=True)  # sort by absolute velocity

            n = len(velocities)
            for rank, (token, _) in enumerate(velocities):
                # Percentile: top performer = 100, bottom = 0
                percentile = round((1 - rank / n) * 100, 1)
                speeds[token]['speed_percentile'] = percentile

        self._speeds = speeds
        self._updated_at = now
        _token_speeds = speeds
        _cache_updated_at = now

        # Persist to DB
        self._persist_to_db()

    def _persist_to_db(self):
        """Write all speed data to SQLite token_speeds table."""
        if not self._speeds:
            return
        conn = _get_conn()
        now_str = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            for token, data in self._speeds.items():
                conn.execute("""
                    INSERT INTO token_speeds
                      (token, price_velocity_5m, price_velocity_15m, price_acceleration,
                       speed_percentile, is_stale, last_move_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(token) DO UPDATE SET
                      price_velocity_5m  = excluded.price_velocity_5m,
                      price_velocity_15m = excluded.price_velocity_15m,
                      price_acceleration = excluded.price_acceleration,
                      speed_percentile   = excluded.speed_percentile,
                      is_stale           = excluded.is_stale,
                      last_move_at       = excluded.last_move_at,
                      updated_at          = excluded.updated_at
                """, (token,
                      data['price_velocity_5m'],
                      data['price_velocity_15m'],
                      data['price_acceleration'],
                      data['speed_percentile'],
                      1 if data['is_stale'] else 0,
                      data.get('last_move_at'),
                      now_str))
            conn.commit()
        except Exception as e:
            print(f"[speed_tracker] DB persist error: {e}")
        finally:
            conn.close()

    # ─── Public API ─────────────────────────────────────────────────────────

    def get_all_speeds(self) -> Dict[str, Dict]:
        """Return dict of all token speed data."""
        return self._speeds.copy()

    def get_token_speed(self, token: str) -> Optional[Dict]:
        """Return speed data for a single token, or None."""
        return self._speeds.get(token.upper())

    def get_fastest_tokens(self, n: int = 10) -> List[Dict]:
        """Return top N fastest-moving tokens (by speed_percentile)."""
        sorted_tokens = sorted(
            self._speeds.items(),
            key=lambda x: x[1].get('speed_percentile', 0),
            reverse=True
        )
        return [data for _, data in sorted_tokens[:n]]

    def get_slowest_tokens(self, n: int = 10) -> List[Dict]:
        """Return top N slowest/most stale tokens."""
        sorted_tokens = sorted(
            self._speeds.items(),
            key=lambda x: x[1].get('speed_percentile', 100)
        )
        return [data for _, data in sorted_tokens[:n]]

    def is_token_stale(self, token: str) -> Tuple[bool, str]:
        """Return (is_stale, stale_reason) for a token."""
        data = self._speeds.get(token.upper())
        if data is None:
            return True, "unknown_token"
        return data.get('is_stale', False), data.get('stale_reason', '')

    def get_velocity_5m(self, token: str) -> float:
        """Return 5-minute price velocity for a token."""
        data = self._speeds.get(token.upper())
        return data['price_velocity_5m'] if data else 0.0

    def get_speed_percentile(self, token: str) -> float:
        """Return speed percentile (0-100) for a token."""
        data = self._speeds.get(token.upper())
        return data['speed_percentile'] if data else 50.0


# ─── Module-level convenience functions ────────────────────────────────────

# Lazy-initialized global tracker instance
_tracker: Optional[SpeedTracker] = None

def _get_tracker() -> SpeedTracker:
    global _tracker
    if _tracker is None:
        _tracker = SpeedTracker()
    return _tracker


def get_all_speeds() -> Dict[str, Dict]:
    """Get all token speeds (convenience function)."""
    return _get_tracker().get_all_speeds()


def get_token_speed(token: str) -> Optional[Dict]:
    """Get speed data for a single token."""
    return _get_tracker().get_token_speed(token)


def get_fastest_tokens(n: int = 10) -> List[Dict]:
    """Get top N fastest tokens."""
    return _get_tracker().get_fastest_tokens(n=n)


def is_token_stale(token: str) -> Tuple[bool, str]:
    """Check if token is stale."""
    return _get_tracker().is_token_stale(token)


def get_speed_percentile(token: str) -> float:
    """Get speed percentile for a token (0-100)."""
    return _get_tracker().get_speed_percentile(token)


if __name__ == '__main__':
    # Self-test: compute and print top 10 fastest tokens
    tracker = SpeedTracker()
    fastest = tracker.get_fastest_tokens(10)
    print("=== Top 10 Fastest Tokens ===")
    for s in fastest:
        print(f"  {s['token']:10s} vel5m={s['price_velocity_5m']:+.2f}% "
              f"vel15m={s['price_velocity_15m']:+.2f}% "
              f"accel={s['price_acceleration']:+.3f} "
              f"pctl={s['speed_percentile']:.0f} "
              f"stale={s['is_stale']}")
