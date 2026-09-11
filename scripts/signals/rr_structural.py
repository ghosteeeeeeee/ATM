#!/usr/bin/env python3
"""rr_structural — Fire on structurally excellent R:R setups.

Uses the risk_reward_engine to evaluate structural quality for every token.
Fires signals ONLY when the engine scores Grade A/B with R:R ≥ 3.0.

Market mechanic: Structural breakout — clear air + strong R:R + right regime = favorable setup.
Edge: RR engine evaluates ~200 tokens per cycle. Most get Grade D/F. Grade A/B have excellent structure.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown, get_all_latest_prices
from tokens import get_all_tradeable_tokens
from risk_reward_engine import evaluate_rr

from hermes_constants import (
    RR_STRUCTURAL_PLUS_ENABLED,
    RR_STRUCTURAL_MINUS_ENABLED,
    RR_STRUCTURAL_MIN_SCORE,
    RR_STRUCTURAL_MIN_RR,
    RR_STRUCTURAL_MIN_ATR_PCT,
    RR_STRUCTURAL_MAX_ATR_PCT,
    RR_STRUCTURAL_REGIMES,
    RR_STRUCTURAL_COOLDOWN_HOURS,
    RR_STRUCTURAL_CONF_BASE,
    RR_STRUCTURAL_CONF_CAP,
    RR_STRUCTURAL_OPEN_SKY_BONUS,
    RR_STRUCTURAL_LIQ_BONUS,
    RR_STRUCTURAL_RR_CONF_MULT,
    RR_STRUCTURAL_RR_CONF_CAP,
    RR_STRUCTURAL_GRADE_A_BONUS,
    RR_STRUCTURAL_GRADE_B_BONUS,
    RR_STRUCTURAL_MAGNET_THRESH,
    RR_STRUCTURAL_MAX_PRICE_AGE,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG  = 'rr_structural_long'
SIGNAL_TYPE_SHORT = 'rr_structural_short'
SOURCE_LONG       = 'rr-struct+'
SOURCE_SHORT      = 'rr-struct-'


def _log(msg):
    print(f'[rr-struct] {msg}', flush=True)


def detect(token, price):
    """Evaluate structural R:R for a token. Returns signal dict or None.

    Checks both LONG and SHORT. Returns the direction with better structure.
    """
    # LONG evaluation
    long_result = evaluate_rr(token, 'LONG', price)
    long_ok = (
        long_result['grade'] in ('A', 'B') and
        long_result['rr_ratio'] >= RR_STRUCTURAL_MIN_RR and
        long_result['score'] >= RR_STRUCTURAL_MIN_SCORE and
        long_result['vol_width']['atr_regime'] in RR_STRUCTURAL_REGIMES and
        RR_STRUCTURAL_MIN_ATR_PCT <= long_result['vol_width']['atr_pct'] <= RR_STRUCTURAL_MAX_ATR_PCT
    )

    # SHORT evaluation
    short_result = evaluate_rr(token, 'SHORT', price)
    short_ok = (
        short_result['grade'] in ('A', 'B') and
        short_result['rr_ratio'] >= RR_STRUCTURAL_MIN_RR and
        short_result['score'] >= RR_STRUCTURAL_MIN_SCORE and
        short_result['vol_width']['atr_regime'] in RR_STRUCTURAL_REGIMES and
        RR_STRUCTURAL_MIN_ATR_PCT <= short_result['vol_width']['atr_pct'] <= RR_STRUCTURAL_MAX_ATR_PCT
    )

    # Pick the better direction
    if long_ok and short_ok:
        # Both pass — pick higher R:R
        if long_result['rr_ratio'] >= short_result['rr_ratio']:
            result, direction = long_result, 'LONG'
        else:
            result, direction = short_result, 'SHORT'
    elif long_ok:
        result, direction = long_result, 'LONG'
    elif short_ok:
        result, direction = short_result, 'SHORT'
    else:
        return None

    # Compute confidence
    conf = RR_STRUCTURAL_CONF_BASE
    conf += min(RR_STRUCTURAL_RR_CONF_CAP, int((result['rr_ratio'] - RR_STRUCTURAL_MIN_RR) * RR_STRUCTURAL_RR_CONF_MULT))
    conf += RR_STRUCTURAL_GRADE_A_BONUS if result['grade'] == 'A' else RR_STRUCTURAL_GRADE_B_BONUS

    # Open skies bonus
    if direction == 'LONG':
        has_target = any(l.get('type') == 'resistance' for l in result['sr_map'])
    else:
        has_target = any(l.get('type') == 'support' for l in result['sr_map'])
    if not has_target:
        conf += RR_STRUCTURAL_OPEN_SKY_BONUS

    # Liquidity proximity bonus
    if result['liquidity'].get('magnet_score', 0) > RR_STRUCTURAL_MAGNET_THRESH:
        conf += RR_STRUCTURAL_LIQ_BONUS

    conf = min(RR_STRUCTURAL_CONF_CAP, conf)

    return {
        'direction': direction,
        'confidence': conf,
        'value': result['rr_ratio'],
        'price': price,
        'notes': f"R:R={result['rr_ratio']:.2f} Score={result['score']} Grade={result['grade']} "
                 f"Regime={result['vol_width']['atr_regime']} ATR={result['vol_width']['atr_pct']:.2f}%",
    }


def scan_signals():
    """Scan all tradeable tokens for structurally excellent R:R setups."""
    added = 0
    tokens = get_all_tradeable_tokens()
    prices = get_all_latest_prices()

    for token in tokens:
        token_upper = token.upper()

        # Price age check
        if price_age_minutes(token) > RR_STRUCTURAL_MAX_PRICE_AGE:
            continue

        # Get latest price
        price_data = prices.get(token_upper)
        if not price_data or price_data.get('price', 0) <= 0:
            continue
        price = price_data['price']

        # Detect
        sig = detect(token_upper, price)
        if not sig:
            continue

        direction = sig['direction']

        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not RR_STRUCTURAL_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not RR_STRUCTURAL_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
        if direction == 'LONG' and token_upper in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token_upper in SHORT_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token_upper, direction=direction):
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        sid = add_signal(
            token=token_upper,
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=sig['confidence'],
            value=sig.get('value'),
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='15m',
            z_score=None,
        )
        if sid:
            added += 1
            set_cooldown(token_upper, direction, hours=RR_STRUCTURAL_COOLDOWN_HOURS)
            _log(f'{token_upper} {direction} conf={sig["confidence"]} {sig["notes"]}')

    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    added = run()
    _log(f'Total: {added} signals')
