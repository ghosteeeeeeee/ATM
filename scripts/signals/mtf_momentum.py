#!/usr/bin/env python3
"""
mtf_momentum.py — Extracted from signal_gen.py lines ~603-651 (LONG block) and ~628-651 (SHORT block).

Multi-timeframe momentum signals:
  - LONG:  mtf-momentum+  fires when score >= ENTRY_THRESHOLD (65) and passes all filters
  - SHORT: mtf-momentum-  mirrors the LONG logic for the SHORT direction

Architecture:
  signal_gen.compute_score() → z-score + velocity + phase + regime + RSI + MACD
  → add_signal(source='mtf-{sources}', signal_type='momentum')
  → signals_hermes_runtime.db → signal_compactor → hotset.json → guardian → HL

Signal types:
  - mtf-momentum+ : LONG  direction, bullish momentum
  - mtf-momentum- : SHORT direction, bearish momentum
"""

import sys, os, sqlite3, time
sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import (
    init_db, get_all_latest_prices, add_signal, set_cooldown,
    get_cooldown, price_age_minutes, approve_signal
)
from signal_gen import (
    compute_score, compute_regime, get_momentum_stats,
    ENTRY_THRESHOLD, AUTO_APPROVE,
    LOG_FILE
)

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# ── Feature flags (from hermes_constants — Layer 1 kill-switch) ────────────────
from hermes_constants import (
    MTF_MOMENTUM_ENABLED,
    MTF_MOMENTUM_PLUS_ENABLED,
    MTF_MOMENTUM_MINUS_ENABLED,
)

# ── Skip conditions (mirrored from signal_gen.py run-loop) ───────────────────
_MIN_PRICE = 1e-8   # discard zero/negative prices
_MAX_PRICE = 1e6    # sanity cap


def _log(msg):
    """Write to both stdout and signals.log."""
    print(msg)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(msg + '\n')
    except Exception:
        pass


def run():
    """
    Scan all tokens for multi-timeframe momentum signals.

    Returns:
        int: number of signals added
    """
    # NOTE: MTF_MOMENTUM_ENABLED guard is in signal_gen.py (inline version).
    # Per-direction MTF_MOMENTUM_PLUS/MINUS_ENABLED checks remain active.
    # This registry version is called by signals_runner.py — Layer 2 add_signal()
    # guard handles final per-source filtering.

    init_db()
    prices_dict = get_all_latest_prices()
    regime, long_mult, short_mult, *_ = compute_regime()

    _log(f'=== mtf_momentum | Regime: {regime.upper()} (L:x{long_mult:.1f} S:x{short_mult:.1f}) | {len(prices_dict)} tokens ===')
    print(f'[mtf-momentum] Regime: {regime.upper()} (L:x{long_mult:.1f} S:x{short_mult:.1f}) | {len(prices_dict)} tokens')

    # open positions — avoid adding redundant signals for tokens we already hold
    open_pos = {}
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("SELECT token, direction FROM trades WHERE server='Hermes' AND status='open'")
        open_pos = {r[0]: r[1] for r in cur.fetchall()}
        cur.close(); conn.close()
    except Exception:
        pass   # fallback: empty dict (no DB access)

    added = 0

    for token, data in prices_dict.items():
        # ── Skip conditions (same as signal_gen.py run-loop) ──
        if price_age_minutes(token) > 10:
            continue
        if not data.get('price') or data['price'] <= _MIN_PRICE:
            continue
        if data['price'] > _MAX_PRICE:
            continue
        if get_cooldown(token):
            continue
        if token in open_pos:
            continue

        price = data['price']
        mom = get_momentum_stats(token)

        # ── LONG signals ──────────────────────────────────────
        if MTF_MOMENTUM_PLUS_ENABLED and (token not in open_pos or open_pos[token] != 'LONG'):
            score, signals = compute_score(token, 'LONG', long_mult, short_mult)
            if score and score >= ENTRY_THRESHOLD:
                sources = '+'.join(sorted(set(s[0] for s in signals)))
                reasons = ' | '.join(s[3] for s in signals[:4])
                add_signal(
                    token=token, direction='LONG', signal_type='momentum',
                    source=f'mtf-{sources}', confidence=score,
                    value=score, price=price,
                    exchange='hyperliquid',
                    timeframe=f'{mom["phase"][:3] if mom else "unk"}',
                    z_score=mom['avg_z'] if mom else None,
                    z_score_tier=mom['z_direction'] if mom else None,
                )
                if score >= AUTO_APPROVE:
                    approve_signal(token, 'LONG')
                    set_cooldown(token, 'LONG', hours=1)
                    _log(f'APPROVED: {token} LONG @{price:.6f} {score:.1f}% {reasons}')
                    print(f'  LONG  {token:8s} {score:5.1f}% [AUTO]  {reasons}')
                else:
                    _log(f'SIGNAL:  {token} LONG @{price:.6f} {score:.1f}% {reasons}')
                    print(f'  LONG  {token:8s} {score:5.1f}% [WAIT]  {reasons}')
                added += 1

        # ── SHORT signals ─────────────────────────────────────
        if MTF_MOMENTUM_MINUS_ENABLED and (token not in open_pos or open_pos[token] != 'SHORT'):
            score, signals = compute_score(token, 'SHORT', long_mult, short_mult)
            if score and score >= ENTRY_THRESHOLD:
                sources = '+'.join(sorted(set(s[0] for s in signals)))
                reasons = ' | '.join(s[3] for s in signals[:4])
                add_signal(
                    token=token, direction='SHORT', signal_type='momentum',
                    source=f'mtf-{sources}', confidence=score,
                    value=score, price=price,
                    exchange='hyperliquid',
                    timeframe=f'{mom["phase"][:3] if mom else "unk"}',
                    z_score=mom['avg_z'] if mom else None,
                    z_score_tier=mom['z_direction'] if mom else None,
                )
                if score >= AUTO_APPROVE:
                    approve_signal(token, 'SHORT')
                    set_cooldown(token, 'SHORT', hours=1)
                    _log(f'APPROVED: {token} SHORT @{price:.6f} {score:.1f}% {reasons}')
                    print(f'  SHORT {token:8s} {score:5.1f}% [AUTO]  {reasons}')
                else:
                    _log(f'SIGNAL:  {token} SHORT @{price:.6f} {score:.1f}% {reasons}')
                    print(f'  SHORT {token:8s} {score:5.1f}% [WAIT]  {reasons}')
                added += 1

    print(f'[mtf-momentum] Done: {added} signals added')
    return added


if __name__ == '__main__':
    run()
