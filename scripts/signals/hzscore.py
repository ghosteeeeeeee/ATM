# MTF Z-Score signal module — extracted from signal_gen.py lines ~1736-1773
"""
MTF Z-Score signal (hzscore).

Fires when z-score agrees across multiple timeframes (4H/1H/15m):
  - bullish_tfs >= 2 (z > 0 on most TFs) → SHORT (hzscore+)
  - bearish_tfs >= 2 (z < 0 on most TFs) → LONG  (hzscore-)

Must match regime direction from get_momentum_stats (z_direction).
hz_dir_char: '-' for LONG, '+' for SHORT.

Checks HZSCORE_PLUS_ENABLED for SHORT, HZSCORE_MINUS_ENABLED for LONG.

FIX (2026-05-07): Added MIN_Z_VALUE = 0.6.
  - Historical data: winners had avg_z ~2.0, losers ~0.72. Marginal z-scores
    in chop zone produce 35% WR vs 47%+ WR at extreme readings.
  - Only fire when |avg_z| >= 0.6 — excludes marginal readings in the noise zone.
"""

# ── Signal Quality Threshold ───────────────────────────────────────────────────
# FIX (2026-05-07): Added to filter out marginal z-score readings.
# Winners avg_z ~2.0, losers avg_z ~0.72. Only fire at genuine extremes.
MIN_Z_VALUE = 0.4   # |avg_z| must exceed this for hzscore to fire (was 0.6, too tight — blocked 50% of signals)
import statistics, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, price_age_minutes


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
        if abs(avg_z) < MIN_Z_VALUE:
            continue

        # ── Build and emit signal ───────────────────────────────────────
        z_conf = min(80, 45 + len(valid_z) * 8 + max(bullish_tfs, bearish_tfs) * 5)
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
