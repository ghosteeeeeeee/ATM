#!/usr/bin/env python3
"""
paths.py — SINGLE SOURCE OF TRUTH for all file/DB paths in Hermes.

All scripts should import from here instead of hardcoding paths.
Two data directories:
  - HERMES_DATA  (/root/.hermes/data)   — local runtime data, gitignored
  - WWW_DATA     (/var/www/hermes/data) — served by nginx, accessible to dashboard

Usage in any script:
  from paths import *
  # or
  from paths import HERMES_DATA, WWW_DATA, RUNTIME_DB, HOTSET_FILE, ...

Environment overrides:
  HERMES_DATA_DIR=/path  — overrides /root/.hermes/data
  WWW_DATA_DIR=/path     — overrides /var/www/hermes/data
"""
import os

__all__ = [
    # Base dirs
    'HERMES_DATA', 'WWW_DATA',
    # DB paths
    'RUNTIME_DB', 'STATIC_DB', 'SIGNALS_DB', 'CANDLES_DB',
    # JSON/state files
    'TRADES_JSON', 'HOTSET_FILE', 'HOTSET_META_FILE', 'HOTSET_FAILURES_FILE',
    'HOTSET_APPROVAL_FILE', 'HOTSET_FAIL_FILE', 'SIGNALS_JSON', 'LIVESWITCH_FILE',
    'HL_CACHE_FILE', 'PIPELINE_HB_FILE', 'ATR_CACHE_FILE', 'TOP150_FILE',
    'AB_CONFIG_FILE', 'AB_RESULTS_FILE', 'AB_CACHE_FILE', 'PRICES_FILE',
    'TOKEN_INTEL_FILE', 'TOKEN_INTEL_WWW', 'PENDING_FILE', 'DELAYED_FILE',
    'REGIME_CACHE_FILE', 'TRAILING_STOPS_FILE', 'KANBAN_FILE', 'METRICS_FILE',
    'BREADCRUMBS_FILE', 'LOSS_COOLDOWN_FILE', 'COOLDOWN_FILE', 'FLIP_COUNTS_FILE',
    'WRONG_SIDE_FILE', 'VOLUME_CACHE_FILE', 'TRADE_PATTERNS_FILE',
    'RECENT_TRADES_FILE', 'HEARTBEAT_FILE', 'DAILY_BUDGET_FILE',
    'PROFIT_MONSTER_CONFIG', 'PROFIT_MONSTER_LAST', 'CUT_LOSER_CONFIG', 'CUT_LOSER_LAST',
    'STALE_ROTATION_RATE_FILE',
    # OpenClaw signal import files
    'OC_INDICATORS_FILE', 'OC_PENDING_FILE',
    # Coordination constants (sourced from hermes_constants.py)
    'SPEED_HOTSET_THRESHOLD', 'SPEED_HOTSET_BONUS',
    # Log paths
    'HERMES_LOG_DIR', 'WWW_LOG_DIR',
    # www paths
    'REGIME_4H_FILE',
    # HL Copy Trading
    'HL_COPY_DB', 'HL_COPY_REPORT', 'HL_COPY_TRADERS',
]

# ── Base directories ──────────────────────────────────────────────────────────
HERMES_DATA = os.environ.get(
    'HERMES_DATA_DIR',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
)
# Canonical: /root/.hermes/data (one level up from scripts/)

WWW_DATA = os.environ.get('WWW_DATA_DIR', '/var/www/hermes/data')

# ── Derived: DB paths ─────────────────────────────────────────────────────────
RUNTIME_DB     = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')
STATIC_DB      = os.path.join(HERMES_DATA, 'signals_hermes.db')
CANDLES_DB     = os.path.join(HERMES_DATA, 'candles.db')

# ── Derived: JSON / state files ───────────────────────────────────────────────
TRADES_JSON          = os.path.join(WWW_DATA, 'trades.json')
HOTSET_FILE          = os.path.join(WWW_DATA, 'hotset.json')
HOTSET_META_FILE     = os.path.join(WWW_DATA, 'hotset_last_updated.json')
SIGNALS_JSON         = os.path.join(WWW_DATA, 'signals.json')
LIVESWITCH_FILE      = os.path.join(WWW_DATA, 'hype_live_trading.json')
HL_CACHE_FILE        = os.path.join(WWW_DATA, 'hl_cache.json')
PIPELINE_HB_FILE     = os.path.join(WWW_DATA, 'pipeline_heartbeat.json')
ATR_CACHE_FILE       = os.path.join(HERMES_DATA, 'atr_cache.json')
TOP150_FILE          = os.path.join(HERMES_DATA, 'top150_tokens.json')
AB_CONFIG_FILE       = os.path.join(HERMES_DATA, 'ab-test-config.json')
AB_RESULTS_FILE      = os.path.join(HERMES_DATA, 'ab-test-results.json')
AB_CACHE_FILE        = os.path.join(HERMES_DATA, 'ab-variant-cache.json')
PRICES_FILE          = os.path.join(HERMES_DATA, 'prices.json')
TOKEN_INTEL_FILE     = os.path.join(HERMES_DATA, 'token_intel.json')   # also at /var/www/html/
PENDING_FILE         = os.path.join(HERMES_DATA, 'pending-signals.json')
DELAYED_FILE         = os.path.join(HERMES_DATA, 'pending-delayed-entries.json')
REGIME_CACHE_FILE    = os.path.join(HERMES_DATA, 'regime_cache.json')
TRAILING_STOPS_FILE  = os.path.join(HERMES_DATA, 'trailing_stops.json')
KANBAN_FILE          = os.path.join(HERMES_DATA, 'kanban.json')
METRICS_FILE         = os.path.join(HERMES_DATA, 'metrics.json')
BREADCRUMBS_FILE     = os.path.join(HERMES_DATA, 'breadcrumbs.json')
LOSS_COOLDOWN_FILE   = os.path.join(HERMES_DATA, 'loss_cooldowns.json')
COOLDOWN_FILE        = os.path.join(HERMES_DATA, 'signal_cooldowns.json')  # legacy per-signal cooldowns
FLIP_COUNTS_FILE     = os.path.join(WWW_DATA, 'flip_counts.json')
HOTSET_FAILURES_FILE = os.path.join(HERMES_DATA, 'hotset-failures.json')
HOTSET_APPROVAL_FILE = os.path.join(HERMES_DATA, 'hotset-approval-rate.json')
WRONG_SIDE_FILE      = os.path.join(HERMES_DATA, 'wrong_side_learning.json')
VOLUME_CACHE_FILE    = os.path.join(HERMES_DATA, 'volume_cache.json')
TRADE_PATTERNS_FILE  = os.path.join(HERMES_DATA, 'trade_patterns.json')
RECENT_TRADES_FILE   = os.path.join(HERMES_DATA, 'recent_trades.json')
HEARTBEAT_FILE       = os.path.join(HERMES_DATA, 'pipeline_heartbeat.json')
DAILY_BUDGET_FILE    = os.path.join(HERMES_DATA, 'ai_decider_daily_tokens.json')
HOTSET_FAIL_FILE     = os.path.join(HERMES_DATA, 'hotset-failures.json')
PROFIT_MONSTER_CONFIG = os.path.join(HERMES_DATA, 'profit_monster_config.json')
PROFIT_MONSTER_LAST  = os.path.join(HERMES_DATA, 'profit_monster_last_run.json')
CUT_LOSER_CONFIG     = os.path.join(HERMES_DATA, 'cut_loser_config.json')
CUT_LOSER_LAST       = os.path.join(HERMES_DATA, 'cut_loser_last_run.json')
STALE_ROTATION_RATE_FILE = os.path.join(HERMES_DATA, 'stale-rotation-rate.json')

# OpenClaw signal import files (workspace.zip snapshots)
OC_INDICATORS_FILE = os.path.join(WWW_DATA, 'oc_indicators.json')
OC_PENDING_FILE    = os.path.join(WWW_DATA, 'oc_pending_signals.json')

# Speed constants — sourced from hermes_constants.py (single source of truth)
from hermes_constants import SPEED_HOTSET_THRESHOLD, SPEED_HOTSET_BONUS

# ── Legacy / migration aliases ────────────────────────────────────────────────
SIGNALS_DB = RUNTIME_DB   # most common alias

# ── www (served) paths ───────────────────────────────────────────────────────
REGIME_4H_FILE  = '/var/www/html/regime_4h.json'   # written by 4h_regime_scanner.py
TOKEN_INTEL_WWW = '/var/www/html/token_intel.json'  # served by nginx

# ── Log paths ─────────────────────────────────────────────────────────────────
HERMES_LOG_DIR  = os.path.join(os.path.dirname(HERMES_DATA), 'logs')
WWW_LOG_DIR     = '/var/www/hermes/logs'

# ── HL Copy Trading paths ─────────────────────────────────────────────────────
HL_COPY_DB      = os.path.join(HERMES_DATA, 'hl_copy.db')
HL_COPY_REPORT  = os.path.join(WWW_DATA, 'hl_copy_report.md')
HL_COPY_TRADERS = os.path.join(WWW_DATA, 'hl_copy_traders.json')
