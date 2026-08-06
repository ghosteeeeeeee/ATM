#!/usr/bin/env python3
"""
bollinger_squeeze (LONG) — Auto-generated candidate signal.

Pattern: bollinger_squeeze
Direction: LONG
Backtest WR: 65.3%
Backtest PnL: +0.5796%
Backtest trades: 668
Generated: 2026-08-06 18:01 UTC

STATUS: CANDIDATE — requires human review before enabling.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from paths import HERMES_DATA

SIGNAL_TYPE = 'bollinger_squeeze_long'
SIGNAL_SOURCE = 'researcher'


def run(prices_dict=None):
    """Detect bollinger_squeeze LONG signals. Returns list of signal dicts."""
    # TODO: Implement real-time detection logic
    # This is a template — fill in the detection algorithm
    return []
