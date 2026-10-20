# Bug Hunter Verification: shadow_trader.py

**Verifier:** bug_hunter subagent
**Date:** 2026-10-20 21:05 UTC
**Script:** `scripts/shadow_trader.py` (839 lines)
**Spec:** `plans/shadow-mode-paper-trading-spec-v1.md` (v1.3)
**Method:** Full code read, live-constant cross-check (`hermes_constants.py`, `position_manager.py`, `profit_monster.py`, `cut_loser.py`, `volatility_gate_v2.py`), end-to-end execution (`--record` / `--close` / `--report`), DB forensics on `brain/shadow_trades.db` (3,000 closed rows at verification time), PostgreSQL leverage check, systemd unit inspection.

## Summary

The infrastructure works end-to-end (record → close → report, timer live, zero runtime errors), but 3 HIGH-severity defects silently distort exactly the A/B data the system exists to produce: leverage is ALWAYS 5 (spec §4.3 CRITICAL violation), the `--reclose` pass is a no-op so slow engines get permanently truncated results, and the tie-break is alphabetical instead of spec precedence (96% of same-candle ties pick the wrong engine).

## Verdict: FAIL

FAIL because the two CRITICAL spec mandates (§4.0 tie-break, §4.3 leverage sourcing) and the CRITICAL §6.4 reclose requirement are unimplemented, and the A/B numbers currently being collected will need to be re-derived (or at minimum re-attributed) after the fixes. The bones are right — fix the 3 HIGHs and this becomes PASS WITH NOTES.

## Findings

### HIGH — Leverage is ALWAYS 5; per-token registry silently never used
- **Location**: `shadow_trader.py:239-251` (`_get_leverage`)
- **Issue**: Calls `get_trade_params(token)` with one argument. The real signature is `get_trade_params(direction, price, max_leverage=5, token='', ...)` (`position_manager.py:2302`) — it raises `TypeError: missing 1 required positional argument: 'price'` on every call. The bare `except Exception` swallows it and falls back to `min(signals.leverage or 5, 5)`. Verified: `_get_leverage('BTC', None) = 5`; `leverage_used = 5` for **all 7,684 rows**. Note the spec's suggested API is itself wrong — `get_trade_params` is an SL/TP computer whose leverage is `min(max_leverage, MAX_LEVERAGE)`, always ≤5; it is NOT a per-token registry.
- **Impact**: Spec §4.3 explicitly forbids cap-at-5. Live PG trades last 14d: **lev 5×192, lev 3×125, lev 10×9, lev 40×1** — 39% of live trades run at lev 3 (live HML = −1.33% price) while shadow simulates −0.80%. Consequences: `hard_max` over-fires on lev-3 trades, under-fires on lev-10 trades; `speed_stale_loser` (threshold −1.0%) can **never** fire in shadow because HML at −0.80% preempts it on the way down — a live-viable engine is invisible in the A/B; `cut_loser` T1/T2 are preempted far more than live.
- **Fix**: Source leverage from the real history — e.g., most-recent/mode `leverage` per token from PostgreSQL `trades` (last 30d), falling back to `min(signals.leverage or 5, 5)`. Also fix the spec's §4.3 code snippet. Remove the bare `except` or log when the fallback fires.

### HIGH — `--reclose` is a silent no-op; slow engines permanently truncated on partial data
- **Location**: `shadow_trader.py:15,63,634-660,815-835`
- **Issue**: `--reclose` appears in docstring, `--help`, and the argparse args, but `main()` never calls any reclose function (`args.reclose` only affects the `run_all` computation). Verified: `python3 scripts/shadow_trader.py --reclose` → exit 0, zero output, does nothing. Meanwhile `close_events()` marks rows `closed=1` **permanently** using whatever candles exist at T+4.5h. Demonstrated on real pending row id=7535 (TRX, created 16:07:39): only 297 min of candles exist at close time → `_simulate_universal_hold` returns `exit_type='truncated'` → row closes forever, 8h universal and 24h ride_it can never fire, and a `'hold'` verdict may actually have been `universal_max_hold` given full data.
- **Impact**: Spec §6.4 flags this as CRITICAL: A/B permanently biased toward fast engines. The 13-day backfill masks it (historical rows have full 24h candles — that's where the 28 universal_hold first-exits and 2,784 universal fires came from). Once the ~4,700-row backlog drains (~3-4h at 1,000/run), **every new signal** will be closed on truncated data. Data collected between now and the fix is degraded for slow engines.
- **Fix**: Implement the §6.4 reclose pass: re-open rows where `first_exit_reason='no_exit'`/`exit_type='truncated'`/hold < max horizon once candles cover `entry_ts + max_hold`, re-simulate, update. Wire it into `main()` and into the service (`--record --close --reclose --report`), or run close only when `now > created_at + 24h` for ride_it rows.

### HIGH — Tie-break is alphabetical engine name, not spec §4.0 precedence
- **Location**: `shadow_trader.py:687-690`
- **Issue**: `fired.sort(key=lambda x: (x[1].get('exit_ts', 0), x[0]))` — the secondary key is the engine dict key string. The comment above it (lines 683-684) states the correct spec precedence but the code never implements it. Alphabetical order puts `atr` before `hard_max`/`cut_loser`, which contradicts loss-side precedence (HML → CL Hard → CL T2 → CL T1 → ATR SL → …). The profit/loss-side split is also unimplemented (ATR TP vs ATR SL are the same `'atr'` key).
- **Impact**: Measured on the 3,000 closed rows: **350 same-candle multi-fire tie events, 337 (96%) attributed to the wrong engine** — typically `atr` winning over `hard_max`/`cut_loser` at the same timestamp. `first_exit_engine`, `first_exit_pnl_pct`, `net_pnl_pct`, and every downstream A/B and gate-justification statistic are mis-attributed on those rows.
- **Fix**: Explicit precedence rank: loss-side `hard_max(0) → cut_loser(1) → atr_sl(2) → speed_stale_loser(3) → trail_arm_timeout(4) → universal_hold(5)`; profit-side `atr_tp(0) → pm_trail(1) → speed_stale_winner(2)`; tie between a loss and profit engine at the same ts → loss-side first (it hit first intra-candle). Rank via `exit_type` inside each engine JSON. Re-attribute existing rows from the stored `exit_*_json` (all data needed is already persisted).

### MEDIUM — Trail Arm Timeout applied to bb-squeeze SHORTs; live is LONG-only
- **Location**: `shadow_trader.py:609-614`
- **Issue**: Live (`position_manager.py:3599+`) wraps the whole trail-arm-timeout block in `if direction == 'LONG'` — bb-squeeze SHORTs never get the 60m timeout. The shadow checks direction only for pump-chain, so bb-squeeze SHORTs are simulated with a timeout that cannot exist live. The `BB_SQUEEZE_/PUMP_CHAIN_TRAIL_ARM_TIMEOUT_ENABLED` kill switches are also ignored (both are `True` today, so no live divergence right now, but the shadow won't notice if they're flipped off).
- **Impact**: `trail_arm_timeout` engine (96 first-exits so far) includes phantom fires on SHORTs; stats stratified by engine will not match live behavior.
- **Fix**: Require `direction == 'LONG'` for both families; read the two ENABLED flags from `hermes_constants` at sim time.

### MEDIUM — Spider PM-Trail override keyed on the wrong regime
- **Location**: `shadow_trader.py:419-424`
- **Issue**: Live spider override fires when `get_spider_active()` — 5m aggregate regime file says `NEUTRAL` (`profit_monster.py:59-70,491-502`) — not on volatility. The shadow triggers on `vol_regime == 'FLAT'` (ATR < 0.48%, a volatility tier from `classify_volatility`). Two different concepts: market-trend NEUTRAL vs low-volatility FLAT.
- **Impact**: The 0.30% activation / tighter tiers are applied to the wrong signal set (144 rows so far). PM Trail exit distributions for those rows don't match live.
- **Fix**: Read `/var/www/hermes/data/regime_5m.json` aggregate `overall == 'NEUTRAL'` (batch-cached per run) for the spider override; keep vol_regime only as stored context.

### MEDIUM — ATR engine uses 1h ATR; spec Appendix B mandates 15m-primary
- **Location**: `shadow_trader.py:210-219,345-346`
- **Issue**: `atr_pct` comes from `volatility_gate_v2.get_atr_pct()` which reads `candles_1h` (verified in source). Spec Appendix B: "ATR(14) 15m-primary via `tpsl_utils.get_fresh_atr` (not volatility_gate 1h)". The 1h value then feeds `_simulate_atr_sl_tp` SL/TP distances. Additionally the SL/TP multipliers are hardcoded (`atr*1.0`, `atr*2.0`) instead of `get_sl_multiplier_v2`/`get_tp_multiplier_v2` (k varies 1.0–1.5 by vol tier live), and the documented EXTREME ×1.2 widening is not applied even though `vol_regime` is available. Spec Appendix D tolerates "simplified ATR", but the timeframe swap is a spec violation, not a listed divergence.
- **Impact**: ATR SL/TP prices (engine with the largest n, 2,905 fires) are systematically off vs live for the same signal.
- **Fix**: Use `tpsl_utils.get_fresh_atr` (15m) for the engine; keep the 1h value only for `vol_regime` context. At minimum record which ATR was used in `exit_atr_json`.

### MEDIUM — Gate-name backfill: spec §6.5 fix (gate_shadow parser) not implemented
- **Location**: `shadow_trader.py:296-307`
- **Issue**: Simple `re.search(r'\[([A-Z-]+)\]', reason)` on `decision_reason`. Spec Appendix C/§6.5 documents that `decision_reason` is `compaction_stale_10min` for ~98.9% of blocks and execution-gate names live only in `pipeline.log`; the mandated fix is `gate_shadow.py`'s log parser. Everything except CONFLUENCE-EXPIRY will be `UNKNOWN`.
- **Impact**: Gate justification — one of the system's two headline deliverables — will only ever answer the confluence-expiry question. Confirmed in current output: single gate row, everything else will land in UNKNOWN as non-expiry rows close.
- **Fix**: Import/reuse `gate_shadow`'s parser and join `pipeline.log` lines by token+timestamp within the backfill window; set `gate_name_backfilled=1` when parsed (column currently never set).

### MEDIUM — MFE/MAE mislabeled; forward-return columns never populated
- **Location**: `shadow_trader.py:703-704,714-715`; schema lines 117-128
- **Issue**: `mfe_pct`/`mae_pct` are computed as max/min of the 7 **engine PnLs** — that is "best/worst engine outcome", not max favorable/adverse **price excursion**. Verified in data: JUP SHORT row has `mfe_pct=0.0, mae_pct=-12.64` — clearly engine-PnL values. `fwd_30m`, `fwd_1h`, `fwd_4h`, `excess_30m/1h/4h`, `mfe_4h`, `mae_4h`, `trade_id` are populated in **0 of 7,684 rows** (spec §3.1 requires them; §7.3 validation needs `trade_id`).
- **Impact**: Anyone querying `mfe_pct` for MFE/MAE analysis (the obvious next question after "which engine wins") gets wrong numbers silently.
- **Fix**: Compute real MFE/MAE from candle highs/lows vs entry during the hold window (per-engine or once at first-exit horizon). Either populate `fwd_*`/`excess_*` from the already-loaded candles or drop them from the schema so they can't mislead. Populate `trade_id` for EXECUTED decisions.

### LOW — `first_exit_pnl_pct` stores gross; spec says after fees; win checks inconsistent
- **Location**: `shadow_trader.py:692-693,758,772`
- **Issue**: Spec §3.1: `first_exit_pnl_pct` = "after fees+slippage". Code stores gross there and net in `net_pnl_pct`. Report win-rates use gross (`first_exit_pnl_pct > 0`) while avg/total use net.
- **Impact**: Minor, but "would_win" percentages are fee-free (e.g., a +0.10% gross exit is a −0.04% net loss yet counted as a win).
- **Fix**: Either follow the spec (store net) or document the deviation; make the report use one basis consistently.

### LOW — Record watermark advances past failed inserts
- **Location**: `shadow_trader.py:322-330`
- **Issue**: A per-signal exception is logged and skipped, but the watermark is still set to `rows[-1][0]` — that signal is never retried (permanent silent loss from the "record ALL signals" guarantee).
- **Impact**: Rare (0 errors in current run), but transient DB errors drop signals forever.
- **Fix**: Track the last **successfully inserted** id (or first failure) as the watermark.

### LOW — Purge not wired into the service; backfill context drift
- **Location**: `shadow_trader.py:801-812`; `/etc/systemd/system/hermes-shadow-trader.service`
- **Issue**: `--purge` exists but the service runs `--record --close --report` only, so 90-day retention never executes. Also `vol_regime`/`atr_pct` are computed at **record time**: for the 13-day backfill they reflect today's ATR, not the signal-time regime (spec Phase 2 assumed ≤30min drift). These backfill `atr_pct` values also feed the ATR engine's SL distance.
- **Impact**: Slow unbounded growth (tolerable at ~600 rows/day); backfill regime/ATR-stratified analysis is invalid for the historical rows.
- **Fix**: Add `--purge` (weekly) to the service. Tag backfill rows (`recorded_at - created_at > 1h`) and exclude them from regime/ATR-stratified reports.

### LOW — Performance: N+1 per-signal connections, no per-token caching
- **Location**: `shadow_trader.py:164-219,276-291`
- **Issue**: Per signal: one fresh `signals` DB connection (`_get_signal_context`), one fresh `candles.db` connection + full ATR recompute (`_get_vol_regime` → `get_atr_pct`), plus `get_trade_params`/`_match_exit_config` imports. 280 pending BTC signals → 280 identical 1h-ATR computations. Spec §6.6 explicitly requires "cache per (token, floor_ts) within a batch". `close()` also re-opens `candles.db` per signal (1,000/run). No leaks (all closed in `finally` — verified), but the first backfill run was needlessly slow and the timer run re-does work.
- **Fix**: Batch-fetch signals in one query keyed by id; cache ATR/vol_regime per token per run; reuse one candles connection per `close()` invocation.

## Verified Working

- Compiles clean (`py_compile` OK); all imports present and used.
- `--record`: +5 new signals, watermark advanced correctly (`last_id=1682625 → 1682630`); `INSERT OR IGNORE` dedup works.
- `--close`: 1,000 pending → 964 closed; no-candle rows correctly marked `closed=1, first_exit_reason='unclosed_no_candles'` with NULL pnl (excluded from stats — spec §6.1 ✓).
- `--report`: all three sections render; SQL correct; totals sane.
- All 7 engines implemented and structurally faithful to spec §4.1–4.8 (ATR continuous peak-trailing with tighten-only + floors ✓, PM Trail tiered + min-hold + bypass list ✓, HML `CUT_LOSER_PNL/leverage` ✓, Cut Loser two-tier full closes with correct −1.0/−2.5/−3.0 ranges ✓, Speed Stale 8min/−1.0% + 120min/+0.6% with `stall_gate_note` ✓, Universal 480/1440 ride_it substrings ✓, Trail Arm 60/45).
- Constants match spec Appendix B numerically — shadow stores percents and divides by 100 where live stores fractions (0.0120 etc.); verified equivalent for `TRAILING_DISTANCE_PCT`, `PM_TRAIL_TIERS` (both tier tables), floors/caps. All values re-derived from `hermes_constants.py` directly.
- Fees/slippage: 0.04% + 0.10% subtracted from gross on every exit path including `hold` — matches spec §12.
- Exit-config routing uses the **real** `_match_exit_config` (proof: `rr_engine` appears for 2,271 rows — the internal fallback can't produce `rr_engine`); versioned signals (`pump-chain-v6-`) route correctly.
- Universal Max Hold ride_it substring set matches spec §4.7 exactly.
- No SQL injection: every query parameterized with `?` (full-file read).
- No connection leaks: every `sqlite3.connect` closed in `finally` (full-file read); WAL + `busy_timeout=5000` on shadow DB; no stray `-wal`/`-shm` at rest.
- `candles_1m` windowed reads are efficient (composite PK + `(token, ts DESC)` index).
- Systemd: timer enabled, `OnBootSec=5min` + `OnUnitActiveSec=30min`, service `Type=oneshot` with `WorkingDirectory=/root/.hermes`, logs to `logs/shadow_trader.log`, last run exit 0, **0 error lines** in log. Next trigger confirmed (21:22 UTC).
- Timestamps: `created_at` format in signals DB is `%Y-%m-%d %H:%M:%S` — matches `strptime` and string-cutoff comparisons in `close()`/`purge()` (no format bug).

## First-Run Results Assessment

**Numbers are plausible; two of the headline figures are structurally guaranteed, and one unit label is wrong.**

- **7679 signals recorded** ✓ — matches signals table (13-day retention, ~590/day). Not 850/day because only EXPIRED/SKIPPED-era rows exist.
- **CONFLUENCE-EXPIRY 1000 blocked, 51% would-win** ✓ plausible — now 3,000 closed at 48%. Caveats: win counted on **gross** pnl, and entry-at-signal-open convention makes all shadow pnl optimistic (spec Appendix D — relative comparisons only).
- **PM Trail 331T → 878T, 100% WR, +$130.57** — **100% WR is structural, not skill.** Verified: minimum net pnl across all pm_trail first-exits = **+0.0617%** (activation +0.40%, tier-0 trail 0.20% → floor exit +0.20% gross − 0.14% costs). PM Trail by construction never holds a loser; comparing its WR to ATR's 41% is meaningless. Also "+$130.57" is **not dollars** — the report prints SUM(net_pnl_pct), i.e. percentage points (+237.91 pct-pts at the time of the quoted run).
- **Hard Max Loss 211T, 0% WR, −$197.77** — 0% WR structural (exits at exactly −0.80%). Again percent-points, not dollars. Magnitude is inflated by the always-lev-5 bug (real lev-3 trades should exit at −1.33%).
- **ATR 396T, 40.4% WR, +$3.65** ✓ plausible (now 41.6% at n=1,207).
- **Red flags confirmed**: (1) all-lev-5 leverage distortion; (2) 96% tie-break mis-attribution inflating `atr` first-exit counts and stealing attribution from `hard_max`/`cut_loser`; (3) `speed_stale_loser` is a permanently dead engine in shadow at lev 5 (HML −0.80% preempts the −1.0% threshold on every loss path) — speed_stale's 833 fires are all winner-variant or unattributed; (4) slow-engine truncation will begin silently once the backfill backlog drains in ~3-4h.

## Recommendations

1. **Fix the 3 HIGHs before the next full report is consumed** — leverage sourcing (from PG `trades` per-token history), real reclose pass, spec-precedence tie-break. All three corrupt the A/B data this system exists to produce. Existing rows are re-derivable: engine JSONs persist `exit_ts`/`exit_type`, so re-attribution and HML re-sim are batch-fixable without re-collecting candles.
2. **After the fixes, re-run a one-off re-simulation** over closed rows (recompute HML with per-token leverage + re-attribute first-exit) so the 13-day backfill isn't thrown away.
3. **Annotate the report** to prevent misreading: print totals as "pct-pts", and add a footnote that PM Trail WR ≥ ~99% is guaranteed by construction (report min/max exit pnl per engine instead of WR for trail-family engines).
4. Fix the MEDIUMs (trail-arm LONG-only + kill switches, spider regime key, 15m ATR, gate_shadow parser, MFE/MAE + fwd columns) in the same pass — they're all small, isolated changes.
5. Spec corrections needed too: §4.3's `get_trade_params(token)['leverage']` snippet does not exist as described (it's an SL/TP computer capped at 5); the spec should name the real leverage source once chosen.
6. Sideways finding (**not shadow_trader's fault, needs a separate ticket**): live signals are still firing today for **KPEPE, KLUNC, KSHIB, KNEIRO** — tokens whose `candles_1m` collection stopped ~2026-10-12 (59 shadow rows already closed `unclosed_no_candles`). If these tokens are delisted from the price collector, live trading on them is blind (no ATR, no SL/TP). Recommend blacklisting or confirming collector coverage.
7. Add `--purge` to the service and a `--reclose` cadence; consider `Persistent=true` on the timer for reboot coverage (minor at 30-min cadence).
