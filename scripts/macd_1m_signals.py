"""
MACD 1m Signal Scanner — per-token tuned, SHORT + LONG.

Standalone module: reads 1m candles from price_history (signals_hermes.db), uses
per-token tuned params from mtf_macd_tuner.db (token_best_config_1m_v2 table), fires
macd-accel-signals for both directions.

Architecture:
- Zero HL API calls (reads from local price_history only)
- Zero Binance API calls
- Per-token tuned params loaded from SQLite on first call, cached for session
- Fires macd_short_1m (SHORT) and macd_long_1m (LONG) signal types
- Uses signal_schema.add_signal() and position_manager guards

Signal types:
- macd_short_1m: SHORT on bearish histogram crossover (hist >= 0 → < 0)
- macd_long_1m:  LONG  on bullish histogram crossover (hist <= 0 → > 0)

Weights (set in signal_compactor.py):
- macd_short_1m: 1.35
- macd_long_1m:  1.10
"""

import sqlite3
import time
from typing import Dict, List, Optional

_TUNER_DB   = '/root/.hermes/data/mtf_macd_tuner.db'

# ── Tuner DB param loading ───────────────────────────────────────────────────

_TOKEN_CACHE: Optional[Dict] = None
_DEFAULT_SHORT = {'fast': 8,  'slow': 15, 'signal': 6, 'hold_bars': 60, 'wr': 56.0, 'n': 0}
_DEFAULT_LONG  = {'fast': 10, 'slow': 25, 'signal': 8, 'hold_bars': 10, 'wr': 50.0, 'n': 0}


def load_token_params() -> Dict:
    """Load per-token 1m MACD params (SHORT + LONG) from tuner DB.

    Returns:
        dict: token -> {'SHORT': {...params}, 'LONG': {...params}}
              Tokens missing a direction use DEFAULT fallback.
              Special key 'DEFAULT' holds the fallback values.
    """
    global _TOKEN_CACHE
    if _TOKEN_CACHE is not None:
        return _TOKEN_CACHE

    cache: Dict = {}
    try:
        conn = sqlite3.connect(_TUNER_DB, timeout=5)
        c = conn.cursor()
        c.execute("""SELECT token, direction, fast, slow, signal, hold_bars,
                             win_rate, signal_count
                      FROM token_best_config_1m_v2""")
        for token, direction, fast, slow, signal, hold_bars, wr, n in c.fetchall():
            t = token.upper()
            if t not in cache:
                cache[t] = {}
            cache[t][direction.upper()] = {
                'fast': fast, 'slow': slow, 'signal': signal,
                'hold_bars': hold_bars, 'wr': wr, 'n': n
            }
        conn.close()
    except Exception as e:
        print(f"[macd_1m] DB load failed: {e}")

    # Fill missing directions with defaults
    for token in cache:
        if 'SHORT' not in cache[token]:
            cache[token]['SHORT'] = _DEFAULT_SHORT
        if 'LONG' not in cache[token]:
            cache[token]['LONG'] = _DEFAULT_LONG

    cache['DEFAULT'] = {'SHORT': _DEFAULT_SHORT, 'LONG': _DEFAULT_LONG}
    _TOKEN_CACHE = cache
    print(f"[macd_1m] Loaded {len(cache)-1} token params from tuner DB")
    return cache


def reset_cache():
    """Clear the param cache so the next call reloads from DB."""
    global _TOKEN_CACHE
    _TOKEN_CACHE = None


# ── Candle data (price_history — live 1m prices, updated every minute) ─────────

_PRICE_DB = '/root/.hermes/data/signals_hermes.db'

def get_1m_closes(token: str, lookback: int = 300) -> List[float]:
    """Fetch 1m close prices from price_history (signals_hermes.db), oldest first.
    price_history is updated every minute with live prices — the ONLY reliable source.
    Freshness guard: skip if most recent price is > 5 minutes old.
    """
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        # Freshness check
        c.execute("SELECT MAX(timestamp) FROM price_history WHERE token = ?", (token.upper(),))
        row = c.fetchone()
        if row and row[0] and (time.time() - row[0]) > 120:
            conn.close()
            return []
        # Get most recent lookback prices, oldest-first
        # Must include timestamp in subquery so outer ORDER BY can reference it
        c.execute("""
            SELECT price FROM (
                SELECT timestamp, price
                FROM price_history
                WHERE token = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ) sub
            ORDER BY timestamp ASC
        """, (token.upper(), lookback))
        rows = c.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


# ── MACD computation ──────────────────────────────────────────────────────────

def ema(data: List[float], n: int) -> Optional[List[float]]:
    """
    Compute EMA of data. Seeds with SMA of first n values (consistent with
    ma_fast_signals, ma_cross_signals, ma300_candle_confirm_signals, gap300_signals).

    Produces same-length output as the Wilder-seeded approach so callers that
    do element-wise alignment (compute_histogram) are not broken.
    """
    if data is None or len(data) < n:
        return None
    k = 2.0 / (n + 1)
    # SMA seed — consistent with other signal scripts; then prepend data[0]
    # so the output list has the same length as the Wilder-seeded version.
    sma_seed = sum(data[:n]) / n
    result = [data[0]]       # same length as Wilder seed for caller compatibility
    ema_val = sma_seed
    for v in data[1:]:
        ema_val = v * k + ema_val * (1 - k)
        result.append(ema_val)
    return result


def compute_histogram(closes: List[float], fast: int, slow: int,
                      signal: int) -> Optional[List[float]]:
    """Compute MACD histogram. Returns list of hist values (oldest first)."""
    ef = ema(closes, fast)
    es = ema(closes, slow)
    if ef is None or es is None:
        return None
    n_ml = min(len(ef), len(es))
    ml = [ef[i] - es[i] for i in range(n_ml)]
    if len(ml) < slow:
        return None
    esig = ema(ml, signal)
    if esig is None or len(esig) < signal:
        return None
    n_h = min(len(ml), len(esig))
    return [ml[i] - esig[i] for i in range(n_h)]


# ── Core signal scanner ───────────────────────────────────────────────────────

def scan_macd_1m_signals(prices_dict: dict) -> int:
    """Scan all tokens for MACD 1m crossovers and emit signals.

    Args:
        prices_dict: token -> {'price': float, ...} dict from signal_gen

    Returns:
        Number of signals successfully written to DB.
    """
    params = load_token_params()
    added = 0

    from signal_schema import add_signal, price_age_minutes
    from position_manager import get_open_positions as _get_open_pos

    # Build open-position set so we don't duplicate
    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}

    # Guards (imported lazily to avoid circular dep at module level)
    from signal_gen import (
        recent_trade_exists, is_delisted, SHORT_BLACKLIST,
        MIN_TRADE_INTERVAL_MINUTES, set_cooldown
    )

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        if not data.get('price') or data['price'] <= 0:
            continue
        if token.upper() in open_pos:
            continue
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue
        if is_delisted(token.upper()):
            continue
        if token.upper() in SHORT_BLACKLIST:
            continue
        if price_age_minutes(token) > 10:
            continue

        p = params.get(token.upper(), params['DEFAULT'])
        closes = get_1m_closes(token, lookback=300)
        if len(closes) < 12:  # minimum for any MACD
            continue

        price = data['price']
        fired_short = False
        fired_long  = False

        # ── SHORT ──────────────────────────────────────────────────────────
        try:
            p_short = p['SHORT']
            fs = p_short['fast']; ss = p_short['slow']; sg_s = p_short['signal']
            if len(closes) >= ss + sg_s + 2:
                h_s = compute_histogram(closes, fs, ss, sg_s)
                if h_s and len(h_s) >= 2:
                    i_s = len(h_s) - 1
                    h_prev_s = h_s[i_s - 1]
                    h_cur_s  = h_s[i_s]
                    if h_prev_s >= 0 > h_cur_s:
                        confidence = min(75, max(55, round(p_short['wr'] * 1.20)))
                        source = 'macd-1m-short'
                        sid = add_signal(
                            token=token, direction='SHORT',
                            signal_type='macd_short_1m', source=source,
                            confidence=confidence, value=float(confidence),
                            price=price, exchange='hyperliquid', timeframe='1m',
                            z_score=None, z_score_tier=None)
                        if sid:
                            added += 1
                            set_cooldown(token, 'SHORT', hours=1)
                            fired_short = True
                            print(f'  SHORT-1M {token:8s} conf={confidence:.0f}% [{source}] @{price:.6f}')
        except Exception as e:
            print(f'  [macd_1m] {token} SHORT compute error: {e}')

        # ── LONG ───────────────────────────────────────────────────────────
        # Skip if SHORT already fired this run (avoid conflicting signals in same token)
        if not fired_short:
            try:
                p_long = p['LONG']
                fl = p_long['fast']; sl = p_long['slow']; sg_l = p_long['signal']
                if len(closes) >= sl + sg_l + 2:
                    h_l = compute_histogram(closes, fl, sl, sg_l)
                    if h_l and len(h_l) >= 2:
                        i_l = len(h_l) - 1
                        h_prev_l = h_l[i_l - 1]
                        h_cur_l  = h_l[i_l]
                        if h_prev_l <= 0 < h_cur_l:
                            confidence = min(75, max(55, round(p_long['wr'] * 1.20)))
                            source = 'macd-1m-long'
                            sid = add_signal(
                                token=token, direction='LONG',
                                signal_type='macd_long_1m', source=source,
                                confidence=confidence, value=float(confidence),
                                price=price, exchange='hyperliquid', timeframe='1m',
                                z_score=None, z_score_tier=None)
                            if sid:
                                added += 1
                                set_cooldown(token, 'LONG', hours=1)
                                fired_long = True
                                print(f'  LONG-1M  {token:8s} conf={confidence:.0f}% [{source}] @{price:.6f}')
            except Exception as e:
                print(f'  [macd_1m] {token} LONG compute error: {e}')

    return added


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    # Minimal prices_dict for testing
    test_prices = {
        'BTC': {'price': 95000},
        'ETH': {'price': 3500},
        'BLUR': {'price': 0.35},
        'BADGER': {'price': 2.5},
    }
    print(f"Scanning {len(test_prices)} tokens...")
    n = scan_macd_1m_signals(test_prices)
    print(f"Done. {n} signals emitted.")
