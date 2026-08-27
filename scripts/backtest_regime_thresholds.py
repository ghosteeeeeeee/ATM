#!/usr/bin/env python3
"""
backtest_regime_thresholds.py — Test if optimal signal thresholds change per volatility regime.

Hypothesis: A signal with threshold X works in low-vol but fails in high-vol,
because wider swings make the threshold too noisy. The optimal threshold shifts
with volatility regime. If true, parameter tuning should be regime-aware.

Tests bb_bounce with BB_TOUCH_PCT across 4 volatility regimes.
"""

import sys, os, sqlite3, json
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERMES_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'data')
CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')

# ── Tokens (high-liquidity, enough data) ─────────────────────────────────────
TOKENS = [
    'BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'AVAX', 'LINK',
    'MATIC', 'UNI', 'ARB', 'OP', 'SUI', 'APT', 'NEAR',
    'FIL', 'ATOM', 'LTC', 'BCH', 'ETC', 'AAVE',
    'WIF', 'PEPE', 'FLOKI', 'BONK', 'TURBO',
]

# ── Threshold values to test ─────────────────────────────────────────────────
TOUCH_PCTS = [0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.25, 0.30, 0.35, 0.40]

# ── Fixed params (everything except touch_pct stays constant) ─────────────────
BB_PERIOD = 20
BB_STDDEV = 2.0
RSI_OVERSOLD = 40
RSI_OVERBOUGHT = 60
BOUNCE_MIN_PCT = 0.05
COOLDOWN_MIN = 10
SL_PCT = 0.008
TP_PCT = 0.015
MAX_HOLD = 24  # 2h at 5m


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_candles_5m(token):
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        rows = conn.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_5m WHERE token = ?
            ORDER BY ts ASC
        """, (token.upper(),)).fetchall()
        conn.close()
        if not rows:
            return []
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
                 'close': r[4], 'volume': r[5]} for r in rows]
    except Exception:
        return []


def load_candles_1h(token):
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        rows = conn.execute("""
            SELECT close FROM candles_1h WHERE token = ?
            ORDER BY ts ASC
        """, (token.upper(),)).fetchall()
        conn.close()
        return [r[0] for r in rows] if rows else []
    except Exception:
        return []


# ── Indicators ────────────────────────────────────────────────────────────────

def compute_bb(closes, period=BB_PERIOD, stddev=BB_STDDEV):
    if len(closes) < period:
        return None, None, None, None
    window = closes[-period:]
    middle = sum(window) / period
    variance = sum((c - middle) ** 2 for c in window) / period
    std = variance ** 0.5
    upper = middle + stddev * std
    lower = middle - stddev * std
    width = (upper - lower) / middle if middle > 0 else 0
    return middle, upper, lower, width


def compute_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = closes[-i] - closes[-i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains) / len(gains) if gains else 0
    avg_loss = sum(losses) / len(losses) if losses else 0.001
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))


def compute_atr_pct(candles, period=14):
    """Compute ATR as percentage of close — this is our volatility regime classifier."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]['high'], candles[i]['low'], candles[i-1]['close']
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    if len(trs) < period:
        return None
    atr = sum(trs[-period:]) / period
    close = candles[-1]['close']
    if close <= 0:
        return None
    return (atr / close) * 100


def classify_volatility(atr_pct):
    """Classify into 4 regimes — same as volatility_gate.py."""
    if atr_pct is None:
        return 'UNKNOWN'
    if atr_pct < 0.48:
        return 'FLAT'
    elif atr_pct < 1.0:
        return 'NORMAL'
    elif atr_pct < 1.5:
        return 'HIGH'
    else:
        return 'EXTREME'


def get_1h_trend(closes_1h):
    if len(closes_1h) < 50:
        return 'NEUTRAL'
    def ema(data, period):
        k = 2 / (period + 1)
        val = data[0]
        for v in data[1:]:
            val = v * k + val * (1 - k)
        return val
    ema20 = ema(closes_1h[-60:], 20)
    ema50 = ema(closes_1h[-60:], 50)
    if ema50 == 0:
        return 'NEUTRAL'
    spread = abs(ema20 - ema50) / ema50 * 100
    if spread < 0.1:
        return 'NEUTRAL'
    return 'BULLISH' if ema20 > ema50 else 'BEARISH'


# ── Signal Detection (modified to capture regime) ─────────────────────────────

def detect_bb_bounce(closes, closes_1h, touch_pct, candles_for_atr=None):
    """Detect bb_bounce signal. Returns (direction, confidence, atr_pct, regime)."""
    if len(closes) < BB_PERIOD + 10:
        return None, 0, None, 'UNKNOWN'

    middle, upper, lower, width = compute_bb(closes, BB_PERIOD, BB_STDDEV)
    if middle is None:
        return None, 0, None, 'UNKNOWN'

    current = closes[-1]
    prev = closes[-2]

    rsi = compute_rsi(closes)
    if rsi is None:
        return None, 0, None, 'UNKNOWN'

    trend = get_1h_trend(closes_1h)

    # Compute ATR regime from candles window
    atr_pct = None
    regime = 'UNKNOWN'
    if candles_for_atr and len(candles_for_atr) >= 20:
        atr_pct = compute_atr_pct(candles_for_atr[-30:])  # 30 candles for ATR
        regime = classify_volatility(atr_pct)

    dist_from_lower = abs(current - lower) / lower * 100 if lower > 0 else 999
    dist_from_upper = abs(current - upper) / upper * 100 if upper > 0 else 999

    # LONG
    if dist_from_lower <= touch_pct and current > prev:
        if rsi > RSI_OVERSOLD:
            return None, 0, atr_pct, regime
        if trend == 'BEARISH':
            return None, 0, atr_pct, regime
        if current <= lower:
            return None, 0, atr_pct, regime
        bounce_pct = (current - lower) / lower * 100 if lower > 0 else 0
        if bounce_pct < BOUNCE_MIN_PCT:
            return None, 0, atr_pct, regime
        conf = 65
        if width < 0.03: conf += 10
        if trend != 'NEUTRAL': conf += 5
        if bounce_pct > 0.15: conf += 5
        return 'LONG', min(conf, 88), atr_pct, regime

    # SHORT
    if dist_from_upper <= touch_pct and current < prev:
        if rsi < RSI_OVERBOUGHT:
            return None, 0, atr_pct, regime
        if trend == 'BULLISH':
            return None, 0, atr_pct, regime
        if current >= upper:
            return None, 0, atr_pct, regime
        bounce_pct = (upper - current) / upper * 100 if upper > 0 else 0
        if bounce_pct < BOUNCE_MIN_PCT:
            return None, 0, atr_pct, regime
        conf = 65
        if width < 0.03: conf += 10
        if trend != 'NEUTRAL': conf += 5
        if bounce_pct > 0.15: conf += 5
        return 'SHORT', min(conf, 88), atr_pct, regime

    return None, 0, atr_pct, regime


# ── Trade Simulation ──────────────────────────────────────────────────────────

def simulate_trade(candles, entry_idx, direction):
    entry_price = candles[entry_idx]['close']
    if direction == 'LONG':
        sl_price = entry_price * (1 - SL_PCT)
        tp_price = entry_price * (1 + TP_PCT)
    else:
        sl_price = entry_price * (1 + SL_PCT)
        tp_price = entry_price * (1 - TP_PCT)

    for i in range(entry_idx + 1, min(entry_idx + MAX_HOLD + 1, len(candles))):
        c = candles[i]
        if direction == 'LONG':
            if c['low'] <= sl_price:
                return {'result': 'loss', 'pnl_pct': -SL_PCT * 100, 'bars': i - entry_idx}
            if c['high'] >= tp_price:
                return {'result': 'win', 'pnl_pct': TP_PCT * 100, 'bars': i - entry_idx}
        else:
            if c['high'] >= sl_price:
                return {'result': 'loss', 'pnl_pct': -SL_PCT * 100, 'bars': i - entry_idx}
            if c['low'] <= tp_price:
                return {'result': 'win', 'pnl_pct': TP_PCT * 100, 'bars': i - entry_idx}

    exit_price = candles[min(entry_idx + MAX_HOLD, len(candles) - 1)]['close']
    if direction == 'LONG':
        pnl = (exit_price - entry_price) / entry_price * 100
    else:
        pnl = (entry_price - exit_price) / entry_price * 100
    return {'result': 'win' if pnl > 0 else 'loss', 'pnl_pct': pnl, 'bars': MAX_HOLD}


# ── Backtest Engine ───────────────────────────────────────────────────────────

def backtest_token_regime(token, candles, closes_1h, touch_pct):
    """Backtest and classify each trade by regime at entry time."""
    trades = []
    cooldown = 0

    for i in range(30, len(candles)):
        if cooldown > 0:
            cooldown -= 1
            continue

        window = [c['close'] for c in candles[max(0, i - 100):i + 1]]
        candles_for_atr = candles[max(0, i - 30):i + 1]
        direction, conf, atr_pct, regime = detect_bb_bounce(
            window, closes_1h, touch_pct, candles_for_atr
        )

        if direction:
            trade = simulate_trade(candles, i, direction)
            if trade:
                trade['token'] = token
                trade['direction'] = direction
                trade['atr_pct'] = round(atr_pct, 4) if atr_pct else None
                trade['regime'] = regime
                trade['touch_pct'] = touch_pct
                trades.append(trade)
                cooldown = COOLDOWN_MIN

    return trades


def aggregate_by_regime(trades):
    """Group trades by regime and compute stats."""
    by_regime = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0, 'pnls': []})
    for t in trades:
        r = t['regime']
        by_regime[r]['trades'] += 1
        by_regime[r]['pnl'] += t['pnl_pct']
        by_regime[r]['pnls'].append(t['pnl_pct'])
        if t['result'] == 'win':
            by_regime[r]['wins'] += 1

    result = {}
    for regime, data in by_regime.items():
        n = data['trades']
        if n == 0:
            continue
        wins = data['wins']
        pnl = data['pnl']
        pnls = data['pnls']
        win_pnl = sum(p for p in pnls if p > 0)
        loss_pnl = abs(sum(p for p in pnls if p <= 0))
        avg_win = win_pnl / wins if wins > 0 else 0
        avg_loss = loss_pnl / (n - wins) if (n - wins) > 0 else 0

        result[regime] = {
            'trades': n,
            'wins': wins,
            'losses': n - wins,
            'wr': round(100 * wins / n, 1),
            'pnl': round(pnl, 2),
            'avg_pnl': round(pnl / n, 3),
            'profit_factor': round(win_pnl / loss_pnl, 2) if loss_pnl > 0 else 999,
            'avg_win': round(avg_win, 3),
            'avg_loss': round(avg_loss, 3),
            'expectancy': round(avg_win * (wins/n) - avg_loss * ((n-wins)/n), 3) if n > 0 else 0,
        }

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 90)
    print("REGIME-THRESHOLD BACKTEST: Does optimal BB_TOUCH_PCT change per volatility regime?")
    print("=" * 90)
    print(f"Tokens: {len(TOKENS)} | SL={SL_PCT*100}% TP={TP_PCT*100}% MaxHold={MAX_HOLD} bars")
    print(f"Testing touch_pct: {TOUCH_PCTS}")
    print()

    # ── Phase 1: Run all thresholds, collect regime-classified trades ──────────
    print("Phase 1: Running backtests...")
    all_results = {}  # touch_pct -> regime -> stats

    for tp in TOUCH_PCTS:
        all_trades = []
        for token in TOKENS:
            candles = load_candles_5m(token)
            if not candles or len(candles) < 100:
                continue
            closes_1h = load_candles_1h(token)
            trades = backtest_token_regime(token, candles, closes_1h, tp)
            all_trades.extend(trades)

        regime_stats = aggregate_by_regime(all_trades)
        all_results[tp] = regime_stats

        total = sum(s['trades'] for s in regime_stats.values())
        total_wins = sum(s['wins'] for s in regime_stats.values())
        total_pnl = sum(s['pnl'] for s in regime_stats.values())
        wr = round(100 * total_wins / total, 1) if total > 0 else 0
        print(f"  touch_pct={tp:.2f}: {total:5d} trades, {wr:5.1f}% WR, {total_pnl:+.2f}% PnL")

    # ── Phase 2: Heatmap — WR by (threshold × regime) ─────────────────────────
    print("\n" + "=" * 90)
    print("HEATMAP: Win Rate by (BB_TOUCH_PCT × Regime)")
    print("=" * 90)

    regimes = ['FLAT', 'NORMAL', 'HIGH', 'EXTREME']
    header = f"{'TOUCH_PCT':>10}"
    for r in regimes:
        header += f" {r:>12}"
    header += f" {'ALL':>12}"
    print(header)
    print("-" * len(header))

    for tp in TOUCH_PCTS:
        row = f"{tp:>10.2f}"
        stats = all_results[tp]
        for r in regimes:
            if r in stats and stats[r]['trades'] >= 5:
                row += f" {stats[r]['wr']:>8.1f}%({stats[r]['trades']:>2}T)"
            else:
                row += f" {'---':>12}"
        # Overall
        total_t = sum(s['trades'] for s in stats.values())
        total_w = sum(s['wins'] for s in stats.values())
        overall_wr = round(100 * total_w / total_t, 1) if total_t > 0 else 0
        row += f" {overall_wr:>8.1f}%({total_t:>2}T)"
        print(row)

    # ── Phase 3: Heatmap — PnL by (threshold × regime) ────────────────────────
    print("\n" + "=" * 90)
    print("HEATMAP: Total PnL (%) by (BB_TOUCH_PCT × Regime)")
    print("=" * 90)

    header = f"{'TOUCH_PCT':>10}"
    for r in regimes:
        header += f" {r:>12}"
    header += f" {'ALL':>12}"
    print(header)
    print("-" * len(header))

    for tp in TOUCH_PCTS:
        row = f"{tp:>10.2f}"
        stats = all_results[tp]
        for r in regimes:
            if r in stats and stats[r]['trades'] >= 5:
                row += f" {stats[r]['pnl']:>+9.2f}%({stats[r]['trades']:>2}T)"
            else:
                row += f" {'---':>12}"
        total_pnl = sum(s['pnl'] for s in stats.values())
        total_t = sum(s['trades'] for s in stats.values())
        row += f" {total_pnl:>+9.2f}%({total_t:>2}T)"
        print(row)

    # ── Phase 4: Heatmap — Profit Factor by (threshold × regime) ──────────────
    print("\n" + "=" * 90)
    print("HEATMAP: Profit Factor by (BB_TOUCH_PCT × Regime)")
    print("=" * 90)

    header = f"{'TOUCH_PCT':>10}"
    for r in regimes:
        header += f" {r:>12}"
    print(header)
    print("-" * len(header))

    for tp in TOUCH_PCTS:
        row = f"{tp:>10.2f}"
        stats = all_results[tp]
        for r in regimes:
            if r in stats and stats[r]['trades'] >= 5:
                pf = stats[r]['profit_factor']
                pf_str = f"{pf:.2f}" if pf < 100 else "∞"
                row += f" {pf_str:>12}"
            else:
                row += f" {'---':>12}"
        print(row)

    # ── Phase 5: Find optimal threshold per regime ────────────────────────────
    print("\n" + "=" * 90)
    print("OPTIMAL THRESHOLD PER REGIME (by PnL, min 5 trades)")
    print("=" * 90)

    for r in regimes:
        best_tp = None
        best_pnl = -999
        best_wr = 0
        for tp in TOUCH_PCTS:
            stats = all_results[tp]
            if r in stats and stats[r]['trades'] >= 5 and stats[r]['pnl'] > best_pnl:
                best_pnl = stats[r]['pnl']
                best_tp = tp
                best_wr = stats[r]['wr']
        if best_tp is not None:
            print(f"  {r:>10}: touch_pct={best_tp:.2f}  (WR={best_wr:.1f}%, PnL={best_pnl:+.2f}%)")
        else:
            print(f"  {r:>10}: insufficient data")

    # Also find best by profit factor
    print()
    for r in regimes:
        best_tp = None
        best_pf = -1
        best_stats = None
        for tp in TOUCH_PCTS:
            stats = all_results[tp]
            if r in stats and stats[r]['trades'] >= 5 and stats[r]['profit_factor'] > best_pf:
                best_pf = stats[r]['profit_factor']
                best_tp = tp
                best_stats = stats[r]
        if best_tp is not None:
            print(f"  {r:>10}: touch_pct={best_tp:.2f}  (PF={best_pf:.2f}, WR={best_stats['wr']:.1f}%, {best_stats['trades']}T)")
        else:
            print(f"  {r:>10}: insufficient data")

    # ── Phase 6: Verify the theory — does optimal threshold shift? ────────────
    print("\n" + "=" * 90)
    print("THEORY CHECK: Does optimal BB_TOUCH_PCT shift with regime?")
    print("=" * 90)

    optimal_per_regime = {}
    for r in regimes:
        best_tp = None
        best_pnl = -999
        for tp in TOUCH_PCTS:
            stats = all_results[tp]
            if r in stats and stats[r]['trades'] >= 5 and stats[r]['pnl'] > best_pnl:
                best_pnl = stats[r]['pnl']
                best_tp = tp
        if best_tp is not None:
            optimal_per_regime[r] = best_tp

    if len(optimal_per_regime) >= 2:
        values = list(optimal_per_regime.values())
        if max(values) - min(values) >= 0.05:
            print("  ✅ CONFIRMED: Optimal threshold CHANGES across regimes!")
            print(f"  Range: {min(values):.2f} (low vol) → {max(values):.2f} (high vol)")
            print()
            for r, tp in sorted(optimal_per_regime.items()):
                print(f"    {r:>10}: touch_pct = {tp:.2f}")
            print()
            print("  IMPLICATION: A fixed threshold (e.g., 0.15) is suboptimal.")
            print("  The self_learner should tune thresholds PER REGIME, not globally.")
        else:
            print("  ❌ NOT CONFIRMED: Optimal threshold is roughly constant across regimes.")
            print(f"  All regimes favor touch_pct ≈ {values[0]:.2f}")
            print("  The signal is robust to volatility changes — threshold tuning")
            print("  doesn't need regime awareness for this signal.")
    else:
        print("  ⚠️  INSUFFICIENT DATA: Not enough regimes with 5+ trades to compare.")

    # ── Phase 7: What happens if we use the wrong threshold? ──────────────────
    print("\n" + "=" * 90)
    print("COST OF WRONG THRESHOLD: PnL loss when using global-optimal in wrong regime")
    print("=" * 90)

    # Find global optimal (across all regimes)
    best_global_tp = None
    best_global_pnl = -999
    for tp in TOUCH_PCTS:
        total_pnl = sum(s['pnl'] for s in all_results[tp].values())
        total_t = sum(s['trades'] for s in all_results[tp].values())
        if total_t >= 10 and total_pnl > best_global_pnl:
            best_global_pnl = total_pnl
            best_global_tp = tp

    if best_global_tp is not None and optimal_per_regime:
        print(f"  Global optimal threshold: {best_global_tp:.2f}")
        print()
        for r in regimes:
            if r in optimal_per_regime:
                regime_optimal = optimal_per_regime[r]
                # PnL with global optimal in this regime
                global_stats = all_results[best_global_tp].get(r, {})
                regime_stats = all_results[regime_optimal].get(r, {})
                global_pnl = global_stats.get('pnl', 0)
                regime_pnl = regime_stats.get('pnl', 0)
                cost = regime_pnl - global_pnl
                if global_stats.get('trades', 0) >= 5:
                    print(f"  {r:>10}: regime-optimal={regime_optimal:.2f} → {regime_pnl:+.2f}%")
                    print(f"             global-optimal={best_global_tp:.2f} → {global_pnl:+.2f}%")
                    print(f"             COST of wrong threshold: {cost:+.2f}%")

    # ── Save raw data ─────────────────────────────────────────────────────────
    output_file = os.path.join(HERMES_DATA, 'regime_threshold_results.json')
    save_data = {}
    for tp in TOUCH_PCTS:
        save_data[str(tp)] = {}
        for r, stats in all_results[tp].items():
            save_data[str(tp)][r] = {k: v for k, v in stats.items() if k != 'pnls'}
    try:
        with open(output_file, 'w') as f:
            json.dump(save_data, f, indent=2)
        print(f"\nRaw data saved to {output_file}")
    except Exception as e:
        print(f"\nError saving: {e}")


if __name__ == '__main__':
    main()
