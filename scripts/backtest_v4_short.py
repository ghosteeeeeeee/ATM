#!/usr/bin/env python3
"""Backtest accel_300_v4_short — test earlier-entry SHORT signal on historical 1m data.

OPTIMIZED: Steps through candles with a configurable stride for speed.
For each token with 1m candle data:
  1. Load candles from candles.db
  2. Step through time (every N candles), checking if v4 signal fires
  3. If signal fires, simulate SHORT entry
  4. Check outcomes at 30m, 60m, 120m horizons
  5. Output results table
"""

import sys, os, sqlite3, time
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, CANDLES_DB

# Import the v4 detection function directly
from signals.accel_300_v4_short import (
    _ema_series, _rsi, detect_accel_300_v4_short,
    _check_volume_spike, _check_price_at_resistance,
    _check_rsi_divergence, _check_momentum_shift, _rsi_series, _get_volume_series,
)
from hermes_constants import (
    ACCEL_300_V4_SHORT_COOLDOWN_BARS,
)

PERIOD = 300  # EMA300

# Backtest parameters
SL_PCT = 1.5    # 1.5% stop loss
TP_PCT = 1.0    # 1.0% take profit
FEE_PCT = 0.035 # 0.035% per side (0.07% round trip)
HORIZONS = [30, 60, 120]  # minutes to check outcomes
STRIDE = 3      # check every N candles (faster than every candle)
MAX_TOKENS = 40 # limit tokens for speed


def load_candles(token: str) -> list:
    """Load all 1m candles for a token from candles.db, oldest first."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_1m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts ASC
        """, (token.upper(),))
        rows = c.fetchall()
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
                 'close': r[4], 'volume': r[5]} for r in rows]
    except Exception as e:
        print(f"  Error loading candles for {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_tokens() -> list:
    """Get all tokens with 1m candle data, sorted by candle count."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT token, COUNT(*) as cnt
            FROM candles_1m
            WHERE is_closed = 1
            GROUP BY token
            HAVING cnt >= 500
            ORDER BY cnt DESC
        """)
        return [(r[0], r[1]) for r in c.fetchall()]
    finally:
        if conn:
            conn.close()


def simulate_trade(candles: list, entry_idx: int, entry_price: float) -> dict:
    """Simulate a SHORT trade from entry_idx forward.
    Check SL/TP hit at each candle using high/low."""
    results = {}
    for horizon in HORIZONS:
        end_idx = min(entry_idx + horizon, len(candles) - 1)
        if end_idx <= entry_idx:
            results[horizon] = {'outcome': 'insufficient_data', 'pnl': 0}
            continue

        tp_price = entry_price * (1 - TP_PCT / 100)
        sl_price = entry_price * (1 + SL_PCT / 100)

        hit_tp = False
        hit_sl = False
        worst_pnl = 0
        best_pnl = 0

        for i in range(entry_idx + 1, end_idx + 1):
            high = candles[i]['high']
            low = candles[i]['low']

            if low <= tp_price and not hit_tp:
                hit_tp = True
            if high >= sl_price and not hit_sl:
                hit_sl = True

            pnl = (entry_price - candles[i]['close']) / entry_price * 100
            worst_pnl = min(worst_pnl, pnl)
            best_pnl = max(best_pnl, pnl)

        if hit_tp and not hit_sl:
            outcome = 'WIN_TP'
            final_pnl = TP_PCT - 2 * FEE_PCT
        elif hit_sl and not hit_tp:
            outcome = 'LOSS_SL'
            final_pnl = -SL_PCT - 2 * FEE_PCT
        elif hit_tp and hit_sl:
            outcome = 'UNCERTAIN'
            final_pnl = 0
        else:
            final_pnl = (entry_price - candles[end_idx]['close']) / entry_price * 100 - 2 * FEE_PCT
            outcome = 'WIN' if final_pnl > 0 else 'LOSS'

        results[horizon] = {
            'outcome': outcome,
            'pnl': round(final_pnl, 4),
            'best_pnl': round(best_pnl, 4),
            'worst_pnl': round(worst_pnl, 4),
        }

    return results


def backtest_token(token: str, candles: list) -> list:
    """Backtest v4 SHORT signal on one token's candle data.
    Returns list of signal dicts with results."""
    if len(candles) < PERIOD + 50:
        return []

    closes = [c['close'] for c in candles]
    ema300 = _ema_series(closes, PERIOD)

    signals = []
    cooldown_until = 0

    # Step through with stride for speed
    for idx in range(PERIOD + 30, len(candles), STRIDE):
        if idx < cooldown_until:
            continue

        # Build prices list for detection
        prices_list = [{'price': closes[i], 'timestamp': candles[i]['ts']}
                       for i in range(max(0, idx - 700), idx + 1)]

        sig = detect_accel_300_v4_short(token, prices_list)
        if sig is None:
            continue

        entry_price = closes[idx]
        ts = candles[idx]['ts']
        dt_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M') if ts else 'N/A'

        results = simulate_trade(candles, idx, entry_price)

        # Collect bonus info
        volumes = [c['volume'] for c in candles[max(0, idx-30):idx+1] if c['volume']]
        vol_spike = _check_volume_spike(volumes) if len(volumes) >= 10 else False

        window_closes = closes[max(0, idx-20):idx+1]
        window_ema = ema300[max(0, idx-20):idx+1]
        resist_rej = _check_price_at_resistance(window_closes, window_ema)

        full_window = closes[max(0, idx-20):idx+1]
        rsi_s = _rsi_series(full_window, 14)
        rsi_div = _check_rsi_divergence(full_window, rsi_s)

        mom_shift = _check_momentum_shift(closes[max(0, idx-20):idx+1])

        signal_data = {
            'token': token,
            'timestamp': ts,
            'datetime': dt_str,
            'entry_price': entry_price,
            'gap_pct': sig['gap_pct'],
            'gap_accel': sig['gap_acceleration'],
            'rsi': sig['rsi'],
            'vol_spike': vol_spike,
            'resist_rej': resist_rej,
            'rsi_div': rsi_div,
            'mom_shift': mom_shift,
            'results': results,
        }
        signals.append(signal_data)

        cooldown_until = idx + ACCEL_300_V4_SHORT_COOLDOWN_BARS

    return signals


def print_results(all_signals: list, tokens_scanned: list):
    """Print backtest results as formatted tables."""
    print("\n" + "=" * 110)
    print("ACCEL-300 V4 SHORT BACKTEST RESULTS")
    print("=" * 110)
    print(f"Total signals found: {len(all_signals)}")
    print(f"Tokens scanned: {len(tokens_scanned)}")
    print(f"SL: {SL_PCT}%  |  TP: {TP_PCT}%  |  Fees: {FEE_PCT}% per side")
    print(f"Stride: {STRIDE} candles  |  Horizons: {HORIZONS} minutes")
    print()

    if not all_signals:
        print("No signals found.")
        return

    # ── Overall stats by horizon ──
    for horizon in HORIZONS:
        horizon_signals = [s for s in all_signals if horizon in s['results']]
        if not horizon_signals:
            continue

        wins = [s for s in horizon_signals if s['results'][horizon]['outcome'] in ('WIN', 'WIN_TP')]
        losses = [s for s in horizon_signals if s['results'][horizon]['outcome'] in ('LOSS', 'LOSS_SL')]
        uncertain = [s for s in horizon_signals if s['results'][horizon]['outcome'] == 'UNCERTAIN']

        total_pnl = sum(s['results'][horizon]['pnl'] for s in horizon_signals)
        wr = len(wins) / len(horizon_signals) * 100 if horizon_signals else 0
        avg_pnl = total_pnl / len(horizon_signals) if horizon_signals else 0

        print(f"── {horizon}m Horizon ──────────────────────────────────────────")
        print(f"  Signals: {len(horizon_signals)}  |  Wins: {len(wins)}  |  Losses: {len(losses)}  |  Uncertain: {len(uncertain)}")
        print(f"  Win Rate: {wr:.1f}%  |  Total PnL: {total_pnl:+.2f}%  |  Avg PnL: {avg_pnl:+.4f}%")
        print()

    # ── Per-token breakdown (120m horizon) ──
    print("── Per-Token Breakdown (120m horizon) ───────────────────────")
    token_stats = defaultdict(lambda: {'signals': 0, 'wins': 0, 'pnl': 0})
    for s in all_signals:
        if 120 in s['results']:
            t = s['token']
            token_stats[t]['signals'] += 1
            token_stats[t]['pnl'] += s['results'][120]['pnl']
            if s['results'][120]['outcome'] in ('WIN', 'WIN_TP'):
                token_stats[t]['wins'] += 1

    sorted_tokens = sorted(token_stats.items(), key=lambda x: x[1]['pnl'], reverse=True)
    print(f"  {'Token':10s} {'Signals':>7s} {'Wins':>5s} {'WR':>6s} {'PnL%':>8s}")
    print(f"  {'-'*10} {'-'*7} {'-'*5} {'-'*6} {'-'*8}")
    for token, stats in sorted_tokens[:20]:
        wr = stats['wins'] / stats['signals'] * 100 if stats['signals'] > 0 else 0
        print(f"  {token:10s} {stats['signals']:7d} {stats['wins']:5d} {wr:5.1f}% {stats['pnl']:+8.2f}%")
    print()

    # ── Top 20 best setups (by 120m PnL) ──
    print("── Top 20 Best Setups (by 120m PnL) ────────────────────────")
    signals_120 = [s for s in all_signals if 120 in s['results']]
    signals_120.sort(key=lambda x: x['results'][120]['pnl'], reverse=True)

    print(f"  {'#':>3s} {'Token':10s} {'Datetime':18s} {'Entry':>10s} {'Gap%':>7s} {'Accel%':>7s} {'RSI':>5s} {'30m':>7s} {'60m':>7s} {'120m':>7s} {'Bonuses'}")
    print(f"  {'-'*3} {'-'*10} {'-'*18} {'-'*10} {'-'*7} {'-'*7} {'-'*5} {'-'*7} {'-'*7} {'-'*7} {'-'*15}")
    for i, s in enumerate(signals_120[:20], 1):
        bonuses = []
        if s.get('vol_spike'): bonuses.append('V')
        if s.get('resist_rej'): bonuses.append('R')
        if s.get('rsi_div'): bonuses.append('D')
        if s.get('mom_shift'): bonuses.append('M')
        bonus_str = ','.join(bonuses) if bonuses else '-'

        pnl_30 = s['results'].get(30, {}).get('pnl', 0)
        pnl_60 = s['results'].get(60, {}).get('pnl', 0)
        pnl_120 = s['results'][120]['pnl']

        print(f"  {i:3d} {s['token']:10s} {s['datetime']:18s} {s['entry_price']:10.6g} "
              f"{s['gap_pct']:7.3f} {s['gap_accel']:7.3f} {s['rsi']:5.1f} "
              f"{pnl_30:+7.3f} {pnl_60:+7.3f} {pnl_120:+7.3f} {bonus_str}")
    print()

    # ── Top 20 worst setups ──
    print("── Top 20 Worst Setups (by 120m PnL) ──────────────────────")
    signals_120.sort(key=lambda x: x['results'][120]['pnl'])

    print(f"  {'#':>3s} {'Token':10s} {'Datetime':18s} {'Entry':>10s} {'Gap%':>7s} {'Accel%':>7s} {'RSI':>5s} {'30m':>7s} {'60m':>7s} {'120m':>7s} {'Bonuses'}")
    print(f"  {'-'*3} {'-'*10} {'-'*18} {'-'*10} {'-'*7} {'-'*7} {'-'*5} {'-'*7} {'-'*7} {'-'*7} {'-'*15}")
    for i, s in enumerate(signals_120[:20], 1):
        bonuses = []
        if s.get('vol_spike'): bonuses.append('V')
        if s.get('resist_rej'): bonuses.append('R')
        if s.get('rsi_div'): bonuses.append('D')
        if s.get('mom_shift'): bonuses.append('M')
        bonus_str = ','.join(bonuses) if bonuses else '-'

        pnl_30 = s['results'].get(30, {}).get('pnl', 0)
        pnl_60 = s['results'].get(60, {}).get('pnl', 0)
        pnl_120 = s['results'][120]['pnl']

        print(f"  {i:3d} {s['token']:10s} {s['datetime']:18s} {s['entry_price']:10.6g} "
              f"{s['gap_pct']:7.3f} {s['gap_accel']:7.3f} {s['rsi']:5.1f} "
              f"{pnl_30:+7.3f} {pnl_60:+7.3f} {pnl_120:+7.3f} {bonus_str}")
    print()

    # ── Bonus filter analysis ──
    print("── Bonus Filter Effectiveness (120m horizon) ───────────────")
    for bonus_name, bonus_key in [('Volume Spike', 'vol_spike'), ('Resistance Rejection', 'resist_rej'),
                                   ('RSI Divergence', 'rsi_div'), ('Momentum Shift', 'mom_shift')]:
        with_bonus = [s for s in signals_120 if s.get(bonus_key)]
        without_bonus = [s for s in signals_120 if not s.get(bonus_key)]

        wr_with = sum(1 for s in with_bonus if s['results'][120]['outcome'] in ('WIN', 'WIN_TP')) / len(with_bonus) * 100 if with_bonus else 0
        wr_without = sum(1 for s in without_bonus if s['results'][120]['outcome'] in ('WIN', 'WIN_TP')) / len(without_bonus) * 100 if without_bonus else 0
        avg_pnl_with = sum(s['results'][120]['pnl'] for s in with_bonus) / len(with_bonus) if with_bonus else 0
        avg_pnl_without = sum(s['results'][120]['pnl'] for s in without_bonus) / len(without_bonus) if without_bonus else 0

        print(f"  {bonus_name:22s}: with={len(with_bonus):3d} WR={wr_with:5.1f}% avg={avg_pnl_with:+.3f}%  "
              f"without={len(without_bonus):3d} WR={wr_without:5.1f}% avg={avg_pnl_without:+.3f}%")

    # ── V3 vs V4 comparison note ──
    print()
    print("── V4 vs V3 Key Differences ───────────────────────────────")
    print("  V4 fires BEFORE the drop (lower gap_accel threshold: 0.10 vs 0.20)")
    print("  V4 adds bonus filters: vol_spike, resistance_rejection, rsi_divergence, momentum_shift")
    print("  V4 lower velocity threshold (0.03% vs 0.05%)")
    print("  V4 lower slope threshold (0.0003 vs 0.0005)")
    print("  V4 wider fresh cross window (10 vs 8 bars)")
    print("  Bonuses: V=volume_spike, R=resistance_rej, D=rsi_divergence, M=momentum_shift")
    print("=" * 110)


def main():
    print("=" * 110)
    print("ACCEL-300 V4 SHORT BACKTEST (OPTIMIZED)")
    print("=" * 110)
    print(f"SL: {SL_PCT}%  |  TP: {TP_PCT}%  |  Fees: {FEE_PCT}% per side")
    print(f"Horizons: {HORIZONS} minutes  |  Stride: {STRIDE} candles  |  Max tokens: {MAX_TOKENS}")
    print()

    tokens = get_tokens()
    tokens = tokens[:MAX_TOKENS]  # limit for speed
    print(f"Scanning {len(tokens)} tokens (top by candle count)")

    all_signals = []
    t0 = time.time()
    for i, (token, count) in enumerate(tokens):
        t1 = time.time()
        print(f"  [{i+1}/{len(tokens)}] {token} ({count} candles)...", end=' ', flush=True)
        candles = load_candles(token)
        if not candles:
            print("SKIP (no data)")
            continue

        signals = backtest_token(token, candles)
        all_signals.extend(signals)
        elapsed = time.time() - t1
        print(f"{len(signals)} signals ({elapsed:.1f}s)")

    total_time = time.time() - t0
    print(f"\nBacktest completed in {total_time:.1f}s")

    print_results(all_signals, tokens)


if __name__ == '__main__':
    main()
