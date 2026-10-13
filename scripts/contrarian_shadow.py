#!/usr/bin/env python3
"""
contrarian_shadow.py — Shadow-mode contrarian engine.

Collects counterfactual data: when a LOSER signal fires, log what the
contrarian trade WOULD have done. No live execution.

Usage: called from signal_compactor.py after scoring, or standalone.
Output: data/contrarian_shadow.jsonl (one JSON line per event)

Classification rules (30d data):
  WINNER:  total PnL > 0  → trade normally, no contrarian
  NEUTRAL: PnL ≈ 0 or WR 45-55% → trade normally, no contrarian
  LOSER:   PnL < 0 AND WR < 45% → contrarian candidate (shadow log)
"""

import os
import sys
import json
import time
import sqlite3
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

# ── Signal Classification (30d verified from PostgreSQL 2026-10-13) ──────────
# Format: signal_name -> (direction, n_30d, wr, pnl_30d, classification)
# WINNER: PnL > 0 → trade normally
# LOSER:  PnL < 0 AND WR < 45% → contrarian candidate
# NEUTRAL: everything else → trade normally

CONTRARIAN_CLASSIFICATION = {
    # ── LOSERS (contrarian candidates) ──
    'pullback-entry-':        ('SHORT', 76, 44.7, -1.97, 'LOSER'),
    'mover+':                 ('LONG',  16, 43.8, -1.16, 'LOSER'),
    'mover-':                 ('SHORT',  5, 20.0, -0.73, 'LOSER'),
    'pump-chain-':            ('SHORT', 111, 43.2, -0.57, 'LOSER'),
    'mtf-regime-trend+':      ('LONG',   9, 44.4, -0.46, 'LOSER'),
    'hmacd_mtf-+':            ('LONG',   8, 25.0, -0.46, 'LOSER'),
    'rr-struct-v2+':          ('LONG',  10, 40.0, -0.45, 'LOSER'),
    'pump-chain-v5':          ('LONG',  12, 33.3, -0.42, 'LOSER'),
    'mtf-regime-trend-':      ('SHORT',  5, 40.0, -0.42, 'LOSER'),
    'open-skies+':            ('LONG',   5, 20.0, -0.42, 'LOSER'),
    'grind-trend-':           ('SHORT',  5, 20.0, -0.38, 'LOSER'),
    'accel-300-':             ('SHORT',  8, 37.5, -0.34, 'LOSER'),
    'btc-pump-rider+':        ('LONG',   5,  0.0, -0.34, 'LOSER'),
    'trend-ride+':            ('LONG',   7, 42.9, -0.18, 'LOSER'),
    'accel-300-breakout':     ('SHORT',  7, 28.6, -0.12, 'LOSER'),
    'hmacd_mtf--':            ('SHORT',  4, 25.0, -0.19, 'LOSER'),

    # ── WINNERS (trade normally) ──
    'pump-chain+':            ('LONG', 101, 42.6,  2.78, 'WINNER'),
    'volume-breakout-long+':  ('LONG',  39, 48.7,  2.32, 'WINNER'),
    'doji-bottom-long':       ('LONG',  24, 54.2,  0.24, 'WINNER'),
    'grind-trend+':           ('LONG',  18, 50.0,  0.24, 'WINNER'),
    'bb-bounce-v2-long+':     ('LONG',  37, 56.8,  0.21, 'WINNER'),
    'continuation+':          ('LONG',   6, 33.3,  0.22, 'WINNER'),
    'volume-buildup+':        ('LONG',   2, 50.0,  0.05, 'WINNER'),
    'oversold-bounce+':       ('LONG',   9, 44.4, -0.08, 'NEUTRAL'),
    'bb-squeeze+':            ('LONG',  70, 61.4, -0.04, 'NEUTRAL'),
    'ai-trader+':             ('LONG',  12, 50.0, -0.12, 'NEUTRAL'),
    'continuum-osc+':         ('LONG',   8, 50.0, -0.14, 'NEUTRAL'),
    'continuum_engine':       ('LONG',  10, 10.0,  0.08, 'NEUTRAL'),
    'r2v2-long3':             ('LONG',   4, 50.0,  0.50, 'NEUTRAL'),
    'r2v2-long9':             ('LONG',   2, 50.0,  0.12, 'NEUTRAL'),
}

SHADOW_FILE = os.path.join(HERMES_DATA, 'contrarian_shadow.jsonl')
SHADOW_SUMMARY = os.path.join(HERMES_DATA, 'contrarian_shadow_summary.json')


def classify_signal(signal_name: str) -> str:
    """Returns 'WINNER', 'LOSER', 'NEUTRAL', or 'UNKNOWN'."""
    # Try exact match first
    if signal_name in CONTRARIAN_CLASSIFICATION:
        return CONTRARIAN_CLASSIFICATION[signal_name][4]
    # Try stripping version suffixes (-v2, -v5, -v6, etc.)
    import re
    stripped = re.sub(r'-v\d+$', '', signal_name)
    if stripped in CONTRARIAN_CLASSIFICATION:
        return CONTRARIAN_CLASSIFICATION[stripped][4]
    # Try bare form (remove trailing +/-)
    bare = signal_name.rstrip('+-')
    if bare in CONTRARIAN_CLASSIFICATION:
        return CONTRARIAN_CLASSIFICATION[bare][4]
    return 'UNKNOWN'


def get_contrarian_direction(signal_name: str) -> str:
    """Returns the OPPOSITE direction for a contrarian trade."""
    cls = classify_signal(signal_name)
    if cls != 'LOSER':
        return None
    if signal_name in CONTRARIAN_CLASSIFICATION:
        orig_dir = CONTRARIAN_CLASSIFICATION[signal_name][0]
    else:
        orig_dir = 'SHORT' if signal_name.endswith('-') else 'LONG'
    return 'LONG' if orig_dir == 'SHORT' else 'SHORT'


def log_contrarian_shadow(token: str, signal_name: str, original_direction: str,
                          entry_price: float, confidence: float, reason: str = ''):
    """Log a contrarian shadow event (no execution)."""
    event = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'token': token,
        'signal': signal_name,
        'original_direction': original_direction,
        'contrarian_direction': get_contrarian_direction(signal_name),
        'entry_price': entry_price,
        'confidence': confidence,
        'classification': classify_signal(signal_name),
        'reason': reason,
        'mode': 'SHADOW',
    }
    try:
        with open(SHADOW_FILE, 'a') as f:
            f.write(json.dumps(event) + '\n')
    except Exception:
        pass


def get_shadow_summary() -> dict:
    """Read shadow summary (updated by hourly monitor)."""
    try:
        if os.path.exists(SHADOW_SUMMARY):
            with open(SHADOW_SUMMARY) as f:
                return json.load(f)
    except Exception:
        pass
    return {'total_events': 0, 'by_signal': {}}


if __name__ == '__main__':
    # Test classification
    print('Signal Classification (30d):')
    print(f'{"Signal":30s} {"Dir":5s} {"n":>4s} {"WR%":>6s} {"PnL":>7s} {"Class":8s} {"Contrarian":10s}')
    print('-' * 80)
    for sig, (d, n, wr, pnl, cls) in sorted(CONTRARIAN_CLASSIFICATION.items(), key=lambda x: x[1][3]):
        contr = get_contrarian_direction(sig) or '—'
        print(f'{sig:30s} {d:5s} {n:4d} {wr:5.1f}% {pnl:+7.2f} {cls:8s} {contr:10s}')

    losers = sum(1 for v in CONTRARIAN_CLASSIFICATION.values() if v[4] == 'LOSER')
    winners = sum(1 for v in CONTRARIAN_CLASSIFICATION.values() if v[4] == 'WINNER')
    neutral = sum(1 for v in CONTRARIAN_CLASSIFICATION.values() if v[4] == 'NEUTRAL')
    print(f'\nTotal: {losers} LOSERS, {winners} WINNERS, {neutral} NEUTRAL')
    loser_pnl = sum(v[3] for v in CONTRARIAN_CLASSIFICATION.values() if v[4] == 'LOSER')
    print(f'LOSER total PnL: ${loser_pnl:+.2f} (contrarian opportunity)')
