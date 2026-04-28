#!/usr/bin/env python3
"""
gap300_5m_signals.py — EMA(300) gap signal on 5m candles only.

Uses candles_5m from candles.db for both the price series AND EMA300
computation. No 1m data. EMA300 on 5m means 300 × 5min = 1500 min lookback.

Signal logic (LONG):
  1. price_5m > EMA300  (price above 5m EMA300)
  2. gap_pct = (price - EMA300) / EMA300 * 100 > MIN_GAP_PCT (0.10%)
  3. gap_now > gap_3bars_ago + MIN_GAP_GROWTH (0.05%)  ← ACCELERATION condition
  4. trend_purity: at least TREND_PURITY fraction of RECENT_BARS bars must have
     gap > avg_gap  ← ensures the gap is widening, not just a stable elevated gap
"""

import sys, os, sqlite3, time, datetime
from typing import Optional, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, price_age_minutes
from position_manager import is_position_open

# ── Paths ─────────────────────────────────────────────────────────────────────
_RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'
_PRICE_DB   = '/root/.hermes/data/signals_hermes.db'
_CANDLE_DB  = '/root/.hermes/data/candles.db'

# ── Signal constants ──────────────────────────────────────────────────────────
MIN_GAP_PCT      = 0.10    # minimum gap % to fire
MIN_GAP_GROWTH   = 0.05    # gap must grow by this much vs 3 bars ago
RECENT_BARS      = 15      # 15 × 5m = 75min — lookback for trend_strength
TREND_PURITY     = 0.55    # fraction of recent bars that must be above their own rolling avg
ACCEL_THRESH     = 0.30   # % gap must widen by vs rolling_avg to bypass purity check
PERSISTENT_BARS  = 3       # price must stay above EMA300 for this many 5m bars
LOOKBACK_5M      = 400     # 5m bars for EMA300 warmup + gap detection (~33h)
COOLDOWN_MINUTES = 10
SIGNAL_TYPE_LONG  = 'gap300_5m_long'
SIGNAL_TYPE_SHORT = 'gap300_5m_short'
SOURCE_LONG       = 'gap300-5m+'
SOURCE_SHORT      = 'gap300-5m-'


# ═══════════════════════════════════════════════════════════════════════════════
# EMA helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _ema300_5m(closes_5m: list) -> list:
    """Compute EMA300 on a 5m close series. Returns same-length list with
    None for indices < 299 (need 300 warmup bars for seed)."""
    if len(closes_5m) < 300:
        return [None] * len(closes_5m)
    k = 2.0 / 301
    ema = sum(closes_5m[:300]) / 300
    result = [None] * 299
    result.append(ema)
    for price in closes_5m[300:]:
        ema = price * k + ema * (1 - k)
        result.append(ema)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetch
# ═══════════════════════════════════════════════════════════════════════════════

def _get_5m_candles(token: str, lookback: int = LOOKBACK_5M) -> list:
    """Fetch 5m close prices from candles.db, MOST RECENT first, then reverse.
    Returns list of {timestamp, price} dicts (oldest first)."""
    try:
        conn = sqlite3.connect(_CANDLE_DB, timeout=10)
        c = conn.cursor()
        c.execute('''
            SELECT close, ts FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        ''', (token, lookback))
        rows = c.fetchall()
        conn.close()
        return [{'timestamp': r[1], 'price': r[0]} for r in reversed(rows)]
    except Exception as e:
        print(f'[_get_5m_candles] {token}: {e}')
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# Signal detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_gap300_5m(token: str, direction: str = 'LONG') -> Optional[dict]:
    """Detect gap300_5m LONG or SHORT signal on 5m candles only.

    Returns dict with signal fields if triggered, None otherwise.
    """
    bars_5m = _get_5m_candles(token, LOOKBACK_5M)

    if len(bars_5m) < 300 + PERSISTENT_BARS + 1:
        return None

    # Compute EMA300 directly on 5m closes
    closes_5m = [b['price'] for b in bars_5m]
    ema300_5m = _ema300_5m(closes_5m)

    # Most recent 5m bar (last in list = most recent)
    i = len(bars_5m) - 1
    bar = bars_5m[i]
    bar_ts = bar['timestamp']
    price = bar['price']

    # EMA300 value: ema300_5m[i] aligns with bars_5m[i]
    ema_val = ema300_5m[i]
    if ema_val is None:
        return None

    gap_pct = (price - ema_val) / ema_val * 100

    # Direction check
    if direction == 'LONG' and gap_pct <= MIN_GAP_PCT:
        return None
    if direction == 'SHORT' and gap_pct >= -MIN_GAP_PCT:
        return None

    # Check gap 3 bars ago
    gap_3ago = None
    if len(bars_5m) >= 4:
        ema_val3 = ema300_5m[i - 3]
        if ema_val3 is not None and ema_val3 != 0:
            gap_3ago = (bars_5m[i - 3]['price'] - ema_val3) / ema_val3 * 100

    # Acceleration: gap must be growing
    if gap_3ago is not None and gap_pct <= gap_3ago + MIN_GAP_GROWTH:
        return None

    # Persistence: need PERSISTENT_BARS consecutive bars above threshold (excluding latest)
    for k in range(1, PERSISTENT_BARS + 1):
        idx = i - k
        ema_k = ema300_5m[idx]
        if ema_k is None or ema_k == 0:
            return None
        gap_k = (bars_5m[idx]['price'] - ema_k) / ema_k * 100
        if direction == 'LONG' and gap_k <= MIN_GAP_PCT:
            return None
        if direction == 'SHORT' and gap_k >= -MIN_GAP_PCT:
            return None

    # Trend strength: gap must be accelerating relative to recent history.
    # Two paths to pass:
    #   (A) gap > avg_recent_gap + ACCEL_THRESH  ← strong acceleration, bypass purity
    #   (B) purity >= TREND_PURITY  ← consistent strength over the window
    recent_gaps = []
    for k in range(1, min(RECENT_BARS, i) + 1):
        idx = i - k
        if idx < 0:
            break
        ema_k = ema300_5m[idx]
        if ema_k is not None and ema_k != 0:
            recent_gaps.append((bars_5m[idx]['price'] - ema_k) / ema_k * 100)

    if len(recent_gaps) < 10:
        return None  # not enough history

    avg_gap = sum(recent_gaps) / len(recent_gaps)
    above_avg = sum(1 for g in recent_gaps if g > avg_gap)
    purity = above_avg / len(recent_gaps)

    # Path A: strong acceleration
    path_a = (gap_pct - avg_gap) > ACCEL_THRESH
    # Path B: consistent strength
    path_b = purity >= TREND_PURITY

    if not path_a and not path_b:
        return None

    # Signal quality: confidence based on gap strength + growth
    gap_growth = (gap_pct - gap_3ago) if gap_3ago is not None else 0
    base_conf = 65 + min(15, max(0, (abs(gap_pct) - MIN_GAP_PCT) * 80))
    growth_bonus = min(10, max(0, (abs(gap_growth) - MIN_GAP_GROWTH) * 100)) if gap_growth else 0
    confidence = min(80, max(60, int(base_conf + growth_bonus)))

    return {
        'token': token,
        'direction': direction,
        'signal_type': SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT,
        'source': SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT,
        'confidence': confidence,
        'gap_pct': round(gap_pct, 4),
        'gap_growth': round(gap_growth, 4) if gap_growth else 0,
        'price': price,
        'bar_ts': bar_ts,
        'ema300': ema_val,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_gap300_5m_signals(prices_dict: dict) -> int:
    """Scan tokens for gap300_5m signals.

    prices_dict: token -> {price, ts} (from signal_gen main loop)
    Returns count of signals emitted.
    """
    try:
        # Get active tokens from latest_prices (signals_hermes.db)
        # NOT from signals_hermes_runtime.db which has no tokens table
        conn_price = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn_price.cursor()
        c.execute("SELECT DISTINCT token FROM latest_prices")
        all_tokens = [r[0] for r in c.fetchall()]
        conn_price.close()
    except Exception as e:
        print(f'[gap300_5m] Failed to load tokens: {e}')
        return 0

    added = 0
    for token in all_tokens:
        for direction in ['LONG', 'SHORT']:
            sig = detect_gap300_5m(token, direction)
            if not sig:
                continue

            # Skip tokens with no recent price
            price_info = prices_dict.get(token)
            if not price_info:
                continue

            # Skip if price is too old
            if price_age_minutes(token) > 5:
                continue

            # Blacklist checks
            if direction == 'LONG':
                try:
                    c2 = sqlite3.connect(_RUNTIME_DB, timeout=5).cursor()
                    c2.execute("SELECT 1 FROM blacklist WHERE token=? AND type='LONG'", (token,))
                    if c2.fetchone():
                        continue
                except Exception:
                    pass
            if direction == 'SHORT':
                try:
                    c2 = sqlite3.connect(_RUNTIME_DB, timeout=5).cursor()
                    c2.execute("SELECT 1 FROM blacklist WHERE token=? AND type='SHORT'", (token,))
                    if c2.fetchone():
                        continue
                except Exception:
                    pass

            # Cooldown: recent_trade_exists check
            try:
                conn_rt = sqlite3.connect(_RUNTIME_DB, timeout=10)
                c_rt = conn_rt.cursor()
                c_rt.execute('''
                    SELECT 1 FROM signals
                    WHERE token = ?
                      AND source = ?
                      AND created_at > datetime('now', '-{} minutes')
                    LIMIT 1
                '''.format(COOLDOWN_MINUTES), (token, sig['source']))
                if c_rt.fetchone():
                    conn_rt.close()
                    continue
                conn_rt.close()
            except Exception:
                pass

            # Check open position
            if is_position_open(token):
                continue

            sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
            source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

            combo_key = f'{token}:{direction}:{source}'

            try:
                from signal_schema import add_signal
                add_signal(
                    token=token,
                    signal_type=sig_type,
                    direction=direction,
                    source=source,
                    confidence=sig['confidence'],
                    price=sig['price'],
                    combo_key=combo_key,
                )
                added += 1
            except Exception as e:
                print(f'[gap300_5m] add_signal error {token}: {e}')

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# CLI / dry-run
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='gap300_5m signal scanner')
    parser.add_argument('--dry', action='store_true', help='dry run — log but dont write signals')
    parser.add_argument('--tokens', type=str, default='SNX,BTC,ETH,SOL,LINK,AVAX,AAVE',
                        help='comma-separated tokens to scan')
    args = parser.parse_args()

    dry = args.dry
    tokens = args.tokens.split(',')

    # When dry-run via CLI, patch add_signal to no-op
    if dry:
        import signal_schema
        _orig_add_signal = signal_schema.add_signal
        signal_schema.add_signal = lambda **kw: print(f"  [DRY] add_signal blocked: {kw}")

    print(f'[gap300_5m] Dry={dry} | Tokens: {tokens}')

    for token in tokens:
        for direction in ['LONG', 'SHORT']:
            sig = detect_gap300_5m(token, direction)
            if sig:
                print(f'  [DRY] {token} {direction} conf={sig["confidence"]} '
                      f'gap={sig["gap_pct"]:.3f}% growth={sig["gap_growth"]:.3f}% '
                      f'price={sig["price"]:.4f} bar_ts={sig["bar_ts"]}')
            else:
                print(f'  {token} {direction}: no gap300_5m signal')
