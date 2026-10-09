# Error Alerts — 2026-10-07 09:48 UTC (health_monitor)

## Error Alerts — 2026-10-08 10:47 UTC (health_monitor)
- **WARN** (recurring): Disk 85% used (/dev/vda2 95G/118G). Gzip of *.log >7d found nothing (rotations already .gz). DBs: coin_tracker ~3.3G, candles ~2.6G, mtf_macd_tuner ~1.6G, session_brain ~1.1G. No safe auto-fix — CEO/bug_hunter DB prune decision still open.
- **WARN** (informational): 136 signals in last hour, but 0 compaction decisions / 0 executions / hotset empty ("no signals survived compaction"). Filters are rejecting candidates — verify compaction thresholds, not a pipeline crash. 1 closed today (+$0.94, 1 win), 0 open, 0 phantom trades.
- **INFO**: Pipeline healthy — LIVE run 10:46:34 rc=0, position_manager rc=0, no Tracebacks. Timers 3/3 active (price-collector, 1m-candle, pipeline). Prices fresh (~1.5min, candles_1m). Regime 5m SHORT_BIAS (8L/30S/88N of 126). Speeds 128/241 ≥50th pct (avg 48.5). tokens.last_update in candles.db ~45d stale but candles_1m fresh — metadata table not updated by collector, not a price staleness issue.
- **INFO**: Side findings unchanged — `signals_hermes_runtime.db` unbounded; `prices.db`/`signals.db` 0-byte stubs still present.

## Error Alerts — 2026-10-08 00:50 UTC (health_monitor)
- **CRITICAL→FIXED** (recurring ~every 4min): `hermes-trade-watchdog.service` crash — `NameError: name 'watchdog_mode' is not defined` in `scripts/trade_watchdog.py` (`analyze_profit_lock`, `analyze_stale_trades`, `write_outputs`). Service failed; deep-analysis wrapper never ran.
  - **AUTO-FIX**: Root cause — those helpers referenced `watchdog_mode` without fetching it. Added `watchdog_mode = get_watchdog_mode()[0]` at top of `analyze_profit_lock` and `analyze_stale_trades`; `write_outputs` now sets `auto_executed` from the steer flag. Verified: compile OK, `--dry-run` completes (5 steers), service restarts into opencode analysis phase. Python analysis path no longer NameErrors.
- **WARN** (recurring): Disk 85% used (95G/118G). Journal vacuum freed 181M (269M→~88M). No uncompressed *.log >7d. Active DBs still large: coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.6G, session_brain 1.1G.
  - **AUTO-FIX**: `journalctl --vacuum-size=80M` (freed 181M). DB prune still CEO/bug_hunter decision.
- **INFO**: Pipeline healthy — LIVE run 00:46:51 rc=0, 86 signals/hr, 1 open (CRV LONG +9% in profit), 0 closed today. Timers 3/3 active (price-collector, 1m-candle, pipeline). Prices fresh (~2min). Regime 5m LONG_BIAS (47L/15S/60N). 0 phantom trades. 0 pipeline Tracebacks. token_speeds 128/241 ≥50th pct (avg 48.6).
- **INFO**: Side findings unchanged — `signals_hermes_runtime.db` unbounded; failed non-critical units (better-coder, bug-hunter, git-release, brain-auditor) still disabled/commit-blocked; `prices.db`/`signals.db` 0-byte stubs still present.

## Error Alerts — 2026-10-07 13:50 UTC
- **CRITICAL→FIXED** (765k+ restarts): `hermes-coding-mcp.service` crash-looping — `can't open file '/root/.hermes/scripts/run_mcp_server.py': No such file or directory`, status=2/INVALIDARGUMENT every 5s since ~44 days of restarts. MCP dir `mcp/hermes-coding-mcp/` gutted (only empty `dispatcher/`).
  - **AUTO-FIX**: `systemctl disable --now hermes-coding-mcp.service`. Not on trading path (pipeline/price-collector/1m-candle unaffected). Re-enable only after restoring `run_mcp_server.py`.
- **WARN→FIXED**: `hermes-better-coder.service` + timer failing every 30min — `ModuleNotFoundError: No module named 'dispatcher.dispatcher'` (dispatcher package deleted). Same gutted MCP dir.
  - **AUTO-FIX**: `systemctl disable --now hermes-better-coder.service hermes-better-coder.timer`.
- **WARN** (recurring): Disk 85% used (95G/118G). No uncompressed *.log >7d. Active DBs: coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.5G, session_brain 1.0G. CEO retention decision still open.
  - **AUTO-FIX**: None safe this run.
- **WARN** (recurring): `hermes-git-release.service` fails hourly — update-git.py refuses dirty tree (`automation/error_alerts.md`, `brain/associative_memory.db`, etc. uncommitted). Needs a commit, not a service fix.
  - **AUTO-FIX**: None (commit workflow is human/CEO-gated per SOP).
- **INFO**: Pipeline healthy — 86 signals/hr, 2 open (APT/FIL SHORT both in profit), 8 closed today +$0.50 / 2 wins. All 3 critical timers active. Prices fresh (87 tokens ~8s). Regime SHORT_BIAS. 0 phantom trades. Position manager rc=0, trailing SLs active on both opens.
- **INFO**: `hermes-atr-sl-updater.timer` not-found — DEFUNCT rename, expected. `hermes-regime-24h-check.timer` / `hermes-regime-transition-check.timer` inactive — intentional, not in run path.

## Error Alerts — 2026-10-07 09:48 UTC (health_monitor)
- **WARN** (recurring): Disk 85% used (95G/118G) — at threshold, goal <80% by Oct 14
  - **AUTO-FIX**: None safe — no *.log older than 7d to gzip; DB prune still delegated to bug_hunter (coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.4G, session_brain 1.0G)
- **INFO**: Pipeline healthy — LIVE run 09:46:42 rc=0, 132 signals/hr, 0 open / 6 closed today +$0.64. Timers 3/3 active. 0 Tracebacks. FOGO SHORT correctly rejected at RSI floor (not a bug).
- **INFO**: Recurring side findings unchanged — signals_hermes_runtime.db unbounded 92MB; decisions table dead since April.

## Error Alerts — 2026-10-07 06:05 UTC (CEO run)

## Error Alerts — 2026-10-07 06:50 UTC (health_monitor)
- **WARN** (1x): Disk 85% used (/dev/vda2 94G/118G) — at alert threshold, goal <80% by Oct 14
  - **AUTO-FIX**: None safe — no uncompressed *.log older than 7d (all rotations already .gz); live logs (pipeline.log 93M) cannot be compressed in place. DB prune delegated to bug_hunter per CEO run 06:00.
- **INFO**: `data/prices.db` and `data/signals.db` are 0 bytes (created 02:00/03:32 today). Regime scanners fall back to candles.db; pipeline unaffected. Flag for bug_hunter — confirm no live writer expects them.
- **INFO**: token_speeds 79/241 stale; avg speed_percentile 48.6 — below 50, market momentum weak (matches low signal volume).

## CEO RUN 06:00 UTC — Wyckoff registered, 7d positive again

### VERIFIED NUMBERS (self-queried PostgreSQL brain)
- **24h: 10T +$1.03 60.0% WR** — GOAL ≥$0 MET (was −$0.19 @02:00)
- **7d: 210T +$0.80 54.3% WR** — FLIPPED POSITIVE (was −$0.31 @02:00)
- **30d: 915T −$0.61 51.1%**
- LONG 7d +$1.35/169T 56.8% | SHORT 7d −$0.55/41T 43.9% (improved from −$1.66)
- Open 1: pump-chain+ LONG @0.17677 −0.19% (opened 05:32)
- hard_max_loss **post-fix: 1T −$0.03 lev5** — bleeding stopped (was 58T −$8.11/7d pre-fix)
- Regime 5m: LONG_BIAS (72L/2S/49N @05:45). Disk 85%. Pipeline healthy.

### DECISIONS
1. **RATIFY brain_auditor 5cd2a9f2** (04:38 UTC) — SHORT_RSI_HARD_FLOOR 25→45, BB_SQUEEZE_LONG_RSI_MIN=60, MOVER± kill. Verified wired: bollinger_squeeze.py:33/188-195 enforces LONG_RSI_MIN; decider_run.py + brain.py enforce HARD_FLOOR at detection + execution. Data-backed. Protected flags untouched.
2. **WYCKOFF WIRE-UP — root cause fix.** Signal file existed, WYCKOFF_PLUS/MINUS_ENABLED=True, but (a) never in SIGNAL_REGISTRY → 0 trades ever; (b) source='wyckoff' blocked by schema on WYCKOFF_ENABLED=False master. Fixed: directional sources wyckoff+/wyckoff-, registry entry enabled=True (PLUS/MINUS checked in run()), FAMILY_MAP Wyckoff family. **Pipeline restarted — wyckoff now in signals_runner list (48 signals).** NOT in STANDALONE_BYPASS — needs confluence partner. 48h shadow eval before any bypass.
3. **REJECT bb-bounce-v3 RSI_MAX 55→40** — meta _signal_metadata.rsi_14 30d: 51-55 = 4T **100%WR +$0.22 BEST band**; 41-50 = 9T 44.4% −$0.16. Old plan used unreliable entry_rsi_14 (DRIFT-E). Do not tighten.
4. **0 trading constant values changed this run.** hard_max_loss fix (aed0aa36) + brain_auditor changes stand.
5. **DELEGATE bug_hunter:** disk prune plan (coin_tracker 3.3G, candles 2.6G, session_brain 1.0G, signals table 26k unbounded); monitor hard_max_loss post-fix cohort (needs n≥10).
6. **DELEGATE signal_analyst:** evaluate wyckoff signals after 48h shadow (confluence partner needed — check if wyckoff pairs with pump-chain/volume-breakout); trend-ride+ n≥10 eval (currently 7T 42.9% −$0.18).

### GOALS (updated Oct 7 06:00)
| Metric | Current | Target | Deadline | Status |
|--------|---------|--------|----------|--------|
| hard_max_loss bleed | 1T post-fix | ≥50% $ cut vs −$8.11 | Oct 11 | FIX LIVE — n=1, monitor |
| SHORT 7d PnL | −$0.55 | ≥$0 | Oct 9 | IMPROVING from −$1.66 |
| 7d PnL | +$0.80 | ≥$0 | Oct 10 | **MET** |
| 24h PnL | +$1.03 | ≥$0 | next run | **MET** |
| New signals live | wyckoff wired | ≥1 firing | Oct 9 | REGISTERED — shadow |
| Disk | 85% | <80% | Oct 14 | Prune delegated |

### SIDE FINDINGS
- signals_hermes_runtime.db 26k rows / 92MB unbounded (purge only removes executed>1h)
- session_brain.db 1.0G, mtf_macd_tuner 1.4G — prune candidates
- volume low 0-2T/hr ~11h (market, not filter failure — confluence working)

## Error Alerts — 2026-10-07 05:59 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: N.N < N`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK-TOK-TOK] CC TOK BLOCKED — exec TOK unavailable (TOK-closed, SHORT_RSI_HARD_FLOOR)`

## Error Alerts — 2026-10-07 09:59 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   [TOK-TOK] TOK: skip TOK — hebbian n=N < N (insufficient data, TOK-open)`

## Error Alerts — 2026-10-07 10:59 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-07 11:47 UTC
- **WARN** (5x): `TRADE FAILED: IO SHORT — RSI hard floor: 26.8 < 45` — signal re-generated each minute but blocked by RSI filter. Signal generator producing oversold short signals that trade executor correctly rejects. No auto-fix: signal quality issue, not system health.
- **WARN**: Disk at 85% (95G/118G). No uncompressed logs >7d found. Monitor.
- **WARN** (5 services failed): `hermes-bug-hunter`, `hermes-better-coder`, `hermes-git-release`, `hermes-trading-checklist`, `hermes-upgrade-implementer` — all failed on code-quality checks (bare excepts, connection leaks, defunct imports). Non-critical maintenance services. No auto-fix: restarting won't help until code issues resolved.
- **INFO**: 0-byte legacy DBs: `prices.db`, `signals.db` — likely defunct, no active references found.

## Error Alerts — 2026-10-07 11:59 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3538s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3483s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3422s left, N failures)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3305s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3243s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3062s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2996s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2939s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2870s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2826s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2768s left, N failures)`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: IO TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: N.N < N`

## Error Alerts — 2026-10-07 12:48 UTC
- **WARN**: Disk at 85% (94G/118G). Auto-fix: vacuumed journald → freed ~453MB. Remaining hogs are active DBs (coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.5G, session_brain 1.0G, signals_hermes 952M) + docker 2.4G + cache 5.3G. No uncompressed logs >7d. Do not delete active DBs without a retention plan.
- **REPEATED** (filter OK): `TRADE FAILED: GRASS SHORT — RSI hard floor: 39.5/44.8 < 45` and `exec RSI unavailable (fail-closed)`. Executor correctly rejecting oversold shorts. Not a system-health issue; signal-quality issue (see prior 11:47 alert re IO SHORT same pattern).
- **INFO**: `data/speed_history.json` is dead — all 567 token series last ts ~2026-05-10 (~151 days stale). No script references found. Live speed data is `token_speeds` in signals_hermes_runtime.db (180 live rows, updated 12:47 UTC). Safe to ignore/delete; not wired into pipeline.
- **INFO**: `decisions` table last write 2026-04-13 (4 rows). Expected — ai_decider defunct, signal_compactor does not write here. No action.
- **OK**: Pipeline running, position manager rc=0, all 3 timers active (fired within last ~90s), prices fresh (18s), 94 signals last 1h, 0 open trades, 7 closed today (+0.50 USDT, 2 wins), regime SHORT_BIAS (18L/23S/83N), 70.6% tokens >= 50th speed percentile.

## Error Alerts — 2026-10-07 12:59 UTC
- **REPEATED** (11x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`

## Error Alerts — 2026-10-07 14:59 UTC
- **REPEATED** (12x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-07 15:50 UTC
- **WARN** (recurring): Disk at 85% (95G/118G, 18G free). No auto-fix applied — no logs >7d to gzip; prior journald vacuum (12:48) already done. Remaining hogs are live DBs (coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.5G, session_brain 1.0G, signals_hermes 953M). Do not delete active DBs without a retention plan. Suggest: retention job for mtf_macd_tuner/session_brain, or grow disk.
- **INFO**: price-collector LOCK-WAIT on candles.db — 46 retries/30min, all waited ≤0.1s and succeeded. Prices fresh (52s), candles_1m fresh (21s). Not blocking; no service stop needed.
- **OK**: Pipeline cycle #232659 all rc=0. Timers: 3/3 active (fired ≤90s). Signals 125/1h. Trades: 0 open, 10 closed today (~+0.28 USDT, 2 wins). Regime SHORT_BIAS (12L/22S/92N). Speed 128/241 (53%) ≥50th pct. Position manager clean. No crashes.

## Error Alerts — 2026-10-07 15:59 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: N.N < N`

## Error Alerts — 2026-10-07 16:48 UTC
- **WARN** (recurring): Disk at 85% (95G/118G, 18G free). No auto-fix — no logs >7d to gzip; journald vacuum already done at 12:48. Hogs are live DBs (coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.5G, session_brain 1.0G). Need retention plan or disk growth.
- **OK**: Pipeline clean (rc=0 all steps). Timers 3/3 active (fired ≤30s). Signals 76/1h. Trades: 0 open, 10 closed today (+0.55 USDT, 2 wins). Regime LONG_BIAS (86L/0S/38N). Speed 128/241 (53%). No phantom trades. No DB lock issues. No crashes.

## Error Alerts — 2026-10-07 16:59 UTC
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-10-07 17:48 UTC
- **WARN** (recurring): Disk at 85% (95G/118G, 18G free). No auto-fix — no logs >7d to gzip; live DBs are the hogs (coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.5G, session_brain 1.0G). Need retention plan or disk growth.
- **OK**: Pipeline cycle rc=0 all steps. Timers 3/3 active (fired ≤60s). Signals: 4 signal_history/1h, recent SHORT signals (BTC/FOGO/STX/BABY/CHIP). Trades: 0 open, 10 closed today (+0.28 USDT, 25% WR pump-chain- SHORT). Regime SHORT_BIAS (3L/77S/45N). Speed 128/241 (53%). Prices fresh (candles.db 17:46, collector 17:47). No phantom trades, no crashes, no DB locks. hotset empty — compaction filtered all signals (BTC-CRASH momentum block + conf <50%). pipeline.service inactive between fires is normal (oneshot + timer).

## Error Alerts — 2026-10-07 20:48 UTC
- **WARN** (recurring): Disk at 85% (95G/118G, 17G free). No logs >7d to gzip. DB hogs unchanged: coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.6G, session_brain 1.1G. Same as 17:48 alert — needs retention plan, not a log cleanup.
- **OK**: Pipeline cycle #232952 rc=0. Timers 3/3 active (fired ≤60s). Services: pipeline, hl-sync-guardian, hl-copy, brain-api all active. Signals: 100/1h (LDO/GRASS/CHIP SHORT pump-chain, WLD SHORT, WCT LONG). Trades: 0 open in signal_outcomes, 11 closed today (+0.22 USDT, 2 wins). Decider sees 2/6 open server positions (not yet in signal_outcomes — normal). Regime LONG_BIAS 44L/12S/67N; coin_tracker STORMY/BEARISH tide; macro gate LONG=FULL, SHORT=REDUCE. Speed 128/241 (53.1%) >= p50. Prices fresh (51s, 87 tokens). No phantom trades, no crashes, no DB locks, no exceptions in 30min. Grep "error" hits were false positives ("0 errors" in coin_tracker lines).

## Error Alerts — 2026-10-07 21:00 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.2s (rc=N)`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TOK position_manager: TOK (most recent call last):`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS WARNING: N steps failed: position_manager`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-10-07 22:00 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-10-07 23:49 UTC
- **WARN** (recurring): Disk at 86% (95G/118G, 17G free). No logs >7d to gzip. DB hogs: coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.6G, session_brain 1.1G. Needs DB retention plan — log cleanup won't help.
- **WARN** (1x): `hermes-better-coder.service` — `ModuleNotFoundError: No module named 'dispatcher.dispatcher'`. Dispatcher dir at `/root/.hermes/mcp/hermes-coding-mcp/dispatcher/` is EMPTY. Service crashes every 30min run. Not auto-fixed — module source unknown.
- **WARN** (1x): Phantom trade — GRASS SHORT closed at -0.0015% / -0.0005 USDT (atr_trail_hit, 12:47). Below 0.01% threshold.
- **INFO**: Hotset empty — 52 signals generated last hour, 0 survived compaction. Compactor filtering aggressively (BTC-CRASH momentum block + conf <50% pattern from earlier alerts).
- **OK**: Pipeline clean (192 rc=0 cycles/30min, 0 tracebacks). Timers 3/3 active, firing ≤75s. Positions: 1 open (CRV LONG +5.38%), 13 closed today. Regime LONG_BIAS (75L/1S/48N). Speed 128/241 (53%). Prices fresh (87 tokens, ~51s). 1m candles flowing (105/5min). No DB locks blocking. hl-sync-guardian clean.
- **INFO**: `hermes-bug-hunter.service` FAILED — by design (exits 1 when bugs found). Real issues logged: defunct ai_decider imports, 127 bare excepts, 52 sqlite connection leaks.
- **INFO**: `hermes-git-release.service` FAILED — by design (exits 1 on uncommitted changes).

## Error Alerts — 2026-10-08 02:48 UTC
- **WARN** (recurring): Disk at 86% (95G/118G, 17G free). No logs >7d to gzip. DB hogs: coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.6G, session_brain 1.1G. Needs DB retention plan — log cleanup won't help.
- **WARN** (1x): `hermes-better-coder.service` FAILED — `ModuleNotFoundError: No module named 'dispatcher.dispatcher'`. Dispatcher dir empty. Service crashes every 30min. Not auto-fixed — module source unknown.
- **WARN** (1x): Phantom trade — 1 trade with |pnl_pct| < 0.01% in last 24h. Below threshold for action.
- **INFO**: Hotset empty — 110 signals generated last hour, 0 survived compaction / none above 50% confidence. Compactor filtering aggressively. Pipeline log confirms: "No signals above 50% confidence — skipping execution."
- **OK**: Pipeline clean — all cycles rc=0, no tracebacks in 30min. Timers 3/3 active (fired ≤46s). Positions: 0 open, 1 closed today (pump-chain LONG +0.94 USDT, 100% WR). Regime SHORT_BIAS (10L/47S/67N across 124 tokens). Prices fresh (60s, 185 tokens). 1m candles flowing. No DB lock contention (3 concurrent readers on candles.db is normal). hl-sync-guardian active. Grep "error" hits were false positives ("0 errors" in coin_tracker lines).

## Error Alerts — 2026-10-08 03:00 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-08 04:49 UTC
- **WARN** (recurring): Disk at 86% (95G/118G, 17G free). Journal vacuum freed 92.5M (156M→64M). DB hogs unchanged: coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.7G, signals_hermes 958M, session_brain 1.1G. Log cleanup won't help — needs DB retention plan (CEO).
- **WARN** (recurring): Hotset empty — 145 signals in DB last hour (many conf≥50: pump-chain SHORTs 88, ichimoku_short 75–78) but pipeline logs "No signals above 50% confidence — skipping execution" and hotset.json `[]`. Compactor filters all. decisions table still dead (4 rows, last 2026-04-13). Not auto-fixed — needs signal-lab review of why high-conf signals don't reach execution.
- **WARN** (recurring): `hermes-better-coder.service` FAILED — `ModuleNotFoundError: No module named 'dispatcher.dispatcher'`. `/root/.hermes/mcp/hermes-coding-mcp/dispatcher/` is EMPTY (since Sep 1). Service crashes every 30min. Not auto-fixed — module source unknown.
- **OK**: Pipeline clean — all cycles rc=0, no Traceback/CRASH/DB-lock in 30min. Timers critical set active: pipeline, price-collector, 1m-candle, 15m-regime, 4h-regime (timer named `4h-regime-scanner.timer` — naming quirk, fires every 4h, last 01:05 next 05:05). Positions: 0 open, 1 closed today in signal_outcomes (+0.94 USDT win); pipeline portfolio log 12 closed today +28.18%. Regime SHORT_BIAS (98S/1L/27N, 126 tokens, scanner 04:45). Prices fresh (1m candles 0.2min, signals 0min). 0 phantom trades. BTC-CRASH/BTC_LEVEL guard blocks expected under SHORT_BIAS. hl-sync-guardian active.
- **INFO**: `decisions` table unused by current signal_compactor.py (deterministic, LLM-free) — dead code path, not a runtime issue.

## Error Alerts — 2026-10-08 05:00 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3541s left, N failures)`

## Error Alerts — 2026-10-08 06:00 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-10-08 06:50 UTC (health_monitor)
- **WARN** (recurring): Disk at 86% (96G/118G, 17G free). Journal vacuum freed 0B (already clean). No uncompressed *.log >7d. DB hogs unchanged: coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.7G, session_brain 1.1G, signals_hermes 959M. Log cleanup will not help — needs DB retention plan (CEO).
- **WARN** (recurring): `hermes-better-coder.service` FAILED — `ModuleNotFoundError: No module named 'dispatcher.dispatcher'`. `/root/.hermes/mcp/hermes-coding-mcp/dispatcher/` still empty. Service+timer report disabled but unit ran 06:46:22 (timer still listed NEXT 07:16). Not auto-fixed — module source unknown.
- **WARN** (recurring): Hotset empty / execution dry — 92 signals in `signals` last hour (conf up to 88: BTC continuum_trend_short, BIGTIME volume_breakout_long) but pipeline logs "No signals above 50% confidence — skipping execution." Known compactor/top-10 admission issue from prior audits; not auto-fixed.
- **INFO**: BANANA SHORT stuck in DECIDER-LOOP — same conf=54.06 hotset=YES volume-breakout-short- re-evaluated every ~60s 06:26–06:46 with BTC-CRASH-OVERRIDE allowing despite crash filter. No fill, no dismissal progress. Worth signal-lab look (stale hotset entry?).
- **OK**: Pipeline clean — 192 rc=0 cycles/30min, LIVE done 06:46:49 rc=0, 0 Tracebacks/CRASH, position_manager rc=0. Critical timers 3/3 active (price-collector 06:46:22, 1m-candle 06:46:32, pipeline 06:47:00). hl-sync-guardian active. Prices fresh: candles_1m age 20s, 89 tokens/10m, token_speeds updated 06:47:36. Speed 128/241 (53%) ≥50th pct. Regime SHORT_BIAS (3L/90S/31N, 124 tokens, 06:45). Trades: 0 open, 1 closed today in signal_outcomes; pipeline portfolio log 10 closed today +31.28%. 0 phantom trades. candles.db held by 3 python procs — normal concurrent access, no lock errors.
- **INFO**: `hermes-atr-sl-updater.timer` not-found (defunct rename, expected). `hermes-health-monitor.timer` active (this monitor). Grep "error|fail" hits were false positives ("0 errors" coin_tracker lines).

## Error Alerts — 2026-10-08 08:50 UTC (health_monitor)
- **WARN** (recurring): Disk at 85% (95G/118G, 18G free). Auto-fix this run: pip cache purged (720 files), uv cache cleaned (1.5GiB, 51081 files), logs >7d gzipped. Disk 86%→85%. DB hogs unchanged: coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.7G, session_brain 1.1G, signals_hermes 960M. Log cleanup exhausted — needs DB retention plan (CEO).
- **WARN** (recurring): Hotset empty / execution dry — 105 signals in `signals` last hour (conf up to 88: BANANA pump-chain SHORT, WLD ichimoku_short, ADA support_resistance LONG) but pipeline logs "No signals above 50% confidence — skipping execution." Known compactor/top-10 admission issue from prior audits; not auto-fixed.
- **WARN** (new): Rapid-fire duplicate signals — CAKE hmacd_mtf 9x (07:55–08:43), USUAL support_resistance 7x (08:01–08:44), MNT hmacd_mtf 6x, CRV pump-chain 4x in last hour. Same signal_type re-firing on same token without dismissal/cooldown. Worth signal-lab look.
- **WARN** (recurring): `hermes-better-coder.service` FAILED — `ModuleNotFoundError: No module named 'dispatcher.dispatcher'`. `/root/.hermes/mcp/hermes-coding-mcp/dispatcher/` still empty. Not auto-fixed — module source unknown.
- **WARN** (info): 8 non-critical agent services in failed state (better-coder, brain-auditor, bug-hunter, ceo, git-release, trading-checklist, upgrade-implementer, wasp). WASP exits 1 BY DESIGN when it finds warnings — not a crash; its output confirms hotset empty + runtime DB 66MB>50MB + rapid-fire duplicates. Core trading path unaffected.
- **OK**: Pipeline clean — LIVE done 08:46:38 rc=0, 0 Tracebacks/CRASH, position_manager rc=0. Critical timers 3/3 active (price-collector, 1m-candle, pipeline). hl-sync-guardian active. Prices fresh: prices.json updated 08:47:05 (~seconds old), 88 tokens. Speed 90/178 (50.6%) ≥50th pct. Regime SHORT_BIAS (7L/57S/62N, 126 tokens, scanner 08:45). Trades: 0 open; signal_outcomes 1 closed today (+0.94 USDT LONG 100% WR); pipeline portfolio log 8 closed today +34.31%. 0 phantom trades. candles.db held by price_collector PID — normal, no lock errors.
- **INFO**: `decisions` table unused by current signal_compactor.py (deterministic, LLM-free) — dead code path, not a runtime issue.

## Error Alerts — 2026-10-08 09:00 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING — BTC_LEVEL`

## Error Alerts — 2026-10-08 11:00 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-08 12:00 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-10-08 13:47 UTC
- **WARN**: Disk 85% used (18G free) — dominated by DBs (coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.8G). No old logs to reclaim.
- **WARN**: Multiple auxiliary services failed (bug-hunter, better-coder, brain-auditor, ceo, git-release) — bug-hunter exits 1 by design when findings exist (sqlite_leaks 49 files, cursor_leaks 51, bare_except 127). Not pipeline-blocking.
- **CRITICAL → FIXED**: hermes-coding-mcp crash-looping (770k+ restarts) — ExecStart points to missing `/root/.hermes/scripts/run_mcp_server.py`. **AUTO-FIX**: stopped service; already disabled (no timer).

## Error Alerts — 2026-10-08 15:00 UTC
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: usage: brain.py trade add [-h] [--exchange EXCHANGE] [--strategy STRATEGY]`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BULL+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-08 15:50 UTC (health_monitor)
- **OK**: Core trading path healthy. Pipeline LIVE done 15:46:41 rc=0, 0 real Tracebacks (6 "CRASH" grep hits were BTC-CRASH momentum blocks, not crashes). Critical timers 3/3 active (price-collector, 1m-candle, pipeline). hl-sync-guardian active. Prices fresh: candles_1m age 0.3min, 128 tokens/10min. Speed 128/241 (53%) ≥50th pct. Regime SHORT_BIAS (1L/120S/5N, 126 tokens, 15:45). Trades: 0 open, 6 closed today in signal_outcomes (+0.23 USDT, 1 win); pipeline portfolio log 9 closed +23.21%. 137 signals/1h. candles.db held by 3 python procs — normal concurrent access, no lock errors.
- **WARN** (recurring): Disk 85% (95G/118G). This run: journal vacuumed (freed 178MB), pip/uv caches empty. Still 85% — DB hogs unchanged (coin_tracker 3.4G, candles 2.6G, mtf_macd_tuner 1.8G, session_brain 1.1G, signals_hermes 1G). Log/cache cleanup exhausted — needs DB retention plan (CEO decision).
- **WARN** (recurring): Hotset empty / execution dry — 137 signals/1h (conf up to 88: ME/TURBO/KAS SHORT, ME/KAS LONG) but pipeline logs "No signals above 50% confidence — skipping execution." Known compactor/top-10 admission issue; not auto-fixed.
- **WARN** (recurring): `hermes-better-coder.service` FAILED — `ModuleNotFoundError: No module named 'dispatcher.dispatcher'`. `/root/.hermes/mcp/hermes-coding-mcp/dispatcher/` still empty. Not auto-fixed — module source unknown.
- **WARN**: `hermes-trading-checklist.service` exits 1 by design on WARNINGS — flagging 28,363 stale signals in `signals` table (28,090 older than 2h; signal_history only 240). signal-purge purges executed signals only; unexecuted stale rows accumulate. Suggest purge extend to unexecuted >2h.
- **WARN**: `hermes-brain-auditor.service` / `hermes-upgrade-implementer.service` exit 124 (timeout). Non-critical agents. `hermes-bug-hunter.service` exits 1 by design (findings: dead signal_gen imports in zscore_momentum.py, trend_purity_signals.py, candle_predictor.py + inline DB passwords).
- **INFO**: `hermes-mtf-macd-tuner.service` currently mid-sweep (activating) — earlier "failed" was prior run completing; not stuck. `hermes-atr-sl-updater.timer` not-found (defunct rename, expected).

## Error Alerts — 2026-10-08 16:00 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: 1s, retrying`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-10-08 16:50 UTC
- **WARN** (1x): Disk `/` at 85% (95G/118G, 18G free). Top consumers: `coin_tracker.db` 3.3G, `candles.db` 2.6G, `mtf_macd_tuner.db` 1.8G, `session_brain.db` 1.1G, logs 329M. Logs actively written by services — no safe compression possible. No auto-fix applied; needs retention/pruning strategy for DBs.

## Error Alerts — 2026-10-08 17:55 UTC (health_monitor)
- **OK**: Core path healthy. Pipeline last done 17:46:51 rc=0, 0 open / 9 closed today (+23.21% PnL). Timers 3/3 active (price-collector, 1m-candle, pipeline) all firing on schedule. No real Tracebacks — BTC-CRASH lines are intentional momentum blocks. Signals: 110/1h. Prices fresh: 87 tokens, 75s old. Speed 126/241 (52%) ≥50th pct. Regime SHORT_BIAS (5L/107S/12N, 124 tokens, 17:45).
- **AUTO-FIX**: `mtf_macd_tuner.py` IndexError — 4h warmup guard was `< 10` but `PrecomputedMACD(12,55,15)` requires ≥70 candles (first_sig=69). Changed guard to `< 70`. Compile OK. Next daily sweep will skip short-4h tokens cleanly instead of crashing mid-sweep.
- **AUTO-FIX**: Journal vacuumed, freed 89.6M. Disk still 85% (95G/118G) — DB hogs unchanged (coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.8G, session_brain 1.1G, signals_hermes 963M). Recurring WARN — needs DB retention plan (CEO decision).
- **WARN** (recurring): `hermes-better-coder.service` FAILED every 30min — `ModuleNotFoundError: dispatcher.dispatcher`. `/root/.hermes/mcp/hermes-coding-mcp/dispatcher/` is an empty dir (no `dispatcher.py`). Module source unknown — not auto-fixed.
- **WARN**: `hermes-trading-checklist.service` exits 1 by design — flags 28,540 stale rows in `signals` (0 approved, 16 pending). signal-purge only purges executed signals; unexecuted accumulate. Suggest extend purge to unexecuted >2h.
- **WARN**: `hermes-bug-hunter.service` exits 1 by design — 9 findings (dead signal_gen imports in zscore_momentum.py/trend_purity_signals.py/candle_predictor.py, bare excepts, sqlite leaks, hardcoded passwords). Known, not new.
- **WARN**: `hermes-upgrade-implementer.service` failed — pipes prompt into opencode; no journal output captured. Non-critical agent.
- **INFO**: `candles.db` held by 3 python procs (price-collector, 1m-candle, pipeline) — normal concurrent WAL access, no lock errors. `price_history.db` is 0 bytes/empty (unused legacy; live prices via `prices.json`).

## Error Alerts — 2026-10-08 18:48 UTC
- **WARN** (1x): Disk at 85% (94G/118G). Top consumers: coin_tracker.db (3.3G), candles.db (2.6G), session_brain.db (1.1G), signals_hermes.db (964M), mtf_macd_tuner.db (944M). 18G free.
- **AUTO-FIX**: None — active DBs, no safe auto-clean without retention review.
- **WARN** (1x): hermes-bug-hunter.service exits status=1 (expected — reports known code-quality audit findings). Timer active, not a runtime fault.
- **INFO**: hermes-atr-sl-updater.timer unit intentionally DEFUNCT/disabled. Stale list entry only.

## Error Alerts — 2026-10-08 19:48 UTC
- **WARN** (1x): Disk at 85% (94G/118G, 18G free). Unchanged since 18:48 check. Top consumers unchanged: coin_tracker.db (3.3G), candles.db (2.6G), session_brain.db (1.1G). Active DBs — no safe auto-clean without retention review.
- **AUTO-FIX**: Compressed stale `/root/.hermes/logs/sniper_exit.log` (>7d) to .gz. No other safe cleanup targets (only 1 log >7d; journals already compact at 56M).
- **INFO**: Pipeline healthy — 1 open / 9 closed today, +35.61% PnL. All core timers firing. Prices fresh (max candle 19:47 UTC). No phantom trades, no DB locks, no crashes.

## Error Alerts — 2026-10-08 20:00 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-08 20:48 UTC
- **WARN** (1x): Disk usage at 85% (18G free). Large logs: pipeline.log (127M), trade-watchdog.log (54M).
- **AUTO-FIX**: Compressed logs older than 3 days. No active errors, all timers running, pipeline healthy.

## Error Alerts — 2026-10-08 21:00 UTC
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] BIGTIME TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] BIGTIME TOK — continuum says DECLINING+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-09 01:50 UTC
- **WARN** (recurring hourly): `hermes-brain-auditor.service` failed at 01:40 — psycopg2 errors inside LLM session: `signal_metadata` column (hint: use `_signal_metadata`), `ROUND(double precision, integer)` needs `::numeric` cast, `hold_minutes` column doesn't exist (likely `hold_min`/`duration_min`). Service is LLM-driven; SQL errors are mid-session but process exited 1.
- **INFO**: `hermes-bug-hunter.service` exit 1 at 01:47 — by design (findings: connection_leaks 53 files, non_atomic_json 75 files, hardcoded_passwords 4 files, dead_imports 3x signal_gen). Not a crash.
- **INFO**: `hermes-atr-sl-updater.timer` unit not-found (stale reference in hermes.target listing). No-op.
- **INFO**: Disk 85% used (18G free) — at WARN threshold. No logs >7d worth compressing. Journal 144M.
- **INFO**: 0 trades open/closed today, 0 outcomes in last hour despite 116 signals generated. Position manager healthy (rc=0 every run). Live trading enabled.
- **AUTO-FIX**: None required. All critical timers (price-collector, 1m-candle, pipeline) active and firing. Pipeline no errors in 30m. Prices fresh (87s). No DB locks.

## Error Alerts — 2026-10-09 03:00 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS TOK signals_runner: timed out (killed after N.0s)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS WARNING: N steps failed: signals_runner`

## Error Alerts — 2026-10-09 03:48 UTC
- **WARN** (1x): disk `/` at 85% used (118G total, 18G free). Largest logs: pipeline.log 132M, trade-watchdog.log 55M, signal-compactor.log 46M. No logs >7d to gzip.
- **WARN** (3x): non-critical agent services failed last run — `hermes-brain-auditor` (exit 124 timeout), `hermes-ceo` (exit 124 timeout), `hermes-bug-hunter` (exit 1). Timers still scheduled; next runs will retry.
- **AUTO-FIX**: None required. Pipeline completed clean at 03:46 (LIVE, rc=0). All critical timers active (price-collector, 1m-candle, pipeline). No tracebacks, no DB locks, prices fresh, 162 signals in last hour.

## Error Alerts — 2026-10-09 04:00 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3533s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3482s left, N failures)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-09 05:00 UTC
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   [TOK-TOK] TOK: skip TOK — hebbian n=N < N (insufficient data, TOK-open)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-09 05:50 UTC
- **WARN** (1x): `disk 85.5% used (107.9G/126.2G, 18.3G free)` — recurring; bulk is active DBs (coin_tracker 3.3G, candles 2.6G, session_brain 1.1G), not logs. No unsafe deletions performed.
- **WARN** (1x): `hermes-brain-auditor.service failed (exit 124 systemd timeout)` — **AUTO-FIX**: restarted, now activating.
- **NOTE**: `hermes-bug-hunter.service exit 1` — by design (exits non-zero when code-quality findings exist: bare excepts, cursor leaks, etc.); not a runtime failure.
- **NOTE**: `hermes-ceo.service inactive` — normal between 6h timer runs.
- Core timers (price-collector, 1m-candle, pipeline) all **active**, last fire <2min. No tracebacks, no position-manager crashes, no phantom trades. Prices fresh (0.6min). 157 signals/1h.

## Error Alerts — 2026-10-09 06:48 UTC
- **WARN** (1x): Disk usage at 85% (/dev/vda2 95G/118G, 18G free)
- **AUTO-FIX**: None applied — no logs older than 7 days to compress. Largest consumers: /var/lib 8.2G, /var/www 2.4G, /root/zscore 2.2G, /root/hermes-agent 2.0G. Manual review recommended before disk hits critical.

## Error Alerts — 2026-10-09 07:00 UTC
- **REPEATED** (9x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-09 09:00 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   [brain.py] ❌ mirror_open TOK for TOK: Balance too low ($N.N < $N.N)`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK rc=N: stderr_tail=(empty)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: brain.py rc=N`

## Error Alerts — 2026-10-09 10:47 UTC
- **WARN**: Disk usage at 86% on / (95G/118G, 17G free)
- **AUTO-FIX**: Compressed logs older than 7d (none found); largest space consumers are DBs: coin_tracker.db (3.3G), candles.db (2.6G), session_brain.db (1.1G). No action taken on DBs — flagging for CEO review.

## Error Alerts — 2026-10-09 11:00 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] CC TOK — continuum says RECOVERY+NEUTRAL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-09 11:50 UTC
- **WARN** (1x): Disk usage 86% on / (96G/118G)
- **AUTO-FIX**: Vacuumed journald (freed 84M); npm cache clean (freed ~2.4G). Disk now 84%. No pipeline errors, no crashes, no phantom trades, timers all firing. DBs untouched (coin_tracker 3.3G, candles 2.6G — flagged previously for CEO review).

## Error Alerts — 2026-10-09 14:00 UTC
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-10-09 15:00 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BEAR+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-09 15:48 UTC
- **[WARN]** (1x): `hermes-brain-auditor.service` exited status=124 (timeout) at 15:40. Prior run at 15:37 succeeded (RC:0, pushed 471cae7d). Self-recovers at next timer (16:30). No action taken — will retry automatically.

## Error Alerts — 2026-10-09 16:00 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ [TOK-TOK] TOK failed for TOK: Command '['/root/.opencode/bin/opencode', 'run', 'You are a crypto trading gate. Evaluate this signal and reply TOK of: GO, TOK, TO`

## Error Alerts — 2026-10-09 17:00 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: CC TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK rc=N: stderr_tail=(empty)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: brain.py rc=N`

## Error Alerts — 2026-10-09 20:00 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3515s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2647s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2591s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2530s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CC TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] CC TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
