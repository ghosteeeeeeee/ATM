#!/usr/bin/env python3
"""
jup_liq_cascade — follow JUP YOLO liquidation cascades (T 2026-11-05).

Thesis (opposite of jup_yolo_mirrored, which follows LIVE positions): follow
FORCED flow. When longs get liquidated one by one, the cascade IS the move —
we go SHORT; shorts liquidated → LONG. "The faster they stack up, the sooner
we enter."

Data: https://yolo-api.jup.ag/trades — kind='liquidate' is a first-class
event with market/side/leverage/notional/heldFor (measured baseline:
~87 liqs/5min feed-wide, per-cell up to 26.7/5min → trigger is a SPIKE vs a
per-cell EWMA baseline, never an absolute count).

Leverage weighting (T): 1000x has almost no wiggle room — instantly wrong,
strongest cascade evidence (weight 1.0); 500x had more wiggle and was still
wrong (0.6); lower leverage least (0.3).

Guards: HTTP failure / short feed → cycle skipped (a fetch error must never
look like a mass liquidation); dust notional filtered; kill-switches +
blacklists + cooldown per add-signal skill Layer 1.
"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, get_cooldown, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    JUP_LIQ_ENABLED, JUP_LIQ_PLUS_ENABLED, JUP_LIQ_MINUS_ENABLED,
    JUP_LIQ_WINDOW_SEC, JUP_LIQ_MIN_WEIGHT, JUP_LIQ_SPIKE_MULT,
    JUP_LIQ_BASELINE_ALPHA, JUP_LIQ_WEIGHT_1000X, JUP_LIQ_WEIGHT_500X,
    JUP_LIQ_WEIGHT_LOW, JUP_LIQ_WEIGHT_1000X_MIN, JUP_LIQ_WEIGHT_500X_MIN,
    JUP_LIQ_MIN_NOTIONAL_USDC, JUP_LIQ_MIN_FEED_TRADES,
    JUP_LIQ_COOLDOWN_HOURS, JUP_LIQ_CONF_BASE, JUP_LIQ_CONF_PER_RATIO,
    JUP_LIQ_CONF_CAP,
    LONG_BLACKLIST, SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'jup_liq_cascade_long'    # shorts liquidated → LONG
SIGNAL_TYPE_SHORT = 'jup_liq_cascade_short'  # longs liquidated → SHORT
SOURCE_LONG = 'jup-liq+'
SOURCE_SHORT = 'jup-liq-'

# limit=500 (bug_hunter): default page =100 events ≈130s — during a heavy
# cascade unseen events roll off the page and are skipped forever by last_ts.
# 500 ≈ 10min of feed covers the burst window we target.
_TRADES_URL = 'https://yolo-api.jup.ag/trades?limit=500'
_STATE_FILE = os.path.join(HERMES_DATA, 'jup_liq_cascade_state.json')
_USDC_SCALE = 1_000_000  # notional/margin are USDC 6-decimals


def _fetch_trades():
    """Latest page of trade events (limit=500). None = unusable (fail-safe: never treat a
    fetch error as liquidations)."""
    try:
        req = urllib.request.Request(
            _TRADES_URL,
            headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        trades = data.get('trades')
        if not isinstance(trades, list) or len(trades) < JUP_LIQ_MIN_FEED_TRADES:
            return None  # short/garbage response — skip cycle
        return trades
    except Exception:
        return None


def _load_state():
    try:
        with open(_STATE_FILE) as f:
            s = json.load(f)
        if not isinstance(s, dict):
            raise ValueError('bad state')
        return s
    except Exception:
        # first run: start from NOW so a backlog of old liquidations never
        # fires a phantom cascade on day one
        return {'last_ts': int(time.time()), 'window': {}, 'baseline': {}}


def _save_state(state):
    try:
        tmp = _STATE_FILE + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(state, f)
        os.replace(tmp, _STATE_FILE)
    except Exception as e:
        print(f'[jup_liq] state save failed: {e}')


def _weight(leverage: int) -> float:
    lev = int(leverage or 0)
    if lev >= JUP_LIQ_WEIGHT_1000X_MIN:
        return JUP_LIQ_WEIGHT_1000X
    if lev >= JUP_LIQ_WEIGHT_500X_MIN:
        return JUP_LIQ_WEIGHT_500X
    return JUP_LIQ_WEIGHT_LOW


def _update_baseline(state, now):
    """Fold each cell's trailing-window score into its EWMA, at most once per
    WINDOW per cell. alpha < 1 lags by design: a fresh spike is compared
    against the pre-spike baseline (fires), then the baseline slowly adapts
    (stops re-firing on a sustained storm — cooldown covers re-entries)."""
    window = state.get('window', {})
    cell_last = state.setdefault('baseline_ts', {})
    for cell, events in list(window.items()):
        if not events:
            continue
        last = cell_last.get(cell, 0)
        if now - last >= JUP_LIQ_WINDOW_SEC:
            score = sum(w for _, w in events)
            prev = state.get('baseline', {}).get(cell)
            new = score if prev is None else (
                JUP_LIQ_BASELINE_ALPHA * score
                + (1 - JUP_LIQ_BASELINE_ALPHA) * prev)
            state.setdefault('baseline', {})[cell] = new
            cell_last[cell] = now


def scan_signals() -> int:
    if not JUP_LIQ_ENABLED:
        return 0
    trades = _fetch_trades()
    if trades is None:
        return 0  # fetch failure = skip, NEVER a cascade

    now = int(time.time())
    state = _load_state()
    last_ts = int(state.get('last_ts', now))

    # ── ingest new liquidate events since last cycle ──
    window = state.setdefault('window', {})   # {cell: [[ts, weight], ...]}
    seen = state.setdefault('seen', {})       # {event_id: executedAt} dedupe
    new_liqs = 0
    for t in trades:
        if t.get('kind') != 'liquidate':
            continue
        try:
            ts = int(t['executedAt'])
        except (KeyError, TypeError, ValueError):
            # KeyError included (delta audit): a liquidate row MISSING the key
            # killed the cycle — malformed rows must skip, never crash.
            continue
        if ts < last_ts:
            # STRICT < (bug_hunter): same-second events arriving on the next
            # page must reach the `seen` dedupe below — `<=` dropped the
            # boundary second before it could be evaluated. seen[id] dedupes
            # re-ingestion (kind is static per event id, verified live).
            continue
        eid = str(t.get('id') or '')
        if not eid or eid in seen:
            continue
        seen[eid] = ts
        # dust filter (USDC 6-dec notional)
        try:
            notional = float(t.get('notional') or 0) / _USDC_SCALE
        except (TypeError, ValueError):
            notional = 0.0
        if notional < JUP_LIQ_MIN_NOTIONAL_USDC:
            continue
        market = str(t.get('market') or '').upper()
        side = str(t.get('side') or '').lower()   # side of the LIQUIDATED position
        if not market or side not in ('long', 'short'):
            continue
        cell = f'{market}:{side}'
        w = _weight(t.get('leverage'))
        window.setdefault(cell, []).append([ts, w])
        new_liqs += 1
    _feed_max = last_ts
    for t in trades:
        try:
            _e = int(t.get('executedAt') or 0)
            if _e > _feed_max:
                _feed_max = _e
        except (TypeError, ValueError):
            continue  # malformed ts on ANY event must not kill the cycle
    state['last_ts'] = _feed_max

    # ── prune: window entries + seen ids older than window + slack ──
    cutoff = now - JUP_LIQ_WINDOW_SEC - 60
    for cell in list(window.keys()):
        window[cell] = [e for e in window[cell] if e[0] > cutoff]
        if not window[cell]:
            del window[cell]
    state['seen'] = {k: v for k, v in seen.items() if v > cutoff}

    # ── evaluate each cell: spike vs PRE-spike baseline ──
    # (baseline fold happens AFTER evaluation — folding first lets the spike
    #  absorb into its own threshold and never fire; caught by spike test)
    added = 0
    baseline = state.get('baseline', {})
    for cell, events in list(window.items()):
        if not events:
            continue
        market, died_side = cell.split(':', 1)
        score = sum(w for _, w in events)
        if score < JUP_LIQ_MIN_WEIGHT:
            continue
        base = baseline.get(cell)
        if base is None or base <= 0:
            continue  # warm-up: cell has no baseline yet — never fire blind
        if score < base * JUP_LIQ_SPIKE_MULT:
            continue

        # cascade direction = WITH the forced flow: longs died → SHORT
        direction = 'SHORT' if died_side == 'long' else 'LONG'

        if direction == 'LONG':
            if not JUP_LIQ_PLUS_ENABLED:
                continue
            if market in LONG_BLACKLIST:
                continue
            sig_type, source = SIGNAL_TYPE_LONG, SOURCE_LONG
        else:
            if not JUP_LIQ_MINUS_ENABLED:
                continue
            if market in SHORT_BLACKLIST:
                continue
            sig_type, source = SIGNAL_TYPE_SHORT, SOURCE_SHORT

        if get_cooldown(market, direction=direction):
            continue

        ratio = score / max(base or JUP_LIQ_MIN_WEIGHT, 0.01)
        conf = JUP_LIQ_CONF_BASE + min(
            JUP_LIQ_CONF_CAP - JUP_LIQ_CONF_BASE,
            max(0.0, (ratio - JUP_LIQ_SPIKE_MULT) * JUP_LIQ_CONF_PER_RATIO))

        # price: entry px from the freshest matching liquidate event
        # (notional/amount = venue-consistent float price)
        price = _last_price_for(trades, market, died_side)
        if not price:
            continue

        sid = add_signal(
            token=market,
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=round(conf, 1),
            value=round(score, 2),
            price=price,
            exchange='hyperliquid',
            timeframe='5m',
            signal_metadata={
                'jup_liq_cell': cell,
                'jup_liq_score': round(score, 2),
                'jup_liq_baseline': round(base, 2) if base else None,
                'jup_liq_ratio': round(ratio, 2),
                'jup_liq_events': len(events),
                'jup_liq_died_side': died_side,
            },
        )
        if sid:
            added += 1
            print(f'[jup_liq] 🌊 CASCADE {market} {direction} — {died_side}s '
                  f'liquidated: score {score:.1f} vs baseline {base if base else "n/a"} '
                  f'(x{ratio:.1f}), {len(events)} liqs, conf={conf:.0f} sid={sid}')
            set_cooldown(market, direction, hours=JUP_LIQ_COOLDOWN_HOURS)

    # fold baselines AFTER evaluation (pre-spike baseline is what fired)
    _update_baseline(state, now)

    _save_state(state)
    return added


def _last_price_for(trades, market, died_side):
    """Entry price from the freshest matching liquidate event.

    brain_auditor #225: amount is ALWAYS "0" in the yolo feed (verified
    27/27 liquidates 2026-11-05), so notional/amount never runs and the raw
    fixed-point price (scale 1e12 — BTC 76425288918390000 / 1e12 = 76425.29)
    was stored as-is. First live fire hit exec guard:
    SUSPICIOUS PRICE 7.658e16 vs cached 76763 (ratio ~1e12) → SKIPPED.
    Fix: live HL price first (same source as jup_yolo mirror), else raw/1e12."""
    try:
        from jup_yolo_monitor import get_hl_price
        live = get_hl_price(market)
        if live and live > 0:
            return float(live)
    except Exception:
        pass
    best = None
    best_ts = -1
    for t in trades:
        if (t.get('kind') == 'liquidate'
                and str(t.get('market', '')).upper() == market
                and str(t.get('side', '')).lower() == died_side):
            # guarded (delta audit): an unparseable executedAt here raised at
            # FIRE TIME — signal died right before add_signal (worst moment).
            try:
                _ts = int(t.get('executedAt') or 0)
            except (TypeError, ValueError):
                _ts = -1
            if best is None or _ts > best_ts:
                best, best_ts = t, _ts
    if not best:
        return None
    try:
        raw = float(best.get('price') or 0)
        if raw <= 0:
            return None
        # JUP fixed-point, 1e12 scale (all markets spot-checked #225)
        px = raw / 1e12
        return px if px > 0 else None
    except (TypeError, ValueError):
        return None


def run():
    """Entry point for signals_runner — feed-driven, no prices_dict needed."""
    return scan_signals()


if __name__ == '__main__':
    # dry-run mode for the skill's verification step
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true')
    args = ap.parse_args()
    if args.dry:
        trades = _fetch_trades()
        if trades is None:
            print('[jup_liq] DRY: feed unusable — would skip cycle')
        else:
            from collections import Counter
            liqs = [t for t in trades if t.get('kind') == 'liquidate']
            cells = Counter(f"{t.get('market')}:{t.get('side')}" for t in liqs)
            print(f'[jup_liq] DRY: {len(trades)} trades, {len(liqs)} liquidate events')
            print(f'[jup_liq] DRY: cells in page: {dict(cells)}')
            st = _load_state()
            print(f'[jup_liq] DRY: state ok, last_ts={st.get("last_ts")}, '
                  f'baseline cells={len(st.get("baseline", {}))}')
    else:
        print(f'added={run()}')
