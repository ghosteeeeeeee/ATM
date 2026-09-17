#!/usr/bin/env python3
"""
DEFINITIVE independent analysis: Test proposed RSI 30-60 filter for open-skies signal.

Uses 1h candles (full history) as proxy for RSI/trend since 5m candles are pruned.
This is a reasonable approximation for filtering analysis.
"""

import sys, sqlite3, datetime, numpy as np
sys.path.insert(0, '/root/.hermes/scripts')
from paths import HERMES_DATA, CANDLES_DB

RUNTIME_DB = f'{HERMES_DATA}/signals_hermes_runtime.db'
CANDLES_1H = CANDLES_DB  # candles.db has candles_1h with full history


def ts_text_to_unix(ts_text):
    dt = datetime.datetime.strptime(ts_text, '%Y-%m-%d %H:%M:%S')
    return int(dt.timestamp())


def get_candles_1h(token, target_unix, limit=100):
    conn = sqlite3.connect(CANDLES_1H, timeout=10)
    cur = conn.cursor()
    cur.execute("""
        SELECT ts, open, high, low, close, volume
        FROM candles_1h
        WHERE token = ? AND is_closed = 1 AND ts <= ?
        ORDER BY ts DESC
        LIMIT ?
    """, (token.upper(), target_unix, limit))
    rows = cur.fetchall()
    conn.close()
    return list(reversed(rows))


def get_candles_5m(token, target_unix, limit=100):
    conn = sqlite3.connect(CANDLES_1H, timeout=10)
    cur = conn.cursor()
    cur.execute("""
        SELECT ts, open, high, low, close, volume
        FROM candles_5m
        WHERE token = ? AND is_closed = 1 AND ts <= ?
        ORDER BY ts DESC
        LIMIT ?
    """, (token.upper(), target_unix, limit))
    rows = cur.fetchall()
    conn.close()
    return list(reversed(rows))


def compute_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    deltas = np.diff(closes[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def get_trend(closes, window=5):
    if len(closes) < window:
        return 'UNKNOWN'
    recent = closes[-window:]
    if recent[-1] > recent[0] * 1.001:
        return 'UP'
    elif recent[-1] < recent[0] * 0.999:
        return 'DOWN'
    return 'FLAT'


def count_higher_highs(highs, window=10):
    if len(highs) < window:
        return 0
    recent = highs[-window:]
    count = 0
    for i in range(1, len(recent)):
        if recent[i] > recent[i - 1]:
            count += 1
    return count


def get_sr_map(token, price):
    try:
        from risk_reward_engine import build_sr_map
        return build_sr_map(token, price)
    except:
        return []


def main():
    # Get all trades
    conn = sqlite3.connect(RUNTIME_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, token, direction, signal_type, is_win, pnl_pct, pnl_usdt,
               confidence, regime, created_at, closed_at
        FROM signal_outcomes
        WHERE signal_type LIKE '%open-skies%'
        ORDER BY created_at ASC
    """)
    trades = cur.fetchall()
    conn.close()

    print(f"="*140)
    print(f"INDEPENDENT AUDIT: Open-Skies Filter Analysis")
    print(f"="*140)
    print(f"Total open-skies trades: {len(trades)}")
    print(f"Data source: 1h candles (full history) as proxy for 5m candles (pruned)")
    print()

    results = []
    data_issues = []

    for trade in trades:
        trade_id, token, direction, signal_type, is_win, pnl_pct, pnl_usdt, confidence, regime, created_at, closed_at = trade

        target_unix = ts_text_to_unix(created_at)

        # Try 5m first (only has recent data), fall back to 1h
        candles = get_candles_5m(token, target_unix, limit=100)
        candle_source = '5m'
        if not candles or len(candles) < 60:
            candles = get_candles_1h(token, target_unix, limit=100)
            candle_source = '1h'

        if not candles or len(candles) < 60:
            data_issues.append(f"{token} ({created_at}) - no candle data at all")
            results.append({
                'trade_id': trade_id, 'token': token, 'created_at': created_at,
                'pnl_pct': pnl_pct, 'is_win': is_win, 'regime': regime,
                'signal_type': signal_type, 'rsi': None, 'trend': 'UNKNOWN',
                'higher_highs': 0, 'support_count': None, 'resistance_count': None,
                'filter_pass': False, 'data_quality': 'NO_DATA',
                'candle_source': 'none',
            })
            continue

        closes = [c[4] for c in candles]
        highs = [c[2] for c in candles]
        price = closes[-1]

        rsi = compute_rsi(closes)
        trend = get_trend(closes)
        hh_count = count_higher_highs(highs, window=10)

        # S/R
        sr_map = get_sr_map(token, price)
        support_count = len([l for l in sr_map if l.get('type') == 'support'])
        resistance_count = len([l for l in sr_map if l.get('type') == 'resistance'])

        # Current S/R is at current time, not historical - mark this
        sr_quality = 'CURRENT'  # S/R is current, not historical

        # Filter: trend UP AND RSI 30-60
        filter_pass = (trend == 'UP' and rsi is not None and 30 <= rsi <= 60)

        candle_ts = candles[-1][0]
        staleness_min = (target_unix - candle_ts) / 60

        result = {
            'trade_id': trade_id, 'token': token, 'created_at': created_at,
            'pnl_pct': pnl_pct, 'is_win': is_win, 'regime': regime,
            'signal_type': signal_type, 'rsi': round(rsi, 2) if rsi else None,
            'trend': trend, 'higher_highs': hh_count,
            'support_count': support_count, 'resistance_count': resistance_count,
            'price': round(price, 6), 'filter_pass': filter_pass,
            'data_quality': 'OK', 'candle_source': candle_source,
            'sr_quality': sr_quality, 'staleness_min': staleness_min,
        }
        results.append(result)

    # ── Print detailed results ──
    print(f"{'Token':8s} {'Created':19s} {'PnL':>8s} {'W/L':4s} {'RSI':>6s} {'Trend':5s} {'HH':>3s} {'Sup':>4s} {'Res':>4s} {'Regime':8s} {'Src':3s} {'Filter':6s}")
    print("-"*100)

    for r in results:
        if r['data_quality'] != 'OK':
            print(f"{r['token']:8s} {r['created_at']}  {'NO DATA':>8s}  {'?':4s}")
            continue
        status = 'WIN' if r['is_win'] else 'LOSS'
        filter_s = 'PASS' if r['filter_pass'] else 'BLOCK'
        rsi_str = f"{r['rsi']:6.1f}" if r['rsi'] is not None else '  N/A'
        sup_str = f"{r['support_count']}" if r['support_count'] is not None else 'N/A'
        res_str = f"{r['resistance_count']}" if r['resistance_count'] is not None else 'N/A'
        print(f"{r['token']:8s} {r['created_at']}  {r['pnl_pct']:+7.2f}%  {status:4s} {rsi_str}  {r['trend']:5s}  {r['higher_highs']:2d}  {sup_str:>4s}  {res_str:>4s}  {r['regime']:8s}  {r['candle_source']:3s}  {filter_s}")

    # ── Summary ──
    valid = [r for r in results if r['data_quality'] == 'OK']
    passed = [r for r in valid if r['filter_pass']]
    blocked = [r for r in valid if not r['filter_pass']]
    wins_pass = [r for r in passed if r['is_win']]
    losses_pass = [r for r in passed if not r['is_win']]
    wins_block = [r for r in blocked if r['is_win']]
    losses_block = [r for r in blocked if not r['is_win']]

    print(f"\n{'='*140}")
    print(f"RESULTS")
    print(f"{'='*140}")
    print(f"Valid trades: {len(valid)} / {len(results)}")
    print(f"Data issues: {len(data_issues)}")

    print(f"\n--- CURRENT SIGNAL (OPEN_SKIES_MAX_RSI=75) ---")
    current_wins = [r for r in valid if r['is_win']]
    current_losses = [r for r in valid if not r['is_win']]
    current_wr = len(current_wins) / len(valid) * 100 if valid else 0
    current_pnl = sum(r['pnl_pct'] for r in valid)
    print(f"Trades: {len(valid)}  Wins: {len(current_wins)}  Losses: {len(current_losses)}  WR: {current_wr:.1f}%  Total PnL: {current_pnl:+.2f}%")

    print(f"\n--- PROPOSED FILTER: trend UP AND RSI 30-60 ---")
    print(f"Would PASS (trade):  {len(passed)} / {len(valid)} ({len(passed)/len(valid)*100:.1f}%)" if valid else "No valid trades")
    if passed:
        print(f"  Wins:  {len(wins_pass)}")
        print(f"  Losses: {len(losses_pass)}")
        wr = len(wins_pass)/len(passed)*100
        avg = sum(r['pnl_pct'] for r in passed)/len(passed)
        tot = sum(r['pnl_pct'] for r in passed)
        print(f"  WR: {wr:.1f}%  Avg PnL: {avg:.2f}%  Total PnL: {tot:+.2f}%")

    print(f"\nWould BLOCK (skip):  {len(blocked)} / {len(valid)} ({len(blocked)/len(valid)*100:.1f}%)" if valid else "")
    if blocked:
        print(f"  Wins:  {len(wins_block)}")
        print(f"  Losses: {len(losses_block)}")
        wr = len(wins_block)/len(blocked)*100
        avg = sum(r['pnl_pct'] for r in blocked)/len(blocked)
        tot = sum(r['pnl_pct'] for r in blocked)
        print(f"  WR: {wr:.1f}%  Avg PnL: {avg:.2f}%  Total PnL: {tot:+.2f}%")

    # ── Big winners ──
    print(f"\n--- BIG WINNERS (>= +2%) ---")
    big = [r for r in valid if r['pnl_pct'] >= 2.0]
    big_blocked = [r for r in big if not r['filter_pass']]
    for bw in big:
        s = 'BLOCKED' if not bw['filter_pass'] else 'PASSED'
        rsi_s = f"{bw['rsi']:.1f}" if bw['rsi'] else 'N/A'
        print(f"  {bw['token']:8s} {bw['pnl_pct']:+7.2f}%  RSI={rsi_s}  trend={bw['trend']}  → {s}")
    if big_blocked:
        print(f"\n  ⚠️  {len(big_blocked)} BIG WINNER(S) WOULD BE BLOCKED!")
    else:
        print(f"\n  ✅ No big winners blocked.")

    # ── Block reason breakdown ──
    print(f"\n--- BLOCK REASON BREAKDOWN ---")
    for r in blocked:
        if r['rsi'] is None or r['trend'] == 'UNKNOWN':
            reason = "NO DATA"
        else:
            reasons = []
            if r['trend'] != 'UP':
                reasons.append(f"trend={r['trend']}")
            if r['rsi'] < 30:
                reasons.append(f"RSI={r['rsi']:.1f}<30")
            elif r['rsi'] > 60:
                reasons.append(f"RSI={r['rsi']:.1f}>60")
            reason = ' + '.join(reasons) if reasons else 'UNKNOWN'
        w = 'W' if r['is_win'] else 'L'
        print(f"  {r['token']:8s} {r['pnl_pct']:+7.2f}%  {w}  reason: {reason}")

    # ── Critical analysis ──
    print(f"\n--- CRITICAL ANALYSIS ---")
    print(f"1. TREND FILTER IMPACT:")
    trend_up = [r for r in valid if r['trend'] == 'UP']
    trend_not_up = [r for r in valid if r['trend'] != 'UP']
    print(f"   Trades with trend=UP: {len(trend_up)}/{len(valid)} ({len(trend_up)/len(valid)*100:.1f}%)" if valid else "")
    if trend_up:
        tw = sum(1 for r in trend_up if r['is_win'])
        print(f"   trend=UP wins: {tw}/{len(trend_up)} ({tw/len(trend_up)*100:.1f}%)")
    if trend_not_up:
        tnw = sum(1 for r in trend_not_up if r['is_win'])
        print(f"   trend!=UP wins: {tnw}/{len(trend_not_up)} ({tnw/len(trend_not_up)*100:.1f}%)")

    print(f"\n2. RSI DISTRIBUTION OF WINS:")
    win_rsis = [(r['token'], r['rsi'], r['pnl_pct']) for r in valid if r['is_win'] and r['rsi'] is not None]
    for tok, rsi, pnl in sorted(win_rsis, key=lambda x: x[1]):
        in_range = '✓' if 30 <= rsi <= 60 else '✗'
        print(f"   {tok:8s} RSI={rsi:6.1f}  PnL={pnl:+7.2f}%  {in_range}")

    print(f"\n3. S/R DATA QUALITY:")
    print(f"   NOTE: S/R data is CURRENT (not historical). Signals fired with")
    print(f"   different S/R maps. Support/resistance counts may not reflect")
    print(f"   actual conditions at signal time.")

    if data_issues:
        print(f"\n4. DATA ISSUES:")
        for issue in data_issues:
            print(f"   - {issue}")

    print(f"\n{'='*140}")
    print(f"VERDICT COMPARISON WITH CLAIMS")
    print(f"{'='*140}")

    # Claims to check
    claim_total_pass = len(passed)
    claim_wins_pass = len(wins_pass)
    claim_losses_pass = len(losses_pass)
    claim_wr = len(wins_pass)/len(passed)*100 if passed else 0

    claim_total_blocked = len(blocked)
    claim_wins_blocked = len(wins_block)
    claim_losses_blocked = len(losses_block)

    print(f"\nClaim 1: '87% win rate (13W/2L) with filter'")
    print(f"  Actual: {len(wins_pass)}W/{len(losses_pass)}L = {claim_wr:.1f}% WR on {len(passed)} trades")
    print(f"  Status: {'AGREE' if claim_wr >= 85 and len(passed) >= 10 else 'DISAGREE or INCONCLUSIVE'}")

    print(f"\nClaim 2: 'Only 3 small winners blocked (+0.28%, +0.60%, +2.32%)'")
    print(f"  Actual: {len(wins_block)} winners blocked")
    blocked_win_pnls = sorted([r['pnl_pct'] for r in wins_block])
    print(f"  Blocked win PnLs: {blocked_win_pnls}")
    print(f"  Status: {'AGREE' if len(wins_block) <= 3 else 'DISAGREE'}")

    print(f"\nClaim 3: '9/11 losers would be caught'")
    print(f"  Actual: {len(losses_block)}/{len(losses_block) + len(losses_pass)} losers caught")
    print(f"  Status: {'AGREE' if len(losses_block) >= 9 else 'DISAGREE'}")

    print(f"\nClaim 4: 'Only change needed is tightening RSI from max 75 to max 60'")
    print(f"  Status: NEEDS VERIFICATION - see RSI distribution above")

    return results


if __name__ == '__main__':
    main()
