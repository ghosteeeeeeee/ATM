# CEO Report — 2026-10-04 21:15 UTC — BTC Momentum Detection

## DECISION: **Option C** — BTC multi-window flat check (not A, not B, not D)

**Queue for post-freeze Oct 6 00:38. Zero trading-config changes this run.**

### Diagnosis (DB + code + logs verified this run)

| Claim in brief | Verified reality |
|---|---|
| Chop threshold 0.05 | **LIVE is 0.20** (`hermes_constants.py:1052`) — 0.05 was freeze-violation b5006cd8, **reverted 17:49** |
| velocity=0.017 is 5m per-candle | **16×5m regression slope_pct** (% per 5m candle) written by `15m_regime_scanner.py` to SQLite `momentum_cache` |
| BTC +0.67%/3h | **CONFIRMED +0.62%** (candles_5m: 85312→85835). 30m move +0.26% |
| Hotset empty | CONFIRMED — logs 21:04–21:09: ZRO/AVAX/IMX/JUP/WLFI LONG blocked "BTC flat, standalone bypass denied" |
| 24h PnL | **32T −$0.70 56.3% WR** (PG brain, this run) |
| Open positions | **0 in PG trades table** (brief's SEI claim stale) |

### Root cause (not "timeframe too short" alone)

1. **Unit mismatch.** Threshold comment says `|BTC 30m|%`. Stored velocity is **% per 5m candle** from a 16-candle regression. A +0.62%/3h pump yields velocity ≈0.02–0.04 ≪ 0.20 → gate almost always reads "flat" in normal markets.
2. **Continuum override asymmetry.** BTC continuum now: `DECLINING + BULL + ABOVE + score 99.96 + STRONG_UP`. `_cont_bullish` requires phase ∈ {RECOVERY,CALM,NEUTRAL} → **False**. Falls through to velocity → blocked. Bearish side was fixed 2026-09-20 to require structural confirm; **bullish side still phase-label-gated**.
3. **Helper already exists, unused by chop gate.** `signal_compactor.py:898 _get_btc_momentum()` computes BTC 3h % from `candles_1h`. Tide system already uses it (`TIDE_BTC_MOM_RISING=0.1`). Chop gate does not.

### Why not A / B / D

| Option | Verdict | Why |
|---|---|---|
| **A** longer TF velocity | Reject as primary | Changing candle TF does not fix unit mismatch; lag on reversals; more constants to re-tune |
| **B** lower threshold 0.05→0.02 | Reject | Live value is **0.20**, not 0.05. 0.02 on wrong unit still fails velocity=0.017. Freeze already reverted this exact class (VALUE change) |
| **C** BTC 3h price check | **SELECT** | Uses real price data; helper exists; OR with existing velocity keeps true-chop detection |
| **D** accept current | Reject | BTC pumping, alt movers +4–6%, system sitting out violates "every pump is a LONG opportunity". Not chop — detection bug |

### Fix applied (queued, not shipped)

**Post-freeze Oct 6 00:38 — bug_hunter:**

1. Chop gate Layer A + Layer B bypass: BTC not flat if  
   `abs(velocity) >= BTC_CHOP_GATE_THRESHOLD` **OR** `abs(_get_btc_momentum()) >= BTC_CHOP_GATE_3H_PCT`
2. New constant `BTC_CHOP_GATE_3H_PCT = 0.50` (task's 0.5% — matches observed pump scale). **Do not change `BTC_CHOP_GATE_THRESHOLD` value.**
3. Continuum bullish override: accept structural bull (`linreg ∈ {LEAN_BULL,BULL} AND ema300=ABOVE`) regardless of phase label — mirror the 2026-09-20 bearish structural fix.
4. **First:** run delegated hit-rate analysis (0.20 vs unit-corrected) on `_btc_30m` before any threshold discussion.

**Freeze ruling:** gate-behavior change = trading config. b960ffe8 48h exec-RSI monitor stays uncontaminated. 0 config changes this run.

### Verification (post-ship, Oct 6+24h)

| Metric | Current | Target | Deadline |
|---|---|---|---|
| "BTC flat" false blocks when \|BTC 3h\|>0.5% | recurring (ZRO/AVAX/IMX/JUP/WLFI 21:04–21:09) | 0 | Oct 7 |
| Hotset approved tokens | 0 | >0 when pump + bypass signals fire | Oct 7 |
| 24h PnL | −$0.70 | ≥ $0 | Oct 5 recheck |
| Continuum bullish override fire rate on DECLINING+BULL+ABOVE | 0 (phase-gated) | >0 when score≥90 | Oct 7 |
| b960ffe8 oversold SHORTs | 1 (RSI 82, not oversold) | 0 | Oct 6 00:38 |

### Freeze / protected flags

- Freeze b960ffe8 ACTIVE → Oct 6 00:38. **0 trading config changes this run.**
- Protected untouched: `CONFLUENCE_REQUIRED=True`, `LIVE_TRADING_ENABLED=True`, `CEO_PROTECTED_FLAGS`, `BTC_CHOP_GATE_THRESHOLD=0.20` (not re-tuned), `ATR_TP_MIN=0.013`, `CUT_LOSER_PNL=-1.00`.

### Delegations

- **bug_hunter (post-freeze Oct 6 00:38):** implement C per scope above; hit-rate analysis first; assert constants pre/post except new `BTC_CHOP_GATE_3H_PCT`.
- **self_learner:** penalty-floor + b960ffe8 monitors through Oct 6; re-check 24h PnL ≥$0.
- **signal_analyst:** unchanged queue (ema_reclaim, doji exec path, coin_tracker Wyckoff).

### Sideways finds

1. **MED** — Task brief stale: threshold 0.05 vs live 0.20; velocity unit mislabeled. Any operator reading the brief would re-replicate the freeze violation.
2. **MED** — Continuum bullish phase list asymmetric vs bearish structural fix (2026-09-20). DECLINING+BULL+ABOVE+99.96 invisible to override.
3. **LOW** — `_get_btc_momentum()` exists but chop gate ignores it — dead path for the exact question it answers.
4. **LOW** — PG open trades = 0; brief cited SEI open. Position source-of-truth drift between reports and DB.

### DB numbers (this run, PostgreSQL brain)

| Window | Trades | PnL | WR |
|--------|--------|-----|-----|
| 24h | 32 | −$0.70 | 56.3% |
| 7d | 221 | +$0.79 | 52.9% |
| 7d LONG | 166 | +$2.11 | 54.8% |
| 7d SHORT | 55 | −$1.32 | 47.3% |
| 48h losses | hard_max_loss 20T | −$3.26 | dominant exit |

**Standing post-freeze queue unchanged:** bb-bounce-v3 NORMAL regime-block + FAMILY_MAP underscore + RSI fold-in + hotset-empty audit + DRIFT-005 + **NEW: BTC chop-gate Option C**.

## CEO Report — 2026-10-04 21:50 UTC (Sunday)

### Diagnosis
PG-verified: 24h **33T −$0.70 54.5%WR** | 7d **221T +$0.81 52.9%** (LONG +$2.13/166T, SHORT −$1.32/55T 47.3%) | 30d **958T −$0.80 51.8%**. Worst: bb-bounce-v3-long+ 9T −$0.42. Hotset empty — ~2h blocks: SHORT-CONTINUUM 130 / LONG-NEUTRAL 79 / SHORT-NEUTRAL 76. Disk 88% (WAL 8.4G, checkpoint busy under live writers).

### Root Cause
Hotset starvation = BTC chop-gate false "flat" during BTC pump (already diagnosed, Option C queued post-freeze) + correct continuum SHORT blocks while BTC bullish + confluence single-type blocks. bb-bounce-v3 bleeds in NORMAL (50% WR −$0.39/7d), wins in HIGH (80% +$0.11). Disk = candle-writer contention, no busy_timeout (code fix pending). BTC-CRASH LONG blocks at session highs are BY DESIGN (top-30% pullback guard), not a bug.

### Fix Applied
**0 trading config** — freeze b960ffe8 stands until Oct 6 00:38. No constant/gate changes. Protected flags untouched. No candles vacuum mid-trading (standing rule). Post-freeze queue unchanged: bb-bounce-v3 NORMAL 0.0 + HIGH 1.0 + FAMILY_MAP underscore; BTC chop-gate Option C; hotset-empty audit; DRIFT-005. Regime memory already holds bb_bounce_v3 planned block.

### Verification
Numbers from PostgreSQL brain this run (not desk/logs). trades.json healthy: open=2 matches PG (USELESS −0.77%, BABY +0.20%). Pipeline active, timers firing. Next: Oct 6 00:38 unfreeze executes queued regime-block + chop-gate fix; measure 24h PnL ≥$0, SHORT 7d ≥$0 by Oct 7, hotset >0, disk <85%.
