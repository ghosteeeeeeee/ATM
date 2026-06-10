"""
speed_tracker.py — Token speed, velocity, acceleration, and momentum percentile.

Tracks how fast each token is moving and identifies:
- Fast movers (high velocity, enter these)
- Stale tokens (flat for 15+ min, exit or skip)
- Acceleration vs deceleration (momentum of momentum)

Uses LOCAL price cache (signals_hermes.db latest_prices + candles_5m).
No external API calls — fast, consistent with signal_gen token universe.
Runs every ~1 min as part of the pipeline.
"""

import json
import os
import sqlite3
import time
from datetime import datetime, timezone

from paths import *
# ── Paths ────────────────────────────────────────────────────────────────────
HERMES_DATA = "/root/.hermes/data"
SPEED_CACHE = os.path.join(HERMES_DATA, "speed_cache.json")

# ── Thresholds ─────────────────────────────────────────────────────────────────
# Sourced from hermes_constants.py — adjust there to propagate to all consumers.
from hermes_constants import (
    SPEED_MIN_THRESHOLD, SPEED_BOOST_THRESHOLD, SPEED_BOOST_FACTOR,
    SPEED_HOTSET_THRESHOLD, SPEED_HOTSET_BONUS,
    VEL_5M_WINDOW, VEL_15M_WINDOW, VEL_STALE_THRESHOLD_PCT, OVEREXTENDED_THRESHOLD,
    STALE_WINNER_TIMEOUT_MINUTES, STALE_LOSER_TIMEOUT_MINUTES,
)


def _now_ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── SpeedTracker ──────────────────────────────────────────────────────────────

class SpeedTracker:
    """
    Tracks token speed metrics in-memory.
    
    Usage:
        st = SpeedTracker()
        st.update()                           # fetch prices + compute speeds
        speeds = st.get_all_speeds()          # dict of token → speed data
        fast = st.get_fastest_tokens(10)      # top 10 movers
        token_speed = st.get_token_speed("BTC")  # single token
    """

    def __init__(self):
        self._speeds: dict = {}        # token → speed dict (in-memory, current run)
        self._percentiles: list = []    # sorted list of all velocities (for percentile rank)
        self._updated_at: str = _now_ts()

    # ── Price fetchers ─────────────────────────────────────────────────────────

    def _get_current_prices_from_db(self) -> dict:
        """Fetch latest prices from local signals_hermes.db (consistent w/ signal_gen)."""
        prices = {}
        if not os.path.exists(STATIC_DB):
            return prices
        try:
            conn = sqlite3.connect(STATIC_DB, timeout=5)
            cur = conn.cursor()
            cur.execute("SELECT token, price FROM latest_prices")
            for token, price in cur.fetchall():
                prices[token] = price
            conn.close()
        except Exception as e:
            print(f"[SpeedTracker] Failed to read latest_prices: {e}")
        return prices

    def _get_candle_history(self, token: str, num_candles: int = 20) -> list:
        """
        Fetch last N 5m candle closes for a token from candles.db.
        Returns list of {price, ts} newest-first (matches old hist format).
        """
        if not os.path.exists(CANDLES_DB):
            return []
        try:
            conn = sqlite3.connect(CANDLES_DB, timeout=5)
            cur = conn.cursor()
            cur.execute("""
                SELECT ts, close FROM candles_5m
                WHERE token = ?
                ORDER BY ts DESC
                LIMIT ?
            """, [token, num_candles])
            rows = cur.fetchall()
            conn.close()
            # Convert to old hist format: {price, ts}, newest-first
            return [{"price": close, "ts": ts} for ts, close in rows]
        except Exception as e:
            return []

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self) -> dict:
        """
        Fetch current prices + recent 5m candle history from local DB,
        compute all speed metrics. Call once per pipeline run.
        """
        t0 = time.time()

        # ── Step 1: Get current prices from local DB ───────────────────────────
        mids = self._get_current_prices_from_db()
        if not mids:
            print("[SpeedTracker] No prices found in local DB — check pipeline order")
            return {}

        # ── Step 2: Fetch candle history from candles.db for each token ────────
        # Build token → hist dict (newest-first, same format as old rolling history)
        history = {}
        for token in mids:
            hist = self._get_candle_history(token, num_candles=20)
            if hist:
                history[token] = hist

        now = time.time()
        now_ts = _now_ts()

        # ── Step 3: Compute speed for each token ───────────────────────────────
        self._speeds = {}
        all_velocities_5m = []

        for token, hist in history.items():
            if len(hist) < 2:
                continue

            speed = self._compute_speed(token, hist, now)
            self._speeds[token] = speed
            if speed["price_velocity_5m"] is not None:
                all_velocities_5m.append(abs(speed["price_velocity_5m"]))

        # ── Step 4: Compute percentile rank ────────────────────────────────────
        if all_velocities_5m:
            all_velocities_5m.sort()
            n = len(all_velocities_5m)
            for token, speed in self._speeds.items():
                if speed["price_velocity_5m"] is None:
                    speed["speed_percentile"] = 50
                    continue
                v = abs(speed["price_velocity_5m"])
                rank = next((i for i, x in enumerate(all_velocities_5m) if x >= v), n - 1)
                speed["speed_percentile"] = round(rank / (n - 1) * 100, 1) if n > 1 else 50

                # ── is_stale: flat on BOTH 5m and 15m windows ─────────────
                vel_5m  = speed["price_velocity_5m"]
                vel_15m = speed["price_velocity_15m"]
                speed["is_stale"] = (
                    vel_5m is not None
                    and abs(vel_5m) < VEL_STALE_THRESHOLD_PCT
                    and vel_15m is not None
                    and abs(vel_15m) < VEL_STALE_THRESHOLD_PCT
                )

                # ── is_overextended ──────────────────────────────────────────
                speed["is_overextended"] = (
                    not speed["is_stale"]
                    and vel_5m is not None
                    and abs(vel_5m) > OVEREXTENDED_THRESHOLD
                )

        # ── Step 5: Wave phase classification ─────────────────────────────────
        for token, speed in self._speeds.items():
            vel  = speed["price_velocity_5m"]
            accel = speed["price_acceleration"]
            if vel is not None and accel is not None:
                if vel > 0 and accel > 0:
                    wave = "accelerating"
                elif vel > 0 and accel < 0:
                    wave = "decelerating"
                elif vel < 0 and accel > 0:
                    wave = "bottoming"
                elif vel < 0 and accel < 0:
                    wave = "falling"
                else:
                    wave = "neutral"
            else:
                wave = "neutral"
            speed["wave_phase"] = wave

            # ── momentum_score ──────────────────────────────────────────────
            vel_comp = min(abs(vel or 0) / 3.0, 1.0) * 60
            accel_comp = (accel or 0) * 5
            speed["momentum_score"] = round(
                speed.get("speed_percentile", 50) * 0.4
                + vel_comp * 0.4
                + min(max(accel_comp, -20), 20) * 0.2,
                1
            )

            # ── last_move_at: when was last significant move (>0.3% in 1 min)
            # Only same-direction moves reset the stale timer
            speed["last_move_at"], speed["last_move_dir"] = self._last_move_time(token, hist, now)

        # ── Step 6: Persist to DB ──────────────────────────────────────────────
        self._persist_to_db()

        self._updated_at = now_ts
        elapsed = time.time() - t0
        print(f"[SpeedTracker] Updated {len(self._speeds)} tokens in {elapsed:.3f}s (local DB)")
        return self._speeds

    def get_all_speeds(self) -> dict:
        """Returns full dict of token → speed data (from last update)."""
        return self._speeds

    def get_token_speed(self, token: str) -> dict:
        """Returns speed data for a single token, or a default empty dict."""
        return self._speeds.get(token.upper(), self._default_speed())

    def get_fastest_tokens(self, n: int = 10) -> list:
        """Returns top N tokens by speed_percentile."""
        sorted_tokens = sorted(
            self._speeds.items(),
            key=lambda x: x[1].get("speed_percentile", 0),
            reverse=True
        )
        return [{"token": t, **s} for t, s in sorted_tokens[:n]]

    def get_updated_at(self) -> str:
        return self._updated_at

    # ── Internal ───────────────────────────────────────────────────────────────

    def _compute_speed(self, token: str, hist: list, now: float) -> dict:
        """
        Compute velocity and acceleration for a token from its price history.

        Automatically detects data interval (1-min vs hourly) and computes
        5m/15m velocity from the appropriate data points.
        """

        def _price_at_idx(idx: int):
            """Get price at historical index from end (0 = most recent)."""
            if idx >= len(hist):
                return None
            return hist[-(idx + 1)]["price"]

        def _ts_at_idx(idx: int):
            if idx >= len(hist):
                return None
            return hist[-(idx + 1)]["ts"]

        # ── Detect data interval ───────────────────────────────────────────
        # Compute avg seconds between consecutive data points
        avg_interval = 60  # default: 1-minute data
        if len(hist) >= 2:
            ts0 = hist[-1]["ts"]
            ts1 = hist[-2]["ts"]
            interval = ts0 - ts1
            if interval > 0:
                avg_interval = interval

        # For hourly data (avg_interval ~= 3600):
        #   5m  window → 1 candle
        #   15m window → 3 candles
        # For 1-min data (avg_interval ≈ 60):
        #   5m  window → VEL_5M_WINDOW  (default 5)
        #   15m window → VEL_15M_WINDOW (default 15)
        if avg_interval >= 1800:  # hourly or higher interval
            win_5m, win_15m = 1, 3
        else:  # 1-min data
            win_5m  = VEL_5M_WINDOW   # 5
            win_15m = VEL_15M_WINDOW  # 15

        # ── Windowed average velocity ─────────────────────────────────────
        # Replaces single-point (p0 - p5)/p5 which is noise-sensitive to one ref candle.
        # Now: mean of last N candle returns — smooth, noise-immune.
        def _avg_vel(window: int) -> float | None:
            """Mean % change per candle over the last `window` candles."""
            if len(hist) < window + 1:
                return None
            total = 0.0
            for i in range(1, window + 1):
                p_cur  = hist[-i]["price"]
                p_prev = hist[-(i + 1)]["price"]
                if p_prev <= 0:
                    return None
                total += (p_cur - p_prev) / p_prev * 100
            return round(total / window, 4)

        vel_5m  = _avg_vel(win_5m)
        vel_15m = _avg_vel(win_15m)

        # ── Acceleration: rate of change of velocity ─────────────────────
        # accel = (avg_vel_5m - avg_vel_15m) / time_span
        # Positive → velocity increasing (momentum building)
        # Negative → velocity decreasing (momentum fading)
        span = win_15m - win_5m
        accel = None
        if vel_5m is not None and vel_15m is not None and span > 0:
            accel = round((vel_5m - vel_15m) / span, 4)

        return {
            "price_velocity_5m": vel_5m,
            "price_velocity_15m": vel_15m,
            "price_acceleration": accel,
            "momentum_score": 50,
            "is_stale": False,
            "last_move_at": None,
            "last_move_dir": None,
        }

    def _last_move_time(self, token: str, hist: list, now: float) -> tuple:
        """
        Find timestamp and direction of last significant price move (>0.3% in 1 min).

        Returns (timestamp_iso, direction) where direction is 'up', 'down', or None.
        Only same-direction moves reset the stale timer — oscillating moves don't.
        """
        MOVE_THRESHOLD_PCT = 0.3
        if len(hist) < 2:
            return (None, None)
        # Scan backwards from most recent
        for i in range(len(hist) - 1):
            p_now = hist[-(i + 1)]["price"]
            p_prev = hist[-(i + 2)]["price"]
            if p_prev <= 0:
                continue
            change = (p_now - p_prev) / p_prev * 100
            if abs(change) > MOVE_THRESHOLD_PCT:
                ts = hist[-(i + 1)]["ts"]
                direction = 'up' if change > 0 else 'down'
                return (
                    datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds"),
                    direction
                )
        # No significant move found — use oldest point
        if hist:
            ts = hist[0]["ts"]
            return (
                datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds"),
                None
            )
        return (None, None)

    def _persist_to_db(self) -> None:
        """Persist current speeds to SQLite (called once per update cycle)."""
        db_path = RUNTIME_DB
        if not os.path.exists(db_path):
            return
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            c = conn.cursor()
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            for token, s in self._speeds.items():
                c.execute("""
                    INSERT INTO token_speeds
                        (token, price_velocity_5m, price_velocity_15m, price_acceleration,
                         speed_percentile, is_stale, wave_phase, is_overextended,
                         momentum_score, last_move_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(token) DO UPDATE SET
                        price_velocity_5m = excluded.price_velocity_5m,
                        price_velocity_15m = excluded.price_velocity_15m,
                        price_acceleration = excluded.price_acceleration,
                        speed_percentile = excluded.speed_percentile,
                        is_stale = excluded.is_stale,
                        wave_phase = excluded.wave_phase,
                        is_overextended = excluded.is_overextended,
                        momentum_score = excluded.momentum_score,
                        last_move_at = excluded.last_move_at,
                        updated_at = excluded.updated_at
                """, (
                    token,
                    s.get("price_velocity_5m") or 0,
                    s.get("price_velocity_15m") or 0,
                    s.get("price_acceleration") or 0,
                    s.get("speed_percentile", 50),
                    1 if s.get("is_stale") else 0,
                    s.get("wave_phase", "neutral"),
                    1 if s.get("is_overextended") else 0,
                    s.get("momentum_score", 50),
                    s.get("last_move_at"),
                    now,
                ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[SpeedTracker] DB persist error: {e}")

    def _default_speed(self) -> dict:
        return {
            "price_velocity_5m": 0,
            "price_velocity_15m": 0,
            "price_acceleration": 0,
            "speed_percentile": 50,
            "is_stale": False,
            "wave_phase": "neutral",
            "is_overextended": False,
            "momentum_score": 50,
            "last_move_at": None,
            "last_move_dir": None,
        }


# ── Module-level singleton ────────────────────────────────────────────────────
# Reuse across calls within the same pipeline run (avoids re-fetching prices)
_instance: SpeedTracker | None = None


def get_tracker() -> SpeedTracker:
    global _instance
    if _instance is None:
        _instance = SpeedTracker()
    return _instance


def update_speeds() -> dict:
    """Convenience: get/update tracker and return speeds dict."""
    tracker = get_tracker()
    return tracker.update()


def get_all_speeds() -> dict:
    return get_tracker().get_all_speeds()


def get_token_speed(token: str) -> dict:
    return get_tracker().get_token_speed(token)


def get_fastest_tokens(n: int = 10) -> list:
    return get_tracker().get_fastest_tokens(n)
