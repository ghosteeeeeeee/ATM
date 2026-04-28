#!/usr/bin/env python3
"""
backtest_gap300.py — Backtest the redesigned gap-300 state machine signal.
Scans ALL available price history, not just the last N bars.
"""

import sys, os, argparse, sqlite3, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gap300_signals import _ema_series, _sma_series

# ── Constants ─────────────────────────────────────────────────────────────────
PERIOD          = 300
MIN_GAP_PCT     = 0.05
COOLDOWN_MIN    = 5          # bars between fires
MOMENTUM_BARS   = 10
COLLAPSE_PCT    = 0.70
PRICE_DB        = '/root/.hermes/data/signals_hermes.db'

# States
S_NO_SIGNAL    = 'NO_SIGNAL'
S_TRACKING_LONG  = 'TRACKING_LONG'
S_TRACKING_SHORT = 'TRACKING_SHORT'
S_ACTIVE_LONG    = 'ACTIVE_LONG'
S_ACTIVE_SHORT   = 'ACTIVE_SHORT'

SIGNAL_TYPES = {
    'LONG':  ('ema_sma_gap_300_long',  'gap-300+'),
    'SHORT': ('ema_sma_gap_300_short', 'gap-300-'),
}


def compute_series(prices):
    closes = [p['price'] for p in prices]
    timestamps = [p['timestamp'] for p in prices]
    ema_s = _ema_series(closes, PERIOD)
    sma_s = _sma_series(closes, PERIOD)
    gap_pcts = []
    raw_gaps = []
    for i in range(PERIOD - 1, len(closes)):
        if ema_s[i] is None or sma_s[i] is None:
            gap_pcts.append(None)
            raw_gaps.append(None)
        else:
            gap = ema_s[i] - sma_s[i]
            gap_pcts.append(abs(gap) / closes[i] * 100.0)
            raw_gaps.append(gap)
    return closes, timestamps, gap_pcts, raw_gaps


def run_backtest(token, prices, verbose=False):
    """Run state machine backtest on full price series. Returns events list."""
    if len(prices) < PERIOD * 2:
        return [], None

    closes, timestamps, gap_pcts, raw_gaps = compute_series(prices)
    n = len(gap_pcts)
    valid_start = PERIOD - 1

    state = S_NO_SIGNAL
    direction = None
    peak_gap = 0.0
    cooldown_until = 0
    fires = []

    for i in range(valid_start, n):
        bar_ts = timestamps[i]
        gap_pct = gap_pcts[i]
        raw_gap = raw_gaps[i]
        cur_dir = 'LONG' if raw_gap > 0 else 'SHORT'
        gap_prev = gap_pcts[i - 1] if i > valid_start else None

        # ── NO_SIGNAL ──────────────────────────────────────────────────────────
        if state == S_NO_SIGNAL:
            if gap_pct is not None and gap_prev is not None:
                if gap_prev < MIN_GAP_PCT <= gap_pct:
                    direction = cur_dir
                    peak_gap = gap_pct
                    state = S_TRACKING_LONG if direction == 'LONG' else S_TRACKING_SHORT
                    if verbose:
                        dt = datetime.datetime.fromtimestamp(bar_ts, datetime.timezone.utc).strftime('%m-%d %H:%M')
                        print(f"  [{token}] {dt} CROSS {direction} → TRACKING (gap={gap_pct:.4f}%)")

        # ── TRACKING_* ─────────────────────────────────────────────────────────
        elif state in (S_TRACKING_LONG, S_TRACKING_SHORT):
            # Opposite cross → replace
            if gap_pct is not None and gap_prev is not None:
                opp_sign = -1 if direction == 'LONG' else 1
                opp_cross = raw_gap * opp_sign < 0
                if opp_cross:
                    direction = 'SHORT' if cur_dir == 'LONG' else 'LONG'
                    peak_gap = gap_pct
                    state = S_TRACKING_LONG if direction == 'LONG' else S_TRACKING_SHORT
                    if verbose:
                        dt = datetime.datetime.fromtimestamp(bar_ts, datetime.timezone.utc).strftime('%m-%d %H:%M')
                        print(f"  [{token}] {dt} OPPOSITE CROSS → {direction} REPLACE")
                    continue

                # Gap below threshold → reset
                if gap_pct < MIN_GAP_PCT:
                    state = S_NO_SIGNAL
                    direction = None
                    peak_gap = 0.0
                    if verbose:
                        dt = datetime.datetime.fromtimestamp(bar_ts, datetime.timezone.utc).strftime('%m-%d %H:%M')
                        print(f"  [{token}] {dt} BELOW THRESHOLD → NO_SIGNAL")
                    continue

                # Gap contracting or collapsed
                if gap_prev is not None:
                    contracting = gap_pct <= gap_prev
                    collapsed = peak_gap > 0 and gap_pct < peak_gap * COLLAPSE_PCT
                    if contracting or collapsed:
                        if gap_pct > peak_gap:
                            peak_gap = gap_pct
                        continue

                # Try to fire
                widening = gap_prev is not None and gap_pct > gap_prev
                momentum_ok = True
                if len(closes) >= i + 1 and i >= MOMENTUM_BARS:
                    ret = (closes[i] / closes[i - MOMENTUM_BARS] - 1) * 100.0
                    momentum_ok = (direction == 'LONG' and ret >= 0) or (direction == 'SHORT' and ret <= 0)
                not_collapsed = peak_gap > 0 and gap_pct >= peak_gap * COLLAPSE_PCT
                cooldown_ok = bar_ts >= cooldown_until

                if widening and momentum_ok and not_collapsed and cooldown_ok:
                    confidence = int(min(75, max(60, 60 + (gap_pct - MIN_GAP_PCT) * 200)))
                    fires.append({'bar_idx': i, 'ts': bar_ts, 'dir': direction, 'gap': gap_pct, 'peak': peak_gap, 'conf': confidence})
                    cooldown_until = bar_ts + COOLDOWN_MIN * 60
                    state = S_ACTIVE_LONG if direction == 'LONG' else S_ACTIVE_SHORT
                    if verbose:
                        dt = datetime.datetime.fromtimestamp(bar_ts, datetime.timezone.utc).strftime('%m-%d %H:%M')
                        print(f"  [{token}] {dt} >>> FIRE {direction} gap={gap_pct:.4f}% peak={peak_gap:.4f}% conf={confidence}")
                elif gap_pct > peak_gap:
                    peak_gap = gap_pct

        # ── ACTIVE_* ───────────────────────────────────────────────────────────
        elif state in (S_ACTIVE_LONG, S_ACTIVE_SHORT):
            if gap_pct is not None and gap_prev is not None:
                opp_sign = -1 if direction == 'LONG' else 1
                opp_cross = raw_gap * opp_sign < 0
                if opp_cross:
                    direction = 'SHORT' if cur_dir == 'LONG' else 'LONG'
                    peak_gap = gap_pct
                    state = S_TRACKING_LONG if direction == 'LONG' else S_TRACKING_SHORT
                    if verbose:
                        dt = datetime.datetime.fromtimestamp(bar_ts, datetime.timezone.utc).strftime('%m-%d %H:%M')
                        print(f"  [{token}] {dt} OPPOSITE CROSS → {direction} REPLACE")
                    continue

                if gap_pct < MIN_GAP_PCT:
                    state = S_NO_SIGNAL
                    direction = None
                    peak_gap = 0.0
                    if verbose:
                        dt = datetime.datetime.fromtimestamp(bar_ts, datetime.timezone.utc).strftime('%m-%d %H:%M')
                        print(f"  [{token}] {dt} BELOW THRESHOLD → NO_SIGNAL")
                    continue

                contracting = gap_prev is not None and gap_pct <= gap_prev
                collapsed = peak_gap > 0 and gap_pct < peak_gap * COLLAPSE_PCT

                if contracting or collapsed:
                    if gap_pct > peak_gap:
                        peak_gap = gap_pct
                    state = S_TRACKING_LONG if direction == 'LONG' else S_TRACKING_SHORT
                    if verbose:
                        dt = datetime.datetime.fromtimestamp(bar_ts, datetime.timezone.utc).strftime('%m-%d %H:%M')
                        reason = 'CONTRACTED' if contracting else 'COLLAPSED'
                        print(f"  [{token}] {dt} {reason} → TRACKING")
                    continue

                # Update peak
                if gap_pct > peak_gap:
                    peak_gap = gap_pct

                # Cooldown
                if bar_ts < cooldown_until:
                    continue

                # Re-fire check
                widening = gap_prev is not None and gap_pct > gap_prev
                momentum_ok = True
                if len(closes) >= i + 1 and i >= MOMENTUM_BARS:
                    ret = (closes[i] / closes[i - MOMENTUM_BARS] - 1) * 100.0
                    momentum_ok = (direction == 'LONG' and ret >= 0) or (direction == 'SHORT' and ret <= 0)
                not_collapsed = gap_pct >= peak_gap * COLLAPSE_PCT

                if widening and momentum_ok and not_collapsed:
                    confidence = int(min(75, max(60, 60 + (gap_pct - MIN_GAP_PCT) * 200)))
                    fires.append({'bar_idx': i, 'ts': bar_ts, 'dir': direction, 'gap': gap_pct, 'peak': peak_gap, 'conf': confidence})
                    cooldown_until = bar_ts + COOLDOWN_MIN * 60
                    if verbose:
                        dt = datetime.datetime.fromtimestamp(bar_ts, datetime.timezone.utc).strftime('%m-%d %H:%M')
                        print(f"  [{token}] {dt} >>> RE-FIRE {direction} gap={gap_pct:.4f}% peak={peak_gap:.4f}% conf={confidence}")

    return fires, {'state': state, 'direction': direction, 'peak_gap': peak_gap}


def get_all_prices(token):
    conn = sqlite3.connect(PRICE_DB, timeout=30)
    c = conn.cursor()
    c.execute("SELECT timestamp, price FROM price_history WHERE token = ? ORDER BY timestamp ASC", (token,))
    rows = c.fetchall()
    conn.close()
    return [{'timestamp': r[0], 'price': r[1]} for r in rows]


def summarize_pulses(fires, cooldown_min=5):
    """Group fires into pulses."""
    if not fires:
        return [], 0, 0
    pulses = []
    current_pulse = [fires[0]]
    for f in fires[1:]:
        if f['ts'] - current_pulse[-1]['ts'] <= cooldown_min * 60 * 3:
            current_pulse.append(f)
        else:
            pulses.append(current_pulse)
            current_pulse = [f]
    pulses.append(current_pulse)

    pulse_durations = []
    for p in pulses:
        dur = (p[-1]['ts'] - p[0]['ts']) / 60
        pulse_durations.append(dur)

    return pulses, min(pulse_durations), sum(pulse_durations)/len(pulse_durations) if pulse_durations else 0


def main():
    parser = argparse.ArgumentParser(description='Backtest gap-300 state machine')
    parser.add_argument('--tokens', nargs='+',
                        default=['BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'ARB', 'AAVE', 'UNI', 'XRP', 'ADA', 'ATOM', 'APT'])
    parser.add_argument('--min-pulses', type=int, default=3, help='Min pulses to show token in results')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--limit', type=int, default=0, help='Limit bars per token (0=all)')
    args = parser.parse_args()

    print(f"gap-300 backtest — PERIOD={PERIOD}, MIN_GAP_PCT={MIN_GAP_PCT}%, COOLDOWN={COOLDOWN_MIN}min, COLLAPSE={COLLAPSE_PCT}")
    print()

    results = {}
    for token in args.tokens:
        prices = get_all_prices(token)
        if not prices:
            print(f"{token}: no data")
            continue
        if len(prices) < PERIOD * 2:
            print(f"{token}: {len(prices)} bars, need {PERIOD*2}")
            continue

        # Optionally limit bars (for faster iteration during tuning)
        if args.limit > 0:
            prices = prices[-args.limit:]

        fires, final = run_backtest(token, prices, verbose=args.verbose)
        pulses, min_dur, avg_dur = summarize_pulses(fires)

        results[token] = {
            'fires': fires,
            'pulses': pulses,
            'n_fires': len(fires),
            'n_pulses': len(pulses),
            'min_dur': min_dur,
            'avg_dur': avg_dur,
            'final_state': final,
        }

    # Print summary
    print(f"\n{'Token':8s} {'Fires':6s} {'Pulses':7s} {'MinDur':7s} {'AvgDur':7s} {'FinalState':20s}")
    print("-" * 65)
    for token, r in sorted(results.items(), key=lambda x: -x[1]['n_pulses']):
        final = r['final_state']
        state_str = f"{final['direction'] or ''}_{final['state']}" if final else 'N/A'
        print(f"{token:8s} {r['n_fires']:6d} {r['n_pulses']:7d} {r['min_dur']:7.0f} {r['avg_dur']:7.0f} {state_str:20s}")

    total_fires = sum(r['n_fires'] for r in results.values())
    total_pulses = sum(r['n_pulses'] for r in results.values())
    print(f"\nTotal: {total_fires} fires, {total_pulses} pulses across {len(results)} tokens")

    # Detailed pulse analysis for tokens with enough pulses
    print("\n" + "=" * 70)
    print("PULSE DETAILS (tokens with >=3 pulses)")
    print("=" * 70)
    for token, r in sorted(results.items(), key=lambda x: -x[1]['n_pulses']):
        if r['n_pulses'] < args.min_pulses:
            continue
        print(f"\n{token} ({r['n_pulses']} pulses, {r['n_fires']} fires):")
        for j, pulse in enumerate(r['pulses']):
            dur = (pulse[-1]['ts'] - pulse[0]['ts']) / 60
            gaps = [f['gap'] for f in pulse]
            confs = [f['conf'] for f in pulse]
            dirs = [f['dir'] for f in pulse]
            dt_start = datetime.datetime.fromtimestamp(pulse[0]['ts'], datetime.timezone.utc).strftime('%m-%d %H:%M')
            dt_end = datetime.datetime.fromtimestamp(pulse[-1]['ts'], datetime.timezone.utc).strftime('%H:%M')
            print(f"  Pulse {j+1}: {dt_start}–{dt_end} {dirs[0]} dur={dur:.0f}min fires={len(pulse)} gap={min(gaps):.4f}–{max(gaps):.4f}% conf={min(confs)}-{max(confs)}")


if __name__ == '__main__':
    main()
