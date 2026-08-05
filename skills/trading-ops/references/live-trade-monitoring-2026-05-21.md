# Live Trade Monitoring — 2026-05-20 Session Notes

## What to Watch During Live Trading

### Key Logs and Commands

```bash
# Guardian orphan status (every 15s when running)
tail -f /root/.hermes/logs/sync-guardian.log

# Pipeline activity (ATR updates, position manager, closes)
tail -f /root/.hermes/logs/pipeline.log

# Check all open positions with current prices and PnL
cd /root/.hermes/scripts && python3 << 'EOF'
from _secrets import BRAIN_DB_DICT
import psycopg2
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("""
    SELECT id, token, direction, status, entry_price, stop_loss, target,
           current_price, pnl_pct, pnl_usdt,
           open_time, close_time, close_reason,
           hl_notional_usdt, hype_realized_pnl
    FROM trades WHERE status='open' ORDER BY open_time DESC
""")
print(f"{'id':>6} {'token':<8} {'dir':<6} {'entry':>8} {'SL':>8} {'TP':>8} "
      f"{'cur':>8} {'pnl%':>7} {'pnl$':>7} {'opened':<26}")
for r in cur.fetchall():
    print(f"{r[0]:>6} {r[1]:<8} {r[2]:<6} {r[3]:>8.4f} {r[4]:>8.4f} {r[5]:>8.4f} "
          f"{r[6]:>8.4f} {r[7]:>7.3f} {r[8]:>7.4f} {str(r[10])[:26]}")
EOF
```

## DOT Trade Incident — Monitoring Gap

**2026-05-20 22:06: DOT SHORT opened (trade #10226) and closed in 3 seconds.**

What we learned:
1. `brain.py` prints `→ ENTERED: DOT SHORT (trade #N)` when DB INSERT succeeds
2. Guardian log shows `HL: N positions | DB: N open trades` every 60s
3. Position Manager logs `5 open | 1 closed | 0 adjusted` when it closes a trade
4. `atr_sl_hit` reason in close_reason field is NOT always a real SL hit — can be phantom close

### Critical Log Entries for a Trade

```
22:06:08  [brain.py] ✔ no duplicate open in PostgreSQL for DOT
22:06:08  [brain.py] → mirror_open(DOT, SHORT, entry_price=1.2511, leverage=5)
22:06:08  [brain.py] ← mirror_open returned: success=False, message=...
22:06:08  [brain.py] → ENTERED: DOT SHORT (trade #10226)    ← DB INSERT happened despite mirror fail
22:06:20  [HYPE Mirror] CLOSED SHORT DOT (HL exit $1.246900 pnl=-0.0033)
22:06:20  [Position Manager] HYPE mirror_close SUCCESS: DOT  ← guardian closed it
22:06:20  Position Manager: 5 open | 1 closed | 0 adjusted    ← PM closed it again
```

The `[brain.py] ← mirror_open returned: success=False` line is the smoking gun — it appeared in logs but was not noticed until after the incident.

### Monitoring Alert Checklist

When T reports "position closed immediately":
1. Check `[brain.py] ← mirror_open returned: success=` — if False, mirror_open failed
2. Check `HL: N positions | DB: N open trades` — if HL < DB, orphan exists
3. Check `atr_sl_hit` close_reason — examine actual price vs SL to determine if it was real
4. Check `mirror_open result: {"success": false, "message": "..."}` in brain.py output