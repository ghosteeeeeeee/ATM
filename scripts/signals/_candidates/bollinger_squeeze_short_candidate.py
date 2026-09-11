#!/usr/bin/env python3
"""
bollinger_squeeze (SHORT) — Auto-generated candidate signal.

Pattern: bollinger_squeeze
Direction: SHORT
Backtest WR: 55.5%
Backtest PnL: +0.4909%
Backtest trades: 589
Generated: 2026-09-11 17:42 UTC

STATUS: CANDIDATE — requires human review before enabling.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from paths import HERMES_DATA

SIGNAL_TYPE = 'bollinger_squeeze_short'
SIGNAL_SOURCE = 'researcher'


def run(prices_dict=None):
    """Detect bollinger_squeeze SHORT signals. Returns list of signal dicts."""
    # TODO: Implement real-time detection logic
    # This is a template — fill in the detection algorithm
    return []
