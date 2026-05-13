#!/usr/bin/env python3
"""
momentum.py — Extracted from signal_gen.py lines ~2451-2517 (LONG) and ~2550-2600 (SHORT).

Inline momentum signals with speed/velocity filtering + spike detection + counter-spike reversal:
  - LONG:  momentum+  fires when score >= ENTRY_THRESHOLD and passes velocity/speed filters
  - SHORT: momentum-  mirrors the LONG logic for SHORT direction

Architecture:
  signal_gen.compute_score() → z-score + velocity + phase + regime + RSI + MACD
  → add_signal(source='momentum+', signal_type='momentum')
  → signals_hermes_runtime.db → signal_compactor → hotset.json → guardian → HL

Signal types:
  - momentum+ : LONG  direction, bullish momentum
  - momentum- : SHORT direction, bearish momentum
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
    LOG_FILE, LONG_BLACKLIST, SHORT_BLACKLIST,
    detect_spike, score_for_counter_spike, _get_reverse_signal_name,
    SPEED_ABS_MIN_THRESHOLD, SPEED_BOOST_THRESHOLD, SPEED_BOOST_FACTOR,
    SPEED_MIN_THRESHOLD,
    get_price_history,
    recent_trade_exists, MIN_TRADE_INTERVAL_MINUTES, is_delisted,
)
try:
    from speed_tracker import SpeedTracker
    _speed_tracker = SpeedTracker()
except Exception:
    _speed_tracker = None

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# ── Feature flag (Layer 1 kill-switch) ───────────────────────────────────────
from hermes_constants import MOMENTUM_ENABLED
from hermes_constants import MOMENTUM_PLUS_ENABLED, MOMENTUM_MINUS_ENABLED

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
    Scan all tokens for inline momentum signals.

    Returns:
        int: number of signals added
    """
    # NOTE: MOMENTUM_ENABLED guard is in signal_gen.py (inline version).
    # Per-direction MOMENTUM_PLUS/MINUS_ENABLED checks remain active.
    # This registry version is called by signals_runner.py — Layer 2 add_signal()
    # guard handles final per-source filtering.

    init_db()
    prices_dict = get_all_latest_prices()
    regime, long_mult, short_mult, *_ = compute_regime()

    _log(f'=== momentum | Regime: {regime.upper()} (L:x{long_mult:.1f} S:x{short_mult:.1f}) | {len(prices_dict)} tokens ===')
    print(f'[momentum] Regime: {regime.upper()} (L:x{long_mult:.1f} S:x{short_mult:.1f}) | {len(prices_dict)} tokens')

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
    blocked = 0

    for token, data in prices_dict.items():
        # ── Skip conditions (same as signal_gen.py run-loop) ──
        if token.startswith('@'):
            continue
        if price_age_minutes(token) > 10:
            continue
        if not data.get('price') or data['price'] <= _MIN_PRICE:
            continue
        if data['price'] > _MAX_PRICE:
            continue
        if get_cooldown(token):
            continue
        if token.upper() in SHORT_BLACKLIST or token.upper() in LONG_BLACKLIST:
            continue
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue
        if is_delisted(token.upper()):
            continue

        price = data['price']
        mom = get_momentum_stats(token)
        rsi_14_val = mom.get('rsi_14') if mom else None
        macd_line_val = mom.get('macd_line') if mom else None
        macd_signal_val = mom.get('macd_signal') if mom else None
        macd_hist_val = mom.get('macd_hist') if mom else None

        # ── Speed/Velocity filter ─────────────────────────────────────────
        speed_pctl = 50.0
        vel_5m = 0.0
        if _speed_tracker is not None:
            spd = _speed_tracker.get_token_speed(token)
            if spd:
                speed_pctl = spd.get('speed_percentile', 50.0)
                vel_5m = spd.get('price_velocity_5m', 0.0)

        # ── LONG signals ────────────────────────────────────────────────────
        if MOMENTUM_PLUS_ENABLED and (token not in open_pos or open_pos[token] != 'LONG'):
            score, signals = compute_score(token, 'LONG', long_mult, short_mult)
            if score and score >= ENTRY_THRESHOLD:
                # Apply speed boost: high-speed tokens get easier entry threshold
                effective_threshold = ENTRY_THRESHOLD
                if speed_pctl >= SPEED_BOOST_THRESHOLD:
                    effective_threshold = ENTRY_THRESHOLD * SPEED_BOOST_FACTOR  # 5% easier

                if score >= effective_threshold:
                    sources = ','.join(sorted(set(s[0] for s in signals)))
                    reasons = ' | '.join(s[3] for s in signals[:4])

                    # ── Spike Detection ────────────────────────────────────
                    spike_type, pct_chg, do_reverse, is_pump = detect_spike(token, 'LONG', price)
                    if do_reverse:
                        opp_score, opp_signals, pump_tag = score_for_counter_spike(
                            token, 'LONG', long_mult, short_mult)
                        opp_dir = _get_reverse_signal_name('LONG')
                        opp_sources = ','.join(sorted(set(s[0] for s in opp_signals))) if opp_signals else 'momentum'
                        opp_reasons = ' | '.join(s[3] for s in opp_signals[:3]) if opp_signals else 'reverse'
                        if is_pump:
                            pump_tag = f'pump-{opp_dir.lower()}'
                            _log(f'PUMP:  {token} {opp_dir} @{price:.6f} {opp_score:.1f}% '
                                f'[spike{spike_type}+{pct_chg:.1f}%] {pump_tag} {opp_reasons}')
                            print(f'  PUMP  {token:8s} {opp_score:5.1f}% [REVERSE->{opp_dir} spike-{spike_type}+{pct_chg:.1f}%]')
                        else:
                            _log(f'REV:   {token} {opp_dir} @{price:.6f} {opp_score:.1f}% '
                                f'[counter-spike{spike_type}+{pct_chg:.1f}%] {opp_reasons}')
                            print(f'  REV   {token:8s} {opp_score:5.1f}% [REVERSE->{opp_dir} ctx-spike-{spike_type}+{pct_chg:.1f}%]')
                        if opp_score and opp_score >= ENTRY_THRESHOLD:
                            add_signal(
                                token=token, direction=opp_dir, signal_type='momentum',
                                source=f'mtf-{opp_sources}', confidence=opp_score,
                                value=opp_score, price=price,
                                exchange='hyperliquid',
                                timeframe=f'{mom["phase"][:3] if mom else "unk"}',
                                z_score=mom['avg_z'] if mom else None,
                                z_score_tier=mom['z_direction'] if mom else None,
                                rsi_14=rsi_14_val,
                                macd_value=macd_line_val,
                                macd_signal=macd_signal_val,
                                macd_hist=macd_hist_val,
                            )
                            _log(f'SIGNAL:  {token} {opp_dir} @{price:.6f} {opp_score:.1f}% [{pump_tag}] {opp_reasons}')
                            set_cooldown(token, opp_dir, hours=1)
                            added += 1
                    else:
                        add_signal(
                            token=token, direction='LONG', signal_type='momentum',
                            source=f'mtf-{sources}', confidence=score,
                            value=score, price=price,
                            exchange='hyperliquid',
                            timeframe=f'{mom["phase"][:3] if mom else "unk"}',
                            z_score=mom['avg_z'] if mom else None,
                            z_score_tier=mom['z_direction'] if mom else None,
                            rsi_14=rsi_14_val,
                            macd_value=macd_line_val,
                            macd_signal=macd_signal_val,
                            macd_hist=macd_hist_val,
                        )
                        _log(f'SIGNAL:  {token} LONG @{price:.6f} {score:.1f}% {reasons}')
                        print(f'  LONG  {token:8s} {score:5.1f}% [AI-DECIDER]  {reasons}')
                        set_cooldown(token, 'LONG', hours=1)
                        added += 1
                else:
                    blocked += 1
            elif score and score < ENTRY_THRESHOLD:
                blocked += 1

        # ── SHORT signals ──────────────────────────────────────────────────
        if MOMENTUM_MINUS_ENABLED and (token not in open_pos or open_pos[token] != 'SHORT'):
            score, signals = compute_score(token, 'SHORT', long_mult, short_mult)
            if score and score >= ENTRY_THRESHOLD:
                # Apply speed boost
                effective_threshold = ENTRY_THRESHOLD
                if speed_pctl >= SPEED_BOOST_THRESHOLD:
                    effective_threshold = ENTRY_THRESHOLD * SPEED_BOOST_FACTOR

                if score >= effective_threshold:
                    sources = ','.join(sorted(set(s[0] for s in signals)))
                    reasons = ' | '.join(s[3] for s in signals[:4])

                    # ── Spike Detection ────────────────────────────────────
                    spike_type, pct_chg, do_reverse, is_pump = detect_spike(token, 'SHORT', price)
                    if do_reverse:
                        opp_score, opp_signals, pump_tag = score_for_counter_spike(
                            token, 'SHORT', long_mult, short_mult)
                        opp_dir = _get_reverse_signal_name('SHORT')
                        opp_sources = ','.join(sorted(set(s[0] for s in opp_signals))) if opp_signals else 'momentum'
                        opp_reasons = ' | '.join(s[3] for s in opp_signals[:3]) if opp_signals else 'reverse'
                        if is_pump:
                            pump_tag = f'pump-{opp_dir.lower()}'
                            _log(f'PUMP:  {token} {opp_dir} @{price:.6f} {opp_score:.1f}% '
                                f'[spike-{spike_type}+{pct_chg:.1f}%] {pump_tag} {opp_reasons}')
                            print(f'  PUMP  {token:8s} {opp_score:5.1f}% [REVERSE->{opp_dir} spike-{spike_type}+{pct_chg:.1f}%]')
                        else:
                            _log(f'REV:   {token} {opp_dir} @{price:.6f} {opp_score:.1f}% '
                                f'[counter-spike{spike_type}+{pct_chg:.1f}%] {opp_reasons}')
                            print(f'  REV   {token:8s} {opp_score:5.1f}% [REVERSE->{opp_dir} ctx-spike-{spike_type}+{pct_chg:.1f}%]')
                        if opp_score and opp_score >= ENTRY_THRESHOLD:
                            add_signal(
                                token=token, direction=opp_dir, signal_type='momentum',
                                source=f'mtf-{opp_sources}', confidence=opp_score,
                                value=opp_score, price=price,
                                exchange='hyperliquid',
                                timeframe=f'{mom["phase"][:3] if mom else "unk"}',
                                z_score=mom['avg_z'] if mom else None,
                                z_score_tier=mom['z_direction'] if mom else None,
                            )
                            _log(f'SIGNAL:  {token} {opp_dir} @{price:.6f} {opp_score:.1f}% [{pump_tag}] {opp_reasons}')
                            set_cooldown(token, opp_dir, hours=1)
                            added += 1
                    else:
                        add_signal(
                            token=token, direction='SHORT', signal_type='momentum',
                            source=f'mtf-{sources}', confidence=score,
                            value=score, price=price,
                            exchange='hyperliquid',
                            timeframe=f'{mom["phase"][:3] if mom else "unk"}',
                            z_score=mom['avg_z'] if mom else None,
                            z_score_tier=mom['z_direction'] if mom else None,
                            rsi_14=rsi_14_val,
                            macd_value=macd_line_val,
                            macd_signal=macd_signal_val,
                            macd_hist=macd_hist_val,
                        )
                        _log(f'SIGNAL:  {token} SHORT @{price:.6f} {score:.1f}% {reasons}')
                        print(f'  SHORT {token:8s} {score:5.1f}% [AI-DECIDER]  {reasons}')
                        set_cooldown(token, 'SHORT', hours=1)
                        added += 1
                else:
                    blocked += 1
            elif score and score < ENTRY_THRESHOLD:
                blocked += 1

    print(f'[momentum] Done: {added} signals added, {blocked} blocked')
    return added


if __name__ == '__main__':
    run()
