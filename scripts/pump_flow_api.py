#!/usr/bin/env python3
"""pump_flow_api.py — Generate JSON data for the Pump Flow Chain dashboard.

Writes to /var/www/hermes/data/pump_flow_data.json
Run via systemd timer or manually.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pump_flow_engine import build_pump_flow_state, save_state


def generate():
    """Generate pump flow data and save."""
    state = build_pump_flow_state()
    save_state(state)
    return state


if __name__ == '__main__':
    generate()
