#!/usr/bin/env python3
"""vol_momentum.py — Volatility Momentum continuation signal (both directions).

Shadow-data thesis (brain/shadow_trades.db, 17,321 shadow signals, brief
2026-10-24): in EXTREME volatility, entries with positive expectancy are
CONTINUATION entries, not mean-reversion:
  SHORT: oversold (RSI<35) + falling momentum BELOW EMA300 in a storm keeps dumping
  LONG : overbought (RSI>70) + rising momentum ABOVE EMA300 in a storm keeps pumping
Mean-reversion at the extremes (LONG oversold / SHORT overbought) is the losing
pattern this signal deliberately avoids.

LONG fires when ALL of:
  1. ATR% > VOLMOM_ATR_PCT_MIN (EXTREME regime — volatility_gate_v2.get_atr_pct)
  2. 5m RSI(14) > VOLMOM_LONG_RSI_MIN (overbought = momentum, not exhaustion)
  3. Close > EMA300 on 5m (uptrend confirmation)
  4. momentum_state == 'rising' (_enrich_indicators — 5-min velocity > 0)
  5. Last 5m bar volume >= VOLMOM_VOL_MULT x 20-bar avg (volume confirmation)

SHORT mirrors: 5m RSI(14) < VOLMOM_SHORT_RSI_MAX (oversold continuation),
Close < EMA300, momentum_state == 'falling', same volume confirmation.

SHADOW MODE: VOLMOM_ENABLED = False (2026-10-24) — enable after validation.
⚠️ VOLMOM_MINUS (SHORT) collides with the OVERSOLD_SHORT_RSI_MAX=35 knife guard
(BANANA lesson) at execution time — see hermes_constants.py. Enabling the SHORT
side requires an explicit CEO ruling on that guardrail.

Architecture: 5m candles → ATR regime → 5m RSI → EMA300 → momentum → volume
  → add_signal() → signals_hermes_runtime.db → signal_compactor → hotset.json
Source: vol-momentum+ / vol-momentum-
Family: Momentum (EXTREME-only habitat via volatility_gate_v2 REGIME_SIGNALS)
"""

import sys, os, sqlite3
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, price_age_minutes, get_cooldown, set_cooldown, _enrich_indicators
from paths import CANDLES_DB

from hermes_constants import (
    VOLMOM_ENABLED,
    VOLMOM_PLUS_ENABLED,
    VOLMOM_MINUS_ENABLED,
    VOLMOM_ATR_PCT_MIN,
    VOLMOM_SHORT_RSI_MAX,
    VOLMOM_LONG_RSI_MIN,
    VOLMOM_EMA_PERIOD,
    VOLMOM_EMA_MIN_CANDLES,
    VOLMOM_VOL_MULT,
    VOLMOM_VOL_AVG_PERIOD,
    VOLMOM_COOLDOWN_MINUTES,
    VOLMOM_MAX_PRICE_AGE_MIN,
    VOLMOM_CONF_BASE,
    VOLMOM_CONF_FLOOR,
    VOLMOM_CONF_CAP,
    VOLMOM_CONF_EXTREME_BONUS,
    VOLMOM_CONF_RSI_BONUS,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'vol_momentum_long'
SIGNAL_TYPE_SHORT = 'vol_momentum_short'
SOURCE_LONG = 'vol-momentum+'
SOURCE_SHORT = 'vol-momentum-'

_SIGNAL_LOG = '/var/www/hermes/logs/signals.log'


def _log(msg: str) -> None:
    print(f'[vol-momentum] {msg}', flush=True)
    try:
        with open(_SIGNAL_LOG, 'a') as f:
            f.write(f'[vol-momentum] {msg}\n')
    except OSError:
        pass


def _get_5m_candles(token: str, limit: int = VOLMOM_EMA_MIN_CANDLES) -> list:
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


def _evaluate(closes, volumes, atr_pct, rsi_5m, momentum_state) -> Optional[dict]:
    """Pure condition check — fails CLOSED on any missing input.

    RSI/ATR/momentum arrive as parameters (computed by rsi_utils /
    volatility_gate_v2 / _enrich_indicators in detect()) so this function is
    unit-testable with synthetic data (see __main__ --selftest).
    """
    if len(closes) < VOLMOM_EMA_MIN_CANDLES or len(volumes) < VOLMOM_VOL_AVG_PERIOD + 1:
        return None
    # Condition 1: EXTREME volatility (ATR% above the EXTREME regime floor)
    if atr_pct is None or atr_pct < VOLMOM_ATR_PCT_MIN:
        return None
    # Condition 2 (per direction): RSI extreme — oversold SHORT / overbought LONG
    if rsi_5m is None:
        return None
    # Condition 3 (per direction): momentum state must be directional (not flat/missing)
    if momentum_state not in ('rising', 'falling'):
        return None

    price = closes[-1]
    if price <= 0:
        return None

    # Condition 4: trend confirmation vs EMA300 (5m)
    ema = _compute_ema(closes, VOLMOM_EMA_PERIOD)
    if ema is None or ema <= 0:
        return None

    # Condition 5: volume confirmation — last bar vs 20-bar average (excludes current bar)
    vol_avg = sum(volumes[-(VOLMOM_VOL_AVG_PERIOD + 1):-1]) / VOLMOM_VOL_AVG_PERIOD
    if vol_avg <= 0:
        return None
    vol_ratio = volumes[-1] / vol_avg
    if vol_ratio < VOLMOM_VOL_MULT:
        return None

    direction = None
    if rsi_5m < VOLMOM_SHORT_RSI_MAX and price < ema and momentum_state == 'falling':
        direction = 'SHORT'
    elif rsi_5m > VOLMOM_LONG_RSI_MIN and price > ema and momentum_state == 'rising':
        direction = 'LONG'
    if direction is None:
        return None

    # Confidence — ranking only (not an edge)
    confidence = VOLMOM_CONF_BASE
    if atr_pct >= 2 * VOLMOM_ATR_PCT_MIN:
        confidence += VOLMOM_CONF_EXTREME_BONUS
    if direction == 'SHORT' and rsi_5m < VOLMOM_SHORT_RSI_MAX - 5:
        confidence += VOLMOM_CONF_RSI_BONUS
    # F4 fix: LONG_RSI_CEILING=75 blocks RSI>=75, so RSI>75 bonus is unreachable.
    # Use RSI>73 (+3) instead — within the allowed (70,75] band.
    if direction == 'LONG' and rsi_5m > VOLMOM_LONG_RSI_MIN + 3:
        confidence += VOLMOM_CONF_RSI_BONUS
    confidence = max(VOLMOM_CONF_FLOOR, min(VOLMOM_CONF_CAP, confidence))

    return {
        'direction': direction,
        'confidence': confidence,
        'value': round(vol_ratio, 2),
        'price': price,
        'rsi': round(rsi_5m, 1),
        'atr_pct': round(atr_pct, 3),
        'momentum': momentum_state,
    }


def detect(token: str) -> Optional[dict]:
    """Detect vol_momentum for a token. Returns dict or None. Fails closed."""
    candles = _get_5m_candles(token)
    if not candles:
        return None
    closes = [r[4] for r in candles]
    volumes = [r[5] for r in candles]

    from rsi_utils import compute_rsi_5m
    from volatility_gate_v2 import get_atr_pct

    rsi_5m = compute_rsi_5m(token)
    atr_pct = get_atr_pct(token)
    enriched = _enrich_indicators(token) or {}
    momentum_state = enriched.get('momentum_state')

    return _evaluate(closes, volumes, atr_pct, rsi_5m, momentum_state)


def run(prices_dict=None) -> int:
    """Entry point for signals_runner."""
    if not VOLMOM_ENABLED:
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
        if price_age_minutes(token) > VOLMOM_MAX_PRICE_AGE_MIN:
            continue

        sig = detect(token)
        if not sig:
            continue

        direction = sig['direction']
        if direction == 'LONG' and not VOLMOM_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not VOLMOM_MINUS_ENABLED:
            continue
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue
        if get_cooldown(token, direction=direction):
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        try:
            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=sig_type,
                source=source,
                confidence=sig['confidence'],
                value=sig['value'],
                price=sig['price'],
                exchange='hyperliquid',
                timeframe='5m',
                momentum_state=sig['momentum'],
                rsi_14=sig['rsi'],
            )
        except Exception as e:
            _log(f'add_signal error {token}: {e}')
            continue

        if sid:
            added += 1
            set_cooldown(token, direction, hours=VOLMOM_COOLDOWN_MINUTES / 60.0)
            _log(f'{direction} {token:8s} conf={sig["confidence"]}% rsi={sig["rsi"]} '
                 f'atr={sig["atr_pct"]}% vol={sig["value"]}x mom={sig["momentum"]} '
                 f'price={sig["price"]:.8g} [{source}]')

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

    # 350-bar declining series → last close below EMA300 (downtrend)
    n = VOLMOM_EMA_MIN_CANDLES
    downtrend_closes = [100.0 - 10.0 * i / (n - 1) for i in range(n)]     # 100 → 90
    uptrend_closes = [90.0 + 10.0 * i / (n - 1) for i in range(n)]        # 90 → 100
    flat_vols = [100.0] * n
    spike_vols = [100.0] * (n - 1) + [250.0]                              # 2.5x last bar

    # SHORT fires: oversold + falling + below EMA300 + EXTREME ATR + vol confirm
    r = _evaluate(downtrend_closes, spike_vols, 2.0, 30.0, 'falling')
    check('SHORT fires (rsi=30, atr=2.0, falling, below EMA300, vol 2.5x)',
          r is not None and r['direction'] == 'SHORT')

    # LONG fires: overbought + rising + above EMA300 + EXTREME ATR + vol confirm
    r = _evaluate(uptrend_closes, spike_vols, 2.0, 75.0, 'rising')
    check('LONG fires (rsi=75, atr=2.0, rising, above EMA300, vol 2.5x)',
          r is not None and r['direction'] == 'LONG')

    # Blocked: ATR below EXTREME floor
    r = _evaluate(downtrend_closes, spike_vols, 1.2, 30.0, 'falling')
    check('BLOCKED: atr=1.2 < 1.5 floor', r is None)

    # Blocked: mid-band RSI (neither extreme)
    r = _evaluate(downtrend_closes, spike_vols, 2.0, 50.0, 'falling')
    check('BLOCKED: rsi=50 not extreme', r is None)

    # Blocked: flat/missing momentum
    r = _evaluate(downtrend_closes, spike_vols, 2.0, 30.0, 'flat')
    check('BLOCKED: momentum flat', r is None)
    r = _evaluate(downtrend_closes, spike_vols, 2.0, 30.0, None)
    check('BLOCKED: momentum missing (fail-closed)', r is None)

    # Blocked: wrong-side trend (oversold but ABOVE EMA300 → no SHORT)
    r = _evaluate(uptrend_closes, spike_vols, 2.0, 30.0, 'falling')
    check('BLOCKED: rsi=30 falling but price ABOVE EMA300', r is None)

    # Blocked: volume not confirmed (1x avg)
    r = _evaluate(downtrend_closes, flat_vols, 2.0, 30.0, 'falling')
    check('BLOCKED: volume 1.0x < 1.2x floor', r is None)

    # Blocked: missing ATR / RSI (fail-closed)
    r = _evaluate(downtrend_closes, spike_vols, None, 30.0, 'falling')
    check('BLOCKED: atr missing (fail-closed)', r is None)
    r = _evaluate(downtrend_closes, spike_vols, 2.0, None, 'falling')
    check('BLOCKED: rsi missing (fail-closed)', r is None)

    # Blocked: insufficient candles for EMA300
    r = _evaluate(downtrend_closes[:100], spike_vols[:100], 2.0, 30.0, 'falling')
    check('BLOCKED: <350 candles (EMA warmup)', r is None)

    # Confidence inside floor/cap
    r = _evaluate(downtrend_closes, spike_vols, 2.0, 30.0, 'falling')
    check('confidence within [floor, cap]',
          r is not None and VOLMOM_CONF_FLOOR <= r['confidence'] <= VOLMOM_CONF_CAP)

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
        print(f'[vol-momentum] dry scan error: {e}')
        return 0
    finally:
        if conn:
            conn.close()

    hits = 0
    for token in tokens:
        sig = detect(token)
        if sig:
            hits += 1
            print(f"  DRY {sig['direction']:5s} {token:8s} conf={sig['confidence']} "
                  f"rsi={sig['rsi']} atr={sig['atr_pct']}% vol={sig['value']}x "
                  f"mom={sig['momentum']} price={sig['price']:.8g}")
    print(f'[vol-momentum] dry scan: {hits} matches across {len(tokens)} tokens')
    return hits


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Volatility Momentum signal (both directions)')
    parser.add_argument('--selftest', action='store_true', help='Run synthetic-data condition tests')
    parser.add_argument('--dry', action='store_true', help='Live scan, no writes, ignores ENABLED flags')
    args = parser.parse_args()

    if args.selftest:
        sys.exit(0 if _selftest() else 1)
    elif args.dry:
        _dry_scan()
    else:
        print(f'Added {run()} signals')
