#!/usr/bin/env python3
"""
btc_pump_rider.py — Ride the BTC Pump to Alts.

When BTC breaks resistance with volume, alts follow within 1-5 minutes.
This signal detects the BTC breakout and fires LONG on correlated alts
that haven't moved yet (catching the lag).

Detection:
  1. BTC broke above 1h high (resistance break)
  2. BTC 1m volume spike (confirmation of breakout)
  3. BTC velocity positive and accelerating
  4. Alt has NOT yet moved (still near pre-pump price)
  5. Alt is correlated with BTC (high beta)

Signal types:
  - btc_pump_rider_long : LONG alt that will follow BTC pump

Architecture:
  BTC 1m candles → breakout detection → alt correlation scan
  → add_signal() → signals_hermes_runtime.db → signal_compactor → hotset.json

Pipeline: runs as a fast signal (every minute) via signals_runner.
"""

import os
import sys
import time
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, price_age_minutes, get_cooldown, set_cooldown
from paths import HERMES_DATA

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
_SIGNAL_LOG = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(_SIGNAL_LOG), exist_ok=True)

# ── Parameters ────────────────────────────────────────────────────────────────
from hermes_constants import (
    LONG_BLACKLIST,
    BTC_PUMP_RIDER_ENABLED,
    BTC_PUMP_RIDER_BREAKOUT_VOL_MULT,
    BTC_PUMP_RIDER_BREAKOUT_VOL_WINDOW,
    BTC_PUMP_RIDER_BREAKOUT_VEL_MIN,
    BTC_PUMP_RIDER_BREAKOUT_FOLLOWUP,
    BTC_PUMP_RIDER_ALT_MAX_LAG_PCT,
    BTC_PUMP_RIDER_ALT_MIN_BETA,
    BTC_PUMP_RIDER_ALT_RSI_MAX,
    BTC_PUMP_RIDER_ALT_RSI_MIN,
    BTC_PUMP_RIDER_ALT_VOLUME_MIN,
    BTC_PUMP_RIDER_CONF_BASE,
    BTC_PUMP_RIDER_CONF_VOLUME_BOOST,
    BTC_PUMP_RIDER_CONF_CAP,
    BTC_PUMP_RIDER_CONF_BETA_BOOST,
    BTC_PUMP_RIDER_COOLDOWN_MINUTES,
)

SIGNAL_TYPE_LONG = 'btc_pump_rider_long'
SOURCE_LONG = 'btc-pump-rider+'


def _log(msg: str) -> None:
    print(msg)
    try:
        with open(_SIGNAL_LOG, 'a') as f:
            f.write(msg + '\n')
    except Exception:
        pass


def _get_candles(token: str, table: str = 'candles_1m', limit: int = 30) -> list:
    """Fetch OHLCV candles. Returns list of (ts, open, high, low, close, volume) oldest-first."""
    valid = {'candles_1m', 'candles_5m', 'candles_15m', 'candles_1h'}
    if table not in valid:
        table = 'candles_1m'
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT ts, open, high, low, close, volume
            FROM {table}
            WHERE token = ?
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), limit))
        rows = cur.fetchall()
        rows.reverse()  # oldest-first
        return rows
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _compute_rsi(closes: list, period: int = 14) -> float:
    """Compute RSI from close prices."""
    if len(closes) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(closes)):
        chg = closes[i] - closes[i-1]
        gains.append(max(0, chg))
        losses.append(max(0, -chg))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def detect_btc_breakout() -> dict | None:
    """
    Detect if BTC just broke above resistance with volume.
    Returns breakout info dict or None.
    """
    btc_candles = _get_candles('BTC', 'candles_1m', 60)
    if len(btc_candles) < 25:
        return None

    # Current candle (should be closed or nearly closed)
    curr = btc_candles[-1]
    curr_ts, curr_open, curr_high, curr_low, curr_close, curr_vol = curr

    # Find 1h high (last 60 candles = 1 hour)
    lookback = btc_candles[-60:] if len(btc_candles) >= 60 else btc_candles[:-1]
    prev_high = max(c[2] for c in lookback[:-1])  # high of all candles except current

    # Check: did current candle break above 1h high? (close must confirm, not just wick)
    if curr_high <= prev_high or curr_close <= prev_high:
        return None  # no breakout

    # Volume spike check
    vol_window = btc_candles[-(BTC_PUMP_RIDER_BREAKOUT_VOL_WINDOW + 1):-1]
    avg_vol = sum(c[5] for c in vol_window) / len(vol_window) if vol_window else 0
    if avg_vol <= 0:
        return None
    vol_ratio = curr_vol / avg_vol

    if vol_ratio < BTC_PUMP_RIDER_BREAKOUT_VOL_MULT:
        return None  # volume not strong enough

    # Price velocity check
    velocity = (curr_close - curr_open) / curr_open * 100 if curr_open > 0 else 0
    if velocity < BTC_PUMP_RIDER_BREAKOUT_VEL_MIN:
        return None  # not enough price movement

    # Follow-through: check if last N candles are also up
    followup_candles = btc_candles[-(BTC_PUMP_RIDER_BREAKOUT_FOLLOWUP + 1):-1]
    followup_up = sum(1 for c in followup_candles if c[4] > c[1])
    if followup_up < BTC_PUMP_RIDER_BREAKOUT_FOLLOWUP:
        return None  # no follow-through yet

    # BTC velocity (5-candle momentum)
    if len(btc_candles) >= 6:
        btc_vel_5m = (btc_candles[-1][4] - btc_candles[-6][4]) / btc_candles[-6][4] * 100
    else:
        btc_vel_5m = velocity

    return {
        'btc_price': curr_close,
        'btc_velocity': velocity,
        'btc_vol_ratio': vol_ratio,
        'btc_1h_high': prev_high,
        'btc_break_pct': (curr_close - prev_high) / prev_high * 100,
        'btc_vel_5m': btc_vel_5m,
    }


def compute_alt_beta(token: str, btc_closes: list, alt_closes: list) -> float:
    """Compute correlation (beta) between alt and BTC. Returns 0-1."""
    if len(btc_closes) < 10 or len(alt_closes) < 10:
        return 0.0

    n = min(len(btc_closes), len(alt_closes))
    btc = btc_closes[-n:]
    alt = alt_closes[-n:]

    # Normalize to % changes
    btc_chg = [(btc[i] - btc[i-1]) / btc[i-1] * 100 for i in range(1, n) if btc[i-1] > 0]
    alt_chg = [(alt[i] - alt[i-1]) / alt[i-1] * 100 for i in range(1, n) if alt[i-1] > 0]

    if len(btc_chg) < 5 or len(alt_chg) < 5:
        return 0.0

    m = min(len(btc_chg), len(alt_chg))
    btc_r = btc_chg[-m:]
    alt_r = alt_chg[-m:]

    # Pearson correlation
    btc_mean = sum(btc_r) / m
    alt_mean = sum(alt_r) / m

    cov = sum((b - btc_mean) * (a - alt_mean) for b, a in zip(btc_r, alt_r)) / m
    btc_std = (sum((b - btc_mean)**2 for b in btc_r) / m) ** 0.5
    alt_std = (sum((a - alt_mean)**2 for a in alt_r) / m) ** 0.5

    if btc_std == 0 or alt_std == 0:
        return 0.0

    corr = cov / (btc_std * alt_std)
    return max(0, corr)  # only care about positive correlation


def find_lagging_alts(btc_info: dict) -> list:
    """
    Find altcoins that haven't moved yet but are correlated with BTC.
    These are the ones that will follow the pump.
    """
    # Get list of tradeable tokens from candles DB
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT token FROM candles_1m
            WHERE token != 'BTC' AND token != 'USDT'
            ORDER BY token
        """)
        tokens = [r[0] for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()

    # Get BTC 1m closes for beta calculation (200 candles = 3.3 hours for meaningful correlation)
    btc_candles = _get_candles('BTC', 'candles_1m', 200)
    btc_closes = [c[4] for c in btc_candles]

    candidates = []
    for token in tokens:
        if token in LONG_BLACKLIST:
            continue

        # Skip if in cooldown
        cd = get_cooldown(token, 'btc_pump_rider')
        if cd and time.time() - cd < BTC_PUMP_RIDER_COOLDOWN_MINUTES * 60:
            continue

        # Get alt candles
        alt_candles = _get_candles(token, 'candles_1m', 30)
        if len(alt_candles) < 10:
            continue

        # Check volume minimum
        if alt_candles[-1][5] < BTC_PUMP_RIDER_ALT_VOLUME_MIN:
            continue

        # Check if alt hasn't moved yet (price near where it was 5 min ago)
        if len(alt_candles) >= 6:
            price_now = alt_candles[-1][4]
            price_5m_ago = alt_candles[-6][4]
            if price_5m_ago > 0:
                lag_pct = abs((price_now - price_5m_ago) / price_5m_ago * 100)
                if lag_pct > BTC_PUMP_RIDER_ALT_MAX_LAG_PCT:
                    continue  # alt already moved, too late

        # Compute beta
        alt_closes = [c[4] for c in alt_candles]
        beta = compute_alt_beta(token, btc_closes, alt_closes)
        if beta < BTC_PUMP_RIDER_ALT_MIN_BETA:
            continue

        # RSI filter
        rsi = _compute_rsi(alt_closes)
        if rsi > BTC_PUMP_RIDER_ALT_RSI_MAX or rsi < BTC_PUMP_RIDER_ALT_RSI_MIN:
            continue

        # Price age check
        age = price_age_minutes(token)
        if age is not None and age > 5:
            continue  # price data too stale

        candidates.append({
            'token': token,
            'price': alt_candles[-1][4],
            'beta': beta,
            'rsi': rsi,
            'volume': alt_candles[-1][5],
            'lag_pct': lag_pct if len(alt_candles) >= 6 else 0,
        })

    # Sort by beta (highest correlation first)
    candidates.sort(key=lambda x: -x['beta'])
    return candidates[:5]  # top 5 (limit concentrated risk)


def fire_signal(token: str, price: float, btc_info: dict, beta: float, rsi: float) -> bool:
    """Fire a btc_pump_rider_long signal."""
    # Compute confidence
    conf = BTC_PUMP_RIDER_CONF_BASE
    conf += min(10, int((btc_info['btc_vol_ratio'] - BTC_PUMP_RIDER_BREAKOUT_VOL_MULT) * BTC_PUMP_RIDER_CONF_VOLUME_BOOST))
    conf += min(6, int((beta - BTC_PUMP_RIDER_ALT_MIN_BETA) * 10 * BTC_PUMP_RIDER_CONF_BETA_BOOST))
    conf = min(BTC_PUMP_RIDER_CONF_CAP, conf)

    # Add signal
    ok = add_signal(
        token=token,
        direction='LONG',
        signal_type=SIGNAL_TYPE_LONG,
        source=SOURCE_LONG,
        confidence=conf,
        value=beta,
        price=price,
        exchange='hyperliquid',
        timeframe='1m',
    )

    if ok:
        _log(f"  🔥 [BTC-PUMP-RIDER] {token} LONG conf={conf} beta={beta:.2f} "
             f"rsi={rsi:.1f} btc_vel={btc_info['btc_velocity']:+.3f}% "
             f"btc_vol={btc_info['btc_vol_ratio']:.1f}x")
        set_cooldown(token, 'btc_pump_rider', BTC_PUMP_RIDER_COOLDOWN_MINUTES * 60)
        return True

    return False


def run() -> int:
    """
    Main entry point. Returns number of signals fired.
    Called by signals_runner every minute.
    """
    from hermes_constants import BTC_PUMP_RIDER_ENABLED
    if not BTC_PUMP_RIDER_ENABLED:
        return 0

    # Step 1: Detect BTC breakout
    btc_info = detect_btc_breakout()
    if btc_info is None:
        return 0

    _log(f"  ⚡ [BTC-PUMP-RIDER] BTC breakout detected: ${btc_info['btc_price']:,.1f} "
         f"(+{btc_info['btc_break_pct']:.3f}% above 1h high) "
         f"vel={btc_info['btc_velocity']:+.3f}% vol={btc_info['btc_vol_ratio']:.1f}x")

    # Step 2: Find lagging alts
    alts = find_lagging_alts(btc_info)
    if not alts:
        _log(f"  ⚠️ [BTC-PUMP-RIDER] No lagging alts found")
        return 0

    # Step 3: Fire signals
    fired = 0
    for alt in alts:
        if fire_signal(alt['token'], alt['price'], btc_info, alt['beta'], alt['rsi']):
            fired += 1

    _log(f"  ✅ [BTC-PUMP-RIDER] Fired {fired} signals from {len(alts)} candidates")
    return fired


if __name__ == '__main__':
    print("=== BTC Pump Rider — Diagnostic ===\n")

    btc_info = detect_btc_breakout()
    if btc_info:
        print(f"BTC Breakout Detected!")
        print(f"  Price: ${btc_info['btc_price']:,.1f}")
        print(f"  Above 1h high by: +{btc_info['btc_break_pct']:.3f}%")
        print(f"  Velocity: {btc_info['btc_velocity']:+.3f}%")
        print(f"  Volume: {btc_info['btc_vol_ratio']:.1f}x average")
        print(f"  5m velocity: {btc_info['btc_vel_5m']:+.3f}%")

        print(f"\nScanning for lagging alts...")
        alts = find_lagging_alts(btc_info)
        if alts:
            print(f"Found {len(alts)} candidates:")
            for a in alts:
                print(f"  {a['token']:8} price=${a['price']:.6f} beta={a['beta']:.2f} rsi={a['rsi']:.1f} vol={a['volume']:.0f}")
        else:
            print("No lagging alts found")
    else:
        print("No BTC breakout detected")

        # Show current BTC state
        btc = _get_candles('BTC', 'candles_1m', 60)
        if btc:
            curr = btc[-1]
            prev_high = max(c[2] for c in btc[:-1])
            vol_avg = sum(c[5] for c in btc[-21:-1]) / 20
            print(f"\nCurrent BTC: ${curr[4]:,.1f}")
            print(f"  1h high: ${prev_high:,.1f} (need to break above)")
            print(f"  Distance: {(curr[4] - prev_high) / prev_high * 100:+.3f}%")
            print(f"  Volume: {curr[5]:.0f} (avg: {vol_avg:.0f}, need {vol_avg * BTC_PUMP_RIDER_BREAKOUT_VOL_MULT:.0f})")
