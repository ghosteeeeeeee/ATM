#!/bin/bash
# Regime Transition Smoothing — 3-Day Follow-Up Check
# Created: 2026-09-10
# Purpose: Verify all 3 layers were properly implemented and are working

echo "=== REGIME TRANSITION SMOOTHING — IMPLEMENTATION CHECK ==="
echo "Date: $(date -u '+%Y-%m-%d %H:%M UTC')"
echo ""

# Layer 3: Check constants
echo "--- Layer 3: Circuit Breaker Constants ---"
grep -n "DIRECTIONAL_OUTCOME_PENALTY\|DIRECTIONAL_OUTCOME_LOCK_VELOCITY" /root/.hermes/scripts/hermes_constants.py
echo ""

# Layer 2: Check directional bias code
echo "--- Layer 2: Directional Bias Code ---"
grep -c "DIR-BIAS" /root/.hermes/scripts/signal_compactor.py
echo " DIR-BIAS log lines found"
grep -c "dir_bias_mult" /root/.hermes/scripts/signal_compactor.py
echo " dir_bias_mult references found"
echo ""

# Layer 4: Check alt-BTC divergence code
echo "--- Layer 4: Alt-BTC Divergence Code ---"
grep -c "ALT-BTC-DIV" /root/.hermes/scripts/signal_compactor.py
echo " ALT-BTC-DIV log lines found"
grep -c "alt_btc_div_mult" /root/.hermes/scripts/signal_compactor.py
echo " alt_btc_div_mult references found"
echo ""

# Check if the filters are actually firing
echo "--- Filter Activity (last 24h) ---"
grep -c "\[DIR-BIAS\]" /root/.hermes/logs/pipeline.log 2>/dev/null || echo "  No DIR-BIAS entries in pipeline.log"
grep -c "\[ALT-BTC-DIV\]" /root/.hermes/logs/pipeline.log 2>/dev/null || echo "  No ALT-BTC-DIV entries in pipeline.log"
grep -c "\[WEATHER-VANE\]" /root/.hermes/logs/pipeline.log 2>/dev/null || echo "  No WEATHER-VANE entries in pipeline.log"
echo ""

# Check trade performance
echo "--- Recent Trade Performance ---"
python3 -c "
import json
with open('/var/www/hermes/data/trades.json') as f:
    data = json.load(f)
closed = data.get('closed', [])
last20 = closed[:20]
wins = sum(1 for t in last20 if t['pnl_usdt'] > 0)
print(f'Last 20 trades: {wins}W/{20-wins}L = {wins/20*100:.0f}% WR')
longs = [t for t in last20 if t['direction'] == 'LONG']
shorts = [t for t in last20 if t['direction'] == 'SHORT']
lw = sum(1 for t in longs if t['pnl_usdt'] > 0)
sw = sum(1 for t in shorts if t['pnl_usdt'] > 0)
print(f'  LONG: {lw}/{len(longs)} = {lw/len(longs)*100:.0f}% WR' if longs else '  LONG: 0 trades')
print(f'  SHORT: {sw}/{len(shorts)} = {sw/len(shorts)*100:.0f}% WR' if shorts else '  SHORT: 0 trades')
print(f'  Net PnL: \${sum(t[\"pnl_usdt\"] for t in last20):+.2f}')
"
echo ""

echo "=== CHECK COMPLETE ==="
echo "Report this to CEO for review."
