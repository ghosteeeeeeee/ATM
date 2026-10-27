#!/bin/bash
# Trial Monitor — quick status check for all active trials
# Usage: bash scripts/trial_monitor.sh

echo "=========================================="
echo "TRIAL MONITOR — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "=========================================="

echo ""
echo "1. WIDER SL TRIAL (CEO Q1)"
echo "------------------------------------------"
sqlite3 /root/.hermes/brain/shadow_trades.db \
  "SELECT 'Data rows: ' || count(*) FROM shadow_trades WHERE exit_wider_sl_json IS NOT NULL" 2>/dev/null
python3 /root/.hermes/scripts/shadow_trader.py --report-wider 2>/dev/null | grep -E "Win Rate|Total PnL|THRESHOLD" | head -5

echo ""
echo "2. EXTENDED TIME TRIAL (CEO Q3)"
echo "------------------------------------------"
sqlite3 /root/.hermes/brain/shadow_trades.db \
  "SELECT 'Data rows: ' || count(*) FROM shadow_trades WHERE exit_extended_time_json IS NOT NULL" 2>/dev/null
python3 /root/.hermes/scripts/shadow_trader.py --report-time 2>/dev/null | grep -E "Win Rate|Total PnL|THRESHOLD|Collecting" | head -5

echo ""
echo "3. CONTRARIAN-LIVE STATUS"
echo "------------------------------------------"
grep -c "CONTRARIAN-LIVE" /root/.hermes/logs/decider*.log 2>/dev/null | tail -3
echo "Real trades: $(grep 'CONTRARIAN-LIVE' /root/.hermes/logs/decider*.log 2>/dev/null | grep -v 'TOK\|smoke\|test' | wc -l)"

echo ""
echo "4. SHADOW DISPOSITION (upcoming deadlines)"
echo "------------------------------------------"
cat /root/.hermes/automation/ceo/shadow_disposition_report.md 2>/dev/null | grep "OPEN" | head -10

echo ""
echo "5. CONFLUENCE-EXPIRY GATE"
echo "------------------------------------------"
sqlite3 /root/.hermes/brain/shadow_trades.db \
  "SELECT 'Blocked: ' || count(*) || ' @ ' || round(100.0*sum(case when first_exit_pnl_pct>0 then 1 else 0 end)/count(*),1) || '% WR' FROM shadow_trades WHERE gate_blocked=1 AND gate_name='CONFLUENCE-EXPIRY'" 2>/dev/null

echo ""
echo "=========================================="
echo "DASHBOARD: brain/trial_tracking_dashboard.md"
echo "=========================================="
