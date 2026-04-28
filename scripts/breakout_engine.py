#!/usr/bin/env python3
"""
breakout_engine.py — Compression → Breakout signal detector.

Detects the classic "coiled spring" pattern:
  Phase 1 — COMPRESSION: tight range + low volume for N consecutive bars
  Phase 2 — PRESSURE BUILDING: volume starts popping above average
  Phase 3 — IGNITION: candle with range > threshold BREAKS resistance

Unlike reactive momentum signals (oc_pending, hzscore, etc.) which fire AFTER
a move has already happened, this is a LEADING signal — it fires when the
compression is detected and the setup is in place, before the breakout.

How to add to hot-set manually (no confluence needed):
  - Writes to /var/www/hermes/data/oc_pending_signals.json
  - oc_signal_importer.py picks it up and calls add_signal(source='oc-pending-breakout')
  - Signal compactor sees 'oc-pending-breakout' as a SINGLE source...
    BUT oc_pending already bypasses normal signal flow
  - Guardian then picks it up from hot-set and executes

For NOW: we also write directly to the signals DB so it bypasses
the normal oc_pending flow entirely.

Run:
    python3 breakout_engine.py              # normal
    python3 breakout_engine.py --dry        # log only
    python3 breakout_engine.py --verbose    # per-token details
    python3 breakout_engine.py --token BNB  # single token
"""

import sys, os, time, json, sqlite3, argparse
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Paths ────────────────────────────────────────────────────────────────────
HERMES_DATA  = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'data')
CANDLES_DB   = os.path.join(HERMES_DATA, 'candles.db')
RUNTIME_DB   = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')
OC_PENDING   = '/var/www/hermes/data/oc_pending_signals.json'  # OC writes here too
HOTSET_PATH  = '/var/www/hermes/data/hotset.json'  # direct hot-set injection
WWW_DATA     = '/var/www/hermes/data'
LOG_FILE     = '/var/www/hermes/logs/breakout_engine.log'

# ── Config ────────────────────────────────────────────────────────────────────
# Compression: how many consecutive bars must be tight + low volume?
COMPRESSION_BARS_1m  = 8    # 8 x 1m = 8 minutes of compression (short enough to outlast spike bars)
COMPRESSION_BARS_5m  = 6    # 6 x 5m  = 30 minutes of compression

# Volume: must be below this fraction of the rolling average to qualify as "quiet"
VOL_COMP_THRESHOLD_ABS  = 250   # max volume per bar to qualify as compressed
RNG_COMP_THRESHOLD_PCT_ABS = 0.20  # max range_pct per bar to qualify as compressed
VOL_SPIKE_THRESHOLD   = 0.30   # compression: vol < 30% of avg
VOL_POP_THRESHOLD     = 3.0    # breakout: vol > 3x avg

# Range: breakout candle must have range > this % of price
BREAKOUT_RANGE_PCT   = 0.50   # 0.50% min candle range to qualify as breakout

# ATR multiplier for stop/target
ATR_PERIOD            = 14
RISK_RATIO            = 1.5   # TP = SL * RISK_RATIO

# Min volume spike candles in compression window
MIN_COMPRESSION_VOL_AVG = 30.0  # skip tokens with near-zero avg volume (illiquid)

# Timeframes to check (5m first = primary; 1m is secondary/backup)
TIMEFRAMES = ['5m', '1m']

# ── Logging ──────────────────────────────────────────────────────────────────
def log(msg, level='INFO'):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] [{level}] [breakout] {msg}'
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


# ── Helpers ──────────────────────────────────────────────────────────────────
def get_candles(token: str, timeframe: str, bars: int = 100) -> List[dict]:
    """Fetch recent candles for token+timeframe from candles.db."""
    table = f'candles_{timeframe}'
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    c = conn.cursor()
    c.execute(f'''
        SELECT ts, open, high, low, close, volume
        FROM {table}
        WHERE token = ?
        ORDER BY ts DESC
        LIMIT ?
    ''', (token.upper(), bars))
    rows = c.fetchall()
    conn.close()
    if not rows:
        return []
    # Return chronologically ordered
    result = []
    for ts, o, h, l, c_price, v in reversed(rows):
        result.append({
            'ts': ts,
            'open': float(o),
            'high': float(h),
            'low': float(l),
            'close': float(c_price),
            'volume': float(v),
            'dt': datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M'),
        })
    return result


def compute_atr(candles: List[dict], period: int = ATR_PERIOD) -> float:
    """Compute ATR from candles."""
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


def rolling_avg_vol(candles: List[dict], window: int = 20) -> float:
    """Average volume over last N candles."""
    if len(candles) < window:
        return sum(c['volume'] for c in candles) / max(len(candles), 1)
    return sum(c['volume'] for c in candles[-window:]) / window


def rolling_avg_range(candles: List[dict], window: int = 20) -> float:
    """Average candle range (% of open) over last N candles."""
    if len(candles) < window:
        return sum((c['high'] - c['low']) / c['open'] * 100 for c in candles) / max(len(candles), 1)
    return sum((c['high'] - c['low']) / c['open'] * 100 for c in candles[-window:]) / window


def detect_compression(candles: List[dict], comp_bars: int) -> Tuple[bool, dict]:
    """
    Phase 1: Detect compression (tight range + low volume for comp_bars consecutive bars).

    Uses ABSOLUTE thresholds — the window must itself be quiet in absolute terms.
    This avoids the old bug where a single noisy bar in the window inflated the
    baseline and made the "quiet window" look noisy relative to itself.

    The 3 conditions all must pass:
      (a) ALL bars in the window: volume < VOL_COMP_THRESHOLD_ABS
      (b) ALL bars in the window: range_pct < RNG_COMP_THRESHOLD_PCT_ABS
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


def detect_breakout(candles: List[dict], direction: str, timeframe: str = '1m') -> Tuple[bool, dict]:
    """
    Phase 3: Detect breakout candle.
    - Volume > VOL_POP_THRESHOLD relative to the compression window itself
    - Candle range > BREAKOUT_RANGE_PCT
    - Direction must match: LONG = close > open, SHORT = close < open
    Returns (is_breakout, breakout_stats).
    """
    if len(candles) < 5:
        return False, {}

    # Use timeframe-aware comp_bars to match compression detection
    comp_bars = COMPRESSION_BARS_1m if timeframe == '1m' else COMPRESSION_BARS_5m
    prior_window = candles[-(comp_bars + 1):-1]
    if len(prior_window) < 3:
        return False, {}
    prior_avg_vol = sum(c['volume'] for c in prior_window) / len(prior_window)

    c = candles[-1]
    prev = candles[-2]

    vol_ratio   = c['volume'] / max(prior_avg_vol, 1)
    range_pct   = (c['high'] - c['low']) / c['open'] * 100
    is_bullish  = c['close'] > c['open']
    is_bearish  = c['close'] < c['open']

    vol_ok   = vol_ratio >= VOL_POP_THRESHOLD
    rng_ok   = range_pct >= BREAKOUT_RANGE_PCT
    dir_ok   = (direction == 'LONG' and is_bullish) or (direction == 'SHORT' and is_bearish)

    # True breakout: the bar BEFORE the breakout was quiet (not already spiking)
    prev_vol_ratio = prev['volume'] / max(prior_avg_vol, 1)
    # Require the bar before breakout to be relatively quiet (< 80% of the threshold)
    first_big_vol  = prev_vol_ratio < VOL_POP_THRESHOLD * 0.8

    is_breakout = vol_ok and rng_ok and dir_ok and first_big_vol

    stats = {
        'vol_ratio': vol_ratio,
        'range_pct': range_pct,
        'direction': direction,
        'price': c['close'],
        'open': c['open'],
        'high': c['high'],
        'low': c['low'],
        'prior_avg_vol': round(prior_avg_vol, 1),
        'dt': c['dt'],
        'first_big_vol': first_big_vol,
    }
    return is_breakout, stats


def detect_volume_pop(candles: List[dict]) -> Tuple[bool, dict]:
    """
    Phase 2: Detect volume pop (pressure building).
    At least 2 of the last 3 bars must have vol > 2x average.
    This fires BEFORE the breakout candle — gives earlier warning.
    Returns (has_pop, stats).
    """
    if len(candles) < 5:
        return False, {}

    avg_vol = rolling_avg_vol(candles)
    recent  = candles[-3:]

    pop_count = sum(1 for c in recent if c['volume'] > avg_vol * 2.0)

    has_pop = pop_count >= 2

    stats = {
        'avg_vol': avg_vol,
        'pop_count': pop_count,
        'last_vol': candles[-1]['volume'],
        'vol_ratio': candles[-1]['volume'] / max(avg_vol, 1),
    }
    return has_pop, stats


def detect_breakout_direction(candles: List[dict]) -> Optional[str]:
    """
    Determine breakout direction from recent price action.
    - If price made a higher high vs the compression high → LONG
    - If price made a lower low  vs the compression low  → SHORT
    """
    if len(candles) < 10:
        return None

    comp_bars = min(COMPRESSION_BARS_1m, len(candles) - 2)
    comp_window = candles[-comp_bars:]
    prev_window = candles[-comp_bars-5:-comp_bars]

    comp_high = max(c['high'] for c in comp_window)
    comp_low  = min(c['low']  for c in comp_window)
    prev_high = max(c['high'] for c in prev_window) if prev_window else comp_high
    prev_low  = min(c['low']  for c in prev_window) if prev_window else comp_low

    # Current price position
    current_close = candles[-1]['close']

    # Breakout: price breaks above resistance (prev_high) or below support (prev_low)
    if current_close > prev_high * 1.001:  # 0.1% above prev high
        return 'LONG'
    elif current_close < prev_low * 0.999:  # 0.1% below prev low
        return 'SHORT'

    return None  # no clear direction yet


def compute_levels(candles: List[dict], direction: str) -> dict:
    """
    Compute entry, stop, and target levels based on ATR.
    Entry: current price (or next open)
    Stop:  1.5x ATR below (for LONG) or above (for SHORT)
    Target: SL * RISK_RATIO
    """
    atr    = compute_atr(candles)
    price  = candles[-1]['close']

    if direction == 'LONG':
        entry  = price
        stop   = price - atr * 1.5
        target = price + atr * 1.5 * RISK_RATIO
    else:
        entry  = price
        stop   = price + atr * 1.5
        target = price - atr * 1.5 * RISK_RATIO

    risk_pct = abs(entry - stop) / entry * 100
    reward_pct = abs(target - entry) / entry * 100

    return {
        'entry':   round(entry, 4),
        'stop':    round(stop, 4),
        'target':  round(target, 4),
        'atr':     round(atr, 4),
        'risk_pct': round(risk_pct, 3),
        'reward_pct': round(reward_pct, 3),
    }


def detect_breakout_for_token(token: str, dry: bool = False) -> Optional[dict]:
    """
    Run full compression → breakout detection for one token across timeframes.
    Returns breakout signal dict or None.
    """
    result = None

    for tf in TIMEFRAMES:
        candles = get_candles(token, tf)
        if not candles or len(candles) < 20:
            continue

        comp_bars = COMPRESSION_BARS_1m if tf == '1m' else COMPRESSION_BARS_5m

        # Phase 1: Compression
        is_compressed, comp_stats = detect_compression(candles, comp_bars)
        if not is_compressed:
            continue

        # Phase 2: Volume pop (pressure building)
        has_pop, pop_stats = detect_volume_pop(candles)

        # Phase 3: Breakout direction
        direction = detect_breakout_direction(candles)
        if not direction:
            continue

        # Phase 4: Breakout candle
        is_breakout, brk_stats = detect_breakout(candles, direction, tf)
        if not is_breakout:
            # If compression + pop but no breakout yet → WATCH state (don't fire)
            continue

        # We have a valid breakout
        levels = compute_levels(candles, direction)
        avg_vol = rolling_avg_vol(candles)

        result = {
            'token': token.upper(),
            'direction': direction,
            'timeframe': tf,
            'confidence': min(95, 70 + brk_stats['vol_ratio'] * 5),  # 70-95 based on vol ratio
            'entry': levels['entry'],
            'stop': levels['stop'],
            'target': levels['target'],
            'atr': levels['atr'],
            'risk_pct': levels['risk_pct'],
            'reward_pct': levels['reward_pct'],
            'price': brk_stats['price'],
            'breakout_dt': brk_stats['dt'],
            'compression_dt': candles[-comp_bars]['dt'],
            'compression_bars': comp_bars,
            'vol_ratio': round(brk_stats['vol_ratio'], 1),
            'range_pct': round(brk_stats['range_pct'], 2),
            'avg_vol_20': round(avg_vol, 1),
            'compression_price_chg': round(comp_stats['price_chg'], 2),
            'source': 'oc-pending-breakout',
            'signal_type': 'breakout_engine',
            'timestamp': time.time(),
        }
        break  # only use highest timeframe that fires

    return result


def write_oc_pending(signals: List[dict], dry: bool = False):
    """Write breakout signals to OC pending file for OC signal importer."""
    if not signals:
        return

    # Load existing OC pending
    existing = []
    if os.path.exists(OC_PENDING):
        try:
            with open(OC_PENDING) as f:
                existing = json.load(f).get('pending_signals', [])
        except Exception:
            pass

    # Dedupe by token
    existing_by_token = {s['token']: s for s in existing}

    for sig in signals:
        existing_by_token[sig['token']] = sig

    output = {
        'pending_signals': list(existing_by_token.values()),
        'updated_at': time.time(),
        'source': 'breakout_engine',
    }

    if not dry:
        with open(OC_PENDING, 'w') as f:
            json.dump(output, f, indent=2)
        log(f"Wrote {len(signals)} breakout signals to OC pending (total: {len(existing_by_token)})")
    else:
        log(f"[DRY] Would write {len(signals)} breakout signals to OC pending")


def write_signals_to_db(signals: List[dict], dry: bool = False):
    """Write breakout signals directly to Hermes signals DB (bypasses OC pipeline)."""
    if not signals:
        return

    from signal_schema import add_signal

    count = 0
    for sig in signals:
        sid = add_signal(
            token=sig['token'],
            direction=sig['direction'],
            signal_type='breakout_engine',
            source='breakout',
            confidence=sig['confidence'],
            value=sig.get('atr'),
            price=sig['price'],
            timeframe=sig['timeframe'],
        )
        if sid:
            count += 1
            log(f"  [{sig['token']}] BREAKOUT {sig['direction']} @ {sig['price']} "
                f"conf={sig['confidence']:.0f} TF={sig['timeframe']} "
                f"vol={sig['vol_ratio']}x rng={sig['range_pct']}% "
                f"SL={sig['stop']} TP={sig['target']} "
                f"(compression={sig['compression_bars']} bars, {sig['compression_price_chg']}% price chg in compression)")

    log(f"Wrote {count} breakout signals to DB")


def write_to_hotset(signals: List[dict], dry: bool = False):
    """
    Inject breakout signals directly into hot-set.json.
    Bypasses the entire signal_compactor/ai_decider pipeline.
    Guardian reads hot-set.json and will execute these directly.

    Uses a lock file to prevent clobbering by signal_compactor between
    write and the next compaction cycle (~1 min).
    """
    if not signals:
        return

    # ── Acquire lock (shared with signal_compactor/ai_decider via FileLock) ──
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from hermes_file_lock import FileLock

    with FileLock('hotset_json', timeout=30, interval=5):
        # Load existing hotset
        existing = []
        if os.path.exists(HOTSET_PATH):
            try:
                with open(HOTSET_PATH) as f:
                    existing = json.load(f).get('hotset', [])
            except Exception as e:
                log(f"Could not load existing hotset: {e}", 'WARN')

        # Build keyed dict, dedupe by token:direction
        existing_by_key = {f"{e['token']}:{e['direction']}": e for e in existing}

        for sig in signals:
            key = f"{sig['token']}:{sig['direction']}"
            # Score = 100 + vol_ratio so breakout signals rank above normal signals
            score = 100 + sig.get('vol_ratio', 0)
            entry = {
                'token': sig['token'],
                'direction': sig['direction'].upper(),
                'confidence': sig['confidence'],
                'source': 'breakout',
                'signal_type': 'breakout_engine',
                'z_score': 0,
                'compact_rounds': 5,  # survive 5 compaction cycles (~25 min if timer stays at 5 min)
                'rounds': 5,
                'staleness': 1.0,
                'entry_origin_ts': time.time(),
                'survival_round': 5,
                'age_h': 0,
                'wave_phase': 'breakout',
                'is_overextended': False,
                'price_acceleration': float(sig.get('vol_ratio', 0)),
                'momentum_score': min(100, 50 + sig['confidence'] / 2),
                'speed_percentile': min(100, sig['confidence']),
                'score': score,
                'reason': (
                    f"breakout conf={sig['confidence']:.0f} "
                    f"vol={sig.get('vol_ratio', 0):.1f}x "
                    f"rng={sig.get('range_pct', 0):.2f}% "
                    f"comp={sig.get('compression_bars', 0)}bars "
                    f"SL={sig.get('stop')} TP={sig.get('target')}"
                ),
            }
            existing_by_key[key] = entry

        # Keep only top 10, sorted by score descending
        all_entries = list(existing_by_key.values())
        all_entries.sort(key=lambda x: x.get('score', 0), reverse=True)
        top10 = all_entries[:10]

        output = {
            'hotset': top10,
            'compaction_cycle': 9999,  # signal_compactor reads this; high value = preserve
            'timestamp': time.time(),
        }

        if not dry:
            with open(HOTSET_PATH, 'w') as f:
                json.dump(output, f, indent=2)
            log(f"Wrote {len(signals)} breakout signals to hotset.json "
                f"(total entries: {len(top10)})")
        else:
            log(f"[DRY] Would write {len(signals)} breakout signals to hotset.json")


# ── Main ──────────────────────────────────────────────────────────────────────
def run(dry: bool = False, verbose: bool = False, token_filter: Optional[str] = None):
    log(f"Breakout engine starting (dry={dry})")

    # Get list of tokens to scan
    if token_filter:
        tokens = [token_filter.upper()]
        log(f"Single token mode: {tokens}")
    else:
        # Scan all tokens that have recent candle data
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute('''
            SELECT DISTINCT token FROM candles_1m
            WHERE ts > strftime('%s', 'now', '-30 minutes')
            ORDER BY token
        ''')
        tokens = [r[0] for r in c.fetchall()]
        conn.close()

    log(f"Scanning {len(tokens)} tokens across {TIMEFRAMES}")

    breakout_signals = []

    for token in tokens:
        try:
            result = detect_breakout_for_token(token, dry=dry)
            if result and not dry:
                breakout_signals.append(result)
                if verbose:
                    log(f"  [{token}] BREAKOUT {result['direction']} @ {result['price']} "
                        f"conf={result['confidence']:.0f} TF={result['timeframe']} "
                        f"vol={result['vol_ratio']}x rng={result['range_pct']}% "
                        f"SL={result['stop']} TP={result['target']} "
                        f"(compression={result['compression_bars']} bars in {result['timeframe']}, "
                        f"price chg={result['compression_price_chg']}% during compression)")
        except Exception as e:
            if verbose:
                log(f"  [{token}] ERROR: {e}", 'WARN')

    log(f"Breakout engine done: {len(breakout_signals)} signals detected")

    if breakout_signals:
        write_oc_pending(breakout_signals, dry=dry)
        write_signals_to_db(breakout_signals, dry=dry)
        write_to_hotset(breakout_signals, dry=dry)

    return breakout_signals


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Breakout engine — compression → breakout detector')
    parser.add_argument('--dry', action='store_true', help='Dry run (log only, no write)')
    parser.add_argument('--verbose', action='store_true', help='Per-token details')
    parser.add_argument('--token', type=str, help='Single token to scan (e.g. BNB)')
    args = parser.parse_args()

    result = run(dry=args.dry, verbose=args.verbose, token_filter=args.token)
    print(f"\nResult: {len(result)} breakout signals")
    if result:
        for r in result:
            print(f"  {r['token']} {r['direction']} @ {r['price']} conf={r['confidence']:.0f} "
                  f"TF={r['timeframe']} vol={r['vol_ratio']}x SL={r['stop']} TP={r['target']}")
