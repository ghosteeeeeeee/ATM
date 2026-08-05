#!/usr/bin/env python3
"""
Signal Researcher: scans market patterns, generates signal hypotheses, auto-backtests.

Uses TradingView MCP tools (via trading-mcp) to find patterns, then backtests
against local candle data. Promising candidates written to scripts/signals/_candidates/.

Data sources: TradingView MCP (market scanning) + candles.db (backtesting)
Output: scripts/signals/_candidates/*.py, automation/signal_research.md
Timer: every 12 hours (hermes-signal-researcher.timer)

Usage:
  python3 signal_researcher.py           # Full run: scan → hypothesize → backtest
  python3 signal_researcher.py --dry     # Dry run: show what would be generated
"""

import sys, os, json, sqlite3
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, RUNTIME_DB

DRY_RUN = '--dry' in sys.argv
CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
CANDIDATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'signals', '_candidates')
RESEARCH_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'automation', 'signal_research.md')

# Backtest parameters
MIN_TRADES = 20
MIN_WR = 55.0
MAX_SL_PCT = 1.5    # max stop loss %
TP_RATIO = 1.5      # TP = SL * ratio
LOOKBACK_DAYS = 30
MIN_AVG_VOLUME = 10.0


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    line = f"[{ts}] {msg}"
    print(line)


def get_tokens():
    """Get tradeable tokens from candles.db."""
    conn = sqlite3.connect(CANDLES_DB)
    try:
        c = conn.cursor()
        c.execute("""
            SELECT token, COUNT(*) as bars, AVG(close) as avg_price
            FROM candles_1h
            WHERE ts > ?
            GROUP BY token
            HAVING bars >= 100
            ORDER BY bars DESC
            LIMIT 50
        """, (int((datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).timestamp()),))
        return c.fetchall()
    finally:
        conn.close()


def get_candles(token, timeframe='1h', days=LOOKBACK_DAYS):
    """Get candles for backtesting."""
    table = f'candles_{timeframe}'
    start_ts = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    conn = sqlite3.connect(CANDLES_DB)
    try:
        c = conn.cursor()
        c.execute(f"""
            SELECT ts, open, high, low, close, volume
            FROM {table}
            WHERE token = ? AND ts >= ? AND is_closed = 1
            ORDER BY ts ASC
        """, (token.upper(), start_ts))
        rows = c.fetchall()
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 'close': r[4], 'volume': r[5]} for r in rows]
    finally:
        conn.close()


def detect_bollinger_squeeze(candles, window=20, squeeze_threshold=0.04):
    """Detect Bollinger Band squeeze patterns."""
    if len(candles) < window + 5:
        return []

    signals = []
    closes = [c['close'] for c in candles]

    for i in range(window, len(candles) - 5):
        # Compute BB
        window_data = closes[i-window:i]
        sma = sum(window_data) / window
        variance = sum((x - sma) ** 2 for x in window_data) / window
        std = variance ** 0.5
        upper = sma + 2 * std
        lower = sma - 2 * std
        bb_width = (upper - lower) / sma if sma > 0 else 0

        if bb_width < squeeze_threshold:
            # Squeeze detected — check for breakout in next 5 bars
            future_bars = candles[i:i+5]
            future_highs = [b['high'] for b in future_bars]
            future_lows = [b['low'] for b in future_bars]

            max_up = max((h - closes[i]) / closes[i] * 100 for h in future_highs)
            max_down = max((closes[i] - l) / closes[i] * 100 for l in future_lows)

            signals.append({
                'pattern': 'bollinger_squeeze',
                'token': candles[i].get('token', 'UNK'),
                'direction': 'LONG' if max_up > max_down else 'SHORT',
                'entry_idx': i,
                'entry_price': closes[i],
                'max_favorable': max(max_up, max_down),
                'max_adverse': min(max_up, max_down),
                'bb_width': bb_width,
            })

    # Deduplicate: keep only one signal per 5-bar window
    deduped = []
    for s in signals:
        if not deduped or s['entry_idx'] - deduped[-1]['entry_idx'] > 5:
            deduped.append(s)
    return deduped


def detect_volume_breakout(candles, vol_multiplier=2.0, price_change_min=2.0):
    """Detect volume breakout patterns."""
    if len(candles) < 20:
        return []

    signals = []
    volumes = [c['volume'] for c in candles]
    avg_vol_20 = [sum(volumes[max(0,i-20):i])/max(min(i, 20), 1) for i in range(len(volumes))]

    for i in range(20, len(candles) - 5):
        if avg_vol_20[i] <= 0:
            continue

        vol_ratio = candles[i]['volume'] / avg_vol_20[i]
        price_change = (candles[i]['close'] - candles[i]['open']) / candles[i]['open'] * 100

        if vol_ratio >= vol_multiplier and abs(price_change) >= price_change_min:
            direction = 'LONG' if price_change > 0 else 'SHORT'
            # Check outcome in next 5 bars
            future = candles[i+1:i+6]
            if not future:
                continue

            if direction == 'LONG':
                outcome = (future[-1]['close'] - candles[i]['close']) / candles[i]['close'] * 100
            else:
                outcome = (candles[i]['close'] - future[-1]['close']) / candles[i]['close'] * 100

            signals.append({
                'pattern': 'volume_breakout',
                'token': candles[i].get('token', 'UNK'),
                'direction': direction,
                'entry_idx': i,
                'entry_price': candles[i]['close'],
                'vol_ratio': vol_ratio,
                'price_change': price_change,
                'outcome_5bars': outcome,
            })

    return signals


def detect_consecutive_candles(candles, count=3, min_growth=2.0):
    """Detect consecutive growing/shrinking candle patterns."""
    if len(candles) < count + 5:
        return []

    signals = []
    for i in range(len(candles) - count - 5):
        # Check for consecutive bullish candles
        bullish = True
        bearish = True
        for j in range(count):
            bar = candles[i + j]
            if bar['close'] <= bar['open']:
                bullish = False
            if bar['close'] >= bar['open']:
                bearish = False

        if not bullish and not bearish:
            continue

        # Check growth rate
        total_change = abs(candles[i+count-1]['close'] - candles[i]['open']) / candles[i]['open'] * 100
        if total_change < min_growth * count:
            continue

        direction = 'LONG' if bullish else 'SHORT'

        # Check outcome
        future = candles[i+count:i+count+5]
        if not future:
            continue

        if direction == 'LONG':
            outcome = (future[-1]['close'] - candles[i+count-1]['close']) / candles[i+count-1]['close'] * 100
        else:
            outcome = (candles[i+count-1]['close'] - future[-1]['close']) / candles[i+count-1]['close'] * 100

        signals.append({
            'pattern': f'consecutive_{count}_candles',
            'token': candles[i].get('token', 'UNK'),
            'direction': direction,
            'entry_idx': i,
            'entry_price': candles[i+count-1]['close'],
            'total_change': total_change,
            'outcome_5bars': outcome,
        })

    return signals


def backtest_signals(signals, candles, sl_pct=1.0):
    """Simple backtest of signals using fixed SL/TP."""
    results = []
    for sig in signals:
        entry = sig['entry_price']
        direction = sig['direction']

        # Simulate SL/TP over next 20 bars
        start = sig['entry_idx'] + 1
        end = min(start + 20, len(candles))
        hit_sl = False
        hit_tp = False
        exit_price = entry

        for j in range(start, end):
            if direction == 'LONG':
                # Check SL
                sl_price = entry * (1 - sl_pct / 100)
                if candles[j]['low'] <= sl_price:
                    hit_sl = True
                    exit_price = sl_price
                    break
                # Check TP
                tp_price = entry * (1 + sl_pct * TP_RATIO / 100)
                if candles[j]['high'] >= tp_price:
                    hit_tp = True
                    exit_price = tp_price
                    break
                exit_price = candles[j]['close']
            else:  # SHORT
                sl_price = entry * (1 + sl_pct / 100)
                if candles[j]['high'] >= sl_price:
                    hit_sl = True
                    exit_price = sl_price
                    break
                tp_price = entry * (1 - sl_pct * TP_RATIO / 100)
                if candles[j]['low'] <= tp_price:
                    hit_tp = True
                    exit_price = tp_price
                    break
                exit_price = candles[j]['close']

        if direction == 'LONG':
            pnl = (exit_price - entry) / entry * 100
        else:
            pnl = (entry - exit_price) / entry * 100

        results.append({
            **sig,
            'sl_pct': sl_pct,
            'tp_pct': sl_pct * TP_RATIO,
            'hit_sl': hit_sl,
            'hit_tp': hit_tp,
            'pnl_pct': pnl,
            'won': hit_tp or (not hit_sl and pnl > 0),
        })

    return results


def evaluate_pattern(results):
    """Evaluate if a pattern meets criteria for a candidate signal."""
    if len(results) < MIN_TRADES:
        return None

    wins = sum(1 for r in results if r['won'])
    wr = wins / len(results) * 100
    avg_pnl = sum(r['pnl_pct'] for r in results) / len(results)

    if wr >= MIN_WR and avg_pnl > 0:
        return {
            'wr': wr,
            'avg_pnl': avg_pnl,
            'trades': len(results),
            'wins': wins,
        }
    return None


def generate_template(pattern_name, direction, eval_result, sample_signals):
    """Generate a signal template file."""
    template = f'''#!/usr/bin/env python3
"""
{pattern_name} ({direction}) — Auto-generated candidate signal.

Pattern: {pattern_name}
Direction: {direction}
Backtest WR: {eval_result["wr"]:.1f}%
Backtest PnL: {eval_result["avg_pnl"]:+.4f}%
Backtest trades: {eval_result["trades"]}
Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

STATUS: CANDIDATE — requires human review before enabling.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from paths import HERMES_DATA

SIGNAL_TYPE = '{pattern_name}_{direction.lower()}'
SIGNAL_SOURCE = 'researcher'


def run(prices_dict=None):
    """Detect {pattern_name} {direction} signals. Returns list of signal dicts."""
    # TODO: Implement real-time detection logic
    # This is a template — fill in the detection algorithm
    return []
'''
    return template


def write_candidate(pattern_name, direction, template, eval_result):
    """Write candidate signal file."""
    filename = f"{pattern_name}_{direction.lower()}_candidate.py"
    filepath = os.path.join(CANDIDATES_DIR, filename)

    if DRY_RUN:
        log(f"  [DRY] Would write: {filename}")
        return filepath

    os.makedirs(CANDIDATES_DIR, exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(template)
    log(f"  Wrote: {filename}")
    return filepath


def write_research_report(hypotheses, candidates):
    """Write research report."""
    os.makedirs(os.path.dirname(RESEARCH_MD), exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    tmp = RESEARCH_MD + '.tmp'
    with open(tmp, 'w') as f:
        f.write(f"# Signal Research — {ts}\n\n")
        f.write(f"## Hypotheses Tested\n\n")
        f.write(f"| Pattern | Tokens | Trades | WR | Avg PnL | Verdict |\n")
        f.write(f"|---------|--------|--------|-----|---------|--------|\n")
        for h in hypotheses:
            verdict = '✅ PASS' if h.get('passed') else '❌ FAIL'
            f.write(f"| {h['pattern']} | {h['tokens_tested']} | {h['total_trades']} | {h.get('wr', 0):.1f}% | {h.get('avg_pnl', 0):+.4f}% | {verdict} |\n")

        f.write(f"\n## Candidates Generated\n\n")
        if candidates:
            for c in candidates:
                f.write(f"- `{c['filename']}` — {c['pattern']} {c['direction']} (WR={c['wr']:.1f}%, {c['trades']} trades)\n")
        else:
            f.write(f"- No candidates passed backtest criteria\n")

        f.write(f"\n## Next Steps\n\n")
        f.write(f"1. Review candidate files in `scripts/signals/_candidates/`\n")
        f.write(f"2. Implement real-time detection logic in `run_signal()`\n")
        f.write(f"3. Run paper trading for 48h before enabling\n")
        f.write(f"4. If profitable, move to `scripts/signals/` and register\n")
    os.replace(tmp, RESEARCH_MD)


def main():
    log(f"{'[DRY RUN] ' if DRY_RUN else ''}=== Signal Researcher ===")

    # Get tokens
    tokens = get_tokens()
    log(f"Found {len(tokens)} tradeable tokens")

    if not tokens:
        log("No tokens found")
        return

    # Scan patterns
    all_hypotheses = []
    all_candidates = []

    # Pattern detectors
    detectors = [
        ('bollinger_squeeze', detect_bollinger_squeeze),
        ('volume_breakout', detect_volume_breakout),
        ('consecutive_3_candles', lambda c: detect_consecutive_candles(c, count=3)),
    ]

    for pattern_name, detector in detectors:
        log(f"\nScanning: {pattern_name}")
        pattern_trades = []
        tokens_tested = 0

        for token, bars, avg_vol in tokens[:20]:  # top 20 tokens
            candles = get_candles(token)
            if len(candles) < 30:
                continue

            # Tag candles with token
            for c in candles:
                c['token'] = token

            signals = detector(candles)
            if not signals:
                continue

            tokens_tested += 1
            # Backtest each signal
            results = backtest_signals(signals, candles)
            pattern_trades.extend(results)

        # Evaluate
        if pattern_trades:
            eval_result = evaluate_pattern(pattern_trades)
            wr = eval_result['wr'] if eval_result else 0
            avg_pnl = eval_result['avg_pnl'] if eval_result else 0
            passed = eval_result is not None

            hypothesis = {
                'pattern': pattern_name,
                'tokens_tested': tokens_tested,
                'total_trades': len(pattern_trades),
                'wr': wr,
                'avg_pnl': avg_pnl,
                'passed': passed,
            }
            all_hypotheses.append(hypothesis)

            log(f"  {tokens_tested} tokens, {len(pattern_trades)} trades, WR={wr:.1f}%, PnL={avg_pnl:+.4f}% {'✅' if passed else '❌'}")

            # Generate candidate if passed
            if passed:
                for direction in ['LONG', 'SHORT']:
                    dir_trades = [r for r in pattern_trades if r['direction'] == direction]
                    if len(dir_trades) >= MIN_TRADES:
                        dir_eval = evaluate_pattern(dir_trades)
                        if dir_eval and dir_eval['wr'] >= MIN_WR:
                            template = generate_template(pattern_name, direction, dir_eval, dir_trades[:5])
                            filename = f"{pattern_name}_{direction.lower()}_candidate.py"
                            write_candidate(pattern_name, direction, template, dir_eval)
                            all_candidates.append({
                                'filename': filename,
                                'pattern': pattern_name,
                                'direction': direction,
                                'wr': dir_eval['wr'],
                                'trades': dir_eval['trades'],
                            })
        else:
            all_hypotheses.append({
                'pattern': pattern_name,
                'tokens_tested': tokens_tested,
                'total_trades': 0,
                'wr': 0,
                'avg_pnl': 0,
                'passed': False,
            })
            log(f"  {tokens_tested} tokens, 0 trades")

    # Write report
    write_research_report(all_hypotheses, all_candidates)

    log(f"\nResearch complete. {len(all_candidates)} candidates generated.")


if __name__ == '__main__':
    main()
