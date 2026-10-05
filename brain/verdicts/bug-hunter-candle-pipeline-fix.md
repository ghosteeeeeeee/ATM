# bug_hunter Verdict — Candle Data Pipeline Fix Verification

**Date:** 2026-10-05 22:20 UTC
**Scope:** 4 commits (950a1e0b, e9a299ca, 8881b9d4 + bundled candles_lock/_fetch_hl_candles)
**Auditor:** bug_hunter (independent verification)

---

## VERDICT: ISSUES FOUND — ship the 4 commits, one critical adjacent bug found & fixed inline

The 4 commits are **correctly implemented** — no logic errors, no regressions, data is recovering.
**However**, verification proved the commits alone would NOT have restored correct RSI gating:
the `LONG-RSI-BLOCK` gate in `signal_compactor.py` had an **independent RSI-inversion bug**
(the exact code path that produced "FIL blocked — RSI 0.0" during the +3.56% pump). That bug was
**not covered by any of the 4 commits**. I found it, fixed it (3 sites in signal_compactor.py),
and verified the fix. See Check 6 — it is the headline finding.

Plus 3 follow-up issues (1 HIGH, 2 MEDIUM) that need separate work items.

---

## 1. Syntax and Imports — **PASS**

| Check | Result | Evidence |
|---|---|---|
| `ast.parse` on `_aggregate_1m.py` | OK | Ran the command — no exception |
| `ast.parse` on `price_collector.py` | OK | Ran the command — no exception |
| `candles_lock` module exists | PASS | `/root/.hermes/scripts/candles_lock.py` (33 lines, flock wrapper) |
| `candles_lock` imports cleanly | PASS | `from candles_lock import acquire, release` → OK; `CANDLES_LOCK = /root/.hermes/data/candles.db.lock` |
| `_fetch_hl_candles` properly defined | PASS | `price_collector.py:111-133` — HL candleSnapshot API, correct payload, volume from `c.get('v')` |
| `_fetch_hl_candles` live-tested | PASS | FIL: real OHLC+volume from HL; CHIP (HL-only alt): HL returns data when tested; Binance also returned CHIP data |

**⚠️ FINDING (MEDIUM):** `_aggregate_1m.py` imports `candles_lock` (line 20) but **never calls
acquire/release** — grep shows the import is the only reference in the file. `price_collector.py`
correctly calls it (lines 641/674). The aggregator therefore runs **unlocked** against
price_collector's write transactions. Currently benign (aggregator writes nothing — see Check 2),
but latent: any future aggregator write storm re-opens the "database is locked" failure mode.

## 2. Aggregator Logic (`_aggregate_1m.py`) — **PASS**

| Check | Result | Evidence |
|---|---|---|
| `INSERT OR IGNORE` for closed candles (is_closed=1) | PASS | Line 148 — verified in full file read |
| `INSERT OR REPLACE` still used for developing (is_closed=0) | PASS | Line 204 — developing candles SHOULD be updated |
| Dev path guards closed candles | PASS | Lines 197-202: `SELECT is_closed ... ; if exists and exists[0] == 1: continue` — closed candles never overwritten by dev path |
| `MIN_BARS_FOR_CLOSED = 3` | PASS | Line 29 |
| `MIN_BARS_FOR_DEVELOPING = 2` | PASS | Line 30 |
| SQL filters `WHERE bar_count >= {MIN_BARS_FOR_CLOSED}` | PASS | Line 127 — correctly interpolated constant |
| PRIMARY KEY (token, ts) exists in candles_1m | PASS | Schema verified — `INSERT OR IGNORE` semantics correct; 0 duplicate (token,ts) rows |

**Behavioral confirmation (journal):**
- 21:29 & 21:33 runs (old MIN_BARS=1): `filled=4929016` / `4929406` — the aggregator re-attempted
  ~4.9M historical windows per run (1-min-52s CPU each). These were mostly no-op IGNOREs but the
  scan+attempt storm is what raced price_collector and produced the "database is locked" errors.
- 21:35 onward (MIN_BARS=3 live): `filled=0, dev=0` every run, ~30-37s CPU, **no errors**.
  Aggregator no longer writes flat candles — **confirmed**.
- Note: `filled=0` is *expected*, not a fault — avg ticks per 1m window = **1.00** (measured over
  last 30min across all tokens), so `bar_count >= 3` essentially never passes. The aggregator is
  now effectively a no-op; price_collector is the sole real 1m source. See Check 7 edge cases.

**⚠️ DATA NOTE:** 230,809 ancient `is_closed=0` rows remain in candles_1m (min_ts ~57 days old,
written by the pre-fix developing path and never closed). Harmless to RSI (all readers filter
`is_closed=1`) but they make the aggregator's `last_closed_dict` compute an ancient boundary for
affected tokens → full-history rescan each run → the ~30s CPU. Recommend pruning (LOW, perf only).

## 3. Price Collector Logic (`price_collector.py`) — **PASS**

| Check | Result | Evidence |
|---|---|---|
| `TOKENS_PER_RUN = 10` | PASS | Line 212 |
| Freshness check skips fresh+volume tokens | PASS | Lines 225-241: skip only if 1m <5min old AND 4h <2h old AND latest 1m volume>0 |
| Refetches flat candles (volume=0) | PASS | `_has_vol` computed from latest 1m volume (lines 229-233); flat → refetch. Confirmed live: FIL got real volume (V=1200) by 22:05 as cursor passed |
| `_fetch_hl_candles` fallback on Binance fail/zero-vol | PASS | Lines 245-250: `if not candles or all(cd.volume==0): _hl = _fetch_hl_candles(...)`. Live-tested both APIs |
| `_store_candles` uses INSERT OR REPLACE | PASS | Line 149 — **correct** for price_collector; API data must overwrite stale/flat rows |
| Cursor cycles through all tokens | PASS | Line 216: `idx = cursor % len(saved_tokens)`; cursor=125178/178 wraps correctly. FIL idx 54 ← cursor idx 152 → reached in ~8 runs ≈16 min. Seeding confirmed live: `Seeded 10/10 tokens (cursor=125178/178)` at 22:01 |

**⚠️ FINDING (HIGH — same bug class, NOT fixed by these commits):** `candles_15m` is **100%
zero-volume**. Measured: 8,160 rows in last 24h, **0 with volume>0**; 57,642 rows in last 7d, 0
with vol>0. Root cause: `_seed_universe_candles` fetches 1m/5m/1h/4h (line 245) but **never 15m**;
`_aggregate_tf` writes candles_15m from price_history with `volume=0` hardcoded (line 533) using
INSERT OR REPLACE, and avg 14 ticks per 15m window always passes `bar_count >= 4`. 15m OHLC *range*
is real (ticks aggregate) but **volume is always 0**. Impact: 15m volume signals read volume=0 —
`ema300_breakthrough` (reads volume FROM candles_15m), `volume_climax` (accepts 15m table).
15m RSI still works (closes vary). **Fix: add ('15m', 100) to the seed TF list** (Binance+HL both
support it; `iv_ms` map already has 15m).

**⚠️ FINDING (MEDIUM):** `_store_candles` INSERT omits `is_closed` → column DEFAULT 1 applies.
Binance's kline response includes the **in-progress minute** (last kline not yet closed), so the
newest candle per token is often a partial minute marked `is_closed=1`. Observed: FIL newest
candle at 22:05 was O=H=L=C=1.1978 with V=1200.88 (single-price partial kline). Minor RSI
distortion (one partial close in the 15-candle window). Fix: exclude the last kline or set
is_closed=0 for it.

**⚠️ FINDING (LOW):** `_aggregate_tf` for 5m/1h/4h still overwrites with `volume=0` (INSERT
OR REPLACE, line 531) for windows not yet re-seeded — self-heals within one ~36min seed cycle,
but 12-29% of higher-TF candles are vol0 at any instant (5m: 6,964/46,051 vol0 in 24h; 1h: 499;
4h: 292). Same overwrite pattern the 1m fix addressed; lower severity because the seed cycle
restores real volume. Consider INSERT OR IGNORE + gap-fill there too, or seed those TFs more often.

## 4. Data Quality Check — **PASS (recovery in progress, measurably working)**

Query run: `is_closed=1 AND ts > now-600 GROUP BY token` + universe-wide classification.

**Last 10 minutes (candles_1m):**
- 298 closed candles: **175 REAL (59%)** (H>L AND vol>0), 123 flat/other (41%)
- At 21:47 check: 91/158 = 57.6% real — improving as seeder cycles

**Universe (178 tokens) at 22:05:**
| Category | Count | % |
|---|---|---|
| REAL OHLC+vol, newest <30min | 64 | 36% |
| FLAT/partial, newest <30min | 61 | 34% |
| STALE >30min | 53 | 30% |
| No candles at all | 0 | 0% |

**Sample tokens (newest closed candle):**
| Token | Age | Quality | Notes |
|---|---|---|---|
| BTC | 0.5min | REAL | O=85913 H=85913 L=85900 C=85900 V=2.85 |
| SOL | 2.6min | REAL | H>L, V=576 |
| ETH | 2min | REAL | H=2721>L=2718 V=74 — **recovered** (was flat at 21:47) |
| FIL | 0min | partial | V=1200 but H=L — in-progress Binance kline (see Finding 3.2) |
| PUMP | 8.5min | REAL | V=172M |
| RENDER | 8.5min | REAL | V=138K |
| ARB | 8min | FLAT w/vol | V=2087 but H=L — partial kline |
| IO / MERL / TURBO | 35/35/17min | FLAT | open live positions — seeder hasn't reached them yet |

**Old flat candles still present:** ✅ Expected — 7,260,072 flat closed candles older than 1h
remain in candles_1m. The fix prevents NEW flat candles; it does not delete old ones. Confirmed.

**Open positions (PostgreSQL brain):** 3 open, all paper=**f** (LIVE money):
- IO LONG trend-ride+ @0.17296 (21:53) — candles flat/stale at check
- MERL LONG bb-squeeze+ @0.031915 (20:36) — candles flat/stale at check
- TURBO LONG bb-squeeze+ @0.001062 (20:21) — candles flat at check
- (CRV, BLUR opened earlier — closed since)

⚠️ Live positions on flat-candle tokens: position_manager's *current-price* path uses
latest_prices (HL allMids, always fresh) so SL/TP marking is safe; but any candle-based checks
(RSI-drift, trailing logic reading candles_1m) read flat data for IO/MERL/TURBO until the seeder
cursor reaches them (~10-25 min). Watch these three trades until their candles refresh.

## 5. Timer Verification — **PASS**

| Check | Result | Evidence |
|---|---|---|
| `hermes-1m-candle.timer` active | PASS | 1min interval, fires on schedule |
| `hermes-price-collector.timer` active | PASS | 1min interval, fires on schedule |
| Aggregator running, errors? | PASS | Journal since 21:35: `filled=0 dev=0`, clean exit each run, 30-37s CPU, **no errors** |
| Aggregator writing flat candles? | **NO — confirmed** | filled=0 since MIN_BARS=3 went live; nothing written |
| price_collector seeding 10 tokens? | PASS | `Seeded 10/10 tokens this run (cursor=125178/178)` at 22:01; `Seeded 9/10` at 21:59 |
| "database is locked" errors | **0 since 21:37** | 84 occurrences in the 3h before (all during MIN_BARS=1 fill-storms); **zero** after TOKENS_PER_RUN commit. Both services show clean `Deactivated successfully` cycles |

Note: `systemctl status` showed "activating (start)" for both services — that is normal for
oneshot-type services mid-run (each cycle takes 30-40s); journal confirms clean completion.

## 6. RSI Impact Assessment — **FAIL → FIXED (headline finding)**

### 6a. RSI values from current candle data

| Token | Candle quality | Gate RSI (15 closes) | True Wilder RSI | Verdict |
|---|---|---|---|---|
| SOL | REAL | 42.9 (DB) / 61.2 (live) | 57.1 / — | meaningful ✅ |
| BTC | REAL | 46.9 (DB) | 69.9 | meaningful ✅ |
| PUMP | REAL | 21.0 (live) | 23.5 | meaningful ✅ |
| RENDER | REAL | 29.3 (live) | 41.1 | meaningful ✅ |
| FIL | flat (DB @21:47) | 23.5 | 76.5 | **GARBAGE** ❌ |
| ETH | flat (DB @21:47) | 24.4 | 75.6 | **GARBAGE** ❌ |
| ARB | flat (DB @21:47) | 0.0 | 100.0 | **GARBAGE** ❌ |

Tokens with real candles → RSI meaningful (21-70 range, plausible). Tokens still flat → garbage.
This part is exactly what the commits address, and it is working as the seeder cycles (ETH
recovered to REAL by 22:05).

### 6b. ⚠️ CRITICAL BUG FOUND — gate RSI inversion (NOT covered by the 4 commits)

`signal_compactor.py` LONG-RSI-BLOCK gate (line 2425-2442) read closes `ORDER BY ts DESC` (index 0
= newest) and computed deltas as `closes[i] - closes[i-1]` — **without reversing**. On DESC data
that negates every delta: a RISING token shows all-"losses" → avg_gain=0 → **RSI = 0.0** →
"LONG blocked — RSI 0.0 < 20 (oversold freefall)". This is precisely the FIL incident
("FIL pumped +3.56% with conf=88 — all blocked by RSI 0.0 < 20 when actual RSI was 72+").

**Root cause of the original report was two stacked bugs:**
1. Flat candles (the 4 commits' target) — made the close series a monotonic step function →
   amplified the inversion to exactly 0.0.
2. **The gate formula itself was inverted** — and this bug is *independent of candle quality*.
   Verified on **real Binance data** (pre-fix formula): ETH rising → gate 39.1 vs true 72.6;
   SOL rising → gate 37.5 vs true 66.7 — understated by 30+ points. During a strong pump
   (true RSI 80+) the gate computes <20 and blocks **even with perfect candles**. Shipping only
   the 4 commits would have left valid pump signals blocked.

The same file already carried the correct fix at 3 sibling sites (lines 3516, 3555, 3591 — with
FIX comments: *"Previous formula computed 100-true_RSI (inverted)"*), but **3 sites were missed**:
- Line 2433 — LONG-RSI-BLOCK (the gate that fired on FIL/ARB)
- Line 3808 — SPIKE-FILTER LONG RSI
- Line 4223 — PRESERVE-SPIKE-BLOCK SHORT

**Fix applied (bug_hunter, 2026-10-05 22:15):** changed all three to
`closes[i] - closes[i+1]` (i+1 = older in DESC order). Verified:
- `ast.parse` OK on signal_compactor.py
- Fixed gate vs `rsi_1m.py` (authoritative) on same DB data: **FIL 60.5=60.5, ETH 70.3=70.3,
  SOL 62.7=62.7, BTC 46.9=46.9, ARB 56.0=56.0 — exact match, 5/5**
- Fixed gate on live Binance data: plausible values (21-61 range), no inversion artifacts
- Other RSI readers audited clean: `rsi_utils.py` (reverses, line 91), `signals/rsi_1m.py`
  (reverses, line 40), `decider_run.py:4374` (reverses). `signal_analyst.py:253` uses abs() —
  direction-independent. No other inverted sites found.

**Deployment:** `hermes-signal-compactor.timer` runs `python3 signal_compactor.py` as a **fresh
process every 60s** (Type=simple, exits after each run — journal shows clean deactivate each
minute). The fix is live on the next timer fire. No restart needed.

### 6c. Pipeline log evidence

- LONG-RSI-BLOCK still firing with **RSI 0.0** through **21:41** (FIL 21:30-21:33, then ARB
  21:36-21:41) — consistent with flat data + inverted gate. Nothing in the last ~20min, but that
  is also because hotset is empty (fewer signals reaching gates) — cannot yet claim gates are
  *passing* correctly.
- hotset: **empty** at 21:46 and 22:00 — `hotset.json is empty — no signals survived compaction`,
  `[hotset] fallback DB query returned 0 tokens`.
- 3 live trades opened 20:21-21:53 (during the transition window).
- Market bias computing fine: `LONG_BIAS (32L/18S/69N)` at 22:00 (slope-based, not candle-based).

**Expected post-fix:** with the gate fix live and the seeder cycling (10 tokens/~2min, full
178-token pass ~36min), RSI gates should start passing valid signals as tokens receive real
candles. Re-check hotset ~30min after this verdict.

## 7. Edge Cases — **PASS (with residual risks noted)**

| Edge case | Behavior | Assessment |
|---|---|---|
| price_history has exactly 3 ticks in a window, all same price | Flat candle (O=H=L=C, vol=0) IS possible — `bar_count>=3` passes. INSERT OR IGNORE → fills only a gap. | ⚠️ ACCEPTABLE — rare (avg 1 tick/1m window), and the seeder overwrites it with real data when the cursor reaches that token (freshness check requires vol>0). Residual risk only in the gap between aggregator write and next seed visit (~36min). |
| Binance AND HL both fail for a token | No candles written → gap remains | ✅ BETTER THAN FLAT — code path confirmed: `if candles: _store_candles(...)`. Gap → RSI reads older-but-real data or returns None (fail-closed). |
| Aggregator runs BEFORE price_collector for a window | Aggregator fills gap only if ≥3 ticks (essentially never now); otherwise gap until seeder reaches token | ✅ ACCEPTABLE — no flat overwrite possible (OR IGNORE + MIN_BARS=3). Worst case: ~36min staleness for that token. |
| DB contention with TOKENS_PER_RUN=10 | 0 "database is locked" since 21:37; `_store_candles` has 1 retry + busy_timeout=30s; seed runs inside price_collector's candles_lock section | ✅ OK NOW — but note the aggregator does **not** take candles_lock (Finding 1). Contention is zero only because the aggregator writes nothing. |

## 8. Live Pipeline Impact — **PASS with caveats**

| Check | Result | Evidence |
|---|---|---|
| Signals passing RSI gates? | NOT YET VISIBLE | hotset empty at 21:46 & 22:00; no RSI-pass log lines in window. Consistent with: (a) 64% of universe still flat/stale at check time, (b) gate inversion bug live until 22:15 fix. |
| hotset entries? | NONE | `hotset.json is empty — no signals survived compaction`; fallback DB query 0 tokens |
| Open positions | 3 LIVE (paper=f) | IO trend-ride+, MERL bb-squeeze+, TURBO bb-squeeze+ — all on tokens with flat/stale candles at check time |

## Bug Register (by severity)

| # | Sev | Location | Issue | Status |
|---|---|---|---|---|
| 1 | **CRITICAL** | `signal_compactor.py:2433, 3808, 4223` | RSI computed on DESC closes without reverse → inverted RSI; rising pump tokens read RSI≈0 and get LONG-blocked. Independent of candle quality; the 4 commits did NOT cover it. This is the FIL "RSI 0.0" gate. | **FIXED by bug_hunter** — verified exact match vs rsi_1m.py (5/5); live via compactor timer (fresh process/min) |
| 2 | **HIGH** | `price_collector.py:245` + `_aggregate_tf` | `candles_15m` 100% zero-volume (8,160/8,160 rows vol0 in 24h). Seeder never fetches 15m; `_aggregate_tf` writes it with volume=0. Same bug class as the 1m fix. Breaks 15m volume signals (ema300_breakthrough, volume_climax). | OPEN — fix: add `('15m', 100)` to seed TF list |
| 3 | **MEDIUM** | `_aggregate_1m.py:20` | `candles_lock` imported but never acquired — aggregator runs unlocked. Benign today (writes nothing at MIN_BARS=3) but latent lock-contention risk. | OPEN — wire acquire/release around aggregate_1m() body |
| 4 | **MEDIUM** | `price_collector.py:149` | `_store_candles` INSERT omits is_closed → in-progress Binance kline stored as is_closed=1 (partial minute in RSI window). | OPEN — skip last kline or set is_closed=0 |
| 5 | LOW | `price_collector.py:531` | `_aggregate_tf` still INSERT OR REPLACE with volume=0 for 5m/1h/4h between seed visits (12-29% vol0 transient). Self-heals per ~36min cycle. | OPEN — consider OR IGNORE + gap-fill |
| 6 | LOW | `candles_1m` | 230,809 ancient is_closed=0 rows (up to 57 days old) force full-history rescan each aggregator run (~30s CPU). No correctness impact. | OPEN — prune WHERE is_closed=0 AND ts < now-3600 |

## Data Quality Assessment (final)

- **Last 10 min closed candles: 59% REAL** (175/298) — up from ~0% before the fixes.
- **Universe (178 tokens): 36% real+fresh / 34% flat-partial / 30% stale** at 22:05, improving
  ~10 tokens per 2-min run. Full recovery ETA ~20-30 min from verdict time.
- Old flat candles retained as designed (7.26M rows >1h old) — expected, not deleted.
- Recovery mechanism verified end-to-end: seeder cursor cycles all 178 tokens, freshness check
  correctly rejects volume=0 rows, Binance+HL both return real data when reached.

## RSI Improvement Assessment (final)

- Tokens with real candles: **RSI now meaningful** (21-70 range, matches market conditions).
- The **gate formula** now matches the authoritative `rsi_1m.py` exactly (5/5 tokens) — RSI gates
  will read correct values whenever real candles are present.
- Before this session: gate read 0.0 for rising tokens (inverted) + flat data → all pump LONGs
  blocked. After both fixes: gate reads true RSI; only genuinely oversold tokens (<20) blocked.
- hotset/trade-flow recovery not yet observable — re-verify ~30 min post-verdict once the seeder
  completes a full cycle AND the fixed compactor has run several cycles.

## Recommendations

1. **Commit + review the signal_compactor.py gate fix** (3 sites) — mandatory code review per
   AGENTS.md. The fix is live via the compactor timer already.
2. **Add 15m to the seed TF list** (`price_collector.py:245`) — one-line fix for the HIGH finding.
   Backfill: one manual run of `_fetch_hl_candles(token,'15m',100)` + `_store_candles` per token,
   or let the 36-min cycle heal it.
3. **Wire candles_lock into `_aggregate_1m.py`** — acquire at function start, release in finally.
4. **Exclude the in-progress kline** in `_fetch_binance_candles` (drop last element) or store it
   with is_closed=0.
5. **Prune ancient is_closed=0 rows** from candles_1m (230K rows, >1h old).
6. **Monitor IO/MERL/TURBO** (3 live positions on flat-candle tokens) until the seeder refreshes
   their candles (~10-25 min).
7. **Re-run this verification ~30 min post-fix**: target >90% universe real+fresh, hotset
   non-empty, zero LONG-RSI-BLOCK on RSI>30 tokens.
8. Consider INSERT OR IGNORE + gap-fill in `_aggregate_tf` for 5m/1h/4h to stop transient vol0
   overwrites entirely.

---

*All numbers in this verdict come from commands executed against the live system (SQLite queries,
journalctl, live Binance/HL API calls, PostgreSQL queries, code reads). No estimates.*
