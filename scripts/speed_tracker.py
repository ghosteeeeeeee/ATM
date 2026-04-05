"""
speed_tracker.py — Token speed, velocity, acceleration, and momentum percentile.

Tracks how fast each token is moving and identifies:
- Fast movers (high velocity, enter these)
- Stale tokens (flat for 15+ min, exit or skip)
- Acceleration vs deceleration (momentum of momentum)

Uses local hype_cache.get_allMids() for current prices.
Maintains in-memory rolling history (60 points = 60 min).
Runs every ~1 min as part of the pipeline — must complete in <2s.
"""

import json
import os
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timezone

import hype_cache as hc

# ── Paths ────────────────────────────────────────────────────────────────────
HERMES_DATA = "/root/.hermes/data"
SPEED_CACHE = os.path.join(HERMES_DATA, "speed_cache.json")

# ── Thresholds (documented rationale) ───────────────────────────────────────
# speed_percentile < 20  → token is near-universe minimum velocity, skip signals
# speed_percentile >= 70 → fast mover, 5% easier entry threshold
# speed_percentile >= 80 → hot set speed bonus (+15% score boost)
# stale_5m_velocity     → 0.2% = "essentially flat" over 5 min (noise threshold)
# stale_15m             → 15 min of flatness = stale winner, book profits
# stale_30m             → 30 min of flatness = stale loser, cut loss

SPEED_MIN_THRESHOLD = 20      # tokens below this rarely get signals
SPEED_ENTRY_BOOST = 70         # percentile at which entry gets 5% easier
SPEED_HOTSET_THRESHOLD = 80    # percentile at which hot set gets speed bonus
STALE_VELOCITY_5M = 0.2        # % change — below this = "flat" for 5m
STALE_WINNER_MINUTES = 15      # stale winner: 15+ min flat while in profit
STALE_LOSER_MINUTES = 30        # stale loser: 30+ min flat while in loss
SPEED_WEIGHT = 0.15            # 15% of hot set score
SPEED_HOTSET_BONUS = 0.15      # +15% score boost for speed_percentile >= 80
SPEED_COMPACTION_WEIGHT = 0.10 # 10% of compaction score

# ── History config ───────────────────────────────────────────────────────────
HISTORY_POINTS = 60   # 60 min of 1-min history
HISTORY_FILE = os.path.join(HERMES_DATA, "speed_history.json")


def _load_history() -> dict:
    """Load rolling price history from disk (persists across pipeline runs)."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_history(history: dict) -> None:
    """Persist rolling history to disk."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)


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
        self._history: dict = _load_history()   # token → list of {price, ts}
        self._percentiles: list = []    # sorted list of all velocities (for percentile rank)
        self._updated_at: str = _now_ts()

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self) -> dict:
        """
        Fetch current prices, update history, compute all speed metrics.
        Call once per pipeline run. Returns dict of token → speed data.
        """
        t0 = time.time()

        # Fetch current prices from local cache (sub-second)
        try:
            mids = hc.get_allMids()
        except Exception as e:
            print(f"[SpeedTracker] Failed to fetch mids: {e}")
            mids = {}

        now = time.time()
        now_ts = _now_ts()

        # Push current prices into rolling history
        for token, price_str in mids.items():
            try:
                price = float(price_str)
            except (ValueError, TypeError):
                continue
            if price <= 0:
                continue

            if token not in self._history:
                self._history[token] = []
            self._history[token].append({"price": price, "ts": now})
            # Keep only last HISTORY_POINTS
            if len(self._history[token]) > HISTORY_POINTS:
                self._history[token] = self._history[token][-HISTORY_POINTS:]

        # Compute speed for each token that has enough history
        self._speeds = {}
        all_velocities_5m = []

        for token, hist in self._history.items():
            if len(hist) < 2:   # need at least 2 points to compute any velocity
                continue

            speed = self._compute_speed(token, hist, now)
            self._speeds[token] = speed
            # Only rank tokens with valid 5m velocity
            if speed["price_velocity_5m"] is not None:
                all_velocities_5m.append(abs(speed["price_velocity_5m"]))

        # Compute percentile rank for each token
        if all_velocities_5m:
            all_velocities_5m.sort()
            n = len(all_velocities_5m)
            for token, speed in self._speeds.items():
                if speed["price_velocity_5m"] is None:
                    speed["speed_percentile"] = 50
                    continue
                v = abs(speed["price_velocity_5m"])
                # percentile: what % of tokens have lower or equal velocity
                rank = next((i for i, x in enumerate(all_velocities_5m) if x >= v), n - 1)
                speed["speed_percentile"] = round(rank / (n - 1) * 100, 1) if n > 1 else 50

                # is_stale: flat for 15+ min (velocity near zero)
                speed["is_stale"] = (
                    abs(speed["price_velocity_5m"]) < STALE_VELOCITY_5M
                    and speed["price_velocity_15m"] is not None
                    and abs(speed["price_velocity_15m"]) < STALE_VELOCITY_5M
                )

                # Wave phase: classify the acceleration regime
                # accelerating  = vel and accel both positive → rising momentum
                # decelerating = vel positive, accel negative → slowing down
                # bottoming    = vel negative, accel positive → reversal potential
                # falling      = vel and accel both negative → continuing down
                vel = speed["price_velocity_5m"]
                accel = speed["price_acceleration"]
                # BUG FIX (2026-04-05): None guards added — _compute_speed() returns None
                # for vel/accel when there's insufficient history, causing TypeError on comparison
                if vel is not None and accel is not None:
                    if vel > 0 and accel > 0:
                        wave_phase = "accelerating"
                    elif vel > 0 and accel < 0:
                        wave_phase = "decelerating"
                    elif vel < 0 and accel > 0:
                        wave_phase = "bottoming"
                    elif vel < 0 and accel < 0:
                        wave_phase = "falling"
                    else:
                        wave_phase = "neutral"
                else:
                    wave_phase = "neutral"
                speed["wave_phase"] = wave_phase

                # is_overextended: velocity has moved too far from 15m baseline
                # → wave is overcooked, reversal likely
                # SHORT overextended: vel_5m < -3%  (ripped up too fast, reversal down coming)
                # LONG overextended:  vel_5m > +3%  (dumped too hard, bounce coming)
                # is_stale tokens are never overextended (they've already flatlined)
                OVEREXTENDED_THRESHOLD = 3.0
                speed["is_overextended"] = (
                    not speed["is_stale"]
                    and abs(vel) > OVEREXTENDED_THRESHOLD
                )

                # momentum_score: composite of current velocity + acceleration
                # Tokens in "bottoming" phase with positive accel are best LONG entries
                # Tokens in "decelerating" phase (high vel, neg accel) are best SHORT exits
                # Range: ~0 to ~100, where 50 = average momentum
                vel_component = min(abs(vel) / 3.0, 1.0) * 60  # 0-60 from velocity magnitude
                accel_component = accel * 5 if accel else 0  # signed: positive accel = +score
                speed["momentum_score"] = round(
                    speed.get("speed_percentile", 50) * 0.4  # 40% base percentile
                    + vel_component * 0.4                    # 40% current velocity
                    + min(max(accel_component, -20), 20) * 0.2,  # 20% acceleration
                    1
                )

                # last_move_at: when was last significant move (>0.3% in 1 min)
                # Only same-direction moves reset the stale timer
                speed["last_move_at"], speed["last_move_dir"] = self._last_move_time(token, hist, now)
        else:
            for token in self._speeds:
                self._speeds[token]["speed_percentile"] = 50
                self._speeds[token]["is_stale"] = False

        # Persist history for next run
        _save_history(self._history)

        # Persist to DB (for cross-script access)
        self._persist_to_db()

        self._updated_at = now_ts
        elapsed = time.time() - t0
        print(f"[SpeedTracker] Updated {len(self._speeds)} tokens in {elapsed:.3f}s")
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
        # For hourly data (avg_interval ~= 3600), we map:
        #   5m velocity  → use index 1  (1 hour ago, ~5% of a 24h token's movement)
        #   15m velocity → use index 3  (3 hours ago)
        # For 1-min data (avg_interval ≈ 60):
        #   5m velocity  → use index 5  (5 min ago)
        #   15m velocity → use index 15 (15 min ago)
        if avg_interval >= 1800:  # hourly or higher interval
            idx_5m, idx_15m = 1, 3
        else:  # 1-min data
            idx_5m, idx_15m = 5, 15

        p0 = _price_at_idx(0)
        p5 = _price_at_idx(idx_5m)
        p15 = _price_at_idx(idx_15m)

        vel_5m = None
        vel_15m = None
        accel = None

        if p0 and p5 and p5 > 0:
            vel_5m = round((p0 - p5) / p5 * 100, 4)

        if p0 and p15 and p15 > 0:
            vel_15m = round((p0 - p15) / p15 * 100, 4)

        # ── Acceleration: change in velocity ───────────────────────────────
        # For hourly data: accel = (vel_5m - vel_15m) / 3 (per-hour, 3hr span)
        # For 1-min data:  accel = (vel_5m - vel_15m) / 15 (per-min, 15min span)
        span = idx_15m - idx_5m  # time span between velocity measurements
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
        db_path = "/root/.hermes/data/signals_hermes_runtime.db"
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
