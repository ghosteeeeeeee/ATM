#!/usr/bin/env python3
"""
mtf_macd.py — MTF MACD: Multi-Timeframe MACD Histogram Alignment Signal.

Fires when:
  - z_1h > 2.0 (price 2+ std dev from 1h mean) AND both histograms negative → SHORT
  - z_1h < -2.0 (price 2+ std dev below 1h mean) AND both histograms positive → LONG

Logic: Mean-reversion entry with momentum confirmation.
  Stretched price + MACD histogram confirming direction = high-probability reversal.

Improvements (2026-10-01):
  - Fixed signal_gen import (was broken since signal_gen.py removal)
  - Added inline z-score calculation (reads from local candles.db)
  - Added regime awareness: skip in strong trends (STRONG_DOWN for LONG, STRONG_UP for SHORT)
  - Added RSI filter: skip SHORT when RSI < 35, skip LONG when RSI > 70
  - Added EMA300 position check: prefer LONG below EMA300, SHORT above EMA300
  - Improved confidence scoring with volume ratio bonus

Source: hmacd_mtf-{+|-}
signal_type: hmacd_mtf
"""

import sys, os, sqlite3, json, time, statistics
from typing import Optional, Tuple

sys.path.insert(0, '/root/.hermes/scripts')

from signal_schema import (
    init_db, get_all_latest_prices, get_price_history,
    price_age_minutes, add_signal, get_cooldown,
)
from hermes_constants import (
    HMACD_MTF_PLUS_ENABLED,
    HMACD_MTF_MINUS_ENABLED,
    SHORT_BLACKLIST,
    LONG_BLACKLIST,
)
from macd_rules import get_macd_params, compute_mtf_macd_alignment, cascade_entry_signal

# ── Constants ─────────────────────────────────────────────────────────────────
Z_MACD_THRESH         = 2.0    # z-score threshold for entry
MIN_TRADE_INTERVAL    = 10     # minutes between trades per token
LOG_FILE              = '/root/.hermes/logs/signals.log'
RSI_SHORT_MIN         = 35     # Don't SHORT when RSI < 35 (oversold)
RSI_LONG_MAX          = 70     # Don't LONG when RSI > 70 (overbought)
ALT_REGIME_CONF_MIN   = 70     # brain_auditor 2026-10-10: min 5m-regime confidence to block counter-bias entries (alt fallback for BTC-only continuum.db)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] [mtf_macd] {msg}'
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def _recent_trade_exists(token: str, minutes: int = MIN_TRADE_INTERVAL) -> bool:
    """Return True if token was traded in last N minutes."""
    TRADE_LOG = '/var/www/hermes/data/recent_trades.json'
    try:
        if not os.path.exists(TRADE_LOG):
            return False
        with open(TRADE_LOG) as f:
            data = json.load(f)
        cutoff = time.time() - minutes * 60
        entries = data.get(token.upper(), [])
        for entry in entries:
            ts = entry.get('timestamp', 0) if isinstance(entry, dict) else entry
            if ts > cutoff:
                return True
    except Exception:
        pass
    return False


def is_reasonable_price(price) -> bool:
    return price is not None and price > 0 and price < 1e6


def is_delisted(token: str) -> bool:
    from hyperliquid_exchange import is_delisted as _dl
    return _dl(token)


def _get_zscore(token: str, timeframe: str = '1h') -> Optional[float]:
    """Calculate z-score from local candles.db (inline, no signal_gen dependency)."""
    # Validate timeframe against allowlist to prevent injection
    _VALID_TF = {'1m', '5m', '15m', '1h', '4h'}
    if timeframe not in _VALID_TF:
        return None
    try:
        from paths import CANDLES_DB
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        # FIX 2026-10-02: per-TF table names (candles_1h, candles_15m, etc.)
        cur.execute(f"""
            SELECT close FROM candles_{timeframe}
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT 500
        """, (token.upper(),))
        rows = [r[0] for r in cur.fetchall()]
        conn.close()
        if len(rows) >= 20:
            mean = statistics.mean(rows)
            stdev = statistics.stdev(rows) if len(rows) > 1 else 1
            if stdev > 0:
                return (rows[0] - mean) / stdev
    except Exception:
        pass
    return None


def _get_rsi(token: str, timeframe: str = '1m', period: int = 14) -> Optional[float]:
    """Calculate RSI from local candles.db. Falls back to 5m/15m if 1m unavailable."""
    _VALID_TF = {'1m', '5m', '15m', '1h', '4h'}
    if timeframe not in _VALID_TF:
        return None
    # Try requested TF first, then fallbacks
    _TF_ORDER = [timeframe, '5m', '15m']
    for tf in _TF_ORDER:
        try:
            from paths import CANDLES_DB
            conn = sqlite3.connect(CANDLES_DB, timeout=10)
            cur = conn.cursor()
            cur.execute(f"""
                SELECT close FROM candles_{tf}
                WHERE token = ? AND is_closed = 1
                ORDER BY ts DESC LIMIT ?
            """, (token.upper(), period + 1))
            rows = [r[0] for r in cur.fetchall()]
            conn.close()
            if len(rows) < period + 1:
                continue
            # Reverse to chronological order
            rows.reverse()
            gains, losses = [], []
            for i in range(1, len(rows)):
                change = rows[i] - rows[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period
            if avg_loss == 0:
                return 100.0
            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))
        except Exception:
            continue
    return None


def _get_ema300_position(token: str) -> Optional[str]:
    """Get EMA300 position (ABOVE/BELOW) from continuum.db."""
    try:
        from paths import HERMES_DATA
        conn = sqlite3.connect(f'{HERMES_DATA}/continuum.db', timeout=3)
        cur = conn.cursor()
        cur.execute("""
            SELECT ema300_position FROM continuum_states
            WHERE token = ? ORDER BY ts DESC LIMIT 1
        """, (token.upper(),))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        pass
    return None


def _get_trend_quality(token: str) -> Optional[str]:
    """Get trend quality from continuum.db."""
    try:
        from paths import HERMES_DATA
        conn = sqlite3.connect(f'{HERMES_DATA}/continuum.db', timeout=3)
        cur = conn.cursor()
        cur.execute("""
            SELECT trend_quality FROM continuum_states
            WHERE token = ? ORDER BY ts DESC LIMIT 1
        """, (token.upper(),))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        pass
    return None


def _get_regime_5m(token: str) -> Tuple[Optional[str], float]:
    """Get (regime, confidence) from regime_5m.json. Fallback for alts — continuum.db is BTC-only."""
    try:
        with open('/var/www/hermes/data/regime_5m.json') as f:
            data = json.load(f)
        r = data.get('regimes', {}).get(token.upper())
        if r:
            return r.get('regime'), float(r.get('confidence') or 0)
    except Exception:
        pass
    return None, 0.0


def _macd_crossover(token: str, minutes: int):
    """
    Compute MACD histogram for a token at given timeframe.
    Reads directly from candles_{tf} table (214 tokens vs price_history's 130).
    Returns: (histogram, macd_line, signal_line, crossover_dir)
    """
    _VALID_TF = {1: '1m', 5: '5m', 15: '15m', 60: '1h', 240: '4h'}
    tf_name = _VALID_TF.get(minutes)
    if tf_name is None:
        return None

    params = get_macd_params(token)
    fast, slow, sig = params['fast'], params['slow'], params['signal']
    # Need slow + sig + buffer candles
    n_needed = slow + sig + 20

    try:
        from paths import CANDLES_DB
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        # FIX 2026-10-02: read from candles_{tf} directly (not price_history)
        cur.execute(f"""
            SELECT ts, open, high, low, close FROM candles_{tf_name}
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), n_needed))
        rows = cur.fetchall()
        conn.close()
    except Exception:
        return None

    if not rows or len(rows) < 40:
        return None

    # Rows are newest-first, reverse to chronological
    rows.reverse()
    closes_all = [r[4] for r in rows]  # close prices

    n_bars = len(closes_all[:-1])   # previous bar
    if n_bars < slow + sig:
        return None

    def _ema(data, period):
        if len(data) < period:
            return None
        k = 2 / (period + 1)
        ema_val = sum(data[:period]) / period
        for price in data[period:]:
            ema_val = price * k + ema_val * (1 - k)
        return ema_val

    def _macd_from_closes(closes_list):
        if len(closes_list) < slow + sig:
            return None, None, None
        ef = _ema(closes_list, fast)
        es = _ema(closes_list, slow)
        if ef is None or es is None:
            return None, None, None
        macd_line = ef - es
        macd_vals = []
        for i in range(slow, len(closes_list)):
            efa = _ema(closes_list[:i+1], fast)
            esa = _ema(closes_list[:i+1], slow)
            if efa and esa:
                macd_vals.append(efa - esa)
        if len(macd_vals) < sig:
            return None, None, None
        sig_val = _ema(macd_vals, sig)
        if sig_val is None:
            return None, None, None
        return round(macd_line, 6), round(sig_val, 6), round(macd_line - sig_val, 6)

    # Previous bar (all closes except last) → current bar (all closes)
    closes_prev = closes_all[:-1]
    closes_cur  = closes_all
    macd_prev, sig_prev, hist_prev = _macd_from_closes(closes_prev)
    macd_cur,  sig_cur,  hist_cur  = _macd_from_closes(closes_cur)
    if macd_cur is None or macd_prev is None:
        return None

    prev_above = (macd_prev - sig_prev) >= 0
    cur_above  = (macd_cur  - sig_cur)  >  0
    if not prev_above and cur_above:
        crossover_dir =  1   # bullish — MACD crossed above signal
    elif prev_above and not cur_above:
        crossover_dir = -1   # bearish — MACD crossed below signal
    else:
        crossover_dir =  0   # no crossover

    return (hist_cur, macd_cur, sig_cur, crossover_dir)


# ── Main run ─────────────────────────────────────────────────────────────────

def run():
    """Scan all tokens for MTF MACD signals. Returns number of signals added."""
    init_db()
    prices_dict = get_all_latest_prices()
    added = 0

    _log(f'Starting | {len(prices_dict)} tokens | z_thresh={Z_MACD_THRESH}')

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        if price_age_minutes(token) > 10:
            continue
        price = data.get('price')
        if not is_reasonable_price(price):
            continue
        if _recent_trade_exists(token, MIN_TRADE_INTERVAL):
            continue
        if token.upper() in SHORT_BLACKLIST or token.upper() in LONG_BLACKLIST:
            continue
        if is_delisted(token.upper()):
            continue

        # ── Get 1H z-score ─────────────────────────────────────────────
        z_1h = _get_zscore(token, '1h')
        if z_1h is None:
            continue

        # ── Get 15m and 1H MACD histograms ────────────────────────────
        xo_15m = _macd_crossover(token, 15)
        xo_1h  = _macd_crossover(token, 60)
        h_15m = xo_15m[0] if xo_15m else None
        h_1h  = xo_1h[0]  if xo_1h  else None
        if h_15m is None or h_1h is None:
            continue

        # ── Determine direction ────────────────────────────────────────
        # Positive z: stretched up → expect down → SHORT if hist confirms
        # Negative z: oversold     → expect up   → LONG  if hist confirms
        mtf_direction = None
        if z_1h > Z_MACD_THRESH:
            if h_15m < 0 and h_1h < 0:
                mtf_direction = 'SHORT'
        elif z_1h < -Z_MACD_THRESH:
            if h_15m > 0 and h_1h > 0:
                mtf_direction = 'LONG'

        if mtf_direction is None:
            continue

        # ── Directional kill-switch ────────────────────────────────────
        if mtf_direction == 'LONG' and not HMACD_MTF_PLUS_ENABLED:
            continue
        if mtf_direction == 'SHORT' and not HMACD_MTF_MINUS_ENABLED:
            continue

        # ── RSI filter (prevent BANANA pattern) ────────────────────────
        rsi = _get_rsi(token, '1m')
        if rsi is not None:
            if mtf_direction == 'SHORT' and rsi < RSI_SHORT_MIN:
                _log(f'  SKIP {token} SHORT: RSI {rsi:.1f} < {RSI_SHORT_MIN} (oversold)')
                continue
            if mtf_direction == 'LONG' and rsi > RSI_LONG_MAX:
                _log(f'  SKIP {token} LONG: RSI {rsi:.1f} > {RSI_LONG_MAX} (overbought)')
                continue

        # ── Trend quality filter ───────────────────────────────────────
        trend_quality = _get_trend_quality(token)
        if trend_quality:
            if mtf_direction == 'LONG' and trend_quality == 'STRONG_DOWN':
                _log(f'  SKIP {token} LONG: trend_quality=STRONG_DOWN')
                continue
            if mtf_direction == 'SHORT' and trend_quality == 'STRONG_UP':
                _log(f'  SKIP {token} SHORT: trend_quality=STRONG_UP')
                continue
        else:
            # Fallback: continuum.db is BTC-only — alts always miss. Use 5m regime.
            # brain_auditor 2026-10-10: W SHORT x2 lost -$0.26 shorting LONG_BIAS conf 90.1
            # because this guard fail-opened (no continuum row for W).
            alt_regime, alt_conf = _get_regime_5m(token)
            if alt_regime and alt_conf >= ALT_REGIME_CONF_MIN:
                if mtf_direction == 'SHORT' and alt_regime == 'LONG_BIAS':
                    _log(f'  SKIP {token} SHORT: 5m regime LONG_BIAS conf={alt_conf:.1f}')
                    continue
                if mtf_direction == 'LONG' and alt_regime == 'SHORT_BIAS':
                    _log(f'  SKIP {token} LONG: 5m regime SHORT_BIAS conf={alt_conf:.1f}')
                    continue

        # ── EMA300 position filter ────────────────────────────────────
        ema_pos = _get_ema300_position(token)
        if ema_pos:
            if mtf_direction == 'LONG' and ema_pos == 'ABOVE':
                # Prefer LONG below EMA300 (mean-reversion from below)
                _log(f'  SKIP {token} LONG: already ABOVE EMA300')
                continue
            if mtf_direction == 'SHORT' and ema_pos == 'BELOW':
                # Prefer SHORT above EMA300 (mean-reversion from above)
                _log(f'  SKIP {token} SHORT: already BELOW EMA300')
                continue

        # ── Confidence scoring (competitive with RS=88) ────────────────
        z_excess   = abs(z_1h) - Z_MACD_THRESH
        # Base: 55 + z_excess * 15 (capped at 85)
        # z=2.0 → 55, z=2.5 → 62.5, z=3.0 → 70, z=3.5 → 77.5, z=4.0 → 85
        conf       = min(85.0, 55.0 + z_excess * 15)
        timeframe  = f'z3_z{z_1h:.1f}'
        strength   = round(z_excess, 3)

        # RSI boost: extreme RSI = higher confidence
        if rsi is not None:
            if mtf_direction == 'SHORT' and rsi >= 55:
                conf += 5   # SHORT at RSI 55+ = good setup
            elif mtf_direction == 'LONG' and rsi <= 45:
                conf += 5   # LONG at RSI 45- = good setup

        # MACD histogram magnitude boost: stronger histogram = more conviction
        avg_hist = abs((h_15m + h_1h) / 2)
        price_scale = price if price > 0 else 1
        hist_ratio = avg_hist / price_scale
        if hist_ratio > 0.005:
            conf += 5   # strong histogram
        elif hist_ratio > 0.002:
            conf += 3   # moderate histogram

        # ── MTF alignment boost ────────────────────────────────────────
        try:
            mtf_align = compute_mtf_macd_alignment(token)
            if mtf_align is not None:
                align_score = mtf_align['mtf_score']
                align_dir   = mtf_align['mtf_direction']
                if align_score >= 3:
                    conf += 10
                elif align_score >= 2 and align_dir == mtf_direction:
                    conf += 5
        except Exception as e:
            _log(f'  [MTF ALIGN] {token} error: {e}')

        # ── Cascade boost / block ──────────────────────────────────────
        cascade_blocked = False
        try:
            cascade = cascade_entry_signal(token)
            if cascade.get('cascade_active') and cascade.get('cascade_direction'):
                if cascade['cascade_direction'] == mtf_direction:
                    conf += 10
                    _log(f'  [CASCADE] {token} confirmed → +10 conf')
                elif cascade['cascade_direction'] is not None:
                    cascade_blocked = True
                    _log(f'  [CASCADE] {token} BLOCKED — opposite direction active')
        except Exception as e:
            _log(f'  [CASCADE] {token} error: {e}')

        if cascade_blocked:
            continue

        # ── Final confidence clamp (match RS cap of 88) ────────────────
        conf = min(88.0, conf)

        # ── Write signal ───────────────────────────────────────────────
        hmacd_char = '+' if mtf_direction == 'LONG' else '-'
        source = f'hmacd_mtf-{hmacd_char}'
        sid = add_signal(
            token=token,
            direction=mtf_direction,
            signal_type='hmacd_mtf',
            source=source,
            confidence=conf,
            value=strength,
            price=float(price),
            exchange='hyperliquid',
            timeframe=timeframe,
            z_score=z_1h,
            macd_hist=(h_15m + h_1h) / 2,
        )
        if sid:
            added += 1
            rsi_s = f'{rsi:.1f}' if rsi is not None else 'N/A'
            _log(f'  SIGNAL: {token} {mtf_direction} @{price:.6f} conf={conf:.1f} z_1h={z_1h:.2f} rsi={rsi_s}')

    _log(f'Done: {added} signals added')
    return added


if __name__ == '__main__':
    run()
