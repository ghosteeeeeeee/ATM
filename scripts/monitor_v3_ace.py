#!/usr/bin/env python3
"""Monitor ACE and other v3 candidates — live tuning session."""
import sys, os, sqlite3, time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signals.accel_300_v3_long import _get_1m_prices, _ema_series, _rsi, _get_15m_trend, _check_volume, detect_accel_300_v3_long
from paths import STATIC_DB, CANDLES_DB, RUNTIME_DB
from hermes_constants import (
    ACCEL_300_V3_LONG_MIN_GAP, ACCEL_300_V3_LONG_MAX_GAP,
    ACCEL_300_V3_LONG_MIN_PULLBACK, ACCEL_300_V3_LONG_MAX_PULLBACK,
    ACCEL_300_V3_LONG_REEXPAND_MIN, ACCEL_300_V3_LONG_RSI_MAX,
    ACCEL_300_V3_LONG_RSI_MIN, ACCEL_300_V3_LONG_GREEN_CAP,
    ACCEL_300_V3_LONG_GREEN_COUNT_WINDOW, ACCEL_300_V3_LONG_VELOCITY_WINDOW,
    ACCEL_300_V3_LONG_GAP_VELOCITY_THRESH,
)

PERIOD = 300
TOKENS = ['ACE', 'UNI', 'PONS', 'ARB']
INTERVAL = 120  # 2 min — faster for live tuning
ROUNDS = 15     # 30 min
LOG_FILE = '/root/.hermes/logs/v3_ace_monitor.log'

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f'{ts} {msg}'
    print(line, flush=True)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except: pass

def detailed_check(token):
    """Full breakdown of every v3 condition."""
    prices = _get_1m_prices(token, 700)
    if not prices or len(prices) < PERIOD + 30:
        return None, {'status': 'NO_DATA'}

    closes = [float(p['price']) for p in prices]
    ema300 = _ema_series(closes, PERIOD)
    gap_pcts = [
        None if ema is None or ema == 0 else (price - ema) / ema * 100.0
        for price, ema in zip(closes, ema300)
    ]

    latest_idx = len(closes) - 1
    gap_now = gap_pcts[latest_idx]
    if gap_now is None:
        return None, {'status': 'NO_EMA'}

    info = {
        'price': closes[latest_idx],
        'gap': gap_now,
        'ema300': ema300[latest_idx],
    }

    # 1. Above EMA
    if gap_now <= 0:
        info['status'] = 'BELOW_EMA'
        return None, info

    # 2. Gap range
    info['gap_ok'] = ACCEL_300_V3_LONG_MIN_GAP <= gap_now <= ACCEL_300_V3_LONG_MAX_GAP

    # 3. Peak & pullback
    peak_start = max(0, latest_idx - 20)
    recent_gaps = [g for g in gap_pcts[peak_start:latest_idx+1] if g is not None]
    gap_peak = max(recent_gaps) if recent_gaps else gap_now
    pullback = gap_peak - gap_now
    info['peak'] = gap_peak
    info['pullback'] = pullback
    info['pullback_ok'] = ACCEL_300_V3_LONG_MIN_PULLBACK <= pullback <= ACCEL_300_V3_LONG_MAX_PULLBACK

    # 4. Re-expansion
    reexpand_start = max(0, latest_idx - 3)
    gap_at_reexpand = gap_pcts[reexpand_start]
    reexpansion = gap_now - gap_at_reexpand if gap_at_reexpand else 0
    info['reexpansion'] = reexpansion
    info['reexp_ok'] = reexpansion >= ACCEL_300_V3_LONG_REEXPAND_MIN

    # 5. Velocity
    if latest_idx >= ACCEL_300_V3_LONG_VELOCITY_WINDOW:
        velocity = closes[latest_idx] - closes[latest_idx - ACCEL_300_V3_LONG_VELOCITY_WINDOW]
        info['velocity'] = velocity
        info['vel_ok'] = velocity > 0
    else:
        info['velocity'] = 0
        info['vel_ok'] = False

    # 6. Green candles
    green_count = 0
    for i in range(latest_idx, max(latest_idx - ACCEL_300_V3_LONG_GREEN_COUNT_WINDOW, 0), -1):
        if i > 0 and closes[i] > closes[i-1]:
            green_count += 1
        else:
            break
    info['greens'] = green_count
    info['green_ok'] = green_count <= ACCEL_300_V3_LONG_GREEN_CAP

    # 7. RSI
    rsi = _rsi(closes, 14)
    info['rsi'] = rsi
    info['rsi_ok'] = ACCEL_300_V3_LONG_RSI_MIN <= rsi <= ACCEL_300_V3_LONG_RSI_MAX

    # 8. Trend
    trend = _get_15m_trend(token)
    info['trend'] = trend
    info['trend_ok'] = trend != 'BEARISH'

    # 9. Volume
    info['vol_ok'] = _check_volume(token)

    # 10. Persistence
    persist_start = max(0, latest_idx - 4)
    info['persist_ok'] = all(
        gap_pcts[i] is not None and gap_pcts[i] > 0
        for i in range(persist_start, latest_idx + 1)
    )

    # 11. Gap velocity (not narrowing)
    if latest_idx >= 3 and gap_pcts[latest_idx - 1] is not None:
        gap_vel = gap_now - gap_pcts[latest_idx - 1]
        info['gap_velocity'] = gap_vel
        info['gap_vel_ok'] = gap_vel >= ACCEL_300_V3_LONG_GAP_VELOCITY_THRESH
    else:
        info['gap_velocity'] = 0
        info['gap_vel_ok'] = True

    # 12. Multi-bar gap (not narrowing over 3 bars)
    if latest_idx >= 3 and gap_pcts[latest_idx - 3] is not None:
        gap_change_3 = gap_now - gap_pcts[latest_idx - 3]
        info['gap_change_3'] = gap_change_3
        info['gap_3bar_ok'] = gap_change_3 >= ACCEL_300_V3_LONG_GAP_VELOCITY_THRESH
    else:
        info['gap_change_3'] = 0
        info['gap_3bar_ok'] = True

    # Full detection
    sig = detect_accel_300_v3_long(token, prices)
    info['detected'] = sig is not None
    if sig:
        info['sig_detail'] = sig

    # Count passes
    checks = ['gap_ok', 'pullback_ok', 'reexp_ok', 'vel_ok', 'green_ok', 'rsi_ok', 'trend_ok', 'vol_ok', 'persist_ok']
    passes = sum(1 for c in checks if info.get(c))
    info['passes'] = passes
    info['total'] = len(checks)

    if sig:
        info['status'] = 'FIRED'
    elif passes >= len(checks) - 1:
        info['status'] = 'ONE_AWAY'
    elif passes >= len(checks) - 2:
        info['status'] = 'TWO_AWAY'
    else:
        info['status'] = f'{len(checks) - passes}_AWAY'

    return sig, info

def check_recent(token):
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


log(f'=== V3 ACE Live Tuning — {len(TOKENS)} tokens, {ROUNDS} rounds, {INTERVAL}s interval ===')

for round_num in range(1, ROUNDS + 1):
    log(f'\n--- Round {round_num}/{ROUNDS} ---')

    for token in TOKENS:
        try:
            sig, info = detailed_check(token)
            recent = check_recent(token)
            status = info.get('status', '?')

            if status == 'FIRED':
                log(f'  🔥 {token}: FIRED! price={info["price"]:.6f} gap={info["gap"]:.3f}%')
                if info.get('sig_detail'):
                    d = info['sig_detail']
                    log(f'     sig: gap={d["gap_pct"]:.3f}% peak={d["gap_peak"]:.3f}% pullback={d["pullback"]:.3f}% reexp={d["reexpansion"]:.3f}% rsi={d["rsi"]:.1f}')
            elif status in ('ONE_AWAY', 'TWO_AWAY'):
                # Detailed breakdown
                log(f'  ⚡ {token}: {status} ({info["passes"]}/{info["total"]}) price={info["price"]:.6f}')
                log(f'     gap={info["gap"]:.3f}% ({"✅" if info.get("gap_ok") else "❌"} need {ACCEL_300_V3_LONG_MIN_GAP}-{ACCEL_300_V3_LONG_MAX_GAP}%)')
                log(f'     peak={info.get("peak",0):.3f}% pullback={info.get("pullback",0):.3f}% ({"✅" if info.get("pullback_ok") else "❌"} need {ACCEL_300_V3_LONG_MIN_PULLBACK}-{ACCEL_300_V3_LONG_MAX_PULLBACK}%)')
                log(f'     reexp={info.get("reexpansion",0):.3f}% ({"✅" if info.get("reexp_ok") else "❌"} need >{ACCEL_300_V3_LONG_REEXPAND_MIN}%)')
                log(f'     vel={info.get("velocity",0):.6f} ({"✅" if info.get("vel_ok") else "❌"}) greens={info.get("greens",0)} ({"✅" if info.get("green_ok") else "❌"} max {ACCEL_300_V3_LONG_GREEN_CAP})')
                log(f'     rsi={info.get("rsi",0):.1f} ({"✅" if info.get("rsi_ok") else "❌"} {ACCEL_300_V3_LONG_RSI_MIN}-{ACCEL_300_V3_LONG_RSI_MAX}) trend={info.get("trend","?")} ({"✅" if info.get("trend_ok") else "❌"})')
                log(f'     gap_vel={info.get("gap_velocity",0):.3f}% gap_3bar={info.get("gap_change_3",0):.3f}%')
                if recent:
                    log(f'     last_signal: {recent[0][0]} @ {recent[0][1]}')
            else:
                fails = info['total'] - info['passes']
                log(f'  {token}: {status} ({info["passes"]}/{info["total"]}) gap={info.get("gap",0):.3f}% rsi={info.get("rsi",0):.1f}')
                # Show only failing checks
                for key, label in [
                    ('gap_ok', f'gap {info.get("gap",0):.3f}%'),
                    ('pullback_ok', f'pullback {info.get("pullback",0):.3f}%'),
                    ('reexp_ok', f'reexp {info.get("reexpansion",0):.3f}%'),
                    ('vel_ok', f'vel {info.get("velocity",0):.6f}'),
                    ('green_ok', f'greens {info.get("greens",0)}'),
                    ('rsi_ok', f'rsi {info.get("rsi",0):.1f}'),
                    ('trend_ok', f'trend {info.get("trend","?")}'),
                ]:
                    if not info.get(key):
                        log(f'       ❌ {label}')
        except Exception as e:
            log(f'  {token}: ERROR — {e}')

    if round_num < ROUNDS:
        log(f'  zzz {INTERVAL}s...')
        time.sleep(INTERVAL)

log(f'\n=== Monitor Complete ===')
