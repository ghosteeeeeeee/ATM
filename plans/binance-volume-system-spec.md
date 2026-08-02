# Binance Volume System — Full Spec

**Date:** 2026-04-30
**Status:** DRAFT — awaiting decision

---

## Problem Statement

The Hermes breakout/compression engine requires real volume data to function:
- `vol_ratio >= 3.0x` in breakout detection — currently non-functional with `volume=0`
- Compression detection checks `volume < VOL_COMP_THRESHOLD_ABS` — works but lacks real volume ground-truth

**Root cause:** `price_history` (written by `price_collector.py` from HL `allMids`) only contains mid-prices, no volume. The HL `recentTrades` API has a burst rate limit (~5 req/s) that would exhaust quickly across 230 tokens, making it unsuitable as a sustained volume source.

**Solution:** Source OHLCV from Binance for the 171 tokens that exist on both HL and Binance.

---

## Facts Established

### Data Freshness (Verified 2026-04-30)
| Table | CHIP max_ts | Age | Status |
|-------|-------------|-----|--------|
| `candles_1m` | 01:20:00 | 46s | Fresh, developing tracked correctly |
| `candles_5m` | 01:15:00 | 5m | Fresh, closed properly |
| `candles_15m` | 01:00:00 | 8m | Fresh, developing tracked correctly |
| `candles_1h` | 01:00:00 | 52m to close | Fresh, developing |
| `candles_4h` | 00:00:00 | 4h to close | Fresh, developing |

**The "staleness" was a false alarm** — all candles are current. The `is_closed=0` flag correctly marks developing candles. Higher TFs haven't closed because they haven't reached their interval boundary.

### Token Split (Verified 2026-04-30)
- **171 tokens** exist on both Hyperliquid + Binance → can source OHLCV from Binance
- **59 tokens** are HL-only → cannot source volume from Binance (meme coins, HL-only listings)

### HL recentTrades API — Rate Limited
- Burst: ~5 requests/second before 429s kick in
- 230 tokens × 1 req = 46 seconds to fetch all — **too slow for 1-minute cadence**
- **Decision: Exclude from this plan. Use Binance for volume.**

### Binance Rate Limits
- Limit: **1200 weight/minute**
- Each `klines(limit=2)` = **1 weight**
- 171 tokens × 2 intervals (1m + 5m) = **342 requests/min = 342 weight/min = 28% of limit**
- Safe for concurrent execution at ~7s total fetch time

---

## Architecture

### Two-DB Strategy

```
/root/.hermes/data/
  candles.db              ← PRODUCTION: HL price + hardcoded volume=0 (existing)
  binance_test.db         ← TEST: Binance OHLCV only (new, Step 1 done)
  candles.db will eventually be deprecated / replaced
```

**Rationale:** Don't mix data sources in the same DB until the Binance pipeline is proven. The test DB is write-only during testing — nothing reads from it yet.

**Future decision:** Whether to consolidate into one DB or keep them separate once the Binance pipeline is production-ready.

---

## Component 1: binance_volume_collector.py ✅ DONE

**Location:** `/root/.hermes/scripts/binance_volume_collector.py`

**What it does:**
- Fetches 1m + 5m klines from Binance for 171 tokens every run
- Writes to `/root/.hermes/data/binance_test.db`
- `limit=2` returns last closed + current developing candle
- Concurrent fetch at 30 workers, ~7s total runtime

**Schema:**
```sql
candles_1m  (token, ts, open, high, low, close, volume, is_closed)
candles_5m  (token, ts, open, high, low, close, volume, is_closed)
```

**is_closed logic:** `now_ts - ts > interval_sec` → 1 (closed), else 0 (developing)

**Verified:** 171/171 tokens fetched, 0 errors, 7.3s on first run.

**Timer:** None wired yet — run manually during testing.
`# TODO: systemd timer once proven`

---

## Component 2: Higher-TF Aggregation (TODO)

**Problem:** Binance gives 1m + 5m. We also need 15m, 1h, 4h.

**Option A — Aggregate from Binance 1m:**
```
Binance 1m → aggregate 5m → aggregate 15m → aggregate 1h → aggregate 4h
```
Advantage: Single source of truth (Binance).
Disadvantage: Missing 59 non-Binance tokens entirely.

**Option B — Two-tier source:**
```
171 Binance tokens: Binance 1m → aggregate 5m/15m/1h/4h
59 HL-only tokens:  HL price_history 1m (volume=0) → aggregate 5m/15m/1h/4h
```
Advantage: All tokens covered.
Disadvantage: Two data sources, volume=0 for 59 tokens forever.

**Option C — Hybrid (recommended):**
```
1m:  Binance for 171 tokens (real OHLCV)
     price_history 1m for 59 tokens (volume=0)
5m:  Binance for 171 tokens (already fetched)
     aggregate from 1m for 59 tokens
15m/1h/4h: aggregate from 1m for ALL tokens
```
Advantage: Most liquid tokens have real volume everywhere.
Disadvantage: 59 tokens still have volume=0 for higher TFs.

**Decision needed from T:** Which option?

---

## Revised Architecture — Option D: Single candles.db (Recommended)

**Core insight:** Don't create a parallel DB. Wire Binance data into `candles.db` directly, replacing the volume=0 entries.

```
For 171 tokens that exist on both HL + Binance:
  binance_test.db candles_1m → _aggregate_1m → candles_1m (with REAL volume)
                              → _aggregate_5m → candles_5m (with REAL volume)
                              → aggregate_15m/1h/4h → (with REAL volume)

For 59 HL-only tokens:
  price_history (HL price only) → _aggregate_1m → candles_1m (volume=0, unchanged)
                               → _aggregate_5m → candles_5m (volume=0, unchanged)
                               → aggregate_15m/1h/4h → (volume=0, unchanged)
```

**What changes:**
- `_aggregate_1m.py` gets modified: for each token, check if binance_test.db has a newer 1m candle. If so, use it (price + volume). If not, fall back to price_history.
- `binance_volume_collector.py` writes to `binance_test.db` (staging) until verified, then writes directly to `candles.db`
- All downstream aggregators: **NO CHANGES** — they read `candles.db candles_1m/5m` which now has real volume
- All signal scripts reading `candles.db`: get real volume automatically, no path changes needed

**Why this is better than Option A/B/C:**
- No new DB to maintain long-term
- No parallel timer infrastructure
- Signal pipeline reads one DB, always has had volume for 171 tokens
- Higher-TF aggregation chain works unchanged
- binance_test.db becomes a staging/verification layer only, can be deprecated after flip

**Risk mitigation:** Keep `binance_test.db` during verification phase. Once candles from `binance_test.db` match Binance live chart for 2+ hours across multiple tokens, flip `_aggregate_1m.py` to write directly to `candles.db`. `binance_test.db` can then be deleted or kept as a backup source.

**Open questions:**
1. Skip staging — write Binance 1m directly to `candles.db` immediately?
2. 59 HL-only tokens: accept volume=0, or wire `recentTrades` for hot-set only (~5-10 tokens)?

---

## Component 4: Dynamic Token List Management

**Problem:** HL adds/removes coins over time. The 171/59 split is a snapshot — it will drift.

**What needs to stay in sync:**
- `binance_volume_collector.py` — which tokens to fetch from Binance
- The 59 HL-only token list in this spec
- Any signal script that branches on Binance-vs-HL-only

**How to keep it updated:**
- Run a token sync job every 12h via systemd timer
- The job hits HL `/meta` endpoint (or `price_history` token list) + Binance `/exchangeInfo`, computes the intersection diff
- If new token added to HL AND exists on Binance → add to Binance fetch list
- If new token added to HL but NOT on Binance → add to HL-only list, flag for review
- If a token is delisted from HL → remove from both lists
- Log the diff so it's auditable

**Design:**
```python
# /root/.hermes/scripts/sync_token_lists.py
- Fetch HL token list from price_history or /meta
- Fetch Binance /exchangeInfo (symbol list)
- Compute: hl_only, binance_only, both
- Update: binance_tokens.txt (171 list), hl_only_tokens.txt (59 list)
- Log diff since last run
- Alert if >5% change in either list
```

**Timer:** `hermes-token-sync.timer` — run every 12h, log to pipeline.log

**Risk:** If we never sync, the Binance fetcher gradually misses new listings and keeps fetching for tokens that no longer exist. Under normal conditions HL adds 1-3 coins/month. A 24h drift is acceptable. 12h is conservative.

**Who calls the sync job:**
- On first deployment: full sync generates both token lists from scratch
- Ongoing: timer fires every 12h, reads from HL `/meta` + Binance `/exchangeInfo`, computes diff
- Manual trigger: `hermes-token-sync --force` for immediate resync

---

## Component 5: recentTrades for HL-Only Tokens (Hot-Set Only)

**Problem:** 59 tokens don't exist on Binance — no volume source via the standard pipeline.

**What we know:**
- HL `recentTrades` API is rate-limited: ~5 req/s burst before 429s
- Fetching 59 tokens × 1 req each = ~12 seconds of burst, which risks hitting the limit
- Not viable as a continuous every-minute fetch across all 59

**What we don't need:**
- Continuous volume tracking for all 59 at 1m resolution
- Most of them are low-liquidity meme coins where volume signals aren't actionable

**When we actually need volume for a HL-only token:**
- Only when it's in the **hot-set** — actively being considered for a trade
- At entry: want volume confirmation before sizing in
- During position: optional, for signal confluence

**Approach: On-Demand recentTrades for Hot-Set HL-Only Tokens**

```python
# In guardian or position_manager, before placing an order for a HL-only token:
if token in hl_only_tokens AND token in hotset:
    trades = hl_client.recentTrades(token, limit=20)
    # Compute real volume from trades
    # Use for vol_ratio check in signal pipeline
```

**Key constraints:**
- Only fetch when a HL-only token enters the hot-set (not every minute for all 59)
- Cache the result for that hot-set window (refresh every 5m if position is open)
- Use `limit=20` to minimize weight — 20 recent trades is enough for a volume snapshot
- HL rate limit: 5 req/s burst ≈ 300 reqs before 429. Even 10 tokens × 12 refreshes/hour = 120 reqs — well within burst budget if spaced

**Integration point:** The signal pipeline already checks `vol_ratio` in `breakout_engine.py`. For HL-only tokens, the volume check would fire from cached recentTrades data rather than `candles.db`.

**Fallback if rate-limited:** `volume=0` — same as current behavior. No signal blocking, just no volume confirmation.

**Summary:**
- 171 Binance tokens: continuous 1m volume from `binance_volume_collector.py`
- 59 HL-only tokens in hot-set: on-demand `recentTrades` at entry + every 5m during position
- 59 HL-only tokens not in hot-set: volume=0 (no change from today)

---

## Open Questions (Updated)


---

## Component 3: Timer System (TODO)

| Timer | Interval | Script | Source | Target DB |
|-------|----------|--------|--------|-----------|
| `hermes-1m-candle.timer` | 1 min | existing `_aggregate_1m.py` | price_history (HL) | candles.db |
| `hermes-binance-1m.timer` | 1 min | `binance_volume_collector.py` | Binance | binance_test.db |
| `hermes-5m-candle.timer` | 5 min | `aggregate_5m.py` | binance_test.db candles_1m | binance_test.db candles_5m |
| `hermes-15m-candle.timer` | 15 min | `aggregate_15m.py` | binance_test.db candles_1m | binance_test.db candles_15m |
| `hermes-1h-candle.timer` | 1 hour | `aggregate_1h.py` | binance_test.db candles_1m | binance_test.db candles_1h |
| `hermes-4h-candle.timer` | 4 hours | `aggregate_4h.py` | binance_test.db candles_1m | binance_test.db candles_4h |

**Note:** The existing 1m aggregation timer (`hermes-1m-candle.timer`) continues unchanged — it reads from `price_history` and writes to `candles.db`. The Binance pipeline is completely separate during the test phase.

**Timer decisions needed:**
1. Should the Binance-timer replace the existing HL 1m timer, or run alongside it?
2. When do we flip the signal pipeline to read from `binance_test.db` instead of `candles.db`?

---

## Component 4: The 59 Non-Binance Tokens

Tokens not on Binance: `AERO, AI16Z, APEX, AZTEC, BLAST, BRETT, BSV, CANTO, CC, CHILLGUY, DOOD, FARTCOIN, FRIEND, GOAT, GRASS, GRIFFAIN, HPOS, HYPE, IP, JELLY, KAS, LAUNCHCOIN, MAVIA, MEGA, MELANIA, MERL, MEW, MNT, MON, MOODENG, MYRO, NEIROETH, NFTI, ORBS, OX, PANDORA, POPCAT, PROMPT, PURR, RLB, SHIA, SKR, SPX, STABLE, STBL, UNIBOT, VINE, VVV, YZY, ZEREBRO, ZETA, ZORA, kBONK, kDOGS, kFLOKI, kLUNC, kNEIRO, kPEPE, kSHIB`

**Volume for these tokens:**
- HL `recentTrades` is rate-limited (~5 req/s burst) — can't fetch for all 59 every minute
- **Practical limit:** Could fetch for hot-set tokens only (~5-10 tokens) every minute
- **Fallback:** Volume = 0 for these tokens in the Binance system

**Decision needed from T:** Is volume for these 59 tokens important enough to also figure out HL `recentTrades` for hot-set tokens? Or do we accept volume=0 for them and focus on the 171?

---

## Component 5: Integration with Signal Pipeline (TODO — Future)

The breakout engine reads from `candles.db`. When we switch to `binance_test.db`:

**Changes needed:**
1. `breakout_engine.py` — update DB path constant
2. `signal_compactor.py` — update candle read path
3. Any script reading `candles.db` for volume data

**Signal sources that need volume:**
- `breakout_engine.py` — `vol_ratio >= 3.0x` check
- `volume_filter.py` — volume threshold checks
- `volume_hl_signals.py` — HL volume signals
- Potentially others

**Verification step:** Need to audit all signal scripts that touch volume before switching.

---

## Open Questions / Decisions Required

1. **Option A/B/C for higher-TF aggregation?** (Single Binance source vs. two-tier)
2. **Replace `candles.db` entirely, or keep both DBs permanently?**
3. **Timer: replace existing HL timers or run Binance pipeline in parallel?**
4. **59 non-Binance tokens: try HL recentTrades for hot-set only, or accept volume=0?**
5. **When to flip signal pipeline to read from Binance DB?** (After verification only)

---

## Step 2 Plan: Build Higher-TF Aggregation

```
/root/.hermes/scripts/aggregate_from_binance.py
  - Reads: binance_test.db candles_1m
  - Writes: binance_test.db candles_5m, candles_15m, candles_1h, candles_4h
  - Closes candles whose interval has passed
  - Marks developing candles correctly
  - Handles: Option C (two-tier) or Option B (single-source)
```

**Timer candidates:**
- `aggregate_5m.timer` — every 5 min on 5-min boundary
- `aggregate_15m.timer` — every 15 min on 15-min boundary  
- `aggregate_1h.timer` — every hour on hour boundary
- `aggregate_4h.timer` — every 4h on 4h boundary

**Step 3: Verification** — compare Binance-seeded candles against Binance live chart for CHIP over 2-hour window.

---

## What Was NOT Built Yet

- [ ] `aggregate_from_binance.py` (5m/15m/1h/4h aggregation)
- [ ] Systemd timers for all intervals
- [ ] HL recentTrades fallback for 59 non-Binance tokens
- [ ] Signal pipeline switchover
- [ ] Audited list of scripts that need DB path updates
