# XRP Executed But Not In Hot-Set — Session Log 2026-05-18

## What Happened

T reported: "XRP was just executed as a live trade (it was not in the hot-set), these were ignored from the hot-set, what's going on???"

The reported hot-set coins were: IP, GRIFFAIN, TIA, COMP, TRB — all SHORT, all with 2 sources (rs + zscore-pump-).

## Investigation Steps Run

1. **Pipeline journal** — authoritative source for execution decisions:
   ```
   journalctl -u hermes-pipeline.service --since "2026-05-18 18:00" --no-pager
   ```
   Showed: ALL decider_run cycles from 18:05 to 18:34 logged `"0 entered"`.
   No pipeline execution for any token during the window.

2. **Confluence gate blocks for XRP** (trading.log):
   - 17:59 — XRP SHORT rs-r156 → BLOCK (single-source)
   - 18:00 — XRP SHORT rs-r156 → BLOCK
   - 18:01 — XRP SHORT rs-r156 → BLOCK
   - 18:02 — XRP SHORT rs-r156 → BLOCK
   - 18:10 — XRP SHORT rs-r84 → BLOCK (single-source)
   - 18:11 — XRP SHORT rs-r84,zscore-pump- → PASS ✅ → HOTSET-WRITE
   - 18:12 — XRP SHORT zscore-pump- alone → BLOCK (single-source)
   - 18:15 — XRP SHORT zscore-pump- alone → BLOCK

   XRP entered hot-set at 18:11 with rs-r84,zscore-pump-. Confluence requirement met at exactly 18:11.

3. **Token list in hot-set at 18:07** (journal):
   `['GRIFFAIN(r1)', 'TIA(r1)', 'COMP(r1)', 'TRB(r1)']`
   XRP was NOT in the hot-set at 18:07 (it passed confluence at 18:11).

4. **Open positions at time of investigation**: 0/5. Positions had been closing throughout the session (5/5 → 4/5 → 3/5 → 2/5 → 0/5).

5. **Execution paths enumerated**:
   - Pipeline: decider_run confirmed 0 entered for entire window
   - pump_hunter.py: direct PostgreSQL write, but only trades tokens it's tracking
   - cascade_flip: CASCADE_FLIP_ENABLED=False (disabled since 2026-04-22)
   - Manual execution: outside Hermes pipeline entirely

## Conclusion

The investigation found NO evidence of XRP being executed through the Hermes pipeline during the reported window. The pipeline journal — the authoritative log — showed 0 entries for every cycle. XRP was confluence-blocked for most of the window and entered the hot-set only at 18:11.

If XRP was executed as a live trade, it was either:
1. Manual execution on Hyperliquid directly (outside Hermes)
2. A pre-existing position from before the confluence gate was fully enforced
3. Dashboard showing a stale/incorrect state

## Key Commands Used

```bash
# Pipeline journal — primary source
journalctl -u hermes-pipeline.service --since "2026-05-18 18:00" --no-pager | grep -iE "🔥|execute|enter|xrp|open:"

# Hot-set contents snapshot
cat /var/www/hermes/data/hotset.json | python3 -c "
import json,sys; d=json.load(sys.stdin)
for e in d['hotset']: print(e['token'], e['direction'], e.get('confidence'))
"

# Confluence gate trace for a token
grep "XRP" /var/www/hermes/logs/trading.log | grep -iE "CONFLUENCE|HOTSET-WRITE|BLOCK"
```