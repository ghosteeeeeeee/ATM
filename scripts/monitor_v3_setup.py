#!/usr/bin/env python3
"""Monitor v3 signal candidates every 3 minutes for 30 minutes."""
import sys, os, sqlite3, time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signals.accel_300_v3_long import _get_1m_prices, _ema_series, _rsi, _get_15m_trend, _check_volume
from paths import STATIC_DB, CANDLES_DB, RUNTIME_DB
from hermes_constants import (
    ACCEL_300_V3_LONG_MIN_GAP, ACCEL_300_V3_LONG_MAX_GAP,
    ACCEL_300_V3_LONG_MIN_PULLBACK, ACCEL_300_V3_LONG_MAX_PULLBACK,
    ACCEL_300_V3_LONG_REEXPAND_MIN, ACCEL_300_V3_LONG_RSI_MAX,
    ACCEL_300_V3_LONG_RSI_MIN, ACCEL_300_V3_LONG_GREEN_CAP,
    ACCEL_300_V3_LONG_GREEN_COUNT_WINDOW, ACCEL_300_V3_LONG_VELOCITY_WINDOW,
    ACCEL_300_V3_LONG_GAP_VELOCITY_THRESH,
)
from signals.accel_300_v3_long import detect_accel_300_v3_long

PERIOD = 300
TOKENS = ['UNI', 'CASHCAT', 'PONS', 'ARB', 'ACE']
INTERVAL = 180  # 3 min
ROUNDS = 10     # 30 min total
LOG_FILE = '/root/.hermes/logs/v3_monitor.log'

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f'{ts} {msg}'
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except: pass

def check_token(token):
    """Check a token's current state against v3 conditions."""
    prices = _get_1m_prices(token, 700)
    if not prices or len(prices) < PERIOD + 30:
        return {'status': 'NO_DATA', 'details': f'only {len(prices) if prices else 0} prices'}

    closes = [float(p['price']) for p in prices]
    ema300 = _ema_series(closes, PERIOD)
    gap_pcts = [
        None if ema is None or ema == 0 else (price - ema) / ema * 100.0
        for price, ema in zip(closes, ema300)
    ]

    latest_idx = len(closes) - 1
    gap_now = gap_pcts[latest_idx]
    if gap_now is None:
        return {'status': 'NO_GAP', 'details': 'EMA300 not computed'}

    result = {
        'price': closes[latest_idx],
        'gap': gap_now,
        'ema300': ema300[latest_idx],
        'checks': {},
    }

    # Check 1: Price above EMA
    if gap_now <= 0:
        result['checks']['above_ema'] = ('FAIL', f'gap={gap_now:.3f}% (below EMA)')
        result['status'] = 'BELOW_EMA'
        return result
    result['checks']['above_ema'] = ('PASS', f'gap={gap_now:.3f}%')

    # Check 2: Gap in range
    if gap_now < ACCEL_300_V3_LONG_MIN_GAP:
        result['checks']['gap_range'] = ('FAIL', f'{gap_now:.3f}% < min {ACCEL_300_V3_LONG_MIN_GAP}%')
    elif gap_now > ACCEL_300_V3_LONG_MAX_GAP:
        result['checks']['gap_range'] = ('FAIL', f'{gap_now:.3f}% > max {ACCEL_300_V3_LONG_MAX_GAP}%')
    else:
        result['checks']['gap_range'] = ('PASS', f'{gap_now:.3f}%')

    # Check 3: Pullback from peak
    peak_start = max(0, latest_idx - 20)
    recent_gaps = [g for g in gap_pcts[peak_start:latest_idx+1] if g is not None]
    gap_peak = max(recent_gaps) if recent_gaps else gap_now
    pullback = gap_peak - gap_now
    result['gap_peak'] = gap_peak
    result['pullback'] = pullback

    if pullback < ACCEL_300_V3_LONG_MIN_PULLBACK:
        result['checks']['pullback'] = ('FAIL', f'{pullback:.3f}% < min {ACCEL_300_V3_LONG_MIN_PULLBACK}% (peak={gap_peak:.3f}%)')
    elif pullback > ACCEL_300_V3_LONG_MAX_PULLBACK:
        result['checks']['pullback'] = ('FAIL', f'{pullback:.3f}% > max {ACCEL_300_V3_LONG_MAX_PULLBACK}%')
    else:
        result['checks']['pullback'] = ('PASS', f'{pullback:.3f}% from peak {gap_peak:.3f}%')

    # Check 4: Re-expansion
    reexpand_start = max(0, latest_idx - 3)
    gap_at_reexpand = gap_pcts[reexpand_start]
    reexpansion = gap_now - gap_at_reexpand if gap_at_reexpand else 0
    result['reexpansion'] = reexpansion

    if reexpansion < ACCEL_300_V3_LONG_REEXPAND_MIN:
        result['checks']['reexpansion'] = ('FAIL', f'{reexpansion:.3f}% < min {ACCEL_300_V3_LONG_REEXPAND_MIN}%')
    else:
        result['checks']['reexpansion'] = ('PASS', f'{reexpansion:.3f}%')

    # Check 5: Velocity
    if latest_idx >= ACCEL_300_V3_LONG_VELOCITY_WINDOW:
        velocity = closes[latest_idx] - closes[latest_idx - ACCEL_300_V3_LONG_VELOCITY_WINDOW]
        result['velocity'] = velocity
        if velocity <= 0:
            result['checks']['velocity'] = ('FAIL', f'{velocity:.6f} (price falling)')
        else:
            result['checks']['velocity'] = ('PASS', f'{velocity:.6f}')
    else:
        result['checks']['velocity'] = ('FAIL', 'insufficient data')

    # Check 6: Green candles
    green_count = 0
    for i in range(latest_idx, max(latest_idx - ACCEL_300_V3_LONG_GREEN_COUNT_WINDOW, 0), -1):
        if i > 0 and closes[i] > closes[i-1]:
            green_count += 1
        else:
            break
    result['green_count'] = green_count
    if green_count > ACCEL_300_V3_LONG_GREEN_CAP:
        result['checks']['green_cap'] = ('FAIL', f'{green_count} > max {ACCEL_300_V3_LONG_GREEN_CAP}')
    else:
        result['checks']['green_cap'] = ('PASS', f'{green_count} greens')

    # Check 7: RSI
    rsi = _rsi(closes, 14)
    result['rsi'] = rsi
    if rsi > ACCEL_300_V3_LONG_RSI_MAX:
        result['checks']['rsi'] = ('FAIL', f'{rsi:.1f} > max {ACCEL_300_V3_LONG_RSI_MAX}')
    elif rsi < ACCEL_300_V3_LONG_RSI_MIN:
        result['checks']['rsi'] = ('FAIL', f'{rsi:.1f} < min {ACCEL_300_V3_LONG_RSI_MIN}')
    else:
        result['checks']['rsi'] = ('PASS', f'{rsi:.1f}')

    # Check 8: 15m trend
    trend = _get_15m_trend(token)
    result['trend'] = trend
    if trend == 'BEARISH':
        result['checks']['trend'] = ('FAIL', f'{trend}')
    else:
        result['checks']['trend'] = ('PASS', f'{trend}')

    # Check 9: Volume
    vol_ok = _check_volume(token)
    result['checks']['volume'] = ('PASS' if vol_ok else 'FAIL', '')

    # Check 10: Persistence (simplified)
    persist_start = max(0, latest_idx - 4)
    persist_ok = all(
        gap_pcts[i] is not None and gap_pcts[i] > 0
        for i in range(persist_start, latest_idx + 1)
    )
    result['checks']['persistence'] = ('PASS' if persist_ok else 'FAIL', '')

    # Count passes
    passes = sum(1 for v in result['checks'].values() if v[0] == 'PASS')
    total = len(result['checks'])
    result['passes'] = passes
    result['total'] = total

    # Try full detection
    sig = detect_accel_300_v3_long(token, prices)
    result['detected'] = sig is not None

    if sig:
        result['status'] = 'FIRED'
    elif passes >= total - 1:
        result['status'] = 'ONE_AWAY'
    elif passes >= total - 2:
        result['status'] = 'TWO_AWAY'
    else:
        result['status'] = f'{total - passes}_AWAY'

    return result


# Also check if the signal already fired
def check_recent_signals(token):
    conn = None
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT created_at, price, confidence FROM signals
            WHERE token = ? AND source = 'accel-300-v3-long+'
            ORDER BY created_at DESC LIMIT 3
        """, (token.upper(),))
        return cur.fetchall()
    except:
        return []
    finally:
        if conn: conn.close()


log(f'=== V3 Monitor Started — {len(TOKENS)} tokens, {ROUNDS} rounds, {INTERVAL}s interval ===')
log(f'Tokens: {", ".join(TOKENS)}')

for round_num in range(1, ROUNDS + 1):
    log(f'\n--- Round {round_num}/{ROUNDS} ({datetime.now().strftime("%H:%M:%S")}) ---')

    for token in TOKENS:
        try:
            result = check_token(token)
            status = result['status']

            # Check for recent signals
            recent = check_recent_signals(token)
            signal_note = ''
            if recent:
                signal_note = f' [LAST SIGNAL: {recent[0][0]} @ {recent[0][1]}]'

            if status == 'FIRED':
                log(f'  🔥 {token}: FIRED! sig={result.get("detected")}{signal_note}')
            elif status in ('ONE_AWAY', 'TWO_AWAY'):
                log(f'  ⚡ {token}: {status} ({result["passes"]}/{result["total"]} checks pass)')
                for check, (res, detail) in result['checks'].items():
                    if res == 'FAIL':
                        log(f'       ❌ {check}: {detail}')
                    else:
                        log(f'       ✅ {check}: {detail}')
                log(f'       price={result["price"]:.6f} gap={result["gap"]:.3f}% peak={result.get("gap_peak",0):.3f}% pullback={result.get("pullback",0):.3f}% reexp={result.get("reexpansion",0):.3f}% rsi={result.get("rsi",0):.1f} greens={result.get("green_count",0)} trend={result.get("trend","?")}')
            else:
                fails = result['total'] - result['passes']
                log(f'  {token}: {status} ({result["passes"]}/{result["total"]} pass, {fails} fail) gap={result.get("gap",0):.3f}% rsi={result.get("rsi",0):.1f}{signal_note}')
                for check, (res, detail) in result['checks'].items():
                    if res == 'FAIL':
                        log(f'       ❌ {check}: {detail}')
        except Exception as e:
            log(f'  {token}: ERROR — {e}')

    if round_num < ROUNDS:
        log(f'  Sleeping {INTERVAL}s...')
        time.sleep(INTERVAL)

log(f'\n=== V3 Monitor Complete ===')
