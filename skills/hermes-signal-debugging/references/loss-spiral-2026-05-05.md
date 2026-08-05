# Loss Spiral Analysis — 2026-05-05

## Symptoms
- 0 green days across 30+ trades
- All losing trades = SHORTs with `pct-hermes-`
- All winning trades = LONGs with `pct-hermes+`
- Win rate: 0% for pct-hermes- SHORT, ~95%+ for pct-hermes+ LONG

## Root Causes (Confirmed)

### 1. `pct-hermes-` Structurally Broken in Bear Markets

`pct_short` = % of 200-bar history where price >= current.
- `pct_short = 92-100` → price is at/near its ALL-TIME LOW
- `pct_short = 8-20` → price is at/near its ALL-TIME HIGH

The system fires SHORT when `pct_short >= 72` (price at bottom). In a bear market, price at the bottom keeps falling. System is shorting the bottom.

```
pct_short >= 72  →  pct-hermes- SHORT  →  price at bottom  →  price keeps falling  →  LOSS
```

**Evidence from live trades** (all losing):
- ETC SHORT: pct_short=87.5 (near bottom)
- STRK SHORT: pct_short=99-100 (at absolute bottom)
- ETH SHORT: pct_short=92.5 (near bottom)
- DASH SHORT: pct_short=99.0 (at absolute bottom)
- LINK SHORT: pct_short=92.5 (near bottom)

### 2. Blacklist Entry for `pct-hermes-` Is Commented Out

`hermes_constants.py` line 128-129:
```python
# 2026-04-20: BLOCK pct-hermes- directional variant — solo source, no independent confirmation
# 'pct-hermes-',   ← COMMENTED OUT
```

To fix: uncomment `'pct-hermes-'` in `SIGNAL_SOURCE_BLACKLIST`.

### 3. Confluence Gate Uses Raw Comma Count, Not Unique Signal Types

`signal_compactor.py` line 419:
```python
if CONFLUENCE_REQUIRED and len(source_parts) < 4 and source != 'breakout':
```

`source_parts = [p.strip() for p in source.split(',') if p.strip()]` = raw comma-split.

`source = 'hzscore+,pct-hermes-,rs-r85,rs-r94,rs-r175,rs-r227'` → 6 parts → passes 4+ gate.
But `_signal_type_key()` normalizes `rs-r####` → `rs-r`, giving only 3 unique types.

**Fake confluence**: Multiple RS levels at different prices each contribute a comma-split part but are the same signal type.

### 4. Regime Filter = 1.0 Multiplier for 96% of Coins

`regime_15m.json` shows 102/106 coins = NEUTRAL.
`_score_signal()` applies `reg_mult = 1.0` for NEUTRAL → no penalty.
Counter-regime SHORT would get `×0.70` but almost everything is NEUTRAL.

### 5. Opposing Signal Penalty Never Fires

`_get_opposing_penalty()` queries `decision IN ('PENDING', 'APPROVED')`.
Most signals are `EXECUTED` or `EXPIRED` → penalty almost always returns 1.0.

## Fixes Required (Priority Order)

1. **Block `pct-hermes-` in blacklist** — uncomment in `hermes_constants.py:129`
2. **Fix confluence gate to use unique types** — `signal_compactor.py:419` use `unique_signal_types` not `len(source_parts)`
3. **Add regime as hard block** — if `LONG_BIAS + SHORT` at conf > 60, hard-block (not just ×0.70)
4. **Fix opposing penalty to check hot-set state** — not just PENDING/APPROVED DB rows

## Diagnostic Queries

```sql
-- Check recent trade outcomes by source
SELECT token, direction, source, signal_type, 
       COUNT(*) as n,
       AVG(pnl_pct) as avg_pnl,
       SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END)::float / COUNT(*) as wr
FROM trades 
WHERE status = 'closed' AND close_time > NOW() - INTERVAL '7 days'
GROUP BY token, direction, source, signal_type
ORDER BY n DESC LIMIT 20;

-- Count by direction and signal type
SELECT direction, 
       CASE WHEN source LIKE '%pct-hermes-%' THEN 'pct-hermes' ELSE 'other' END as sig,
       COUNT(*) as n, AVG(pnl_pct) as avg_pnl
FROM trades
WHERE status = 'closed' AND close_time > NOW() - INTERVAL '7 days'
GROUP BY direction, sig ORDER BY n DESC;
```

## Hot-Set at Time of Analysis (2026-05-05 04:40 UTC)

```
ETC   SHORT: hzscore+,pct-hermes-,rs-r180,rs-r268    ← LOSER
XLM   SHORT: pct-hermes-,rs-r1181,rs-r1248,rs-r4134  ← LOSER
ME    LONG:  pct-hermes+,rs-s1910,rs-s1936,rs-s2812  ← WINNER
LINK  SHORT: hzscore+,pct-hermes-,rs-r615,rs-r625    ← LOSER
CHIP  SHORT: pct-hermes-,rs-r205,rs-r409,rs-r415    ← LOSER
UNI   SHORT: hzscore+,pct-hermes-,rs-r1240,rs-r1264  ← LOSER
STRK  SHORT: pct-hermes-,rs-r1206,rs-r1212,rs-r1215  ← LOSER
SNX   SHORT: hzscore+,rs-r3146,rs-r3237,rs-r3253    ← mixed
ONDO  SHORT: pct-hermes-,rs-r189,rs-r89,rs-r99      ← LOSER
NIL   LONG:  pct-hermes+,rs-s364,rs-s384,rs-s710    ← WINNER
```

Pattern: Every `pct-hermes-` SHORT = near historical bottom = losing. Every `pct-hermes+` LONG = near top = winning.

## Regime Data at Time of Analysis

```
Non-NEUTRAL coins (4/106):
  ALGO:   LONG_BIAS  conf=63.2
  HYPER:  SHORT_BIAS conf=53.2
  MEME:   LONG_BIAS  conf=60.6
  MINA:   LONG_BIAS  conf=62.8

Losing coins regime:
  ETC:    NEUTRAL  conf=61.3  ← regime filter dormant
  STRK:   ? (not in file)
  ETH:    NEUTRAL  conf=62.0  ← regime filter dormant
  DASH:   NEUTRAL  conf=60.7  ← regime filter dormant
  LINK:   NEUTRAL  conf=59.3  ← regime filter dormant
```
