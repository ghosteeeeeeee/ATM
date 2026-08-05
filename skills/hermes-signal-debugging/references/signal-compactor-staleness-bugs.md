# Signal Compactor — Deep Debug Reference

## APPROVED Signal Staleness Bugs (2026-05-12)

### Bug 1: `combo_key IS NOT NULL` Guard

**Location:** `signal_compactor.py` ~line 1030, `run_compaction()` APPROVED expiry query

**Problem:** The expiry query had `AND combo_key IS NOT NULL`. Signals with `combo_key IS NULL` were **never expired** regardless of age.

**Fix applied:**
```python
# REMOVED: AND combo_key IS NOT NULL
c.execute("""
    UPDATE signals SET decision='EXPIRED'
    WHERE decision='APPROVED'
    AND executed=0
    AND (julianday('now') - julianday(created_at)) * 1440 >= 5.0
""")
```

### Bug 2: `hot_cycle_count >= 2` Guard

**Location:** Same query

**Problem:** Signals with `hot_cycle_count=0` or `hot_cycle_count=1` survived **2 extra compaction cycles** before the expiry countdown started.

**Fix:** Removed the `AND hot_cycle_count >= 2` condition entirely. Expiry is purely based on `created_at` age.

### Combined Effect

An APEX SHORT signal with `combo_key IS NULL` and `hot_cycle_count=0` would NEVER be expired by the compactor. It would survive every compaction cycle, re-enter top-10 when it fired again, get re-approved, and never leave APPROVED state.

---

## `_filter_safe_prev_hotset` — Missing Open-Position Check

**Location:** `signal_compactor.py` `_filter_safe_prev_hotset()` ~line 1289

**Problem:** When preserving previous hot-set entries (merge from prev_hotset), there was **no open-position check**. A token that guardian just traded (open position in PostgreSQL) could have its stale hot-set entry preserved and re-enter the hot-set.

**Fix applied:**
```python
# Skip tokens with open positions — don't preserve entries for tokens already traded
live_open = _get_open_tokens()
if tok.lower() in live_open:
    continue
```

Also applies to the main Step 11 filter loop at line ~907 (already had the check). The bug was specifically in the preserve/merge path.

---

## pump_hunter Bypass (Myth — Not the ASTER Cause)

**Investigation:** ASTER SHORT traded at 04:26. Query: `SELECT id, token, direction, signal, status FROM trades WHERE token='ASTER'`

**Result:** Signal was `hhh-short6,ma-death33` — legitimate Hermes signal, NOT pump_hunter.

**pump_hunter was ruled out:** pump_hunter writes `signal='pump_hunter'` to brain DB. ASTER's signal field does not contain pump_hunter. pump_hunter has never fired a trade to date.

**What actually happened:** The signal was a real hh_hl signal that went through the normal pipeline. It may have been in hot-set briefly then expired correctly, but by 04:26 the compactor had approved a fresh signal that decider_run executed.

---

## hot-set Empty After Adding trend_purity Requirement

**Context:** After making `trend_purity+` required for LONG and `trend_purity-` required for SHORT (2026-05-12), many single-source signals were blocked. The hot-set went empty.

**Resolution:** Replaced hard trend_purity requirement with:
- **hh_hl required** for ALL entries (hard filter)
- **trend_purity bonus**: +50% score multiplier when present (not hard block)

This means:
- `accel-300+` alone (no hh_hl) → blocked (needs hh_hl)
- `hhh-long5,ma-death33` → enters hot-set, no bonus
- `hhh-long5,ma-death33,trend_purity+` → enters hot-set with 1.5x score boost

---

## BERA in Hot-Set With Open Position

**Symptom:** BERA had a closed LONG trade (id=9330, opened 05:54, closed 05:59). A BERA SHORT entry appeared in hot-set after the trade was already closed.

**Root cause:** The compactor queries PostgreSQL for open positions at line 83: `WHERE status='open' AND server='Hermes'`. BERA's trade was `status='closed'` — so `_get_open_tokens()` correctly returned no BERA in open_tokens.

**BUT:** BERA SHORT was in prev_hotset and survived the merge because it had a higher score than the DB entry. The open-position check was missing in `_filter_safe_prev_hotset` (fixed above).

**Note:** BERA's hot-set entry was `combo_key: null` (broken field). The merging logic may not have worked correctly for that reason too.

---

## Key Files and Line References

| File | Section | Purpose |
|------|---------|---------|
| `signal_compactor.py:76` | `_get_open_tokens()` | Queries PostgreSQL for open positions |
| `signal_compactor.py:838` | `open_tokens = _get_open_tokens()` | Called before Step 11 filter |
| `signal_compactor.py:907` | `if tkn.lower() in open_tokens` | Open-position filter in main loop |
| `signal_compactor.py:1030` | APPROVED expiry query | Fixed two expiry bugs |
| `signal_compactor.py:1289` | `_filter_safe_prev_hotset()` | Fixed missing open-position check |
| `signal_compactor.py:644` | hh_hl required filter | Main scoring loop |
| `signal_compactor.py:701` | `tp_bonus_mult` ranking | Trend purity bonus applied at ranking |

---

## Diagnostic Commands

```bash
# Check for stuck APPROVED signals (age > 5 min = broken expiry)
cd /root/.hermes/scripts && python3 << 'EOF'
import sqlite3, time
conn = sqlite3.connect('data/signals_hermes_runtime.db')
c = conn.cursor()
c.execute("""
    SELECT token, direction, decision, created_at,
           (julianday('now') - julianday(created_at)) * 1440 AS age_min
    FROM signals WHERE decision='APPROVED' ORDER BY age_min DESC LIMIT 10
""")
for row in c.fetchall():
    print(f"{row[0]} {row[1]} age={row[4]:.1f}min created={row[3]}")
conn.close()
EOF

# Check PostgreSQL for open positions
psql -h /var/run/postgresql -U postgres -d brain -t -c \
  "SELECT token, LOWER(token), status FROM trades WHERE status='open' AND server='Hermes'"

# Check hot-set contents
cat /var/www/hermes/data/hotset.json | python3 -c "
import json, sys, time
d = json.load(sys.stdin)
print(f'hotset: {len(d[\"hotset\"])} entries, age={(time.time()-d[\"timestamp\"])/60:.1f}m')
for e in d['hotset']:
    print(e.get('token'), e.get('direction'), 'src=', e.get('source'))
"

# Check pipeline log for compactor runs
tail -200 /root/.hermes/logs/pipeline.log | strings | grep -iE "APPROVED|EXPIRED|compactor|HOTSET-FILTER" | tail -20
```