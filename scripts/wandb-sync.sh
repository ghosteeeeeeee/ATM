#!/bin/bash
# wandb-sync.sh — Sync offline W&B runs to hermes-ai project once you have an API key.
# Usage: WANDB_API_KEY=your_key ./wandb-sync.sh
# Or:   ./wandb-sync.sh your_api_key

KEY="${WANDB_API_KEY:-$1}"
if [ -z "$KEY" ]; then
    echo "Usage: WANDB_API_KEY=... ./wandb-sync.sh"
    echo "  or:  ./wandb-sync.sh your_api_key"
    exit 1
fi

export WANDB_API_KEY="$KEY"
export WANDB_DIR=/root/.hermes/wandb-local
export WANDB_MODE=online

echo "=== Syncing offline W&B runs from $WANDB_DIR ==="
echo "Project: hermes-ai"
echo ""

# Find all offline run directories
RUN_DIRS=$(find "$WANDB_DIR" -mindepth 2 -maxdepth 3 -type d -name "run-*" 2>/dev/null | head -50)
if [ -z "$RUN_DIRS" ]; then
    echo "No offline runs found in $WANDB_DIR"
    echo "Offline runs are stored as JSONL backups at:"
    echo "  /root/.hermes/wandb-local/candle-predictor-*.json"
    echo "  /root/.hermes/wandb-local/ab-tests.jsonl"
    echo "  /root/.hermes/wandb-local/decisions.jsonl"
    exit 0
fi

COUNT=0
for run_dir in $RUN_DIRS; do
    echo "Syncing: $run_dir"
    wandb sync "$run_dir" --project hermes-ai --entity "" && echo "  ✓ synced" || echo "  ✗ failed"
    COUNT=$((COUNT+1))
done

echo ""
echo "Done. Synced $COUNT offline run(s)."
echo ""
echo "=== Local JSONL backups still available at: ==="
ls -lh /root/.hermes/wandb-local/*.jsonl /root/.hermes/wandb-local/candle-predictor-*.json 2>/dev/null
