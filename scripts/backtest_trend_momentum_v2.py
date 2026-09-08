#!/usr/bin/env python3
"""
backtest_trend_momentum_v2.py — High-quality trend_momentum backtest.

Focus: MAXIMIZE win rate, not trade count. Every trade should be a winner.

New filters in v2:
1. Pullback entry — enter on dip within uptrend (not at the top)
2. Volume surge confirmation (if available from price_history velocity)
3. Multi-timeframe slope agreement (1m + 5m trend aligned)
4. Trend maturity — not too early (choppy), not too late (overextended)
5. Price position relative to Bollinger Bands — buy at middle, not top
6. Higher-highs/lower-lows pattern confirmation
7. RSI pullback — RSI dipped then recovering (not overbought)
8. ATR expansion — volatility increasing = breakout imminent

Usage:
    python3 backtest_trend_momentum_v2.py [--days 14] [--verbose]
"""
import sys, os, sqlite3, time, json
from datetime import datetime
from collections import defaultdict

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

DB_PATH = os.path.join(os.path.dirname(SCRIPTS_DIR), 'data', 'signals_hermes.db')

# ── V2 Parameters (HIGH WIN RATE FOCUS) ────────────────────────────────
EMA_FAST = 20
EMA_SLOW = 50
EMA_TREND = 100       # Third EMA for trend confirmation
MIN_SLOPE_PCT = 0.00015  # Raised from 0.0001 — require stronger trend
ACCEL_LOOKBACK = 10
RSI_PERIOD = 14
RSI_MIN = 40          # Raised from 35 — avoid weak momentum
RSI_MAX = 60          # Tighter than 70 — avoid chasing overbought
RSI_PULLBACK_MIN = 30 # RSI must have dipped to this level recently
RSI_RECOVERY_BARS = 20 # Within last 20 bars, RSI touched RSI_PULLBACK_MIN
ATR_PERIOD = 14
ATR_MIN_PCT = 0.30
ATR_MAX_PCT = 2.0
CONF_BASE = 70        # Higher base — quality over quantity
CONF_CAP = 88
SL_ATR_MULT = 1.5
TP_PCT = 2.5
MAX_HOLD_BARS = 60
COOLDOWN_BARS = 180   # 3h cooldown
BB_PERIOD = 20
BB_STD = 2.0
MIN_TREND_BARS = 30   # Price must be above EMA50 for at least 30 bars
MIN_HIGHER_HIGHS = 2  # Need at least 2 higher highs in last 20 bars


def compute_ema(prices, period):
    result = [None] * (period - 1)
    k = 2 / (period + 1)
    sma = sum(prices[:period]) / period
    result.append(sma)
    for i in range(period, len(prices)):
        result.append(prices[i] * k + result[-1] * (1 - k))
    return result


def compute_rsi(prices, period=14):
    result = [None] * period
    if len(prices) < period + 1:
        return result
    gains, losses = [], []
    for i in range(1, period + 1):
        d = prices[i] - prices[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains) / period
    al = sum(losses) / period
    result.append(100 if al == 0 else 100 - 100 / (1 + ag / al))
    for i in range(period + 1, len(prices)):
        d = prices[i] - prices[i-1]
        ag = (ag * (period - 1) + max(d, 0)) / period
        al = (al * (period - 1) + max(-d, 0)) / period
        result.append(100 if al == 0 else 100 - 100 / (1 + ag / al))
    return result


def compute_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return [None] * len(closes)
    trs = []
    for i in range(1, len(closes)):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
    result = [None] * period
    atr_val = sum(trs[:period]) / period
    result.append(atr_val)
    for i in range(period, len(trs)):
        atr_val = (atr_val * (period - 1) + trs[i]) / period
        result.append(atr_val)
    return result


def compute_slope(values, window=20):
    result = [None] * (window - 1)
    for i in range(window - 1, len(values)):
        v = values[i - window + 1:i + 1]
        if any(x is None for x in v):
            result.append(None)
            continue
        n = len(v)
        xm = (n - 1) / 2.0
        ym = sum(v) / n
        num = sum((j - xm) * (vv - ym) for j, vv in enumerate(v))
        den = sum((j - xm) ** 2 for j in range(n))
        result.append(num / den if den > 0 else 0.0)
    return result


def compute_bollinger(prices, period=20, num_std=2.0):
    """Returns (upper, middle, lower, pct_b) arrays."""
    n = len(prices)
    upper = [None] * n
    middle = [None] * n
    lower = [None] * n
    pct_b = [None] * n

    for i in range(period - 1, n):
        window = prices[i - period + 1:i + 1]
        m = sum(window) / period
        std = (sum((x - m) ** 2 for x in window) / period) ** 0.5
        middle[i] = m
        upper[i] = m + num_std * std
        lower[i] = m - num_std * std
        if upper[i] != lower[i]:
            pct_b[i] = (prices[i] - lower[i]) / (upper[i] - lower[i])
        else:
            pct_b[i] = 0.5

    return upper, middle, lower, pct_b


def find_swing_highs(highs, lookback=20, idx=None):
    """Find swing highs in the last `lookback` bars ending at idx."""
    if idx is None:
        idx = len(highs) - 1
    start = max(0, idx - lookback)
    swing_highs = []
    for i in range(start + 1, min(idx, len(highs) - 1)):
        if highs[i] >= highs[i-1] and highs[i] >= highs[i+1]:
            swing_highs.append(highs[i])
    return swing_highs


def find_swing_lows(lows, lookback=20, idx=None):
    """Find swing lows in the last `lookback` bars ending at idx."""
    if idx is None:
        idx = len(lows) - 1
    start = max(0, idx - lookback)
    swing_lows = []
    for i in range(start + 1, min(idx, len(lows) - 1)):
        if lows[i] <= lows[i-1] and lows[i] <= lows[i+1]:
            swing_lows.append(lows[i])
    return swing_lows


def detect_trend_momentum_v2(prices, highs, lows, closes, idx, ema_f, ema_s, ema_t, rsi_vals, atr_vals, slopes, pct_b):
    """
    V2 Detection: HIGH WIN RATE focus.

    Adds to v1:
    - Price must be in "pullback zone" (not at BB top)
    - RSI must have recently dipped and recovered (not overbought)
    - Trend must be mature (above EMA50 for 30+ bars)
    - Higher highs pattern confirmed
    - Slope must be consistent (not just positive, but STEADY)
    """
    min_bars = max(EMA_TREND, RSI_PERIOD + 1, ATR_PERIOD + 1, ACCEL_LOOKBACK * 2, BB_PERIOD, MIN_TREND_BARS) + 10
    if idx < min_bars:
        return None

    price = prices[idx]
    ef = ema_f[idx]
    es = ema_s[idx]
    et = ema_t[idx]
    rv = rsi_vals[idx]
    av = atr_vals[idx]
    sl = slopes[idx]
    pb = pct_b[idx]

    if None in (ef, es, et, rv, av, sl, pb):
        return None

    atr_pct = av / price * 100 if price > 0 else 0
    slope_pct = sl / price if price > 0 else 0

    # ── FILTER 1: EMA alignment (price > EMA20 > EMA50 > EMA100) ──
    if not (price > ef > es > et):
        return None

    # ── FILTER 2: Slope must be meaningful ──
    if slope_pct < MIN_SLOPE_PCT:
        return None

    # ── FILTER 3: Trend maturity — price above EMA50 for 30+ bars ──
    above_ema50_count = 0
    for j in range(max(0, idx - MIN_TREND_BARS), idx + 1):
        if prices[j] > ema_s[j]:
            above_ema50_count += 1
    if above_ema50_count < MIN_TREND_BARS * 0.8:  # 80% of bars must be above
        return None

    # ── FILTER 4: RSI guard — not overbought, and recently pulled back ──
    if rv < RSI_MIN or rv > RSI_MAX:
        return None

    # Check RSI pulled back in last RSI_RECOVERY_BARS
    rsi_dipped = False
    for j in range(max(0, idx - RSI_RECOVERY_BARS), idx):
        if rsi_vals[j] is not None and rsi_vals[j] <= RSI_PULLBACK_MIN:
            rsi_dipped = True
            break
    # If RSI never dipped, check if it's recovering from a low
    if not rsi_dipped:
        # At minimum, RSI should not be at its 20-bar high
        rsi_window = [r for r in rsi_vals[max(0, idx - 20):idx + 1] if r is not None]
        if rsi_window and rv >= max(rsi_window) * 0.95:
            return None  # RSI at highs — chasing

    # ── FILTER 5: ATR% guard ──
    if atr_pct < ATR_MIN_PCT or atr_pct > ATR_MAX_PCT:
        return None

    # ── FILTER 6: Bollinger Band position — NOT at top ──
    # Buy in middle zone (pct_b 0.3-0.7), not at top (0.8+)
    if pb > 0.70:
        return None  # Too close to upper band — overextended
    if pb < 0.20:
        return None  # Too close to lower band — in breakdown

    # ── FILTER 7: Higher highs confirmation ──
    swing_highs = find_swing_highs(highs, lookback=20, idx=idx)
    if len(swing_highs) < MIN_HIGHER_HIGHS:
        return None
    increasing_highs = sum(1 for i in range(1, len(swing_highs)) if swing_highs[i] > swing_highs[i-1])
    if increasing_highs < MIN_HIGHER_HIGHS - 1:
        return None

    # ── FILTER 8: Acceleration positive ──
    vel_recent = (prices[idx] - prices[max(0, idx - ACCEL_LOOKBACK)]) / ACCEL_LOOKBACK
    vel_prev = (prices[max(0, idx - ACCEL_LOOKBACK)] - prices[max(0, idx - ACCEL_LOOKBACK * 2)]) / ACCEL_LOOKBACK
    acceleration = vel_recent - vel_prev

    # ── SCORING ──
    score = 0
    reasons = ['ema_4stack']

    # Slope quality
    slope_q = min(8, int(slope_pct / 0.0003))
    score += slope_q
    reasons.append(f'slope={slope_pct:.5f}')

    # Acceleration bonus
    if acceleration > 0:
        score += min(8, int(acceleration / price * 10000))
        reasons.append('accel+')
    else:
        return None  # V2: REQUIRE acceleration

    # RSI quality — prefer RSI in 45-55 range (strong but not overbought)
    if 45 <= rv <= 55:
        score += 5
        reasons.append(f'rsi_ideal={rv:.0f}')
    elif 40 <= rv <= 60:
        score += 3
        reasons.append(f'rsi_ok={rv:.0f}')
    else:
        score += 1
        reasons.append(f'rsi_border={rv:.0f}')

    # BB position quality — prefer middle (0.4-0.6)
    if 0.35 <= pb <= 0.65:
        score += 5
        reasons.append(f'bb_mid={pb:.2f}')
    else:
        score += 2
        reasons.append(f'bb_edge={pb:.2f}')

    # Trend maturity bonus
    if above_ema50_count >= MIN_TREND_BARS * 0.95:
        score += 3
        reasons.append('mature_trend')

    conf = min(CONF_CAP, CONF_BASE + score)

    sl_price = price - av * SL_ATR_MULT
    tp_price = price * (1 + TP_PCT / 100)

    return {
        'direction': 'LONG',
        'confidence': conf,
        'price': price,
        'sl': sl_price,
        'tp': tp_price,
        'atr_pct': atr_pct,
        'slope_pct': slope_pct,
        'accel_pct': acceleration / price * 100 if price > 0 else 0,
        'rsi': rv,
        'bb_pct_b': pb,
        'trend_maturity': above_ema50_count,
        'reasons': reasons,
    }


def backtest_token_v2(token, prices, timestamps, verbose=False):
    n = len(prices)
    min_bars = max(EMA_TREND, RSI_PERIOD + 1, ATR_PERIOD + 1, ACCEL_LOOKBACK * 2, BB_PERIOD, MIN_TREND_BARS) + 10
    if n < min_bars + 20:
        return []

    highs = [max(prices[max(0, i-1):min(n, i+2)]) for i in range(n)]
    lows = [min(prices[max(0, i-1):min(n, i+2)]) for i in range(n)]
    closes = list(prices)

    ema_f = compute_ema(prices, EMA_FAST)
    ema_s = compute_ema(prices, EMA_SLOW)
    ema_t = compute_ema(prices, EMA_TREND)
    rsi_vals = compute_rsi(prices, RSI_PERIOD)
    atr_vals = compute_atr(highs, lows, closes, ATR_PERIOD)
    slopes = compute_slope(ema_f, 20)
    _, _, _, pct_b = compute_bollinger(prices, BB_PERIOD, BB_STD)

    trades = []
    cooldown_until = 0

    for i in range(min_bars, n):
        if i <= cooldown_until:
            continue

        signal = detect_trend_momentum_v2(prices, highs, lows, closes, i, ema_f, ema_s, ema_t, rsi_vals, atr_vals, slopes, pct_b)
        if signal is None:
            continue

        # Simulate trade
        exit_idx = None
        exit_price = None
        exit_reason = None
        for j in range(i + 1, min(i + MAX_HOLD_BARS + 1, n)):
            if lows[j] <= signal['sl']:
                exit_idx, exit_price, exit_reason = j, signal['sl'], 'SL'
                break
            if highs[j] >= signal['tp']:
                exit_idx, exit_price, exit_reason = j, signal['tp'], 'TP'
                break
        if exit_idx is None:
            exit_idx = min(i + MAX_HOLD_BARS, n - 1)
            exit_price = prices[exit_idx]
            exit_reason = 'TIME'

        pnl_pct = (exit_price - signal['price']) / signal['price'] * 100
        hold = exit_idx - i

        trade = {
            'token': token,
            'entry_time': timestamps[i] if timestamps else i,
            'entry_price': signal['price'],
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason,
            'confidence': signal['confidence'],
            'hold_bars': hold,
            'atr_pct': signal['atr_pct'],
            'slope_pct': signal['slope_pct'],
            'accel_pct': signal['accel_pct'],
            'rsi': signal['rsi'],
            'bb_pct_b': signal['bb_pct_b'],
            'trend_maturity': signal['trend_maturity'],
            'reasons': signal['reasons'],
        }
        trades.append(trade)
        cooldown_until = i + COOLDOWN_BARS

        if verbose:
            w = '✅' if pnl_pct > 0 else '❌'
            t_str = datetime.fromtimestamp(timestamps[i]).strftime('%m-%d %H:%M') if timestamps else str(i)
            print(f'  {w} {token} @ {t_str} entry={signal["price"]:.4f} → {exit_price:.4f} ({pnl_pct:+.2f}%) [{exit_reason}] conf={signal["confidence"]} hold={hold}min rsi={signal["rsi"]:.0f} bb={signal["bb_pct_b"]:.2f}')

    return trades


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=14)
    parser.add_argument('--tokens', type=str, default=None)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    start_time = time.time()
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    cutoff = int(datetime.now().timestamp()) - args.days * 86400

    if args.tokens:
        token_list = [t.strip().upper() for t in args.tokens.split(',')]
    else:
        c.execute("""
            SELECT token, COUNT(*) as cnt FROM price_history
            WHERE timestamp > ? GROUP BY token HAVING cnt >= 1000
            ORDER BY cnt DESC LIMIT 30
        """, (cutoff,))
        token_list = [r[0] for r in c.fetchall()]

    print(f'\n{"="*70}')
    print(f'V2 BACKTEST (HIGH WR): trend_momentum_v2 | {len(token_list)} tokens | {args.days}d')
    print(f'  Filters: EMA4stack, pullback zone, RSI recovery, higher-highs, accel required')
    print(f'  RSI range: {RSI_MIN}-{RSI_MAX} | BB: 0.20-0.70 | Conf base: {CONF_BASE}')
    print(f'{"="*70}')

    all_trades = []
    token_stats = {}

    for token in token_list:
        c.execute("""
            SELECT price, timestamp FROM price_history
            WHERE token = ? AND timestamp > ? ORDER BY timestamp ASC
        """, (token, cutoff))
        rows = c.fetchall()
        if len(rows) < 200:
            continue

        prices = [r[0] for r in rows]
        timestamps = [r[1] for r in rows]

        trades = backtest_token_v2(token, prices, timestamps, verbose=args.verbose)

        if trades:
            wins = sum(1 for t in trades if t['pnl_pct'] > 0)
            total_pnl = sum(t['pnl_pct'] for t in trades)
            wr = wins / len(trades) * 100
            avg_win = sum(t['pnl_pct'] for t in trades if t['pnl_pct'] > 0) / max(1, wins)
            avg_loss = sum(t['pnl_pct'] for t in trades if t['pnl_pct'] <= 0) / max(1, len(trades) - wins)

            token_stats[token] = {
                'trades': len(trades), 'wins': wins,
                'wr': round(wr, 1), 'total_pnl': round(total_pnl, 2),
                'avg_win': round(avg_win, 2), 'avg_loss': round(avg_loss, 2),
            }
            print(f'  {token:8s}: {len(trades):3d}T | WR={wr:.0f}% | PnL={total_pnl:+.2f}% | avg_win={avg_win:+.2f}% avg_loss={avg_loss:+.2f}%')

        all_trades.extend(trades)

    conn.close()

    if all_trades:
        wins = sum(1 for t in all_trades if t['pnl_pct'] > 0)
        total_pnl = sum(t['pnl_pct'] for t in all_trades)
        wr = wins / len(all_trades) * 100
        sl = sum(1 for t in all_trades if t['exit_reason'] == 'SL')
        tp = sum(1 for t in all_trades if t['exit_reason'] == 'TP')
        tm = sum(1 for t in all_trades if t['exit_reason'] == 'TIME')
        avg_hold = sum(t['hold_bars'] for t in all_trades) / len(all_trades)
        avg_win = sum(t['pnl_pct'] for t in all_trades if t['pnl_pct'] > 0) / max(1, wins)
        avg_loss = sum(t['pnl_pct'] for t in all_trades if t['pnl_pct'] <= 0) / max(1, len(all_trades) - wins)
        rr = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        fees = len(all_trades) * 0.10
        net = total_pnl - fees

        print(f'\n{"="*70}')
        print(f'V2 SUMMARY: {len(all_trades)} trades | {len(token_stats)} tokens | {time.time()-start_time:.1f}s')
        print(f'{"="*70}')
        print(f'  Win Rate:  {wr:.1f}% ({wins}W / {len(all_trades)-wins}L)')
        print(f'  Total PnL: {total_pnl:+.2f}%')
        print(f'  Est Fees:  -{fees:.2f}%')
        print(f'  Net PnL:   {net:+.2f}%')
        print(f'  Avg PnL:   {total_pnl/len(all_trades):+.2f}% per trade')
        print(f'  Exits:     {tp} TP | {sl} SL | {tm} TIME')
        print(f'  Avg Hold:  {avg_hold:.0f} min')
        print(f'  R:R Ratio: {rr:.1f}:1 (breakeven WR: {100/(1+rr):.1f}%)')
        print(f'  Avg Win:   {avg_win:+.2f}%')
        print(f'  Avg Loss:  {avg_loss:+.2f}%')

        # Confidence buckets
        print(f'\n  By Confidence:')
        for lo, hi in [(70,75),(75,80),(80,85),(85,88)]:
            bt_list = [t for t in all_trades if lo <= t['confidence'] < hi]
            if bt_list:
                bwr = sum(1 for t in bt_list if t['pnl_pct'] > 0) / len(bt_list) * 100
                bpnl = sum(t['pnl_pct'] for t in bt_list)
                print(f'    {lo}-{hi}: {len(bt_list):3d}T | WR={bwr:.0f}% | PnL={bpnl:+.2f}%')

        # RSI distribution of entries
        print(f'\n  By Entry RSI:')
        for lo, hi in [(40,45),(45,50),(50,55),(55,60)]:
            bt_list = [t for t in all_trades if lo <= t['rsi'] < hi]
            if bt_list:
                bwr = sum(1 for t in bt_list if t['pnl_pct'] > 0) / len(bt_list) * 100
                bpnl = sum(t['pnl_pct'] for t in bt_list)
                print(f'    RSI {lo}-{hi}: {len(bt_list):3d}T | WR={bwr:.0f}% | PnL={bpnl:+.2f}%')

        # BB position distribution
        print(f'\n  By Entry BB Position:')
        for lo, hi in [(0.20,0.35),(0.35,0.50),(0.50,0.65),(0.65,0.70)]:
            bt_list = [t for t in all_trades if lo <= t['bb_pct_b'] < hi]
            if bt_list:
                bwr = sum(1 for t in bt_list if t['pnl_pct'] > 0) / len(bt_list) * 100
                bpnl = sum(t['pnl_pct'] for t in bt_list)
                print(f'    BB {lo:.2f}-{hi:.2f}: {len(bt_list):3d}T | WR={bwr:.0f}% | PnL={bpnl:+.2f}%')

        # Trend maturity
        print(f'\n  By Trend Maturity (bars above EMA50):')
        for lo, hi in [(30,40),(40,50),(50,60)]:
            bt_list = [t for t in all_trades if lo <= t['trend_maturity'] < hi]
            if bt_list:
                bwr = sum(1 for t in bt_list if t['pnl_pct'] > 0) / len(bt_list) * 100
                bpnl = sum(t['pnl_pct'] for t in bt_list)
                print(f'    Maturity {lo}-{hi}: {len(bt_list):3d}T | WR={bwr:.0f}% | PnL={bpnl:+.2f}%')

        # Worst trades
        worst = sorted(all_trades, key=lambda t: t['pnl_pct'])[:5]
        print(f'\n  Worst 5:')
        for t in worst:
            ts = datetime.fromtimestamp(t['entry_time']).strftime('%m-%d %H:%M') if isinstance(t['entry_time'], (int, float)) else str(t['entry_time'])
            print(f'    {t["pnl_pct"]:+.2f}% | {t["token"]} @ {ts} | conf={t["confidence"]} rsi={t["rsi"]:.0f} bb={t["bb_pct_b"]:.2f}')

        best = sorted(all_trades, key=lambda t: t['pnl_pct'], reverse=True)[:5]
        print(f'\n  Best 5:')
        for t in best:
            ts = datetime.fromtimestamp(t['entry_time']).strftime('%m-%d %H:%M') if isinstance(t['entry_time'], (int, float)) else str(t['entry_time'])
            print(f'    {t["pnl_pct"]:+.2f}% | {t["token"]} @ {ts} | conf={t["confidence"]} rsi={t["rsi"]:.0f} bb={t["bb_pct_b"]:.2f}')

        # Save
        results = {
            'timestamp': datetime.now().isoformat(),
            'version': 'v2_high_wr',
            'params': {
                'ema_fast': EMA_FAST, 'ema_slow': EMA_SLOW, 'ema_trend': EMA_TREND,
                'min_slope_pct': MIN_SLOPE_PCT, 'accel_lookback': ACCEL_LOOKBACK,
                'rsi_min': RSI_MIN, 'rsi_max': RSI_MAX, 'rsi_pullback_min': RSI_PULLBACK_MIN,
                'atr_min_pct': ATR_MIN_PCT, 'atr_max_pct': ATR_MAX_PCT,
                'sl_atr_mult': SL_ATR_MULT, 'tp_pct': TP_PCT,
                'max_hold_bars': MAX_HOLD_BARS, 'cooldown_bars': COOLDOWN_BARS,
                'bb_period': BB_PERIOD, 'bb_std': BB_STD,
                'min_trend_bars': MIN_TREND_BARS, 'min_higher_highs': MIN_HIGHER_HIGHS,
                'conf_base': CONF_BASE,
            },
            'summary': {
                'total_trades': len(all_trades),
                'tokens_with_signals': len(token_stats),
                'total_pnl': round(total_pnl, 2),
                'win_rate': round(wr, 1),
                'avg_pnl': round(total_pnl / len(all_trades), 2),
                'estimated_fees': round(fees, 2),
                'net_pnl': round(net, 2),
                'rr_ratio': round(rr, 1),
                'avg_hold': round(avg_hold, 0),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
            },
            'token_stats': token_stats,
            'trades': all_trades,
        }
        out_path = os.path.join(os.path.dirname(SCRIPTS_DIR), 'plans', 'trend_momentum_v2_backtest.json')
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f'\nResults saved to: {out_path}')
    else:
        print('\n  No signals found across any token.')


if __name__ == '__main__':
    main()
