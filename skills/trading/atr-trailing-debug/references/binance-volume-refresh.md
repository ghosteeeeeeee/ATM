---
name: binance-volume-refresh
description: Source live OHLCV candles from Binance for Hyperliquid tokens — replaces zero-volume candles in candles.db. Only ~2-3% of HL-only tokens exist on Binance (e.g. IP=CHIP, HYPE=HYPER). The 171 Binance-sourced tokens are a different set (mostly mainstream coins). Binance klines API caps at 1000 candles per request regardless of limit param (1m→~16.7h, 1h→~41 days). RecentTrades API is the only real-time option with no historical OHLCV. Architecture for binance_candle_refresh.py running every minute.
triggers:
  - volume=0 in candles.db
  - breakout engine not catching pumps
  - Binance token coverage for HL universe
  - stale 1m/5m candles
  - volume ratio signals not working
  - CHIP pump signal analysis
  - can we get X data from Binance for any token
  - cross-exchange symbol mapping HL vs Binance
  - which tokens exist on which exchange
---

# Skill: Binance Volume Refresh for Hermes

## What Changed (2026-04-30)

This skill was updated after empirical investigation. Key corrections:
- `is_closed=0` is correctly tracked for ALL TFs — higher TFs were NOT stale, they were developing candles waiting to close at their natural interval boundary (1h closes in 52min, 4h in 172min)
- `price_history` is actually fresh (~87s old) — the "staleness" was a false alarm
- Volume = 0 because `_aggregate_1m.py` hardcodes `volume=0`, not because prices are stale
- HL `recentTrades` API is burst-limited (~5 req/s) — confirmed via testing, not safe for sustained per-minute fetching

## Confirmed Binance Token List (2026-04-30) — CORRECTED

**CRITICAL DISCOVERY:** The "171 Binance tokens" are NOT the same as "HL-only tokens that need Binance seeding."

- **171 Binance tokens** = mainstream coins that exist on BOTH Binance AND Hyperliquid (APT, ARB, SOL, etc.) — these already have volume from HL and don't need Binance seeding
- **59 HL-only tokens** = tokens that exist ONLY on Hyperliquid (meme coins, HL-native listings) — these are the target for Binance seeding

Of the 59 HL-only tokens, **ONLY 2 have Binance pairs:**
| HL Symbol | Binance Symbol | Notes |
|-----------|----------------|-------|
| `IP` | `CHIPUSDT` | Same token, different symbol |
| `HYPE` | `HYPERUSDT` | Same token, different symbol |

All others (`POPCAT, SPX, ZEREBRO, MEGA, FARTCOIN, GOAT, BRETT, MEW, MNT, kBONK`, etc.) — **NOT on Binance at all.**

**59 HL-only tokens (none on Binance except IP/HYPE):**
```
AERO, AI16Z, APEX, AZTEC, BLAST, BRETT, BSV, CANTO, CC,
CHILLGUY, DOOD, FARTCOIN, FRIEND, GOAT, GRASS, GRIFFAIN, HPOS,
HYPE, IP, JELLY, KAS, LAUNCHCOIN, MAVIA, MEGA, MELANIA, MERL,
MEW, MNT, MON, MOODENG, MYRO, NEIROETH, NFTI, ORBS, OX,
PANDORA, POPCAT, PROMPT, PURR, RLB, SHIA, SKR, SPX, STABLE,
STBL, UNIBOT, VINE, VVV, YZY, ZEREBRO, ZETA, ZORA,
kBONK, kDOGS, kFLOKI, kLUNC, kNEIRO, kPEPE, kSHIB
```

**Binance API limits (empirical):**
- `limit` param maxes at **1000 candles** regardless of what you pass
- 1m → 1000 candles ≈ **16.7 hours** per request
- 1h → 1000 candles ≈ **41 days** per request  
- Pagination via `startTime/endTime` windows still caps at 1000 per call — can't chain to get more
- `recentTrades` API: real-time only, no historical OHLCV

**Practical implication:** For the 57/59 HL-only tokens not on Binance, the only volume source is HL `recentTrades` (rate-limited burst-only) or accept volume=0. The "Binance volume seeding" plan only helps for IP and HYPE among HL-only tokens.

## Implemented Script

`/root/.hermes/scripts/binance_volume_collector.py` — **DONE** (2026-04-30)
- Fetches 1m + 5m klines from Binance for all 171 tokens
- Writes to `/root/.hermes/data/binance_test.db` (separate from production)
- 171 tokens × 2 intervals = 342 requests @ ~7s total with 30 workers
- Rate: 342 weight/min = 28% of Binance 1200 limit — safe
- No HL API calls used — entirely Binance-sourced

## is_closed Logic (Verified Working)

All TFs correctly track developing vs closed candles:

| Table | is_closed=0 means | is_closed=1 means |
|-------|-------------------|-------------------|
| candles_1m | Developing (current minute) | Closed |
| candles_5m | Developing (current 5m) | Closed |
| candles_15m | Developing (current 15m) | Closed |
| candles_1h | Developing (current hour) | Closed |
| candles_4h | Developing (current 4h) | Closed |

The "staleness" false alarm: A 1h candle with `is_closed=0` at ts=01:00 is NOT stale — it's the current developing candle and won't close until 02:00. Same for 4h candles at midnight — they develop all night.

**To check freshness correctly:**
```python
age = now_ts - candle_ts
interval_sec = {'1m': 60, '5m': 300, '15m': 900, '1h': 3600, '4h': 14400}[tf]
if is_closed == 0:
    # developing — age should be < interval_sec
    pass  # fresh if age < interval_sec
else:
    # closed — stale only if age > interval_sec * 3
    pass  # stale if age > interval_sec * 3
```

## HL recentTrades API — Confirmed Rate Limited

**API name:** `recentTrades` (not `get_recent_trades` — HL changed this)

**Rate limit findings (empirical, 2026-04-30):**
- Burst: ~5 requests/second before 429s kick in
- After 429s: sustained rate recovers slowly
- NOT suitable for fetching all 230 tokens every minute

**Decision: Exclude from volume strategy.** Use Binance klines only for volume.

## Phase Status

| Phase | Status | Notes |
|-------|--------|-------|
| 1. binance_volume_collector.py | ✅ DONE | 171 tokens, test DB |
| 2. Higher-TF aggregation | 📋 PENDING | 5m/15m/1h/4h from Binance 1m |
| 3. Systemd timers | 📋 PENDING | Not wired yet |
| 4. Signal pipeline switchover | 📋 PENDING | After Step 2 verification |
| 5. 59 non-Binance tokens | 📋 DECISION | Volume=0 or HL recentTrades for hot-set only |

## Full Spec

See `/root/.hermes/plans/binance-volume-system-spec.md` for complete architecture plan.
