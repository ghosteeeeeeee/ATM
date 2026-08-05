# Hermes Signal Debugging — Key Commands

## Hot-set state
cat /var/www/hermes/data/hotset.json | python3 -m json.tool

## Runtime DB signals
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "SELECT token,signal_type,source,decision,executed FROM signals WHERE decision='APPROVED' AND executed=0 ORDER BY created_at DESC LIMIT 20;"

## Pipeline log
tail -100 /var/www/hermes/logs/pipeline.log

## Trading log (signal_compactor logs here)
tail -100 /var/www/hermes/logs/trading.log

## Regime check (Python)
cd /root/.hermes/scripts && python3 -c "
import sys; sys.path.insert(0, '.')
from signal_compactor import get_regime_1m
tokens = ['ZEN','STRK','GALA','SNX','APEX','ATOM','DASH','ETHFI','ASTER']
for t in tokens:
    r, c = get_regime_1m(t)
    print(f'{t}: regime={r} conf={c}')
"

## Open trades (PostgreSQL brain DB)
psql -h localhost -U postgres -d brain -c "SELECT trade_id, token, direction, entry_price, open_time, status, pnl_pct FROM trades WHERE status='open';"

## Signal count per type
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "SELECT signal_type, COUNT(*) FROM signals GROUP BY signal_type;"

## Compactor mtime (check if patches deployed)
stat /root/.hermes/scripts/signal_compactor.py | grep Modify

## Decider_run hot-set gate location
grep -n 'in_hotset\|HOT-SET\|bypass' /root/.hermes/scripts/decider_run.py | head -20

## Regime function location
grep -n 'get_regime_1m\|LONG_BIAS\|SHORT_BIAS' /root/.hermes/scripts/signal_compactor.py | head -10

## Confluence gate location
grep -n 'unique_signal_types\|confluence\|GOOD_STANDALONE' /root/.hermes/scripts/signal_compactor.py | head -15

## DB path
ls -la /root/.hermes/data/signals_hermes_runtime.db