#!/usr/bin/env python3
"""volbreak_cont.py — Volume Breakout Continuation signal (LONG only).

Shadow-data thesis (brain/shadow_trades.db, 17,321 shadow signals, brief
2026-10-24): volume_breakout_short was the single best shadow performer
(14T 100% WR +1.70 avg in EXTREME, 20T 100% WR +1.63 in HIGH). This is the
LONG mirror: volume breakouts in EXTREME volatility REGIME-CONFIRMED by an
EMA300 uptrend and a 3-bar price breakout keep going — the legacy
volume_breakout_long died because it fired in the wrong regimes (NORMAL/HIGH).

LONG fires when ALL of:
  1. Volume > VOLBREAK_CONT_VOL_MULT x 20-bar average (institutional flow)
  2. ATR% > VOLBREAK_CONT_ATR_PCT_MIN (EXTREME regime — volatility_gate_v2)
  3. Close > EMA300 on 5m (uptrend confirmation)
  4. Close > max(HIGH of previous VOLBREAK_CONT_BREAKOUT_BARS bars) (breakout)

No SHORT side — legacy volume_breakout_short is KILLED (2026-10-15) and the
shadow thesis only validated the SHORT habitat for the legacy signal.

SHADOW MODE: VOLBREAK_CONT_ENABLED = False (2026-10-24) — enable after validation.

Architecture: 5m candles → volume spike → ATR regime → EMA300 → breakout
  → add_signal() → signals_hermes_runtime.db → signal_compactor → hotset.json
Source: volbreak-cont+
Family: Volume (EXTREME-only habitat via volatility_gate_v2 REGIME_SIGNALS)
Exit: pm_trail (100% WR +$0.424 EXTREME LONG per shadow data — hermes_constants)
"""

import sys, os, sqlite3
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, price_age_minutes, get_cooldown, set_cooldown
from paths import CANDLES_DB

from hermes_constants import (
    VOLBREAK_CONT_ENABLED,
    VOLBREAK_CONT_PLUS_ENABLED,
    VOLBREAK_CONT_VOL_MULT,
    VOLBREAK_CONT_VOL_AVG_PERIOD,
    VOLBREAK_CONT_ATR_PCT_MIN,
    VOLBREAK_CONT_BREAKOUT_BARS,
    VOLBREAK_CONT_EMA_PERIOD,
    VOLBREAK_CONT_EMA_MIN_CANDLES,
    VOLBREAK_CONT_COOLDOWN_MINUTES,
    VOLBREAK_CONT_MAX_PRICE_AGE_MIN,
    VOLBREAK_CONT_CONF_BASE,
    VOLBREAK_CONT_CONF_FLOOR,
    VOLBREAK_CONT_CONF_CAP,
    VOLBREAK_CONT_CONF_VOL_BONUS,
    LONG_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'volbreak_cont_long'
SOURCE_LONG = 'volbreak-cont+'

_SIGNAL_LOG = '/var/www/hermes/logs/signals.log'


def _log(msg: str) -> None:
    print(f'[volbreak-cont] {msg}', flush=True)
    try:
        with open(_SIGNAL_LOG, 'a') as f:
            f.write(f'[volbreak-cont] {msg}\n')
    except OSError:
        pass


def _get_5m_candles(token: str, limit: int = VOLBREAK_CONT_EMA_MIN_CANDLES) -> list:
    """Fetch closed 5m candles (oldest first): [(ts, open, high, low, close, volume)]."""
    conn = None
    try:
        conn = sqlite3.connect(f'file:{CANDLES_DB}?mode=ro', uri=True, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT ts, open, high, low, close, volume FROM (
                SELECT ts, open, high, low, close, volume
                FROM candles_5m WHERE token = ? AND is_closed = 1
                ORDER BY ts DESC LIMIT ?
            ) sub ORDER BY ts ASC
        """, (token.upper(), limit))
        return c.fetchall()
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _compute_ema(prices: list, period: int) -> Optional[float]:
    """EMA over a chronological price series."""
    if not prices or len(prices) < period:
        return None
    k = 2.0 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return ema


def _evaluate(closes, highs, volumes, atr_pct) -> Optional[dict]:
    """Pure condition check — fails CLOSED on any missing input.

    ATR arrives as a parameter (volatility_gate_v2.get_atr_pct in detect())
    so this function is unit-testable with synthetic data (see __main__ --selftest).
    """
    need = max(VOLBREAK_CONT_EMA_MIN_CANDLES, VOLBREAK_CONT_BREAKOUT_BARS + 1)
    if len(closes) < need or len(highs) < need or len(volumes) < VOLBREAK_CONT_VOL_AVG_PERIOD + 1:
        return None

    # Condition 1: volume spike — last bar vs 20-bar average (excludes current bar)
    vol_avg = sum(volumes[-(VOLBREAK_CONT_VOL_AVG_PERIOD + 1):-1]) / VOLBREAK_CONT_VOL_AVG_PERIOD
    if vol_avg <= 0:
        return None
    vol_ratio = volumes[-1] / vol_avg
    if vol_ratio < VOLBREAK_CONT_VOL_MULT:
        return None

    # Condition 2: EXTREME volatility (ATR% above the EXTREME regime floor)
    if atr_pct is None or atr_pct < VOLBREAK_CONT_ATR_PCT_MIN:
        return None

    price = closes[-1]
    if price <= 0:
        return None

    # Condition 3: uptrend confirmation vs EMA300 (5m)
    ema = _compute_ema(closes, VOLBREAK_CONT_EMA_PERIOD)
    if ema is None or ema <= 0 or price <= ema:
        return None

    # Condition 4: breakout — close above the HIGH of the previous N bars
    prev_high = max(highs[-(VOLBREAK_CONT_BREAKOUT_BARS + 1):-1])
    if price <= prev_high:
        return None

    # Confidence — ranking only (not an edge)
    confidence = VOLBREAK_CONT_CONF_BASE
    if vol_ratio >= 2 * VOLBREAK_CONT_VOL_MULT:
        confidence += VOLBREAK_CONT_CONF_VOL_BONUS
    confidence = max(VOLBREAK_CONT_CONF_FLOOR, min(VOLBREAK_CONT_CONF_CAP, confidence))

    return {
        'direction': 'LONG',
        'confidence': confidence,
        'value': round(vol_ratio, 2),
        'price': price,
        'atr_pct': round(atr_pct, 3),
    }


def detect(token: str) -> Optional[dict]:
    """Detect volbreak_cont for a token. Returns dict or None. Fails closed."""
    candles = _get_5m_candles(token)
    if not candles:
        return None
    closes = [r[4] for r in candles]
    highs = [r[2] for r in candles]
    volumes = [r[5] for r in candles]

    from volatility_gate_v2 import get_atr_pct
    atr_pct = get_atr_pct(token)

    return _evaluate(closes, highs, volumes, atr_pct)


def run(prices_dict=None) -> int:
    """Entry point for signals_runner."""
    if not VOLBREAK_CONT_ENABLED or not VOLBREAK_CONT_PLUS_ENABLED:
        return 0

    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()

    from position_manager import get_open_positions
    open_pos = {p['token']: p['direction'] for p in get_open_positions()}

    added = 0
    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        price = data.get('price') if isinstance(data, dict) else None
        if not price or price <= 0:
            continue
        if token.upper() in open_pos:
            continue
        if price_age_minutes(token) > VOLBREAK_CONT_MAX_PRICE_AGE_MIN:
            continue
        if token.upper() in LONG_BLACKLIST:
            continue
        if get_cooldown(token, direction='LONG'):
            continue

        sig = detect(token)
        if not sig:
            continue

        try:
            sid = add_signal(
                token=token.upper(),
                direction='LONG',
                signal_type=SIGNAL_TYPE_LONG,
                source=SOURCE_LONG,
                confidence=sig['confidence'],
                value=sig['value'],
                price=sig['price'],
                exchange='hyperliquid',
                timeframe='5m',
            )
        except Exception as e:
            _log(f'add_signal error {token}: {e}')
            continue

        if sid:
            added += 1
            set_cooldown(token, 'LONG', hours=VOLBREAK_CONT_COOLDOWN_MINUTES / 60.0)
            _log(f'LONG {token:8s} conf={sig["confidence"]}% atr={sig["atr_pct"]}% '
                 f'vol={sig["value"]}x price={sig["price"]:.8g} [{SOURCE_LONG}]')

    return added


# ── Self-test (synthetic data — verifies the conditions fire) ─────────────────

def _selftest() -> bool:
    ok = True

    def check(name, cond):
        nonlocal ok
        status = 'PASS' if cond else 'FAIL'
        if not cond:
            ok = False
        print(f'  [{status}] {name}')

    n = VOLBREAK_CONT_EMA_MIN_CANDLES
    # Uptrend 90 → 100, last bar breaks above prior-3-bar high with a volume spike
    closes = [90.0 + 10.0 * i / (n - 1) for i in range(n)]
    highs = [c + 0.1 for c in closes]
    closes[-1] = highs[-2] + 0.5          # close > max(high of prev 3 bars)
    highs[-1] = closes[-1] + 0.1
    vols = [100.0] * (n - 1) + [250.0]    # 2.5x spike

    r = _evaluate(closes, highs, vols, 2.0)
    check('FIRE: vol 2.5x, atr=2.0, above EMA300, 3-bar breakout',
          r is not None and r['direction'] == 'LONG')

    # Blocked: no volume spike (1x)
    r = _evaluate(closes, highs, [100.0] * n, 2.0)
    check('BLOCKED: volume 1.0x < 2.0x', r is None)

    # Blocked: ATR below EXTREME floor
    r = _evaluate(closes, highs, vols, 1.2)
    check('BLOCKED: atr=1.2 < 1.5 floor', r is None)

    # Blocked: ATR missing (fail-closed)
    r = _evaluate(closes, highs, vols, None)
    check('BLOCKED: atr missing (fail-closed)', r is None)

    # Blocked: close not above prev-3-bar high
    flat_closes = list(closes)
    flat_closes[-1] = flat_closes[-2]     # no breakout
    r = _evaluate(flat_closes, highs, vols, 2.0)
    check('BLOCKED: close not above prev 3-bar high', r is None)

    # Blocked: below EMA300 (downtrend). EMA300 of this declining series ends at
    # ~93.87; a 92.0 close still breaks the prior-3-bar high (~90.19) but is
    # below EMA300, so the trend-confirmation condition must block it.
    down_closes = [100.0 - 10.0 * i / (n - 1) for i in range(n)]
    down_highs = [c + 0.1 for c in down_closes]
    down_closes[-1] = 92.0                # above prev highs, but below EMA300
    down_highs[-1] = 92.1
    r = _evaluate(down_closes, down_highs, vols, 2.0)
    check('BLOCKED: price below EMA300 (downtrend)', r is None)

    # Blocked: insufficient candles
    r = _evaluate(closes[:100], highs[:100], vols[:100], 2.0)
    check('BLOCKED: <350 candles (EMA warmup)', r is None)

    # Confidence within floor/cap
    r = _evaluate(closes, highs, vols, 2.0)
    check('confidence within [floor, cap]',
          r is not None and VOLBREAK_CONT_CONF_FLOOR <= r['confidence'] <= VOLBREAK_CONT_CONF_CAP)

    print('SELFTEST', 'OK' if ok else 'FAILED')
    return ok


def _dry_scan() -> int:
    """Scan all tokens with 5m data and report matches — ignores ENABLED flags,
    never writes signals. For validation before enabling."""
    conn = None
    try:
        conn = sqlite3.connect(f'file:{CANDLES_DB}?mode=ro', uri=True, timeout=10)
        tokens = [r[0] for r in conn.execute(
            "SELECT DISTINCT token FROM candles_5m WHERE is_closed=1").fetchall()]
    except Exception as e:
        print(f'[volbreak-cont] dry scan error: {e}')
        return 0
    finally:
        if conn:
            conn.close()

    hits = 0
    for token in tokens:
        sig = detect(token)
        if sig:
            hits += 1
            print(f"  DRY LONG {token:8s} conf={sig['confidence']} "
                  f"atr={sig['atr_pct']}% vol={sig['value']}x price={sig['price']:.8g}")
    print(f'[volbreak-cont] dry scan: {hits} matches across {len(tokens)} tokens')
    return hits


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Volume Breakout Continuation signal (LONG)')
    parser.add_argument('--selftest', action='store_true', help='Run synthetic-data condition tests')
    parser.add_argument('--dry', action='store_true', help='Live scan, no writes, ignores ENABLED flags')
    args = parser.parse_args()

    if args.selftest:
        sys.exit(0 if _selftest() else 1)
    elif args.dry:
        _dry_scan()
    else:
        print(f'Added {run()} signals')
