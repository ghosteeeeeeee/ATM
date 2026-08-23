# MTF Z-Score signal module — extracted from signal_gen.py lines ~1736-1773
"""
MTF Z-Score signal (hzscore).

Fires when z-score agrees across multiple timeframes (4H/1H/15m):
  - bullish_tfs >= 2 (z > 0 on most TFs) → SHORT (hzscore+)
  - bearish_tfs >= 2 (z < 0 on most TFs) → LONG  (hzscore-)

Must match regime direction from get_momentum_stats (z_direction).
hz_dir_char: '-' for LONG, '+' for SHORT.

Checks HZSCORE_PLUS_ENABLED for SHORT, HZSCORE_MINUS_ENABLED for LONG.

FIX (2026-05-07): Added MIN_Z_VALUE = 0.4.
  - Historical data: winners had avg_z ~2.0, losers ~0.72. Marginal z-scores
    in chop zone produce 35% WR vs 47%+ WR at extreme readings.
  - Only fire when |avg_z| >= 0.4 — excludes marginal readings in the noise zone.
  - Was 0.6, too tight — blocked 50% of signals.
"""

# ── Signal Quality Threshold ───────────────────────────────────────────────────
# FIX (2026-05-07): Added to filter out marginal z-score readings.
# Winners avg_z ~2.0, losers avg_z ~0.72. Only fire at genuine extremes.
# FIX (2026-08-06): Raised from 0.4 to 0.8 — 12 signals had |z|<0.5, marginal noise.
MIN_Z_VALUE = 1.0   # |avg_z| must exceed this (backtested: 1.0 = 64.3% WR, 0.8 = 58.3%, 0 = 51.2%)
COOLDOWN_HOURS = 0.083  # 5 minutes per-token+direction cooldown (was 2h — too aggressive)
REQUIRE_3TF = False  # if True, require 3/3 TF agreement (was always 2/3 minimum)
# Solo-specific (stricter when no co-signal present)
SOLO_MIN_Z_VALUE = 1.2   # require genuine extreme for standalone (solo avg_z losers ~1.1, winners ~1.8)
SOLO_REQUIRE_3TF = True  # require 3/3 TF agreement when solo (no co-signal backup)
import sqlite3, statistics, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import CANDLES_DB
from signal_schema import add_signal, price_age_minutes


def _is_solo(token, direction):
    """Check if this token+direction has any other active signals in DB (no co-signal)."""
    try:
        from signal_schema import _get_conn, _runtime
        conn = _get_conn(_runtime())
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM signals
            WHERE token = ? AND direction = ? AND signal_type != 'mtf_zscore'
              AND created_at > datetime('now', '-10 minutes')
        """, (token.upper(), direction))
        count = cur.fetchone()[0]
        conn.close()
        return count == 0
    except Exception:
        return True  # assume solo if DB check fails


def run() -> int:
    """
    Scan all tokens for MTF Z-score agreement signals.

    Returns:
        Number of signals successfully written to DB.
    """
    from hermes_constants import (
        HZSCORE_ENABLED,
        HZSCORE_PLUS_ENABLED,
        HZSCORE_MINUS_ENABLED,
    )
    # NOTE: HZSCORE_ENABLED guard is in signal_gen.py (inline version).
    # This registry version is called by signals_runner.py — Layer 2 add_signal()
    # guard handles per-source filtering.

    # Imports needed for guards and signal generation
    from signal_gen import (
        get_tf_zscores,
        get_momentum_stats,
        recent_trade_exists,
        is_delisted,
        SHORT_BLACKLIST,
        MIN_TRADE_INTERVAL_MINUTES,
    )
    from position_manager import get_open_positions as _get_open_pos
    from signal_schema import get_all_latest_prices

    prices_dict = get_all_latest_prices()
    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}

    # ── Per-token cooldown check ───────────────────────────────────────────
    # Query last hzscore signal time for each token+direction
    last_signal_times = {}
    try:
        from signal_schema import _get_conn, _runtime
        conn_cd = _get_conn(_runtime())
        cur_cd = conn_cd.cursor()
        cur_cd.execute("""
            SELECT token, direction, MAX(created_at) as last_ts
            FROM signals
            WHERE signal_type = 'mtf_zscore'
            GROUP BY token, direction
        """)
        for row in cur_cd.fetchall():
            last_signal_times[(row[0], row[1])] = row[2]
        conn_cd.close()
    except Exception:
        pass  # non-fatal: skip cooldown if DB query fails

    added = 0

    for token, data in prices_dict.items():
        # ── Skip conditions (same as signal_gen.py) ──────────────────────
        if token.startswith('@'):
            continue
        if price_age_minutes(token) > 10:
            continue
        if not data.get('price') or data['price'] <= 0:
            continue
        if token.upper() in open_pos:
            continue
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue
        if token.upper() in SHORT_BLACKLIST:
            continue
        if is_delisted(token.upper()):
            continue

        # ── Range-bound gate: skip in choppy markets ──────────────────────
        # Trend-fading signals (like hzscore) should not fire in ranges.
        try:
            import json as _json
            regime_file = '/var/www/hermes/data/regime_5m.json'
            if os.path.exists(regime_file):
                with open(regime_file) as _f:
                    _regime_data = _json.load(_f)
                _token_regime = _regime_data.get('regimes', {}).get(token.upper(), {})
                if _token_regime.get('is_ranging', False):
                    continue
        except Exception:
            pass

        # ── EMA200 trend filter (2026-08-13) ──────────────────────────────
        # REMOVED (2026-08-23): z-score extremes ARE the signal — they fire when
        # price is far from mean (above/below EMA200). Blocking SHORT above EMA200
        # killed 2/6 valid signals. The trend filter in add_signal already handles
        # counter-trend protection, and hzscore is now exempt from it.

        price = data['price']

        # ── Get momentum stats for regime direction ───────────────────────
        mom = get_momentum_stats(token)
        if not mom:
            continue

        z_dir = mom.get('z_direction', 'neutral')

        # ── MTF Z-Score Agreement ────────────────────────────────────────
        zscores = get_tf_zscores(token)
        z_4h  = zscores.get('4h',  (None, None))[0]
        z_1h  = zscores.get('1h',  (None, None))[0]
        z_15m = zscores.get('15m', (None, None))[0]

        valid_z = [v for v in [z_4h, z_1h, z_15m] if v is not None]
        if len(valid_z) < 2:
            continue

        bullish_tfs = sum(1 for v in valid_z if v > 0)
        bearish_tfs = len(valid_z) - bullish_tfs

        # z > 0 = price above mean = bearish = SHORT
        # z < 0 = price below mean = bullish = LONG
        local_dir = 'SHORT' if bullish_tfs >= 2 else ('LONG' if bearish_tfs >= 2 else None)
        if not local_dir:
            continue

        # ── Momentum fade + spike exhaustion + consolidation filter ──────────
        # MANDATORY: if this fails, skip the signal (don't proceed without it)
        _conn = None
        try:
            from paths import HERMES_DATA
            import sqlite3 as _sqlite3
            from hermes_constants import SPIKE_EXHAUSTION_VEL_5M_THRESHOLD
            _conn = _sqlite3.connect(os.path.join(HERMES_DATA, 'signals_hermes.db'), timeout=10)
            _cur = _conn.cursor()
            _cur.execute("""
                SELECT price FROM (
                    SELECT price, timestamp FROM price_history
                    WHERE token = ?
                    ORDER BY timestamp DESC LIMIT 6
                ) sub ORDER BY timestamp ASC
            """, (token.upper(),))
            _prices = [r[0] for r in _cur.fetchall()]
            if len(_prices) >= 2 and _prices[0] > 0:
                vel_5m = (_prices[-1] - _prices[0]) / _prices[0] * 100
                # FIX (2026-08-23): Removed momentum fade direction gate.
                # z-score extremes are LEADING indicators — they should fire before
                # the move, not wait for confirmation. The old fade filter blocked
                # ALL SHORT signals when 5m vel > 0, killing 10 valid signals/cycle.
                # Spike exhaustion still blocks sharp moves.
                # Spike exhaustion: skip after sharp 5m moves
                if abs(vel_5m) > SPIKE_EXHAUSTION_VEL_5M_THRESHOLD:
                    continue  # spike exhaustion — skip

            # ── BB consolidation filter: skip SHORT in tight ranges ─────────
            # Backtest (54 hzscore- trades): bb_width < 0.4% blocks 46% losers,
            # keeps 68% winners. Catches bullish flag breakdowns (BSV 2026-08-16).
            try:
                _cur.execute("""
                    SELECT close FROM candles_1m
                    WHERE token = ? ORDER BY ts DESC LIMIT 20
                """, (token.upper(),))
                _closes = [r[0] for r in _cur.fetchall()]
                if len(_closes) >= 20:
                    import statistics as _stat
                    _sma = _stat.mean(_closes)
                    _std = _stat.stdev(_closes)
                    _lower = _sma - 2 * _std
                    _upper = _sma + 2 * _std
                    _bb_width = (_upper - _lower) / _sma * 100
                    if _bb_width < 0.4:
                        continue  # tight consolidation — likely bullish flag, skip SHORT
            except Exception:
                pass  # non-fatal: BB filter is secondary

        except Exception:
            # Velocity filter is MANDATORY — if it fails, skip the signal
            continue
        finally:
            if _conn:
                _conn.close()

        # Solo detection — apply stricter params when no co-signal
        solo = _is_solo(token, local_dir)
        tf_required = SOLO_REQUIRE_3TF if solo else REQUIRE_3TF
        if tf_required and len(valid_z) < 3:
            continue

        # Map z_direction to regime direction for MTF agreement check.
        # 'rising' → 'LONG', 'falling' → 'SHORT', 'neutral' → None (skip)
        z_dir_map = {'rising': 'LONG', 'falling': 'SHORT', 'neutral': None}
        regime_dir = z_dir_map.get(z_dir.lower(), None)

        # Only fire if MTF direction matches regime direction (or regime is neutral)
        if regime_dir is not None and local_dir != regime_dir:
            continue

        # ── Direction-specific enable check ───────────────────────────────
        # FIX (2026-05-11): Flipped hz_dir_char so naming matches direction convention.
        # hzscore- = LONG, hzscore+ = SHORT (was inverted: hzscore- = SHORT, hzscore+ = LONG)
        hz_dir_char = '+' if local_dir == 'LONG' else '-'
        if local_dir == 'SHORT' and not HZSCORE_PLUS_ENABLED:
            continue
        if local_dir == 'LONG' and not HZSCORE_MINUS_ENABLED:
            continue

        avg_z = statistics.mean(valid_z)

        # FIX (2026-05-07): Only fire at genuine extremes, not marginal z-score readings.
        # |avg_z| < 0.6 is the chop zone — winners had avg_z ~2.0, losers ~0.72.
        # Solo-specific: require higher z-score when no co-signal (solo losers avg_z ~1.1)
        z_thresh = SOLO_MIN_Z_VALUE if solo else MIN_Z_VALUE
        if abs(avg_z) < z_thresh:
            continue

        # ── Per-token cooldown (2h default) ─────────────────────────────────
        # Prevents duplicate signals on same token+direction within cooldown window
        if COOLDOWN_HOURS > 0:
            import datetime
            last_ts_str = last_signal_times.get((token, local_dir))
            if last_ts_str:
                try:
                    last_ts = datetime.datetime.strptime(last_ts_str, '%Y-%m-%d %H:%M:%S')
                    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                    if (now - last_ts).total_seconds() < COOLDOWN_HOURS * 3600:
                        continue
                except Exception:
                    pass  # non-fatal: proceed if parse fails

        # ── Build and emit signal ───────────────────────────────────────
        # Dynamic confidence: z-score magnitude + TF agreement + speed
        avg_z = abs(statistics.mean(valid_z))
        z_bonus = min(15, int(avg_z * 8))         # 0.5→+4, 1.0→+8, 1.5→+12, 2.0→+15
        tf_bonus = len(valid_z) * 3                 # 2→+6, 3→+9
        agree_bonus = max(bullish_tfs, bearish_tfs) * 3  # 2→+6, 3→+9
        speed_pct = 0
        try:
            from speed_tracker import get_token_speed
            _spd = get_token_speed(token)
            speed_pct = _spd.get('speed_percentile', 0) if _spd else 0
        except Exception:
            pass
        speed_bonus = 5 if speed_pct >= 80 else 0
        z_conf = min(88, 50 + z_bonus + tf_bonus + agree_bonus + speed_bonus)
        z_conf = max(50, z_conf)
        z_tf_str = f'{max(bullish_tfs, bearish_tfs)}z{len(valid_z)}'
        rsi_val = mom.get('rsi_14')

        sid = add_signal(
            token=token,
            direction=local_dir,
            signal_type='mtf_zscore',
            source=f'hzscore{hz_dir_char}',
            confidence=z_conf,
            value=round(avg_z, 3),
            price=price,
            exchange='hyperliquid',
            timeframe=z_tf_str,
            z_score=avg_z,
            z_score_tier=z_dir,
            rsi_14=rsi_val,
        )
        if sid:
            added += 1

    return added


if __name__ == '__main__':
    n = run()
    print(f'hzscore: {n} signals emitted')
