#!/usr/bin/env python3
"""
backtest_trend_momentum_v3.py — MAXIMUM WIN RATE trend signal.

Focus: Every filter imaginable to only take HIGH CONVICTION trades.
Goal: 55%+ WR, accept fewer trades.

New v3 filters (on top of v1):
1. ADX filter — only trade in strong trends (ADX > 20)
2. RSI must be RISING over last 5 bars (momentum confirmation)
3. Price pullback — not within 0.5% of 20-bar high (avoid chasing)
4. Consolidation breakout — price must have consolidated 10+ bars before move
5. EMA slope agreement — EMA20 slope must be positive AND accelerating
6. Token blacklist — remove consistent losers
7. Time-of-day filter — avoid low-liquidity hours
8. Consecutive loss cooldown — if last 2 trades lost, skip next signal
"""
import sys, os, sqlite3, time, json
from datetime import datetime

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

DB_PATH = os.path.join(os.path.dirname(SCRIPTS_DIR), 'data', 'signals_hermes.db')

# ── V3 Parameters (MAXIMUM WR) ─────────────────────────────────────────
EMA_FAST = 20
EMA_SLOW = 50
EMA_TREND = 100
MIN_SLOPE_PCT = 0.00015
ACCEL_LOOKBACK = 10
RSI_PERIOD = 14
RSI_MIN = 45
RSI_MAX = 60
ATR_PERIOD = 14
ATR_MIN_PCT = 0.30
ATR_MAX_PCT = 2.0
CONF_BASE = 70
CONF_CAP = 88
SL_ATR_MULT = 2.5
TP_PCT = 2.5
MAX_HOLD_BARS = 60
COOLDOWN_BARS = 180  # 3h cooldown
BB_PERIOD = 20
BB_STD = 2.0

# V3-specific
ADX_PERIOD = 14
ADX_MIN = 20           # Strong trend only
RSI_RISING_BARS = 5    # RSI must rise over last 5 bars
PULLBACK_MAX_PCT = 0.5 # Must be >0.5% below 20-bar high
CONSOLIDATION_BARS = 10 # Min bars of consolidation before breakout
MIN_EMA_SLOPE_ACCEL = True  # EMA slope must be accelerating
TOKEN_BLACKLIST = {'AVNT', 'DOGE', 'BCH', 'BANANA', 'ALGO', 'ATOM', 'BABY', 'CC', 'COMP', 'CFX', 'DYDX', 'ETC'}
SKIP_HOURS = {0, 1, 2, 3, 4, 5}  # Skip low-liquidity hours (UTC)
MAX_CONSEC_LOSSES = 2  # Skip signal if last 2 trades were losses


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


def compute_adx(highs, lows, closes, period=14):
    """Compute ADX (Average Directional Index) — trend strength."""
    n = len(closes)
    if n < period * 2 + 1:
        return [None] * n
    
    # True Range
    trs = [None]
    plus_dm = [None]
    minus_dm = [None]
    for i in range(1, n):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
        up = highs[i] - highs[i-1]
        down = lows[i-1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)
    
    # Smoothed TR, +DM, -DM
    atr_s = [None] * period
    plus_dm_s = [None] * period
    minus_dm_s = [None] * period
    
    atr_sum = sum(trs[1:period+1])
    plus_sum = sum(plus_dm[1:period+1])
    minus_sum = sum(minus_dm[1:period+1])
    
    atr_s.append(atr_sum)
    plus_dm_s.append(plus_sum)
    minus_dm_s.append(minus_sum)
    
    for i in range(period + 1, n):
        atr_s.append(atr_s[-1] - atr_s[-1] / period + trs[i])
        plus_dm_s.append(plus_dm_s[-1] - plus_dm_s[-1] / period + plus_dm[i])
        minus_dm_s.append(minus_dm_s[-1] - minus_dm_s[-1] / period + minus_dm[i])
    
    # +DI, -DI
    plus_di = [None] * n
    minus_di = [None] * n
    dx = [None] * n
    for i in range(period, n):
        if atr_s[i] and atr_s[i] > 0:
            plus_di[i] = (plus_dm_s[i] / atr_s[i]) * 100
            minus_di[i] = (minus_dm_s[i] / atr_s[i]) * 100
            di_sum = plus_di[i] + minus_di[i]
            if di_sum > 0:
                dx[i] = abs(plus_di[i] - minus_di[i]) / di_sum * 100
    
    # ADX = smoothed DX
    adx = [None] * n
    dx_start = period
    dx_valid = [d for d in dx[dx_start:dx_start + period] if d is not None]
    if len(dx_valid) >= period:
        adx[dx_start + period - 1] = sum(dx_valid) / period
        for i in range(dx_start + period, n):
            if dx[i] is not None and adx[i-1] is not None:
                adx[i] = (adx[i-1] * (period - 1) + dx[i]) / period
    
    return adx


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
    n = len(prices)
    pct_b = [None] * n
    upper = [None] * n
    lower = [None] * n
    for i in range(period - 1, n):
        window = prices[i - period + 1:i + 1]
        m = sum(window) / period
        std = (sum((x - m) ** 2 for x in window) / period) ** 0.5
        upper[i] = m + num_std * std
        lower[i] = m - num_std * std
        if upper[i] != lower[i]:
            pct_b[i] = (prices[i] - lower[i]) / (upper[i] - lower[i])
        else:
            pct_b[i] = 0.5
    return pct_b


def detect_v3(prices, highs, lows, closes, idx, ema_f, ema_s, ema_t, rsi_vals, atr_vals, slopes, pct_b, adx_vals, timestamps):
    """V3 Detection with maximum filters."""
    min_bars = max(EMA_TREND, RSI_PERIOD + 1, ATR_PERIOD + 1, ACCEL_LOOKBACK * 2, BB_PERIOD, ADX_PERIOD * 3) + 10
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
    adx = adx_vals[idx]

    if None in (ef, es, et, rv, av, sl, pb, adx):
        return None

    atr_pct = av / price * 100 if price > 0 else 0
    slope_pct = sl / price if price > 0 else 0

    # ── FILTER 1: EMA alignment ──
    if not (price > ef > es > et):
        return None

    # ── FILTER 2: Slope meaningful ──
    if slope_pct < MIN_SLOPE_PCT:
        return None

    # ── FILTER 3: ADX — strong trend only ──
    if adx < ADX_MIN:
        return None

    # ── FILTER 4: RSI range ──
    if rv < RSI_MIN or rv > RSI_MAX:
        return None

    # ── FILTER 5: RSI must be RISING over last 5 bars ──
    rsi_window = [r for r in rsi_vals[max(0, idx - RSI_RISING_BARS):idx + 1] if r is not None]
    if len(rsi_window) < 3:
        return None
    # Check RSI is higher now than 5 bars ago
    if rsi_window[-1] <= rsi_window[0]:
        return None
    # Check at least 3 of last 5 bars had rising RSI
    rsi_rising_count = sum(1 for i in range(1, len(rsi_window)) if rsi_window[i] > rsi_window[i-1])
    if rsi_rising_count < len(rsi_window) * 0.6:
        return None

    # ── FILTER 6: ATR% guard ──
    if atr_pct < ATR_MIN_PCT or atr_pct > ATR_MAX_PCT:
        return None

    # ── FILTER 7: Pullback — not chasing at the top ──
    recent_high = max(highs[max(0, idx - 20):idx + 1])
    pullback_pct = (recent_high - price) / recent_high * 100 if recent_high > 0 else 0
    if pullback_pct < PULLBACK_MAX_PCT:
        return None  # Too close to recent high — chasing

    # ── FILTER 8: BB position — middle zone ──
    if pb > 0.65 or pb < 0.25:
        return None

    # ── FILTER 9: Consolidation before breakout ──
    # Check that price was relatively flat for 10+ bars before the move
    consol_range = []
    for j in range(max(0, idx - CONSOLIDATION_BARS - 10), idx - CONSOLIDATION_BARS):
        if j >= 0:
            consol_range.append(prices[j])
    if len(consol_range) >= 5:
        consol_high = max(consol_range)
        consol_low = min(consol_range)
        consol_pct = (consol_high - consol_low) / consol_low * 100 if consol_low > 0 else 100
        if consol_pct > 3.0:
            return None  # Was volatile before — not a consolidation breakout

    # ── FILTER 10: EMA slope accelerating ──
    ema_f_slopes = [s for s in slopes[max(0, idx - 20):idx + 1] if s is not None]
    if len(ema_f_slopes) >= 10:
        early_slope = sum(ema_f_slopes[:5]) / 5
        late_slope = sum(ema_f_slopes[-5:]) / 5
        if late_slope <= early_slope:
            return None  # Slope not accelerating

    # ── FILTER 11: Higher highs ──
    swing_highs = []
    for j in range(max(1, idx - 20), min(idx, len(highs) - 1)):
        if highs[j] >= highs[j-1] and highs[j] >= highs[j+1]:
            swing_highs.append(highs[j])
    if len(swing_highs) < 2:
        return None
    increasing = sum(1 for i in range(1, len(swing_highs)) if swing_highs[i] > swing_highs[i-1])
    if increasing < 1:
        return None

    # ── FILTER 12: Time of day ──
    if timestamps:
        hour = datetime.fromtimestamp(timestamps[idx]).hour
        if hour in SKIP_HOURS:
            return None

    # ── SCORING ──
    score = 0
    reasons = ['ema_4stack', 'adx_strong']

    # ADX quality
    if adx > 30:
        score += 5
        reasons.append(f'adx={adx:.0f}>>')
    elif adx > 25:
        score += 3
        reasons.append(f'adx={adx:.0f}')
    else:
        score += 1
        reasons.append(f'adx={adx:.0f}weak')

    # RSI rising quality
    rsi_rise = rsi_window[-1] - rsi_window[0]
    if rsi_rise > 3:
        score += 5
        reasons.append(f'rsi_rising+{rsi_rise:.1f}')
    elif rsi_rise > 1:
        score += 3
        reasons.append(f'rsi_rising+{rsi_rise:.1f}')
    else:
        score += 1

    # Pullback quality (further from high = better entry)
    if pullback_pct > 1.5:
        score += 5
        reasons.append(f'pullback={pullback_pct:.1f}%>>')
    elif pullback_pct > 0.8:
        score += 3
        reasons.append(f'pullback={pullback_pct:.1f}%')
    else:
        score += 1

    # Slope quality
    slope_q = min(5, int(slope_pct / 0.0003))
    score += slope_q

    # BB position quality
    if 0.35 <= pb <= 0.55:
        score += 3
        reasons.append('bb_mid')
    else:
        score += 1

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
        'rsi': rv,
        'adx': adx,
        'bb_pct_b': pb,
        'pullback_pct': pullback_pct,
        'reasons': reasons,
    }


def backtest_token_v3(token, prices, timestamps, verbose=False):
    n = len(prices)
    min_bars = max(EMA_TREND, RSI_PERIOD + 1, ATR_PERIOD + 1, ACCEL_LOOKBACK * 2, BB_PERIOD, ADX_PERIOD * 3) + 10
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
    pct_b = compute_bollinger(prices, BB_PERIOD, BB_STD)
    adx_vals = compute_adx(highs, lows, closes, ADX_PERIOD)

    trades = []
    cooldown_until = 0
    consec_losses = 0

    for i in range(min_bars, n):
        if i <= cooldown_until:
            continue

        # Consecutive loss check
        if consec_losses >= MAX_CONSEC_LOSSES:
            consec_losses = 0  # Reset after cooldown
            cooldown_until = i + COOLDOWN_BARS
            continue

        signal = detect_v3(prices, highs, lows, closes, i, ema_f, ema_s, ema_t, rsi_vals, atr_vals, slopes, pct_b, adx_vals, timestamps)
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
            'rsi': signal['rsi'],
            'adx': signal['adx'],
            'bb_pct_b': signal['bb_pct_b'],
            'pullback_pct': signal['pullback_pct'],
            'reasons': signal['reasons'],
        }
        trades.append(trade)
        cooldown_until = i + COOLDOWN_BARS

        if pnl_pct > 0:
            consec_losses = 0
        else:
            consec_losses += 1

        if verbose:
            w = '✅' if pnl_pct > 0 else '❌'
            t_str = datetime.fromtimestamp(timestamps[i]).strftime('%m-%d %H:%M') if timestamps else str(i)
            print(f'  {w} {token} @ {t_str} entry={signal["price"]:.4f} → {exit_price:.4f} ({pnl_pct:+.2f}%) [{exit_reason}] conf={signal["confidence"]} adx={signal["adx"]:.0f} rsi={signal["rsi"]:.0f} pb={signal["pullback_pct"]:.1f}%')

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

    # Filter out blacklisted tokens
    token_list = [t for t in token_list if t not in TOKEN_BLACKLIST]

    print(f'\n{"="*70}')
    print(f'V3 BACKTEST (MAX WR): trend_momentum_v3 | {len(token_list)} tokens | {args.days}d')
    print(f'  Filters: EMA4stack, ADX>{ADX_MIN}, RSI {RSI_MIN}-{RSI_MAX} rising, pullback>{PULLBACK_MAX_PCT}%, consolidation')
    print(f'  Blacklist: {TOKEN_BLACKLIST}')
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

        trades = backtest_token_v3(token, prices, timestamps, verbose=args.verbose)

        if trades:
            wins = sum(1 for t in trades if t['pnl_pct'] > 0)
            total_pnl = sum(t['pnl_pct'] for t in trades)
            wr = wins / len(trades) * 100

            token_stats[token] = {
                'trades': len(trades), 'wins': wins,
                'wr': round(wr, 1), 'total_pnl': round(total_pnl, 2),
            }
            print(f'  {token:8s}: {len(trades):3d}T | WR={wr:.0f}% | PnL={total_pnl:+.2f}%')

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
        print(f'V3 SUMMARY: {len(all_trades)} trades | {len(token_stats)} tokens | {time.time()-start_time:.1f}s')
        print(f'{"="*70}')
        print(f'  Win Rate:  {wr:.1f}% ({wins}W / {len(all_trades)-wins}L)')
        print(f'  Total PnL: {total_pnl:+.2f}%')
        print(f'  Est Fees:  -{fees:.2f}%')
        print(f'  Net PnL:   {net:+.2f}%')
        print(f'  Avg PnL:   {total_pnl/len(all_trades):+.2f}% per trade')
        print(f'  R:R Ratio: {rr:.1f}:1 (breakeven WR: {100/(1+rr):.1f}%)')
        print(f'  Avg Win:   {avg_win:+.2f}%')
        print(f'  Avg Loss:  {avg_loss:+.2f}%')
        print(f'  Exits:     {tp} TP | {sl} SL | {tm} TIME')
        print(f'  Avg Hold:  {avg_hold:.0f} min')

        # Confidence buckets
        print(f'\n  By Confidence:')
        for lo, hi in [(70,75),(75,80),(80,85),(85,88)]:
            bt_list = [t for t in all_trades if lo <= t['confidence'] < hi]
            if bt_list:
                bwr = sum(1 for t in bt_list if t['pnl_pct'] > 0) / len(bt_list) * 100
                bpnl = sum(t['pnl_pct'] for t in bt_list)
                print(f'    {lo}-{hi}: {len(bt_list):3d}T | WR={bwr:.0f}% | PnL={bpnl:+.2f}%')

        # ADX distribution
        print(f'\n  By Entry ADX:')
        for lo, hi in [(20,25),(25,30),(30,35),(35,50)]:
            bt_list = [t for t in all_trades if lo <= t['adx'] < hi]
            if bt_list:
                bwr = sum(1 for t in bt_list if t['pnl_pct'] > 0) / len(bt_list) * 100
                bpnl = sum(t['pnl_pct'] for t in bt_list)
                print(f'    ADX {lo}-{hi}: {len(bt_list):3d}T | WR={bwr:.0f}% | PnL={bpnl:+.2f}%')

        # Pullback distribution
        print(f'\n  By Pullback %:')
        for lo, hi in [(0.5,1.0),(1.0,1.5),(1.5,2.0),(2.0,5.0)]:
            bt_list = [t for t in all_trades if lo <= t['pullback_pct'] < hi]
            if bt_list:
                bwr = sum(1 for t in bt_list if t['pnl_pct'] > 0) / len(bt_list) * 100
                bpnl = sum(t['pnl_pct'] for t in bt_list)
                print(f'    PB {lo}-{hi}%: {len(bt_list):3d}T | WR={bwr:.0f}% | PnL={bpnl:+.2f}%')

        # Worst trades
        worst = sorted(all_trades, key=lambda t: t['pnl_pct'])[:5]
        print(f'\n  Worst 5:')
        for t in worst:
            ts = datetime.fromtimestamp(t['entry_time']).strftime('%m-%d %H:%M') if isinstance(t['entry_time'], (int, float)) else str(t['entry_time'])
            print(f'    {t["pnl_pct"]:+.2f}% | {t["token"]} @ {ts} | conf={t["confidence"]} adx={t["adx"]:.0f} rsi={t["rsi"]:.0f} pb={t["pullback_pct"]:.1f}%')

        best = sorted(all_trades, key=lambda t: t['pnl_pct'], reverse=True)[:5]
        print(f'\n  Best 5:')
        for t in best:
            ts = datetime.fromtimestamp(t['entry_time']).strftime('%m-%d %H:%M') if isinstance(t['entry_time'], (int, float)) else str(t['entry_time'])
            print(f'    {t["pnl_pct"]:+.2f}% | {t["token"]} @ {ts} | conf={t["confidence"]} adx={t["adx"]:.0f} rsi={t["rsi"]:.0f} pb={t["pullback_pct"]:.1f}%')

        # Save
        results = {
            'timestamp': datetime.now().isoformat(),
            'version': 'v3_max_wr',
            'params': {
                'sl_atr_mult': SL_ATR_MULT, 'rsi_min': RSI_MIN, 'rsi_max': RSI_MAX,
                'adx_min': ADX_MIN, 'pullback_max_pct': PULLBACK_MAX_PCT,
                'consolidation_bars': CONSOLIDATION_BARS, 'rsi_rising_bars': RSI_RISING_BARS,
                'cooldown_bars': COOLDOWN_BARS, 'max_consec_losses': MAX_CONSEC_LOSSES,
                'token_blacklist': list(TOKEN_BLACKLIST), 'skip_hours': list(SKIP_HOURS),
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
        out_path = os.path.join(os.path.dirname(SCRIPTS_DIR), 'plans', 'trend_momentum_v3_backtest.json')
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f'\nResults saved to: {out_path}')
    else:
        print('\n  No signals found across any token.')


if __name__ == '__main__':
    main()
