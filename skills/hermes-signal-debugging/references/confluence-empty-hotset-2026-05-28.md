# Confluence Gate Empty Hotset — 2026-05-28

## What happened
Signal compactor found signals in DB but hotset.json stayed empty every cycle.
`[signal-compactor] Compaction done in 0.04s — 0 tokens in hotset`

## Root cause: confluence gate
Signal compactor requires ≥2 unique signal types per token+direction (CONFLUENCE_REQUIRED rule).
Single-source signals stay PENDING → expire after 5 min.
No co-signals means nothing ever enters hot-set.

## Examples of blocked signals
```
VINE SHORT  mtp-zscore-       → 1 type → BLOCKED
MON SHORT   mtp-zscore-       → 1 type → BLOCKED
BCH SHORT   mtp-zscore-       → 1 type → BLOCKED
AXS LONG    rs-s1041          → 1 type → BLOCKED
APEX SHORT  rs-r2840          → 1 type → BLOCKED
ALT SHORT   rs-r1306, rs-r873 → still 1 type (rs only) → BLOCKED
GRASS LONG  rs-s1061          → 1 type → BLOCKED
VINE SHORT  mtp-zscore- (02:05:05) → 1 type → BLOCKED
```

## Why rs stacking doesn't help
Multiple `rs-sXXX` entries for same token collapse to 1 unique type ("rs").
The unique_signal_types count is per signal TYPE, not per source tag.
So `rs-s72,rs-s52` for same token = 1 type → fails confluence.

## Why mtp-zscore+ fires alone
mtp_zscore.py: ALL 3/3 periods agree → fire immediately without waiting for co-signal.
No mechanism to hold the signal pending until a second source arrives.

## Relevant logs
- Decider: `Approved signals: 0` / `No signals above 50% confidence`
- Pipeline: `[hotset] fallback DB query returned 0 tokens`
- Compactor: `0 hotset entries | cycle=42095 | approved=0 | rejected=0`

## DB query to reproduce
```sql
SELECT token, direction, source, confidence, created_at
FROM signals
WHERE created_at > '2026-05-28 01:30:00'
ORDER BY created_at DESC;
```

## Files involved
- signal_compactor.py: confluence gate at line ~568 — `unique_signal_types >= 2` required
- mtp_zscore.py: fires solo, no pending/wait mechanism
- rs.py: fires solo, no pending/wait mechanism

## Fix needed (not implemented)
Either:
1. Reduce CONFLUENCE_REQUIRED to 1 for mtp_zscore (it has 3/3 already = self-confluence)
2. Add a wait mechanism in signal_compactor so single-source signals can find co-signals within 5 min
3. Make mtp_zscore detect if a co-signal (rs/something) exists for same token before firing, else hold as PENDING