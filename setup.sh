#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Hermes Trading System — Fresh Install Setup
# Run this once on a new machine. Takes ~30s.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${YELLOW}Hermes Trading System — Setup${NC}"
echo "─────────────────────────────────"

# 1. Python deps
echo -e "\n[1/4] Checking Python deps..."
python3 -c "import requests, sqlite3" 2>/dev/null && echo "  OK: requests, sqlite3" \
  || { echo -e "${RED}Missing: pip install requests sqlite3${NC}"; exit 1; }

# 2. Create directories
echo -e "\n[2/4] Creating directories..."
mkdir -p data logs seed sessions
echo "  OK: data/ logs/ seed/ sessions/"

# 2b. Load seed SQL if it was extracted alongside setup.sh (from git zip)
SEED_ZIP=$(find . -maxdepth 1 -name "*_seed.sql" 2>/dev/null | head -1)
if [[ -f "$SEED_ZIP" && ! -s seed/signals_hermes.sql ]]; then
    echo -e "\n[2b] Found seed SQL — copying to seed/signals_hermes.sql ..."
    cp "$SEED_ZIP" seed/signals_hermes.sql
    echo "  Loaded: $(wc -l < seed/signals_hermes.sql) lines"
fi

# 3. Init DBs (auto-loads seed if empty)
echo -e "\n[3/4] Initializing databases..."
python3 scripts/signal_schema.py
echo "  Run: python3 scripts/signal_schema.py"

# 4. Quick pipeline smoke test
echo -e "\n[4/4] Smoke test — price collector..."
python3 scripts/price_collector.py 2>&1 | grep -E "Collected|error|Error" | head -3

echo -e "\n${GREEN}Setup complete!${NC}"
echo "─────────────────────────────────"
echo "Next steps:"
echo "  1. cp .env.example .env   # add your Hyperliquid/OpenAI keys"
echo "  2. python3 scripts/price_collector.py"
echo "  3. python3 scripts/signal_gen.py"
echo "  4. python3 scripts/ai-decider.py"
echo "  5. python3 scripts/decider_run.py"
echo ""
echo "Or run the full pipeline:"
echo "  python3 scripts/run_pipeline.py"
