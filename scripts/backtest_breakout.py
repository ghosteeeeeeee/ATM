#!/usr/bin/env python3
"""
backtest_breakout.py — Historical backtest of the breakout engine.

Tests on multiple tokens over a date range to see how the compression→breakout
pattern would have performed historically.

Usage:
    python3 backtest_breakout.py                        # all tokens, last 7 days
    python3 backtest_breakout.py --days 30 --token BNB BTC  # specific tokens
    python3 backtest_breakout.py --verbose             # per-trade details
"""

import sys, os, json, sqlite3, argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERMES_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'data')
CANDLES_DB  = os.path.join(HERMES_DATA, 'candles.db')

# ── Config (same as breakout_engine.py) ─────────────────────────────────────
COMPRESSION_BARS_1m = 8    # must match breakout_engine.py
COMPRESSION_BARS_5m = 6
VOL_COMP_THRESHOLD_ABS  = 250   # max volume per bar to qualify as compressed
RNG_COMP_THRESHOLD_PCT_ABS = 0.20  # max range_pct per bar to qualify as compressed
VOL_SPIKE_THRESHOLD  = 0.30
VOL_POP_THRESHOLD    = 3.0
BREAKOUT_RANGE_PCT   = 0.50
ATR_PERIOD            = 14
RISK_RATIO            = 1.5   # TP = SL * RISK_RATIO
FIXED_STOP_PCT        = 0.50   # Fixed % stop (used instead of ATR * 1.5 when USE_FIXED_STOP=True)
USE_FIXED_STOP        = True  # Use fixed % stop instead of ATR multiplier
TIME_EXIT_BARS        = 120   # Exit after this many bars if SL/TP not hit (120 = ~2h on 1m)
MIN_AVG_VOL          = 30.0

TIMEFRAMES = ['1m', '5m']


def get_candles_range(token: str, timeframe: str, start_ts: int, end_ts: int) -> List[dict]:
    """Get candles in a specific time range for backtesting."""
    table = f'candles_{timeframe}'
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    c = conn.cursor()
    c.execute(f'''
        SELECT ts, open, high, low, close, volume
        FROM {table}
        WHERE token = ? AND ts >= ? AND ts <= ?
        ORDER BY ts ASC
    ''', (token.upper(), start_ts, end_ts))
    rows = c.fetchall()
    conn.close()
    return [{
        'ts': r[0],
        'open': float(r[1]),
        'high': float(r[2]),
        'low': float(r[3]),
        'close': float(r[4]),
        'volume': float(r[5]),
        'dt': datetime.fromtimestamp(r[0]).strftime('%Y-%m-%d %H:%M'),
    } for r in rows]


def rolling_avg_vol(candles: List[dict], window: int = 20) -> float:
    if len(candles) < window:
        return sum(c['volume'] for c in candles) / max(len(candles), 1)
    return sum(c['volume'] for c in candles[-window:]) / window


def rolling_avg_range(candles: List[dict], window: int = 20) -> float:
    if len(candles) < window:
        return sum((c['high'] - c['low']) / c['open'] * 100 for c in candles) / max(len(candles), 1)
    return sum((c['high'] - c['low']) / c['open'] * 100 for c in candles[-window:]) / window


def compute_atr(candles: List[dict], period: int = ATR_PERIOD) -> float:
    if len(candles) < period + 1:
        return 0.0
    trs = []
    for i in range(len(candles) - period, len(candles)):
        c = candles[i]
        p = candles[i - 1]
        high_low = c['high'] - c['low']
        high_close = abs(c['high'] - p['close'])
        low_close = abs(c['low'] - p['close'])
        tr = max(high_low, high_close, low_close)
        trs.append(tr)
    return sum(trs) / len(trs) if trs else 0.0


def detect_compression(candles: List[dict], comp_bars: int) -> Tuple[bool, dict]:
    """
    Phase 1: Detect compression (tight range + low volume for comp_bars consecutive bars).

    Uses ABSOLUTE thresholds — the window must itself be quiet in absolute terms.
    This avoids the bug where a single noisy bar in the window inflated the
    baseline and made the "quiet window" look noisy relative to itself.

    3 conditions, all must pass:
      (a) 80%+ of bars: volume < VOL_COMP_THRESHOLD_ABS
      (b) 80%+ of bars: range_pct < RNG_COMP_THRESHOLD_PCT_ABS
      (c) Price change during the window < 1%
    """
    if len(candles) < comp_bars + 10:
        return False, {}

    comp_window = candles[-comp_bars:]
    rng_pcts    = [(c['high'] - c['low']) / c['open'] * 100 for c in comp_window]
    vols        = [c['volume'] for c in comp_window]

    avg_vol     = sum(vols)     / len(vols)
    avg_rng_pct = sum(rng_pcts) / len(rng_pcts)

    # (a) 80%+ of bars quiet in absolute volume
    quiet_vol_bars = sum(1 for v in vols if v < VOL_COMP_THRESHOLD_ABS)
    pct_vol_quiet = quiet_vol_bars / len(vols)

    # (b) 80%+ of bars tight in absolute range_pct
    tight_rng_bars = sum(1 for r in rng_pcts if r < RNG_COMP_THRESHOLD_PCT_ABS)
    pct_rng_tight = tight_rng_bars / len(rng_pcts)

    # (c) Price doesn't trend more than 1% during compression
    price_chg  = abs(comp_window[-1]['close'] - comp_window[0]['open']) / comp_window[0]['open'] * 100
    price_ok   = price_chg < 1.0

    compressed = bool(pct_vol_quiet >= 0.80 and pct_rng_tight >= 0.80 and price_ok)

    stats = {
        'avg_vol':      round(avg_vol, 1),
        'avg_rng_pct':  round(avg_rng_pct, 3),
        'pct_vol_quiet': round(pct_vol_quiet * 100, 1),
        'pct_rng_tight': round(pct_rng_tight * 100, 1),
        'price_chg':    round(price_chg, 3),
        'comp_bars':    comp_bars,
        'last_close':   candles[-1]['close'],
    }
    return compressed, stats


def detect_breakout(candles: List[dict], direction: str) -> Tuple[bool, dict]:
    """
    Phase 3: breakout candle.
    Uses same comp_bars as compression detection for consistency.
    """
    if len(candles) < 5:
        return False, {}

    # Use same comp_bars as compression
    comp_bars = COMPRESSION_BARS_1m
    prior_window = candles[-(comp_bars + 1):-1]
    if len(prior_window) < 3:
        return False, {}
    prior_avg_vol = sum(c['volume'] for c in prior_window) / len(prior_window)

    c = candles[-1]
    prev = candles[-2]

    vol_ratio  = c['volume'] / max(prior_avg_vol, 1)
    range_pct  = (c['high'] - c['low']) / c['open'] * 100
    is_bullish = c['close'] > c['open']
    is_bearish = c['close'] < c['open']

    vol_ok   = vol_ratio >= VOL_POP_THRESHOLD
    rng_ok   = range_pct >= BREAKOUT_RANGE_PCT
    dir_ok   = (direction == 'LONG' and is_bullish) or (direction == 'SHORT' and is_bearish)

    prev_vol_ratio = prev['volume'] / max(prior_avg_vol, 1)
    first_big_vol  = prev_vol_ratio < VOL_POP_THRESHOLD * 0.8

    is_breakout = vol_ok and rng_ok and dir_ok and first_big_vol

    stats = {
        'vol_ratio': vol_ratio,
        'range_pct': range_pct,
        'price': c['close'],
        'dt': c['dt'],
    }
    return is_breakout, stats


def detect_breakout_direction(candles: List[dict], comp_bars: int) -> Optional[str]:
    if len(candles) < comp_bars + 5:
        return None

    prev_window  = candles[-comp_bars-5:-comp_bars] if len(candles) >= comp_bars + 5 else candles[-comp_bars:]
    comp_window = candles[-comp_bars:]

    comp_high = max(c['high'] for c in comp_window)
    comp_low  = min(c['low']  for c in comp_window)
    prev_high = max(c['high'] for c in prev_window) if prev_window else comp_high
    prev_low  = min(c['low']  for c in prev_window) if prev_window else comp_low

    current_close = candles[-1]['close']

    if current_close > prev_high * 1.001:
        return 'LONG'
    elif current_close < prev_low * 0.999:
        return 'SHORT'
    return None



def compute_levels(candles: List[dict], direction: str) -> dict:
    atr   = compute_atr(candles)
    price = candles[-1]['close']

    if USE_FIXED_STOP:
        # Fixed % stop/target — no ATR dependency
        stop_dist_pct = FIXED_STOP_PCT
        target_dist_pct = stop_dist_pct * RISK_RATIO
    else:
        # ATR-based stop
        stop_dist_pct = (atr / price) * 100 * 1.5
        target_dist_pct = stop_dist_pct * RISK_RATIO

    if direction == 'LONG':
        entry  = price
        stop   = price * (1 - stop_dist_pct / 100)
        target = price * (1 + target_dist_pct / 100)
    else:
        entry  = price
        stop   = price * (1 + stop_dist_pct / 100)
        target = price * (1 - target_dist_pct / 100)

    risk_pct   = stop_dist_pct
    reward_pct = target_dist_pct

    return {
        'entry': round(entry, 4),
        'stop':  round(stop, 4),
        'target': round(target, 4),
        'atr':   round(atr, 4),
        'risk_pct': round(risk_pct, 3),
        'reward_pct': round(reward_pct, 3),
    }


def simulate_trade(
    candles: List[dict],
    entry_price: float,
    direction: str,
    stop_price: float,
    target_price: float,
    entry_idx: int,
    timeframe: str
) -> dict:
    """
    Walk forward from entry_idx and simulate the trade outcome.
    Returns dict with outcome details.
    """
    is_long = direction == 'LONG'

    for i in range(entry_idx + 1, len(candles)):
        c = candles[i]
        high, low = c['high'], c['low']

        # Stop hit
        if is_long and low <= stop_price:
            exit_price = stop_price
            pnl_pct = (exit_price - entry_price) / entry_price * 100
            return {
                'outcome': 'STOP_HIT',
                'exit_price': exit_price,
                'exit_dt': c['dt'],
                'pnl_pct': round(pnl_pct, 3),
                'bars_held': i - entry_idx,
                'max_favorable': 0,
            }
        elif not is_long and high >= stop_price:
            exit_price = stop_price
            pnl_pct = (entry_price - exit_price) / entry_price * 100
            return {
                'outcome': 'STOP_HIT',
                'exit_price': exit_price,
                'exit_dt': c['dt'],
                'pnl_pct': round(pnl_pct, 3),
                'bars_held': i - entry_idx,
                'max_favorable': 0,
            }

        # Target hit
        if is_long and high >= target_price:
            exit_price = target_price
            pnl_pct = (exit_price - entry_price) / entry_price * 100
            return {
                'outcome': 'TARGET_HIT',
                'exit_price': exit_price,
                'exit_dt': c['dt'],
                'pnl_pct': round(pnl_pct, 3),
                'bars_held': i - entry_idx,
                'max_favorable': round((target_price - entry_price) / entry_price * 100, 3),
            }
        elif not is_long and low <= target_price:
            exit_price = target_price
            pnl_pct = (entry_price - exit_price) / entry_price * 100
            return {
                'outcome': 'TARGET_HIT',
                'exit_price': exit_price,
                'exit_dt': c['dt'],
                'pnl_pct': round(pnl_pct, 3),
                'bars_held': i - entry_idx,
                'max_favorable': round((entry_price - target_price) / entry_price * 100, 3),
            }

    # Exhausted all candles — no exit
    last = candles[-1]
    last_price = last['close']
    pnl_pct = (last_price - entry_price) / entry_price * 100 if is_long \
              else (entry_price - last_price) / entry_price * 100
    return {
        'outcome': 'NO_EXIT',
        'exit_price': last_price,
        'exit_dt': last['dt'],
        'pnl_pct': round(pnl_pct, 3),
        'bars_held': len(candles) - entry_idx,
        'max_favorable': round(pnl_pct, 3),
    }


def backtest_token(
    token: str,
    start_ts: int,
    end_ts: int,
    timeframe: str = '1m',
    verbose: bool = False
) -> List[dict]:
    """
    Backtest breakout signals for one token over the given time range.
    Uses a rolling window — after a trade is entered, we skip compression
    detection until the trade is closed (no re-entry until current trade resolves).
    """
    candles = get_candles_range(token, timeframe, start_ts, end_ts)
    if len(candles) < 50:
        return []

    comp_bars = COMPRESSION_BARS_1m if timeframe == '1m' else COMPRESSION_BARS_5m
    trades = []
    in_trade = False
    trade_entry_idx = None
    pending_breakout = None  # compression detected, waiting for breakout

    for i in range(20, len(candles) - 5):  # need warmup + room to exit
        window = candles[:i+1]  # up to current bar

        if in_trade:
            # Check if trade should close (stop or target)
            c = candles[i]
            levels = pending_breakout['levels']
            direction = pending_breakout['direction']
            is_long = direction == 'LONG'

            # Stop check
            if is_long and c['low'] <= levels['stop']:
                exit_price = levels['stop']
                pnl_pct = (exit_price - pending_breakout['entry']) / pending_breakout['entry'] * 100
                pending_breakout['result'] = {
                    'outcome': 'STOP_HIT',
                    'exit_price': exit_price,
                    'exit_dt': c['dt'],
                    'pnl_pct': round(pnl_pct, 3),
                    'bars_held': i - trade_entry_idx,
                }
                trades.append(pending_breakout)
                in_trade = False
                pending_breakout = None
                continue
            elif not is_long and c['high'] >= levels['stop']:
                exit_price = levels['stop']
                pnl_pct = (pending_breakout['entry'] - exit_price) / pending_breakout['entry'] * 100
                pending_breakout['result'] = {
                    'outcome': 'STOP_HIT',
                    'exit_price': exit_price,
                    'exit_dt': c['dt'],
                    'pnl_pct': round(pnl_pct, 3),
                    'bars_held': i - trade_entry_idx,
                }
                trades.append(pending_breakout)
                in_trade = False
                pending_breakout = None
                continue

            # Target check
            if is_long and c['high'] >= levels['target']:
                exit_price = levels['target']
                pnl_pct = (exit_price - pending_breakout['entry']) / pending_breakout['entry'] * 100
                pending_breakout['result'] = {
                    'outcome': 'TARGET_HIT',
                    'exit_price': exit_price,
                    'exit_dt': c['dt'],
                    'pnl_pct': round(pnl_pct, 3),
                    'bars_held': i - trade_entry_idx,
                }
                trades.append(pending_breakout)
                in_trade = False
                pending_breakout = None
                continue
            elif not is_long and c['low'] <= levels['target']:
                exit_price = levels['target']
                pnl_pct = (pending_breakout['entry'] - exit_price) / pending_breakout['entry'] * 100
                pending_breakout['result'] = {
                    'outcome': 'TARGET_HIT',
                    'exit_price': exit_price,
                    'exit_dt': c['dt'],
                    'pnl_pct': round(pnl_pct, 3),
                    'bars_held': i - trade_entry_idx,
                }
                trades.append(pending_breakout)
                in_trade = False
                pending_breakout = None
                continue

            # Time-based exit: if held > TIME_EXIT_BARS, exit at market
            if i - trade_entry_idx > TIME_EXIT_BARS:
                c = candles[i]
                exit_price = c['close']
                pnl_pct = (exit_price - pending_breakout['entry']) / pending_breakout['entry'] * 100 if is_long \
                          else (pending_breakout['entry'] - exit_price) / pending_breakout['entry'] * 100
                pending_breakout['result'] = {
                    'outcome': 'TIME_EXIT',
                    'exit_price': exit_price,
                    'exit_dt': c['dt'],
                    'pnl_pct': round(pnl_pct, 3),
                    'bars_held': i - trade_entry_idx,
                }
                trades.append(pending_breakout)
                in_trade = False
                pending_breakout = None
                continue

        else:
            # Not in trade — look for compression + breakout setup
            is_compressed, comp_stats = detect_compression(window, comp_bars)

            if is_compressed:
                direction = detect_breakout_direction(window, comp_bars)
                if direction:
                    is_breakout, brk_stats = detect_breakout(window, direction)
                    if is_breakout:
                        levels = compute_levels(window, direction)
                        pending_breakout = {
                            'token': token.upper(),
                            'direction': direction,
                            'timeframe': timeframe,
                            'levels': levels,
                            'entry': levels['entry'],
                            'stop': levels['stop'],
                            'target': levels['target'],
                            'atr': levels['atr'],
                            'risk_pct': levels['risk_pct'],
                            'reward_pct': levels['reward_pct'],
                            'entry_dt': candles[i]['dt'],
                            'entry_idx': i,
                            'compression_dt': candles[i - comp_bars]['dt'],
                            'compression_bars': comp_bars,
                            'compression_price_chg': comp_stats['price_chg'],
                            'vol_ratio': round(brk_stats['vol_ratio'], 1),
                            'range_pct': round(brk_stats['range_pct'], 2),
                            'avg_vol': round(comp_stats['avg_vol'], 1),
                            'result': None,
                        }
                        in_trade = True
                        trade_entry_idx = i

                        if verbose:
                            print(f"  [{token}] ENTRY {direction} @ {levels['entry']:.4f} "
                                  f"(SL={levels['stop']:.4f} TP={levels['target']:.4f}) "
                                  f"vol={brk_stats['vol_ratio']}x rng={brk_stats['range_pct']}% "
                                  f"comp={comp_bars} bars, {comp_stats['price_chg']}% price chg in compression")

    return trades


def get_all_tokens(candles_db_path: str) -> List[str]:
    """Get all tokens that have 1m candle data."""
    conn = sqlite3.connect(candles_db_path, timeout=10)
    c = conn.cursor()
    c.execute('''
        SELECT DISTINCT token FROM candles_1m
        WHERE ts > strftime('%s', 'now', '-7 days')
        ORDER BY token
    ''')
    tokens = [r[0] for r in c.fetchall()]
    conn.close()
    return tokens


def main():
    parser = argparse.ArgumentParser(description='Backtest breakout engine')
    parser.add_argument('--days', type=int, default=7, help='Days to look back (default: 7)')
    parser.add_argument('--token', nargs='+', help='Specific token(s) to test')
    parser.add_argument('--timeframe', default='1m', choices=['1m', '5m'], help='Timeframe (default: 1m)')
    parser.add_argument('--verbose', action='store_true', help='Per-trade details')
    args = parser.parse_args()

    end_ts   = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=args.days)).timestamp())

    print(f"\n{'='*80}")
    print(f"BACKTEST: Breakout Engine — {args.days} days ({datetime.fromtimestamp(start_ts)} to {datetime.fromtimestamp(end_ts)})")
    print(f"Timeframe: {args.timeframe}")
    print(f"{'='*80}\n")

    if args.token:
        tokens = [t.upper() for t in args.token]
    else:
        tokens = get_all_tokens(CANDLES_DB)
        print(f"Testing {len(tokens)} tokens...\n")

    all_trades = []
    token_results = {}

    for token in tokens:
        try:
            trades = backtest_token(
                token=token,
                start_ts=start_ts,
                end_ts=end_ts,
                timeframe=args.timeframe,
                verbose=args.verbose
            )
            for t in trades:
                t['token'] = token.upper()
            all_trades.extend(trades)
            token_results[token.upper()] = trades
        except Exception as e:
            print(f"  [{token}] ERROR: {e}")

    # ── Summary ───────────────────────────────────────────────────────────────
    if not all_trades:
        print("No trades generated. Try --days 30 or a different timeframe.")
        return

    wins   = [t for t in all_trades if t['result'] and t['result']['pnl_pct'] > 0]
    losses = [t for t in all_trades if t['result'] and t['result']['pnl_pct'] <= 0]
    stops  = [t for t in all_trades if t['result'] and t['result']['outcome'] == 'STOP_HIT']
    targets= [t for t in all_trades if t['result'] and t['result']['outcome'] == 'TARGET_HIT']
    time_exits = [t for t in all_trades if t['result'] and t['result']['outcome'] == 'TIME_EXIT']

    total_pnl = sum(t['result']['pnl_pct'] for t in all_trades if t['result'])
    wr = len(wins) / len(all_trades) * 100 if all_trades else 0
    avg_win = sum(t['result']['pnl_pct'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['result']['pnl_pct'] for t in losses) / len(losses) if losses else 0
    rr = abs(avg_win / avg_loss) if avg_loss else 0

    print(f"\n{'='*80}")
    print(f"OVERALL RESULTS — {len(all_trades)} trades")
    print(f"{'='*80}")
    print(f"  Win Rate:        {len(wins)}/{len(all_trades)} = {wr:.1f}%")
    print(f"  Total PnL:       {total_pnl:+.2f}%")
    print(f"  Avg Win:         {avg_win:+.3f}%")
    print(f"  Avg Loss:        {avg_loss:+.3f}%")
    print(f"  Win/Loss Ratio:  {rr:.2f}")
    print(f"  Stop Hits:       {len(stops)} ({len(stops)/len(all_trades)*100:.1f}%)")
    print(f"  Target Hits:     {len(targets)} ({len(targets)/len(all_trades)*100:.1f}%)")
    print(f"  Time Exits:      {len(time_exits)} ({len(time_exits)/len(all_trades)*100:.1f}%)")

    # Per-token breakdown
    print(f"\n{'='*80}")
    print(f"PER-TOKEN BREAKDOWN")
    print(f"{'='*80}")
    print(f"{'TOKEN':<12} {'TRADES':<7} {'WR%':<6} {'PnL%':<8} {'AVG_W':<7} {'AVG_L':<7} {'BEST':<8} {'WORST':<8}")
    print(f"{'-'*70}")

    token_summary = []
    for tok, trades in sorted(token_results.items(), key=lambda x: -sum(t['result']['pnl_pct'] for t in x[1] if t['result'])):
        if not trades:
            continue
        t_results = [t['result'] for t in trades if t['result']]
        if not t_results:
            continue
        t_wins  = [r for r in t_results if r['pnl_pct'] > 0]
        t_loss  = [r for r in t_results if r['pnl_pct'] <= 0]
        t_wr    = len(t_wins) / len(t_results) * 100 if t_results else 0
        t_pnl   = sum(r['pnl_pct'] for r in t_results)
        t_avg_w = sum(r['pnl_pct'] for r in t_wins) / len(t_wins) if t_wins else 0
        t_avg_l = sum(r['pnl_pct'] for r in t_loss) / len(t_loss) if t_loss else 0
        t_best  = max(r['pnl_pct'] for r in t_results)
        t_worst = min(r['pnl_pct'] for r in t_results)
        token_summary.append({
            'token': tok, 'trades': len(trades), 'wr': t_wr, 'pnl': t_pnl,
            'avg_w': t_avg_w, 'avg_l': t_avg_l, 'best': t_best, 'worst': t_worst
        })
        print(f"{tok:<12} {len(trades):<7} {t_wr:<6.1f} {t_pnl:<+8.2f} {t_avg_w:<+7.2f} {t_avg_l:<+7.2f} {t_best:<+8.2f} {t_worst:<+8.2f}")

    # Show best trades
    print(f"\n{'='*80}")
    print(f"BEST 10 TRADES")
    print(f"{'='*80}")
    best = sorted([t for t in all_trades if t['result']], key=lambda x: x['result']['pnl_pct'], reverse=True)[:10]
    print(f"{'TOKEN':<10} {'DIR':<6} {'ENTRY':<10} {'EXIT':<10} {'PnL%':<7} {'OUTCOME':<12} {'BARS':<5} {'DT'}")
    print(f"{'-'*80}")
    for t in best:
        r = t['result']
        print(f"{t['token']:<10} {t['direction']:<6} {t['entry']:<10.4f} {r['exit_price']:<10.4f} {r['pnl_pct']:>+6.2f}% {r['outcome']:<12} {r['bars_held']:<5} {t['entry_dt']}")

    # Show worst trades
    print(f"\n{'='*80}")
    print(f"WORST 10 TRADES")
    print(f"{'='*80}")
    worst = sorted([t for t in all_trades if t['result']], key=lambda x: x['result']['pnl_pct'])[:10]
    print(f"{'TOKEN':<10} {'DIR':<6} {'ENTRY':<10} {'EXIT':<10} {'PnL%':<7} {'OUTCOME':<12} {'BARS':<5} {'DT'}")
    print(f"{'-'*80}")
    for t in worst:
        r = t['result']
        print(f"{t['token']:<10} {t['direction']:<6} {t['entry']:<10.4f} {r['exit_price']:<10.4f} {r['pnl_pct']:>+6.2f}% {r['outcome']:<12} {r['bars_held']:<5} {t['entry_dt']}")

    print(f"\n{'='*80}")
    print(f"PARAMETERS USED")
    print(f"{'='*80}")
    print(f"  COMPRESSION_BARS_{args.timeframe}: {COMPRESSION_BARS_1m if args.timeframe == '1m' else COMPRESSION_BARS_5m}")
    print(f"  VOL_SPIKE_THRESHOLD:   {VOL_SPIKE_THRESHOLD} (compression: vol < {VOL_SPIKE_THRESHOLD*100:.0f}% of avg)")
    print(f"  VOL_POP_THRESHOLD:    {VOL_POP_THRESHOLD}x (breakout: vol > {VOL_POP_THRESHOLD}x avg)")
    print(f"  BREAKOUT_RANGE_PCT:   {BREAKOUT_RANGE_PCT}% min candle range for breakout")
    print(f"  RISK_RATIO:           {RISK_RATIO} (TP = SL * {RISK_RATIO})")
    print(f"  ATR_PERIOD:           {ATR_PERIOD}")
    print()


if __name__ == '__main__':
    main()
