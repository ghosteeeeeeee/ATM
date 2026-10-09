# CEO Action Plan — BUG-048: 1m Candle Pipeline (2026-10-09 22:30 UTC)

**Decision: Option A — split the seeder. Aggregator stays dead; do not revert MIN_BARS.**
**Owner of implementation: bug_hunter. NO hermes_constants.py changes.**

## Ordered action items

| # | Action | Owner | Due | Depends on |
|---|--------|-------|-----|------------|
| 1 | Split `price_collector._seed_universe_candles` into (a) fast 1m-only loop: **60 tokens/run**, 1 API call/token (Binance→HL fallback), INSERT OR REPLACE with real volume; (b) existing slow multi-TF loop unchanged (10 tok × 4 TFs, 5m/15m/1h/4h). Keep single cursor per loop (two cursors in the same JSON progress file or separate files). | bug_hunter | Oct 10 | — |
| 2 | Fix `_aggregate_tf` closed-path: INSERT OR REPLACE → **INSERT OR IGNORE**, volume=0 writes stop clobbering seeded candles (4h currently 27.8% vol0, 1h 11.4%). Exclude 1m from `_aggregate_tf` call sites — seeder owns 1m. | bug_hunter | Oct 10 | 1 (same file, ship together) |
| 3 | py_compile + manual run of price_collector.py; verify `Seeded N/60` log line; verify candles_1m on-time(<2min) ≥150/178 within one rotation (~5min) via the staleness SQL in the report. Restart pipeline (AGENTS.md rule: new code needs restart). | bug_hunter | Oct 10 | 1, 2 |
| 4 | 48h soak: journal for lock errors, seed cadence, vol0% on higher TFs. If clean → DELETE `scripts/_aggregate_1m.py` + `hermes-1m-candle.service`/`.timer` + prune `candles_1m WHERE is_closed=0 AND ts < now-3600` (~230,827 rows). | bug_hunter | Oct 12 | 3 |
| 5 | After soak gate passes: begin `plans/align-with-btc-regime.md` (default OFF, LONG-only) — its 7d shadow window needs fresh 1m data to produce meaningful would-block logs. | signal_analyst | Oct 12 | 3 (soak started, not necessarily complete) |

## Explicit non-actions
- **Do NOT** revert `MIN_BARS_FOR_CLOSED` 3→1 (re-arms 5.5M fill-storm + DB-lock race; boundary landmine verified: 91/91 tokens ancient-dev shape, 230,827 stuck rows).
- **Do NOT** touch `scripts/hermes_constants.py` (line 2: DO NOT UPDATE WITHOUT ASKING T). New params (`FAST_1M_TOKENS_PER_RUN=60`) live in `price_collector.py` next to the existing hardcoded `TOKENS_PER_RUN=10`.
- **Do NOT** raise `price_history` tick density (breaks 1-bar=60s signal contract).
- **Do NOT** block on this for wyckoff pairing (Oct 11 deadline, signal_analyst, independent path).

## Success criteria (verify, don't trust)
```sql
-- on-time 1m coverage (target ≥150/178 within 5min of split going live)
SELECT COUNT(*) tokens, SUM(CASE WHEN age<=120 THEN 1 ELSE 0 END) ontime
FROM (SELECT token, strftime('%s','now')-MAX(ts) age FROM candles_1m
      WHERE is_closed=1 GROUP BY token);
```
- `Seeded N/60` appears in price_collector journal; skip-if-fresh starts firing after rotation 2+
- 0 "database is locked" in hermes-price-collector journal over 48h
- 1h/4h vol0% < 2% after one full multi-TF cycle
- Aggregator service deleted only AFTER 48h soak passes
