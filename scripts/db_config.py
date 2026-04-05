"""
Database configuration for Hermes trading system.
Single source of truth for all DB paths.

ARCHITECTURE:
  signals_hermes.db  — static backfill data, git-tracked
    └── price_history, latest_prices, regime_log

  signals_hermes_runtime.db  — runtime data, LOCAL ONLY (.gitignored)
    └── signals, decisions, token_intel, cooldown_tracker, momentum_cache
"""
import os

# Base directory for all data
HERMES_DATA_DIR = os.environ.get('HERMES_DATA_DIR', '/root/.hermes/data')

# Static DB — committed to git, contains backfill data
HERMES_STATIC_DB = os.path.join(HERMES_DATA_DIR, 'signals_hermes.db')

# Runtime DB — local only, never commit this
HERMES_RUNTIME_DB = os.path.join(HERMES_DATA_DIR, 'signals_hermes_runtime.db')

# Legacy path (for migration only — scripts should update)
LEGACY_SIGNALS_DB = '/root/.hermes/data/openclaw_signals.db'
