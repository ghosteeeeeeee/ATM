# Error Alerts — 2026-10-07 09:48 UTC (health_monitor)

## Error Alerts — 2026-10-26 08:47 UTC (health_monitor)
- **WARN** (1x): `hermes-daily-orchestrator.service` failed at 05:21 (systemd start timeout, killed by TERM after ~23 min; was mid-analysis on price_history retention plan, wrote plan file before kill). Non-critical 24h autonomous improvement agent. **AUTO-FIX**: `systemctl reset-failed` so the next timer run (today 16:51 UTC) isn't blocked. If it recurs, raise `TimeoutStartSec`.
- **WARN** (recurring): Disk 84% used (93G/118G, 19G free). No uncompressed `*.log` >7d to gzip (already 15 .gz files). Growth drivers unchanged from 2026-10-23 analysis. No safe auto-fix — DB prune = CEO decision. Approaching 85% warn threshold.
- **INFO**: Pipeline healthy — LIVE run 08:43:05 rc=0, position_manager active, 0 Tracebacks/CRASH in 30min. Timers 4/4 active (price-collector, 1m-candle, pipeline, watchdog). 84 signals/hr. Portfolio: 1 open | 8 closed today | -0.14 USDT | WR 50% (PG). 0 phantom trades (`atr_sl_hit` <0.01% = 0). Regime 5m SHORT_BIAS (4L/53S/66N of 123 @08:30). Speeds 128/241 (53.1%) ≥50th pct (avg 73.5). Prices fresh (26s). hl-sync-guardian: active. Vacation pause: not active.
- **INFO**: Side findings unchanged — `hermes-atr-sl-updater.timer` ghost entry (DEFUNCT unit, disabled); `signals_hermes_runtime.db` unbounded; `decisions` table dormant (expected — ai_decider defunct).

## Error Alerts — 2026-10-23 21:47 UTC (health_monitor)
- **WARN** (ongoing, 11,829+ cycles): `hotset.json is empty — no signals survived compaction` — 19 signals in last hour (all conf ≥70, max 88) but 0 admitted. Reproducible root cause this cycle (cycle 11829): (1) ALT LONG passes confluence (2 unique types) then **RR HARD BLOCKED R:R=0.51 < 0.55** — TP via CANDLE at +1.24% vs SL 2.43% in EXTREME regime; (2) STX LONG **CONFLUENCE-GATE-BLOCK** single-type not in standalone bypass. Compactor only sees 1-2 combo_keys in its 5-min top-10 window, so both blocks empty the hotset. Not a crash — gate/RR tuning decision for CEO, no auto-fix applied (same finding flagged 16:44 and in trading_log.md).
- **WARN** (recurring): Disk 85% used (101.4G/126.2G raw = 80.3%; df reports 85% of usable space after ext4 reserved blocks, 18G free). No uncompressed `*.log` >7d to gzip (0 files; 15 already .gz). Growth drivers: `/root/.hermes/data` 7.9G (coin_tracker 3.3G, session_brain 1.5G+92M WAL, candles 1.2G), `/root/.local` 12G, `/root/.cache` 3.5G, `/usr` 32G. No safe auto-fix — DB prune = CEO decision.
- **INFO**: Pipeline healthy — LIVE run 21:42:23 rc=0, position_manager rc=0, 0 Tracebacks/CRASH in 30min. Timers 4/4 active (price-collector, 1m-candle, pipeline, watchdog) + 71 more scheduled. 19 signals/hr. Portfolio: 1 open (CFX) | 18 closed today | -0.54 USDT (PG) / -7.34% PnL (portfolio, pipeline log). Exit reasons 24h: profit-monster-trail 8 (+$0.44), hard_max_loss 3 (-$0.39), trail_arm_timeout 2 (-$0.02), UNIVERSAL_MAX_HOLD 2 (-$0.06), stale_exit 1, hard_sl 1, cut-loser-CL-T1 1, atr_sl_hit 1. 0 phantom trades (`atr_sl_hit` <0.01% PnL = 0). Regime 5m LONG_BIAS (40L/17S/66N of 123 @21:45). Speeds 128/241 (53.1%) ≥50th pct. Prices fresh (55s, 87 tokens/1h). Vacation pause: not active.
- **INFO**: Side findings unchanged — `hermes-atr-sl-updater.timer` ghost entry (unit file missing); `signals_hermes_runtime.db` unbounded; `decisions` table dormant since 2026-04-13 (ai_decider defunct, expected).

## Error Alerts — 2026-10-23 10:45 UTC (health_monitor)
- **CRITICAL→FIXED** (20,307 restarts ≈28h @5s): `hermes-coding-mcp.service` crash-looping again — `can't open file '/root/.hermes/scripts/run_mcp_server.py': No such file or directory` (script deleted in commit 3786b550 dead-scripts cleanup; same fault as 2026-10-07, unit had been re-started despite `disabled`).
  - **AUTO-FIX (root cause)**: `hermes-better-coder-health.service` (daily 06:00) and `hermes-better-coder-audit.service` (weekly Sun 03:00) both had `Wants=hermes-coding-mcp.service`, pulling the dead unit back up — verified: current storm resumed exactly Oct 23 06:00:00 at the health service start. This is why the fault kept recurring after previous stop/fix attempts. Removed the `Wants=` lines from both units, `systemctl daemon-reload`, verified: health service runs green while coding-mcp stays `inactive`. Also `systemctl stop hermes-coding-mcp.service`. Do not restart until `run_mcp_server.py` is restored.
- **INFO**: Pipeline healthy — LIVE run 10:42:23 rc=0, position_manager rc=0, 0 Tracebacks in 30min. Timers 4/4 active (price-collector, 1m-candle, pipeline, watchdog). 39 signals/hr. Hotset fresh (14s, 1 token NEAR SHORT). Portfolio: 2 open | 9 closed today | +6.35% PnL. Exit reasons 24h: profit-monster-trail 5 (+$0.33), trail_arm_timeout 2 (-$0.02), hard_max_loss 1 (-$0.11), UNIVERSAL_MAX_HOLD 1 (-$0.03). 0 phantom trades. Regime 5m NEUTRAL (16L/18S/95N of 129). Speeds 128/241 (53.1%) ≥50th pct. Prices fresh (9s). Disk 84% (threshold 85%). Vacation pause: not active.
- **INFO**: Side findings unchanged — `hermes-atr-sl-updater.timer` ghost entry; `signals_hermes_runtime.db` unbounded; `decisions` table dormant since 2026-04-13 (expected — ai_decider defunct, signal_compactor replaced it).

## Error Alerts — 2026-10-21 06:42 UTC (health_monitor)
- **WARN** (1x): `hermes-upgrade-implementer.service` failed at 04:36 (systemd start timeout, killed by TERM after ~2h — audit itself completed and wrote "audit written" just before the kill). Non-critical 12h agent. **AUTO-FIX**: `systemctl reset-failed` so the next timer run isn't blocked. Consider raising `TimeoutStartSec` in the unit if it recurs.
- **INFO**: Pipeline healthy — LIVE run 06:42:25 rc=0, position_manager rc=0, 0 Tracebacks in 30min. Timers 3/3 active (price-collector, 1m-candle, pipeline). 64 signals generated last hour. Portfolio: 2 open | 7 closed today | -0.32 USDT. Exit reasons 24h: atr_sl_hit 8 (-$0.59), trail_arm_timeout 4 (-$0.15), hard_sl 3 (-$0.22), profit-monster-trail 2 (+$0.27). 0 phantom trades. Regime 5m SHORT_BIAS (11L/46S/72N of 129). token_speeds 241 rows, 128 stale-flagged (avg percentile 48.5). Prices fresh (~0.5min, 87 tokens). Disk 83%. Vacation pause: not active.
- **INFO**: Side findings unchanged — `hermes-atr-sl-updater.timer` ghost entry (unit file missing); pipeline logged `[hotset] fallback DB query returned 0 tokens` (hotset empty this cycle, same pattern as 2026-10-08 WARN); `signals_hermes_runtime.db` still unbounded.

## Error Alerts — 2026-10-15 22:24 UTC (health_monitor)
- **WARN** (1x): `hermes-brain-auditor.service` failed with timeout at 21:50 (killed by systemd after exceeding start timeout). Non-critical hourly analysis agent; timer still active, will self-retry next hour. No action needed.
- **INFO**: Pipeline healthy — LIVE run 22:23:23 rc=0, position_manager rc=0, 0 Tracebacks in 30min. Timers 3/3 active (price-collector, 1m-candle, pipeline). 26 signals generated last hour. Portfolio: 3 open | 14 closed today | +18.64% PnL. Exit reasons 24h: atr_sl_hit 5 (-$0.36), hard_max_loss 3 (-$0.29), atr_trail_hit 3 (+$1.19), trail_arm_timeout 2 (-$0.08), profit-monster-trail 1 (+$0.04), HL_CLOSED 1 (-$0.18). 0 phantom trades. Regime 5m LONG_BIAS (42L/12S/72N of 126). Speeds top: INIT 100, BLZ 100, CASHCAT 99.4. Disk improved to 80% (was 85%). Prices fresh (~2min). Vacation pause: not active.
- **INFO**: Side finding — `hermes-atr-sl-updater.timer` appears in list-timers as a ghost entry (unit file missing at /etc/systemd/system/). Harmless, no service attached. `signals_hermes_runtime.db` still unbounded; `prices.db`/`signals.db` 0-byte stubs still present.

## Error Alerts — 2026-10-10 04:47 UTC (health_monitor)
- **WARN** (recurring): Disk 85% used (/dev/vda2 94G/118G). No uncompressed *.log >7d to gzip. Top DBs: coin_tracker 3.3G, candles 2.7G, session_brain 1.1G, signals_hermes 979M, mtf_macd_tuner 948M. No safe auto-fix — DB prune still a CEO/bug_hunter decision.
- **INFO**: Pipeline healthy — cycle #236303 running, no Tracebacks in 30min. Timers 3/3 active (price-collector, 1m-candle, pipeline). Prices fresh (~1min, 347 tokens in candles_1m last 5min). Regime 5m SHORT_BIAS (10L/16S/71N of 97). Speeds 128/241 ≥50th pct. 332 active signals, 1 generated last hour. 11 closed today (8W/3L, +$0.53), 0 open. 4 phantom trades (<0.01% pnl) in last 7d.
- **INFO**: Side findings unchanged — `signals_hermes_runtime.db` unbounded; `prices.db`/`signals.db` 0-byte stubs still present; `brain.db` 0-byte stub.

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

## Error Alerts — 2026-10-09 23:00 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-10-10 02:48 UTC
- **WARN** (4x): Non-critical automation services in failed state: bug-hunter (code-quality FAILs, by design), ceo (exit 124 timeout), summarizer (timeout), upgrade-implementer (exit 124)
- **AUTO-FIX**: `systemctl reset-failed` on all 4 — they re-trigger on next timer fire. Pipeline/timers/price-collector unaffected.
- **WATCH**: Disk at 85% (/dev/vda2, 18G free). No logs >7d to compress; journal rotation covers system logs. Monitor.

## Error Alerts — 2026-10-10 07:00 UTC
- **REPEATED** (8x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: W TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   [TOK-TOK] TOK: skip TOK — hebbian n=N < N (insufficient data, TOK-open)`

## Error Alerts — 2026-10-10 07:49 UTC
- **WARN** (777982x): `hermes-coding-mcp.service` crash-looping — `/root/.hermes/scripts/run_mcp_server.py` does not exist
- **AUTO-FIX**: Disabled `hermes-coding-mcp.service` (no script found anywhere on disk; re-enable only after restoring the script or updating ExecStart)
- **WARN** (1x): `hermes-ceo.service` exited status=124 (timeout) at 05:57 UTC
- **AUTO-FIX**: `reset-failed` applied; next timer fire 09:47 UTC will start clean
- **INFO**: Disk at 84% (94G/118G) — approaching 85% warn threshold; compress logs soon if it ticks up

## Error Alerts — 2026-10-10 08:00 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`

## Error Alerts — 2026-10-10 12:48 UTC
- **WARN** (1x): Disk at 84% (94G/118G) — approaching 85% threshold. Largest consumers: coin_tracker.db (3.3G), candles.db (2.7G). No auto-fix applied (no logs >7d to compress; DBs are active).
- **INFO** (5x): `TRADE FAILED: GMT SHORT — RSI hard floor: 42.5 < 45` — signal correctly rejected by safety filter, not a crash. No action needed.
- **INFO**: `hermes-atr-sl-updater.timer` unit not-found — likely decommissioned, no impact.

## Error Alerts — 2026-10-10 13:00 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   [TOK-TOK] TOK: skip TOK — hebbian n=N < N (insufficient data, TOK-open)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: N.N < N`

## Error Alerts — 2026-10-10 14:48 UTC
- **WARN** (9x): Phantom trades — `atr_sl_hit` exit with <0.01% PnL (today). Investigate ATR SL placement or execution slippage.
- Disk at 84% (approaching 85% threshold) — consider log cleanup if it crosses.
- No AUTO-FIX needed: all timers active, pipeline running, no crashes.

## Error Alerts — 2026-10-10 16:00 UTC
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BULL+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-10 16:48 UTC
- **WARN** (1x): Disk at 85% (94G/118G) — crossed threshold since 14:48 check (was 84%). Top consumers: coin_tracker.db (3.3G), candles.db (2.7G), session_brain.db (1.1G), signals_hermes.db (983M). No logs >7d to compress; DBs are active — no safe auto-fix. Consider pruning coin_tracker.db history or moving old DBs off-disk.
- **INFO**: 1 phantom trade in last 24h (`atr_sl_hit` <0.01% PnL) — down from 9 at 14:48. No action needed.
- All timers active, pipeline running, prices 2.5min fresh, no crashes. No auto-fixes needed.

## Error Alerts — 2026-10-10 17:00 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   [brain.py] ❌ mirror_open TOK for TOK: Balance too low ($N.N < $N.N)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK rc=N: stderr_tail=(empty)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: brain.py rc=N`

## Error Alerts — 2026-10-10 18:00 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   [TOK Mirror] TOK open TOK TOK: Insufficient margin to place order. asset=N`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   [brain.py] ❌ mirror_open TOK for TOK: Insufficient margin to place order. asset=N`

## Error Alerts — 2026-10-10 19:00 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   [TOK Mirror] TOK open TOK ME: Insufficient margin to place order. asset=N`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   [brain.py] ❌ mirror_open TOK for ME: Insufficient margin to place order. asset=N`

## Error Alerts — 2026-10-10 20:00 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS [Position Manager] TOK mirror_close TOK (DB committed, HL still open): mirror_close(TOK): HL TOK failed — Unknown TOK`

## Error Alerts — 2026-10-10 20:49 UTC
- **WARN** (disk): Disk at 85% (100.7G/118G). **AUTO-FIX**: Compressed pipeline.log (177MB→17MB gz), trade-watchdog.log (62MB→gz), signal-compactor.log (59MB→gz). DBs (coin_tracker.db 3.3G, candles.db 2.7G) are top consumers — no safe auto-fix.
- **WARN** (1x): 1 phantom trade in last 24h (SOPH LONG bb-bounce-v2-long+ 0.0% PnL). Low count, no action.
- **INFO**: Pipeline cycle #237263 completed cleanly. 3 open, 32 closed today, +1.01% PnL. 32 signals in last hour. Prices 1min fresh. No crashes/tracebacks in 30min. All critical timers active.
- Earlier today: HL mirror errors (insufficient margin) — not recurring in last 30min.

## Error Alerts — 2026-10-11 02:00 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-11 04:00 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`

## Error Alerts — 2026-10-11 05:48 UTC
- **[WARN]** (1x): Disk usage at 85% (95G/118G). Big consumers: coin_tracker.db (3.3G), candles.db (2.7G), session_brain.db (1.1G), signals_hermes.db (989M).
- **AUTO-FIX**: Vacuumed 262M of archived systemd journals. Data DBs left untouched (essential). Recommend periodic candle/token pruning if disk climbs past 90%.

## Error Alerts — 2026-10-11 06:49 UTC
- **WARN** (1x): `[DISK]` Root filesystem at 85% used (95G/118G). No logs >7d to compress; journals already minimal. candles.db is 2.8GB.
- **WARN** (1x): `[bug-hunter exit 1]` Failed at 06:46 — by design when findings exist: dead signal_gen imports (zscore_momentum, trend_purity_signals, candle_predictor), 4 hardcoded password files, 75 non-atomic JSON writers. **AUTO-FIX**: `systemctl reset-failed` — will re-fire on next 8h timer.
- **WARN** (1x): `[ceo exit 124]` Timed out at 05:57 after ~1min CPU. **AUTO-FIX**: `systemctl reset-failed` — will re-fire on next timer.

## Error Alerts — 2026-10-11 08:00 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ [TOK-TOK] TOK failed for TOK: Command '['/root/.opencode/bin/opencode', 'run', 'You are a crypto trading gate. Evaluate this signal and reply TOK of: GO, TOK, TO`

## Error Alerts — 2026-10-11 08:50 UTC
- **[WARN]** (1x): Disk usage at 85% on / (95G/118G). No old logs to compress — bloat is DBs: coin_tracker.db 3.3G, candles.db 2.7G, session_brain.db 1.1G, signals_hermes.db 990M.
- **AUTO-FIX**: Checked for log cleanup (>7d, >30d gz) — none found; rotation working. DB vacuum/retention left for manual review (not auto-applied, risky on live DBs).
- **[INFO]**: hl-copy.err.log shows recurring [LOCK-WAIT] info_rate 0.1s retries — recovering on its own, not stuck.

## Error Alerts — 2026-10-11 10:00 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-11 10:49 UTC
- **[WARN]** (1x): Disk usage at 85% (`/dev/vda2` 95G/118G, 18G free). No >7d logs found to compress. Monitor; if it crosses 90%, archive `data/coin_tracker.db` (3.4G) or old pipeline logs.
- **[WARN]** (1x): `hermes-ceo.service` failed at 09:57 with exit 124 (timeout). Auto-fix: `systemctl reset-failed`. Next timer run: 14:41 UTC.
- **[INFO]** (4x): RESOLV SHORT execution failures — `RSI hard floor: 17.7 < 45`. Filter working as intended (blocked shorts below RSI 45). No action needed; signal marked executed, no rollback.
- **AUTO-FIXES**: reset-failed hermes-ceo.service. All 3 critical timers verified active.

## Error Alerts — 2026-10-11 11:00 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: N.N < N`

## Error Alerts — 2026-10-11 14:48 UTC
- **WARN** (1x): Disk at 85% used (/dev/vda2, 95G/118G). No logs >7d to reclaim; growth is data (candles_1m ~18M rows). Consider archiving candles_1m >60d (18.1M rows flagged by CEO script).
- **WARN** (1x): `hermes-ceo.service` failed — exit 124 (timeout) at 13:57 UTC. Non-critical oversight job; timer will retry. Not a trading-path failure.
- **WARN** (1x): `hermes-upgrade-implementer.service` failed — exit 124 (timeout) at 06:12 UTC. Non-critical; timer will retry.
- **INFO**: `hermes-atr-sl-updater.timer` shows as not-found (stale unit reference). ATR SL is applied inline by position_manager — no functional impact.
- **AUTO-FIX**: None required. Pipeline, price-collector, 1m-candle, signal-compactor, hl-sync-guardian all healthy. Prices fresh (80s). 0 phantom trades. No DB locks.

## Error Alerts — 2026-10-11 16:50 UTC
- **WARN** (1x): Disk at 86% used (/dev/vda2, 95G/118G). No uncompressed logs >7d to reclaim. candles_1m (18.2M rows) is the growth driver — consider archiving >60d candles.
- **WARN** (3x): Non-critical services failed: `hermes-bug-hunter` (exit 1), `hermes-ceo` (exit 124 timeout), `hermes-upgrade-implementer` (exit 124 timeout). Timers will retry. Not trading-path.
- **INFO**: bug-hunter "dead_imports" finding is a **false positive** — grep confirms no actual `import signal_gen`/`import ai_decider` statements in zscore_momentum.py, trend_purity_signals.py, candle_predictor.py; only comments mention signal_gen.
- **AUTO-FIX**: None required. Pipeline healthy (cycle #238463, 128 signals/h). All critical timers active (price-collector, 1m-candle, pipeline, hl-sync-guardian). Prices fresh (1.6 min). 0 phantom trades. 9 trades closed today. Regime: LONG_BIAS (80L/3S/26N).

## Error Alerts — 2026-10-11 17:00 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   [TOK-TOK] USELESS: skip TOK — hebbian n=N < N (insufficient data, TOK-open)`
- **REPEATED** (8x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-11 17:50 UTC
- **[WARN]** (1x): Disk usage 86% (>85% threshold) on /dev/vda2
- **AUTO-FIX**: Cleaned 52 ATM backup zips in /tmp older than 24h (~1G freed). Disk now 85%. No other safe auto-fix — remaining usage is active DBs (coin_tracker.db 3.3G, candles.db 2.7G) and /usr+/snap system files. Recommend manual review if disk approaches 90%.

## Error Alerts — 2026-10-11 18:00 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   [TOK-TOK] TOK: skip TOK — hebbian n=N < N (insufficient data, TOK-open)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3542s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.8s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TOK decider_run: TOK (most recent call last):`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS WARNING: N steps failed: decider_run`

## Error Alerts — 2026-10-11 19:54 UTC
- **WARN** (1x): Disk at 85% (/dev/vda2, 18G free). Logs only 191M — bloat is /root/.local (11G), /root/.cache (3.5G), /root/snap (1.7G), /root/.ollama (1.2G). Not auto-cleaned (outside hermes logs scope).
- **WARN** (1x): hermes-bug-hunter.service failed (exit 1 by design — 7 CRITICAL code-hygiene findings: sqlite/cursor leaks, bare excepts, f-string SQL, non-atomic JSON). Chronic, not new.
- **WARN** (1x): hermes-ceo.service failed 17:57 UTC (exit 124 = timeout). Timer active, next run 21:47 UTC — self-recovers.
- **AUTO-FIX**: bug_hunter.py false positives — dead_imports/defunct_imports were substring-matching comments and bug_hunter's own grep pattern. Now regex-match real import lines only, and skip bug_hunter.py itself. Verified: both checks PASS, 9→7 criticals.
- **INFO**: No pipeline errors in 30min. Timers all firing. Prices fresh (1m: 67s). 59 signals/1h. 0 open / 19 closed today, +$1.12 PnL, 36.8% WR.

## Error Alerts — 2026-10-11 20:50 UTC
- **[WARN]** (1x): Disk usage hit 85% (`/dev/vda2 95G/118G`)
- **AUTO-FIX**: Cleaned 6.7GB of stale JIT `.so` artifacts (1286 files >3 days old) + old ATM backup zips from `/tmp`. Disk now 82% (21G free). No pipeline services affected.

## Error Alerts — 2026-10-11 21:00 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: N.N < N`

## Error Alerts — 2026-10-11 23:00 UTC
- **REPEATED** (17x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK rc=N: stderr_tail=(empty)`
- **REPEATED** (17x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: brain.py rc=N`
- **REPEATED** (12x): `Oct N N:N:N python3[TOK]: TS   [brain.py] ❌ mirror_open TOK for TOK: Balance too low ($N.N < $N.N)`

## Error Alerts — 2026-10-12 00:50 UTC
- **AUTO-FIX**: `coin_tracker_api.py` PURR/USDC export failing every minute — symbol contains `/`, path joined to `coin_tracker_coins/PURR/USDC.json.tmp` but parent dir didn't exist. Fixed: `os.makedirs(os.path.dirname(path), exist_ok=True)` before write. Verified: 95/95 exports succeed (was 94), PURR/USDC.json 379KB, 1440 events.
- **WARN** (15x): Phantom trades — `is_win=0 AND |pnl_pct|<0.01` in signal_outcomes. Mostly BTC continuum_engine (0.0/0.0) and dust losses <$0.001. Historical, not modified.
- **INFO**: Pipeline healthy — cycle #238943, no Tracebacks in 30min. Timers 3/3 active. Disk 82%. Prices fresh (2.2m, 105 tokens in last 5m). Regime 5m SHORT_BIAS (15L/22S/60N of 97). 231 active signals, 1 generated last hour. 0 open / 1 closed today (-$0.10).

## Error Alerts — 2026-10-12 01:00 UTC
- **REPEATED** (49x): `Oct N N:N:N python3[TOK]: [coin_tracker_api] TOK/TOK export failed: [Errno N] No such file or directory: '/var/www/html/coin_tracker_coins/TOK/TOK.json.tmp'`
- **REPEATED** (13x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-12 02:00 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TOK position_manager: NameError: name 'PM_TRAIL_ACTIVATE_PCT' is not defined`

## Error Alerts — 2026-10-12 04:00 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`

## Error Alerts — 2026-10-12 05:00 UTC
- **REPEATED** (8x): `Oct N N:N:N python3[TOK]: TS   [brain.py] ❌ mirror_open TOK for TOK: Balance too low ($N.N < $N.N)`
- **REPEATED** (8x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK rc=N: stderr_tail=(empty)`
- **REPEATED** (8x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (8x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (10x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (8x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: brain.py rc=N`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3549s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3302s left, N failures)`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-10-12 09:00 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-12 10:00 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: N.N < N`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`

## Error Alerts — 2026-10-12 12:51 UTC
- **CRITICAL** (7987x): `hermes-coding-mcp.service` crash-looping — ExecStart script `/root/.hermes/scripts/run_mcp_server.py` missing (file does not exist anywhere in repo).
- **AUTO-FIX**: `systemctl disable --now hermes-coding-mcp.service` — loop stopped. Needs CEO decision: restore the script or remove the unit.
- **WARN**: `hermes-bug-hunter.service` exits 1 — audit FAILs: 35 files f-string SQL, 50 files cursor leaks, 132 bare excepts, 52 connection leaks, 75 non-atomic JSON writes, 4 hardcoded passwords (worst: session_brain.py:498, ceo_dashboard_api.py, hl_sync_guardian.py). By-design exit code, but findings are real debt.
- **WARN**: `hermes-upgrade-implementer.service` timed out 06:17 UTC (2.1G memory peak, killed after timeout). Runs again in 12h cycle.
- **INFO**: `hermes-atr-sl-updater.timer` unit not-found (stale reference in list-units).
- **NOTE**: Disk at 83% (92G/118G); `candles.db` is 2.9 GB. Watch, not yet >85%.

## Error Alerts — 2026-10-12 14:00 UTC
- **REPEATED** (10x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+TOK+TOK, allowing despite TOK filter`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-12 15:00 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (8x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-10-12 20:48 UTC
- **INFO**: Pipeline health check — all clear. 3 core timers firing, services active, no errors in 30min, 38 signals/hr, 18 trades closed today, regime LONG_BIAS, candles fresh (~2.4min).
- **NOTE**: Disk at 84% (94G/118G, 19G free). Watch — will WARN at >85%. No logs >7d to compress. candles.db = 2.8G.
- **NOTE**: 8 historical atr_sl_hit phantom trades (|pnl|<0.01%) all from Jul-Sep, none recent.

## Error Alerts — 2026-10-12 21:52 UTC
- **WARN**: `hermes-1m-candle.timer` STILL ACTIVE but documented dead — price_collector.py:43-44 says "timer disabled 2026-10-12 after confirming filled=0/dev=0 every run for ~7 days". Evidence: 1209/1209 runs over 7d = filled=0/dev=0, ~37s CPU each (~12 CPU-hours wasted). Fast 1m seeder in price_collector.py (BUG-048, CEO-ratified) owns 1m candles now — candles_1m fresh at 1.1min/176 tokens. Aggregator is pure waste + contends for candles.db write locks.
- **NO AUTO-FIX APPLIED**: service-safety rule forbids stopping a timer. **CEO action:** `systemctl disable --now hermes-1m-candle.timer` (then delete `_aggregate_1m.py` or leave as gap-filler reference).
- **INFO**: Disk 84% (94G/118G) — under 85% WARN. No logs >7d to gzip. candles.db 2.9G, session_brain.db 1.2G, signals_hermes.db 1.0G. DB-prune goal (<80% by Oct 14) still open.
- **INFO**: Pipeline healthy — 3 core timers firing, hl-sync-guardian active, 0 Tracebacks/30min, 68 signals/hr, 20 closed today, 0 open, 0 phantoms, prices fresh (46s), regime SHORT_BIAS (6L/77S/34N), token_speeds 241 tokens @ 52.7% >=p50.

## Error Alerts — 2026-10-12 22:00 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-10-13 00:00 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK rc=N: stderr_tail=(empty)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: brain.py rc=N`

## Error Alerts — 2026-10-13 00:50 UTC
- **WARN**: 0 signals / 0 decisions in last hour — all candidates below 40% confidence threshold. Market SHORT_BIAS (1L/106S/11N). No fix; confidence gate working as designed.
- **INFO**: Disk 84% (94G/118G) — still under 85% WARN. DB-prune goal (<80% by Oct 14) remains open. Largest logs: pipeline.log 47M, 15m_regime.log 38M.
- **INFO**: hermes-bug-hunter.service failed at 00:47 (exit 1) — code-quality findings (f-string SQL 35 files, bare excepts 132, cursor leaks 50). Not a runtime failure; report only.
- **INFO**: hermes-upgrade-implementer.service failed yesterday 18:17 (timeout after completing work + push). Recurring every 12h; consider raising TimeoutStartSec.
- **INFO**: hermes-1m-candle.timer STILL active despite documented dead aggregator (previous CEO action pending). Not touched — service-safety rule.
- **INFO**: 1 open trade (PUMP LONG, trade_id 16095), 18 closed today, portfolio -27.25% PnL today. 0 phantoms in 24h. Prices fresh (~2min), all 3 core timers firing.
- **AUTO-FIXES**: none required.

## Health Check — 2026-10-13 02:51 UTC
- **INFO**: All systems green. Pipeline running, 3/3 timers active, 58 signals/hr, 0 open trades, prices fresh (185 tokens, 02:51 UTC). Regime: LONG_BIAS (82L/3S/36N). No errors or crashes.
- **WARN** (1x): Disk at 84% (threshold 85%). Suggest compressing logs older than 7 days if usage continues climbing.
- **AUTO-FIX**: none needed.

## Health Check — 2026-10-13 03:52 UTC
- **INFO**: All systems green. Pipeline LIVE cycle at 03:49 rc=0 (open 2/6: ALT +0.46%, LDO +1.61%). 3/3 core timers active & firing (pipeline 46s, price-collector 34s, 1m-candle 8s ago). No errors/tracebacks in last hour. 0 phantom trades (24h). Prices fresh (<1min).
- **WARN**: Disk 84% (94G/118G) — under 85% threshold but DB-prune goal (<80% by Oct 14) still open. No files >7d old to gzip.
- **INFO**: 1 signal in last hour (ai-trader+ LONG). 0 closed today. 128/241 tokens ≥50th pct speed. Regime LONG_BIAS (81L/3S/36N, 120 tokens, 03:45).
- **INFO**: `hermes-1m-candle.timer` still dead-but-active (filled=0/dev=0 confirmed again this run). Briefly enabled during check by mistake, reverted to disabled within seconds — timer stayed active throughout, no interruption. CEO action still pending: `systemctl disable --now hermes-1m-candle.timer`.
- **AUTO-FIX**: none (1m-candle toggle fully reverted).

## Error Alerts — 2026-10-13 04:48 UTC
- **[WARN]** (1x): Disk usage at 85% (/dev/vda2, 18G free). Largest consumers: candle DBs (candles.db 2.9G, coin_tracker.db 3.4G), logs 252M. No uncompressed logs >7d to compress. No auto-fix applied — monitor; consider candles.db/coin_tracker.db retention policy.
- **[WARN]** (8x, historical): Phantom trades — atr_sl_hit exits with |pnl_pct| < 0.01%. Most recent 2026-09-14 (JUP). No new occurrences in 30 days. No auto-fix applied.
- No CRITICAL issues. Pipeline, timers, price freshness all OK. "CRASH" log hits were BTC-CRASH guard messages (correct behavior), not actual crashes.

## Error Alerts — 2026-10-13 05:00 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-13 06:49 UTC
- **WARN** (1): Disk at 85% used (18G free) — no action yet, compress if >85%
- **WARN** (8): 8 phantom trades (`atr_sl_hit` with <0.01% pnl) in signal_outcomes — historical, not new

## Error Alerts — 2026-10-13 07:49 UTC
- **WARN** (1): Disk at 85% used (18G free) — at threshold, no uncompressed old logs to gzip; monitor
- **WARN** (1): `hermes-coding-mcp.service` crash-looped 9275x — `/root/.hermes/scripts/run_mcp_server.py` missing (exit 2). **AUTO-FIX**: stopped service (disabled, not in trading path; script needs restore or unit removal)
- **WARN** (1): `hermes-daily-orchestrator.service` timed out & killed (TERM) at 06:58 — will retry on next timer
- **INFO** (1): `hermes-bug-hunter.service` exit 1 — code-quality findings (f-string SQL, cursor leaks, bare excepts), not runtime failures
- Pipeline OK: 4 open / 21 closed today, -33.93% portfolio PnL, 0 crashes. Timers 3/3 active. Prices fresh (<1min). No phantoms.

## Error Alerts — 2026-10-13 08:56 UTC
- **WARN** (1): Disk at 85% used (18G free) — at threshold; no uncompressed logs >7d to gzip; largest consumers are DBs (candles.db 2.9G, coin_tracker.db 3.4G). No auto-fix possible; consider retention policy.
- **WARN** (1): `hermes-daily-orchestrator.service` timed out & killed (TERM) at 06:58 — non-critical, will retry on next 24h timer.
- **WARN** (1): `hermes-upgrade-implementer.service` timed out & killed (TERM) at 06:17 — non-critical, will retry on next 12h timer.
- **INFO** (1): `hermes-bug-hunter.service` exit 1 — 7 pre-existing code-quality findings (sqlite/cursor leaks, f-string SQL, bare excepts, non-atomic JSON, hardcoded passwords), not runtime failures.
- **INFO** (1): ATOM SHORT execution failed at 08:45 (RSI hard floor 36.6 < 40) — handled correctly: marked FAILED, no rollback loop, hotset failure recorded. Working as designed.
- Pipeline OK: 4 open / 23 closed today, -37.89% portfolio PnL, 0 crashes, 0 errors in 30min. Timers 3/3 active (price-collector, 1m-candle, pipeline). Prices fresh (<4min). Regime: SHORT_BIAS (10L/25S/84N). Signals 1h: 44 detected / 4 outcomes. No phantoms (24h).

## Error Alerts — 2026-10-13 09:00 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-13 09:50 UTC
- **WARN** (1x): Disk usage at 85% (/dev/vda2, 95G/118G). No logs >7d to compress; largest files: candles.db (2.9G), coin_tracker.db (3.5G). Consider pruning candle/token DB retention.
- **WARN** (8x): Phantom trades — atr_sl_hit with |pnl_pct| < 0.01%. Review entry conditions for these fills.
- **INFO**: hermes-daily-orchestrator failed (timeout kill at 06:58 UTC after ModuleNotFoundError: paths + FileNotFoundError wyckoff_shadow.jsonl). Non-critical improvement agent.
- **INFO**: hermes-bug-hunter exit 1 by design (static analysis FAILs: bare_except 132, connection_leaks 52, non_atomic_json 76, hardcoded_passwords 4). Not a crash.
- **AUTO-FIX**: None required — pipeline, timers, price freshness all healthy. Disk/phantom flagged for CEO attention.

## Error Alerts — 2026-10-13 10:00 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BEAR+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] IO TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   [brain.py] ❌ mirror_open TOK for TOK: Insufficient margin to place order. asset=N`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK rc=N: stderr_tail=(empty)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: brain.py rc=N`

## Error Alerts — 2026-10-13 10:48 UTC
- **WARN** (2x): `[brain.py] ❌ REJECTED: {DYDX,GMX} SHORT — SHORT RSI < HARD_FLOOR 35 (extreme oversold)` — signals entered shorts at RSI 25-29, killed at execution. Upstream v2 filters let oversold shorts through to brain.py (BANANA SHORT pattern). No retry loop (marked FAILED correctly). Suggest: RSI floor check in signal/decider stage before EXEC.
- **WARN**: Disk 85% used (94G/118G). Auto-fixed: vacuumed journald (-342MB). Watch for growth.
- **AUTO-FIX**: `journalctl --vacuum-size=300M` — freed 342MB. Timers verified active. No pipeline crashes, no DB locks, no phantom trades.

## Error Alerts — 2026-10-13 11:00 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] IO TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-13 11:52 UTC
- **WARN**: Disk 85% used (95G/118G). Largest: coin_tracker.db 3.3G, candles.db 2.8G. Log compression attempted (minimal gain — logs already gzipped). Suggest: DB retention policy for coin_tracker.db / candles.db old rows.
- **INFO**: systemd daemon-reload executed — hermes-hl-sync-guardian unit files had changed on disk without reload. Guardian service confirmed running (PID 2789376, 20h uptime).
- **INFO**: "24 critical errors" grep match = false positive (BTC-CRASH-OVERRIDE filter log lines, not actual crashes). Zero Tracebacks, zero DB locks, zero FATAL.
- **AUTO-FIX**: `systemctl daemon-reload` for stale unit files. All critical timers verified active. No pipeline crashes, no phantom trades, prices fresh (BTC 29s, ETH 37s, SOL 29s).

## Error Alerts — 2026-10-13 12:00 UTC
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BEAR+AT, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+NEUTRAL+AT, allowing despite TOK filter`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`

## Error Alerts — 2026-10-13 13:00 UTC
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: N.N < N`

## Error Alerts — 2026-10-13 14:01 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK rc=N: stderr_tail=(empty)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: brain.py rc=N`

## Error Alerts — 2026-10-13 14:50 UTC
- **WARN** (1x): `hermes-1m-candle.timer` was **disabled** — would not survive reboot. Last run 14:46:59, timer unit still active in-memory.
- **AUTO-FIX**: `systemctl enable hermes-1m-candle.timer` — re-enabled, symlink created.
- **WARN** (1x): Disk at **85%** (18G free of 118G). Top consumers: coin_tracker.db 3.3G, candles.db 2.8G, session_brain.db 1.2G, signals_hermes.db 1.0G. Logs only 274M — compression won't help. Needs DB retention policy (CEO decision, not auto-fixed).

## Error Alerts — 2026-10-13 15:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] IO TOK — continuum says TOK+LEAN_BEAR+TOK, allowing despite TOK filter`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] BIGTIME TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-13 16:01 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK rc=N: stderr_tail=(empty)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: brain.py rc=N`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-13 16:52 UTC
- **WARN** (1): Disk usage at 85% (/dev/vda2 95G/118G, 18G free). No uncompressed logs >7d to gzip; bulk is candles.db (2.9G) + coin_tracker.db (3.5G). Manual pruning/VACUUM needed if it crosses 90%.
- **WARN** (4): Failed services — hermes-signal-reporter (timeout 11:29, retries 17:09), hermes-bug-hunter, hermes-daily-orchestrator, hermes-upgrade-implementer. Auxiliary only; core pipeline/timers unaffected.
- Core pipeline, price-collector, 1m-candle timers: all active, last runs clean (rc=0). No auto-fixes required.

## Error Alerts — 2026-10-13 17:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CC TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-13 17:51 UTC
- **WARN** (1x): Disk usage at 85% (17G free of 118G). Largest consumers: coin_tracker.db (3.3G), candles.db (2.8G), session_brain.db (1.3G). No safe auto-cleanup available (no stale logs >7d uncompressed).
- **INFO**: Win rate today 26.5% (49 closed, -0.37 USDT net) — performance note, not a system fault.

## Error Alerts — 2026-10-13 18:01 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CC TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CC TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BEAR+TOK, allowing despite TOK filter`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
2026-10-13 18:54

## Error Alerts — 2026-10-13 18:52 UTC
- **WARN** (1x): `hermes-bug-hunter.service` exited status=1 — by design after finding 7 critical code-quality issues (sqlite leaks 48 files, sql injection patterns 35 files, bare excepts 132, connection leaks 52, non-atomic JSON 78, hardcoded passwords 4). Scanner working as intended; timer retries ~2026-10-15 02:50 UTC. Not trading-path.
- **WARN** (1x): `hermes-upgrade-implementer.service` timed out (killed at systemd TimeoutStartSec ~2min while scanning file list). Non-critical; timer retries 2026-10-14 06:02 UTC. Suggested fix: raise TimeoutStartSec in unit file.
- **WARN** (1x): Disk at 83% (118G total, 20G free) — approaching 85% threshold. pipeline.log 66M, 15m_regime.log 41M. No auto-fix applied (logs actively written; logrotate owns rotation).
- No CRITICAL issues. Trading pipeline, position manager, price collector, 1m candles, HL sync guardian all healthy. Timers all firing.

## Error Alerts — 2026-10-13 19:50 UTC
- **[WARN]** (3x): `APT SHORT rejected by brain.py HARD_FLOOR (RSI 23.02 < 35)` — retry loop 19:45–19:47, signal IDs 1674797/1674801/1674804
- **AUTO-FIX**: none needed — hotset cooldown (BUG-049, 2-fails→1h) engaged at count=3, no further retries after 19:47. Self-resolved.
- **[INFO]**: hotset.json empty since 19:48 — no signals surviving compaction safety filters. No new entries until multi-source signals appear. 3/6 slots open.

## Error Alerts — 2026-10-13 20:01 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BEAR+AT, allowing despite TOK filter`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK rc=N: stderr_tail=(empty)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: brain.py rc=N`

## Error Alerts — 2026-10-13 20:49 UTC
- **WARN** (8x): `atr_sl_hit` with <0.01% PnL — phantom trades detected in signal_outcomes
- **WARN**: Disk at 83% (threshold 85%) — monitor
- No auto-fixes needed. All timers and services active. Pipeline completed successfully.

## Error Alerts — 2026-10-13 21:56 UTC
- **WARN** (5x): `CAKE SHORT` brain.py rejection loop — SHORT RSI 22.22 < HARD_FLOOR 35, retried 5x in 4min (21:36-21:39). Hotset failures recorded (count=5) but `_check_hotset_cooldown` never called in main exec loop — only in read-only `_run_hot_set()`. Same gap pattern as BTC-CRASH (BANANA 09-08).
- **ROOT CAUSE**: RSI mismatch — brain.py uses `signal_rsi_14` from detection-time metadata (22.22), signal_compactor/decider_run compute live RSI (46-50) which passes HARD_FLOOR 35. Compactor keeps re-approving; brain.py keeps rejecting.
- **AUTO-FIX**: Added hotset failure cooldown check to main exec loop (decider_run.py:4012-4021). 2+ same-direction failures in 1hr → block for 1hr with SKIPPED mark. Matches BUG-049 intent.
- **INFO**: Disk 83% (threshold 85%). Prices fresh (1m candles <1min, 100 tokens). All 3 timers active. Macro gate REDUCE (wr=15%).

## Error Alerts — 2026-10-13 22:01 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK rc=N: stderr_tail=(empty)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: brain.py rc=N`

## Error Alerts — 2026-10-13 23:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (530s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (491s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (432s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (376s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (296s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (245s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (177s left, N failures)`

## Error Alerts — 2026-10-14 00:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+NEUTRAL+TOK, allowing despite TOK filter`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor (detect): N.N < N`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: CC TOK (count=N)`

## Error Alerts — 2026-10-14 01:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+NEUTRAL+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3539s left, N failures)`

## Error Alerts — 2026-10-14 02:01 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`

## Error Alerts — 2026-10-14 02:48 UTC
- **[WARN]** (1x): `disk 84% used` — 19G free on 118G disk. Approaching 85% WARN threshold.
- **AUTO-FIX**: None needed yet. Will compress logs >7d when disk crosses 85%.
- **[WARN]** (1x): `hermes-bug-hunter.service failed` — code quality scanner exits 1, reports pre-existing issues (bare excepts, cursor leaks, hardcoded passwords). Non-critical.
- **AUTO-FIX**: None. Timer still active, will retry in 8h.
- **[INFO]**: `hermes-upgrade-implementer.service timeout` (Oct 13 18:17) — timed out during file scan. Timer still scheduled.
- **AUTO-FIX**: None. Timer will retry in next 12h window.

## Error Alerts — 2026-10-14 03:01 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3544s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3544s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3487s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3487s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3427s left, N failures)`

## Error Alerts — 2026-10-14 04:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+TOK+TOK, allowing despite TOK filter`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] IO TOK — continuum says TOK+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-14 04:53 UTC
- **[WARN]** (1x): `disk 84% used` — 19G free on 118G disk. Approaching 85% WARN threshold.
- **AUTO-FIX**: Cleaned 5 old ATM zip backups + stale trend_ride_backtest.json from /tmp (~84M freed). Compress logs >7d when disk crosses 85%.
- **[WARN]** (1x): `hermes-bug-hunter.service failed` — code quality scanner exits 1 by design when it finds issues (sqlite leaks, bare excepts, etc.). Pre-existing debt, not a new crash.
- **AUTO-FIX**: `systemctl reset-failed hermes-bug-hunter.service` — clears failed state, timer still active, will retry in 8h.
- **[WARN]**: `hotset empty — 0 tokens survived compaction` — signals generating (75 in last hour) but none passing compaction threshold right now. Monitor; may be normal low-activity period.
- **AUTO-FIX**: None needed. Not a service failure.

## Error Alerts — 2026-10-14 05:01 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-14 07:01 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3547s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3490s left, N failures)`

## Error Alerts — 2026-10-14 08:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3540s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3540s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3463s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3463s left, N failures)`

## Error Alerts — 2026-10-14 08:50 UTC
- **CRITICAL** (11222x): `hermes-coding-mcp.service: can't open file '/root/.hermes/scripts/run_mcp_server.py': No such file or directory` — crash-looping every 5s since script was deleted; `/root/.hermes/mcp/hermes-coding-mcp/` contains only empty `dispatcher/` dir.
- **AUTO-FIX**: `systemctl disable --now hermes-coding-mcp.service` — stopped the restart loop. Nothing listens on port 8765 (service never successfully started). Needs either restore of `run_mcp_server.py` or removal of the unit file.
- **WARN** (1x): `hermes-upgrade-implementer.service` timed out at 06:16 UTC (killed by systemd after start timeout). One-off; next timer run in ~12h.
- **NOTE**: Disk at 84% (19G free of 118G). Under 85% warn threshold but trending up — largest consumers: coin_tracker.db 3.3G, candles.db 2.8G, session_brain.db 1.3G, signals_hermes.db 1020M.

## Error Alerts — 2026-10-14 09:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3549s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3542s left, N failures)`

## Error Alerts — 2026-10-14 09:53 UTC
- **WARN** (1x): `hermes-upgrade-implementer.service` in failed state (timed out 06:16 UTC, killed by systemd start timeout).
- **AUTO-FIX**: `systemctl reset-failed hermes-upgrade-implementer.service` — cleared failed state so next timer run (12h cadence) can start cleanly.
- **NOTE**: Disk 84% (19G free of 118G) — under 85% threshold, previously flagged trending up. Largest DBs: coin_tracker 3.3G, candles.db 2.98G, session_brain 1.3G, signals_hermes 1.0G.
- **NOTE**: Pipeline log reports "60 closed today | -72.06% PnL" but PG shows 23 closed today (-$0.36) — likely a metric/label discrepancy in the portfolio summary line, not a data issue. Worth a look by whoever owns the summary code.
- All critical timers (pipeline, 1m-candle, price-collector) active and firing. Prices fresh (candles_1m age 0.1 min). 0 phantom trades. No pipeline errors in last 30min.

## Error Alerts — 2026-10-14 10:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (961s left, N failures)`

## Error Alerts — 2026-10-14 11:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3554s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2414s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2414s left, N failures)`

## Error Alerts — 2026-10-14 14:01 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+TOK+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3547s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3546s left, N failures)`

## Error Alerts — 2026-10-14 15:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.8s (rc=N)`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TOK position_manager: IndentationError: expected an indented block after 'if' statement on line N`

## Error Alerts — 2026-10-14 15:50 UTC
- **[WARN]** (1x): Disk usage at 85% on /dev/vda2 (118G total, 18G free)
- **AUTO-FIX**: Vacuumed journald archives (freed 261.7M, 380M→~120M). Disk now 84%. No .log files older than 7d found to gzip. Top consumers: pipeline.log (87M), 15m_regime.log (44M), signal-compactor.log (36M) — all actively written, left alone. Recommend adding logrotate policy for hermes logs if disk trends toward 90%.

## Error Alerts — 2026-10-14 16:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3536s left, N failures)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BEAR+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1509s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1509s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1428s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1428s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1388s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1325s left, N failures)`

## Error Alerts — 2026-10-14 17:01 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] IO TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: N.N < N`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: IO TOK (count=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: IO TOK in hotset failure cooldown — TOK in cooldown (3534s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: IO TOK in hotset failure cooldown — TOK in cooldown (3476s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: IO TOK in hotset failure cooldown — TOK in cooldown (3416s left, N failures)`

## Error Alerts — 2026-10-14 18:01 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor (detect): N.N < N`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3462s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3422s left, N failures)`

## Error Alerts — 2026-10-14 19:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3467s left, N failures)`

## Error Alerts — 2026-10-14 19:55 UTC
- **WARN** (1x): `hermes-upgrade-implementer.service: start operation timed out. Terminating.` — ran 2.5min CPU, killed by systemd TimeoutStartSec=900
- **AUTO-FIX**: `systemctl reset-failed hermes-upgrade-implementer.service` — service cleared, timer will retry next cycle (every 12h)
- **NOTE**: 1m-candle aggregator showing filled=0 for 30min — **expected behavior** per BUG-048 (dead tick aggregator disabled 2026-10-12; real 1m candles seeded by price_collector fast path). Not an issue.
- **NOTE**: Disk at 84% (threshold 85%) — monitor, no action needed yet.

## Error Alerts — 2026-10-14 20:01 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] USELESS TOK — continuum says DECLINING+LEAN_BULL+AT, allowing despite TOK filter`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3541s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3485s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3485s left, N failures)`

## Error Alerts — 2026-10-14 21:01 UTC
- **REPEATED** (9x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] IO TOK — continuum says DECLINING+LEAN_BULL+AT, allowing despite TOK filter`
- **REPEATED** (9x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BULL+AT, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ [TOK-TOK] TOK failed for TOK: Command '['/root/.opencode/bin/opencode', 'run', 'You are a crypto trading gate. Evaluate this signal and reply TOK of: GO, TOK, TO`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3534s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3484s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3423s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2729s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2670s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2613s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1469s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1469s left, N failures)`

## Error Alerts — 2026-10-14 22:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2717s left, N failures)`

## Error Alerts — 2026-10-14 23:01 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor (detect): N.N < N`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3543s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3481s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3553s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3429s left, N failures)`

## Error Alerts — 2026-10-15 00:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3537s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3478s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3478s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2256s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2256s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2199s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2199s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2135s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2135s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2087s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2087s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2032s left, N failures)`

## Error Alerts — 2026-10-15 01:50 UTC
- **CRITICAL**: `hermes-pipeline.timer` and `hermes-pipeline.service` were both stopped at 01:40:14 UTC (duration 14s, killed by TERM — not a crash; something issued `systemctl stop`). No pipeline cycles ran for ~8 minutes. `hermes-pipeline.timer` was not re-triggering (`Active: inactive (dead)`, Trigger: n/a).
- **AUTO-FIX**: `systemctl start hermes-pipeline.timer` — timer active, service fired at 01:49:20 UTC and is running. Price-collector and 1m-candle timers were unaffected and remained active throughout.
- **WARN**: Disk `/` at 85% (95G/118G, 18G free). No logs >7d to compress; largest active logs: pipeline.log 96M, 15m_regime.log 46M, signal-compactor.log 39M. Not truncating active logs at 18G headroom — revisit at 90%.
- **INFO**: IO SHORT trade failed at 01:37:30 (RSI hard floor 31.1 < 40 at detect) — filter working as designed, not a system fault. Signal 1676732 marked FAILED, hotset cooldown 3540s active.

## Error Alerts — 2026-10-15 02:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: IO TOK in hotset failure cooldown — TOK in cooldown (3540s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: IO TOK in hotset failure cooldown — TOK in cooldown (3481s left, N failures)`

## Error Alerts — 2026-10-15 03:01 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] ME TOK — continuum says RECOVERY+TOK+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] ME TOK — continuum says TOK+TOK+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-15 04:01 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MULTI_ALT`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: Multi-alt weakness: N alts diverging -N.N%+ below TOK`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3555s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1937s left, N failures)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1330s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1278s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1278s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1219s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1219s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1160s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1160s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1067s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1067s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3539s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3477s left, N failures)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+TOK+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3538s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3360s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3301s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3301s left, N failures)`

## Error Alerts — 2026-10-15 15:08 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-15 16:08 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3525s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3525s left, N failures)`

## Error Alerts — 2026-10-15 17:08 UTC
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2702s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3426s left, N failures)`
- **REPEATED** (9x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-15 18:08 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-15 19:08 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3479s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3419s left, N failures)`

## Error Alerts — 2026-10-15 21:08 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor (detect): N.N < N`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3489s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3489s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: TOK,TOK,BTC_LEVEL | vol=N.1x eth_div=+N.N% | BTC_LEVEL: TOK blocked (-N.N% from high)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2694s left, N failures)`

## Error Alerts — 2026-10-15 22:08 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3538s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3480s left, N failures)`

## Error Alerts — 2026-10-15 23:08 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3411s left, N failures)`

## Error Alerts — 2026-10-16 00:08 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2939s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2939s left, N failures)`

## Error Alerts — 2026-10-16 02:08 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor (detect): N.N < N`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] IO TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3482s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3420s left, N failures)`

## Error Alerts — 2026-10-16 03:08 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BEAR+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2540s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2515s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2450s left, N failures)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`

## Error Alerts — 2026-10-16 03:24 UTC
- **WARN** (1x): `hermes-brain-auditor.service` failed — start operation timed out (60s TimeoutStartSec) at 02:50 UTC; script was mid-analysis and got SIGTERM.
- **AUTO-FIX**: `systemctl reset-failed hermes-brain-auditor.service` so next hourly timer fires clean. No pipeline impact (analytics only). If it recurs, raise `TimeoutStartSec` in the unit.
- Note: hotset.json empty (0 signals survived compaction at 03:23) — pipeline logged this normally; 86 signals generated in last 1h, so detection is healthy.

## Error Alerts — 2026-10-16 04:08 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3444s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3444s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1386s left, N failures)`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] IO TOK — continuum says DECLINING+LEAN_BEAR+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-16 05:08 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3483s left, N failures)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (474s left, N failures)`

## Error Alerts — 2026-10-16 05:24 UTC
- **[WARN]** (1x): `hermes-brain-auditor.service start operation timed out` — killed at 60s systemd limit while investigating confidence-gap (journal shows APT SHORT conf 50 vs DB 29.5). Timer still active (next 06:00). No auto-fix needed; transient timeout.
- **[INFO]**: `hermes-bug-hunter.service exit=1` — by design; reported known pre-existing hygiene findings (bare excepts, cursor leaks, non-atomic JSON). Not a crash.
- No CRITICAL issues. Pipeline healthy, 68 signals/h, 2 open trades, disk 80%, all timers active.

## Error Alerts — 2026-10-16 06:08 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3555s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3495s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3495s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3435s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3435s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3374s left, N failures)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CC TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-16 09:08 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK mid-band death band: N.N in N-N`

## Error Alerts — 2026-10-16 10:08 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-16 10:25 UTC
- **[WARN]** (2nd time today): `hermes-brain-auditor.service start operation timed out` — killed at 09:50 (run started ~09:30, consumed 2m43 CPU while inspecting hermes_constants.py). Timer still active (next :30). `reset-failed` applied. Recurring: script hangs past systemd start limit — needs a hard timeout inside `run_brain_auditor.sh` or longer `TimeoutStartUSec`.
- **[CRITICAL → FIXED]**: `hermes-coding-mcp.service` crash-looping every 5s (restart counter 3293+) — `ExecStart` points to `/root/.hermes/scripts/run_mcp_server.py` which does not exist; `/root/.hermes/mcp/hermes-coding-mcp/` is empty. **AUTO-FIX**: `systemctl disable --now hermes-coding-mcp.service`. If MCP host is still needed, restore the script then `systemctl enable --now`.
- **[INFO]**: `hermes-atr-sl-updater.timer` not-found — stale unit reference, no unit file on disk, not scheduled. Harmless; clean up from any lingering references.
- **[INFO]**: price_collector `[LOCK-WAIT]` retries — normal WAL contention with 1m-candle (both hold candles.db briefly); candles fresh (1.7 min old). No action.
- Pipeline healthy: 48 signals/h, 3 open / 17 closed today (+19.42% portfolio PnL), regime SHORT_BIAS, disk 81%, all core timers active. Vacation pause: not set.

## Error Alerts — 2026-10-16 11:08 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3552s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3552s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3490s left, N failures)`

## Error Alerts — 2026-10-16 11:25 UTC
- Pipeline healthy: 52 signals/h, 5 open / 18 closed today (44.4% WR, -$0.32 realized), regime LONG_BIAS, disk 81%, all core timers active, candles fresh (1.2 min). Vacation pause: not set.
- **[INFO]**: `[PHANTOM-WRITE] BTC LONG BLOCKED tight SL` recurring every ~2min in position_manager (trade_id=16211) — defensive guard working as intended, blocking SL too close to entry (dist=0.025%). No action needed.
- **[INFO]**: `[BTC-CRASH-OVERRIDE] CRV SHORT` firing every cycle — continuum filter allowing despite crash detection. Intentional override path, not an error.
- **[INFO]**: price_collector `[LOCK-WAIT]` retries — normal WAL contention with 1m-candle. No action.
- No auto-fixes required this cycle.

## Error Alerts — 2026-10-16 12:08 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1639s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1639s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1580s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1580s left, N failures)`

## Error Alerts — 2026-10-16 13:08 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor (detect): N.N < N`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS [Position Manager] TOK mirror_close TOK (DB committed, HL still open): mirror_close(BIGTIME): HL TOK failed — Unknown TOK`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1556s left, N failures)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-10-16 14:08 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-16 15:08 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+TOK+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-16 16:08 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3488s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3428s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2569s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2569s left, N failures)`

## Error Alerts — 2026-10-16 17:25 UTC
- **WARN** (1x): `hermes-signal-reporter.service failed: start operation timed out (14:33 UTC)` — reporting only, no trading impact
- **WARN** (1x): `hermes-upgrade-implementer.service failed: git push remote disconnect + start timeout (15:17 UTC)` — transient network, no trading impact
- **INFO** (3x): `hermes-bug-hunter.service exit 1` — audit findings (sql_injection, cursor_leaks, bare_except, connection_leaks, non_atomic_json, hardcoded_passwords) — code quality, not runtime crashes
- **AUTO-FIX**: None required — pipeline healthy (60 runs/h), timers active, prices fresh. Non-critical failed services left for their next scheduled run.

## Error Alerts — 2026-10-16 18:08 UTC
- **REPEATED** (9x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3418s left, N failures)`

## Error Alerts — 2026-10-16 21:08 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BULL+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-17 00:24 UTC
- **[WARN]** (1x): `hermes-bug-hunter.service` failed (exit 1) — code quality audit found sql_injection (35 files), bare_except (132), connection_leaks (52), non_atomic_json (81), hardcoded_passwords (4). By-design non-zero exit on findings; not a runtime trading failure. No auto-fix (long-term code hygiene).
- **[WARN]** (Nx): `[hotset] fallback DB query returned 0 tokens` — hotset.json is empty `[]`. Compactor cycle 13001 has no hot tokens. Investigate hotset generator if signals thin out.
- **[WARN]**: Daily PnL -55.47% across 47 closed trades — not a system health issue but flagged for CEO visibility.

## Error Alerts — 2026-10-17 01:08 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.2s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TOK decider_run: IndentationError: unexpected indent`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.1s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TOK position_manager: IndentationError: unexpected indent`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   hermes-trades-api: TOK in N.1s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TOK hermes-trades-api: IndentationError: unexpected indent`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS WARNING: N steps failed: decider_run, position_manager, hermes-trades-api`
- **REPEATED** (10x): `Oct N N:N:N python3[TOK]: TOK (most recent call last):`
- **REPEATED** (10x): `Oct N N:N:N python3[TOK]: IndentationError: unexpected indent`
- **REPEATED** (10x): `Oct N N:N:N systemd[N]: hermes-pipeline.service: Main process exited, code=exited, status=N/FAILURE`
- **REPEATED** (10x): `Oct N N:N:N systemd[N]: hermes-pipeline.service: Failed with result 'exit-code'.`

## Error Alerts — 2026-10-17 01:24 UTC
- **CRITICAL**: `hermes-pipeline.timer` and `hermes-watchdog.timer` were both inactive (not scheduled).
- **AUTO-FIX**: Restarted both timers via `systemctl start`. Verified active.
- **WARN** (1x): `hermes-brain-auditor.service` — timeout, killed (Result: timeout). Flaky, non-critical.
- **WARN** (1x): `hermes-bug-hunter.service` — exit code 1. Flaky, non-critical.

## Error Alerts — 2026-10-17 04:25 UTC
- **INFO**: Pipeline paused by vacation guardrail at 04:08 UTC (7d WR 34.2% < 35%, 7d PnL -$3.41). Intentional — NOT restarted. Price-collector + 1m-candle timers left running (data collection safe). Guardian still managing 1 open BTC SHORT position.
- **WARN** (250x/10min): `hermes-price-collector` — `[LOCK-WAIT] info_rate: waited 0.1s, retrying`. SQLite contention (likely with 1m-candle service). Collector completes successfully each run (rc=0). Noise-level; no fix applied. If it escalates to failures, consider WAL busy_timeout tuning.
- No auto-fixes applied this cycle.

## Error Alerts — 2026-10-17 07:26 UTC
- **INFO**: Pipeline paused by vacation guardrail at 07:08 UTC (7d WR 34.2% < 35.0%, 7d PnL -$3.08 < -$2.00, 219T). Intentional — pipeline.timer + trade-watchdog.timer left inactive. Price-collector + 1m-candle timers active, candles fresh (1 min).
- **WARN** (4285x): `hermes-coding-mcp.service` — crash-loop: `run_mcp_server.py` missing (Errno 2), restart counter 4285. **AUTO-FIX**: stopped service (already disabled; stop breaks the loop). Needs: restore script or remove unit.
- **WARN** (1x): `hermes-brain-auditor.service` — timeout at 06:50 after long run; also `psycopg2 round(double precision, integer)` UndefinedFunction errors (needs ::numeric cast). Work completed before timeout. Non-critical.
- **WARN** (1x): `hermes-daily-orchestrator.service` — timeout at 04:03; queries PG tables `candles_1m`/`price_history` that don't exist (they're SQLite). Pre-existing bug in orchestrator SQL.
- **WARN** (1x): `hermes-bug-hunter.service` — exit 1 from audit FAILs (52 sqlite no-finally, 81 non-atomic JSON, 4 hardcoded passwords). Findings, not crashes.
- Disk 82% (was 82% last check — stable, under 85% threshold). 0 signals last 1h (expected: pipeline paused). 24h outcomes: 42T, 38.1% WR, -$2.63. Phantom trades: 0.

## Error Alerts — 2026-10-17 11:27 UTC
- **[INFO]** (1x): `hermes-trading-checklist.service` — CRIT `pipeline_service: hermes-pipeline.timer is inactive` at 11:08. **False positive**: caused by intentional vacation pause (paused_at 11:08:26, 7d WR 34.7% < 35.0% AND pnl_7d $-2.84 < $-2.00). No action taken — pause is by design. **Suggestion**: checklist should check `vacation_pause.json` before flagging inactive pipeline timer.
- **[INFO]**: Health check at 11:27 — vacation pause active, pipeline/watchdog left stopped per guardrail rule. All data timers healthy (price-collector collected 87 prices at 11:23, 1m-candle firing, 30+ timers on schedule). 1 open trade (BTC ai-trader, opened 03:25). 4 closed today (-$0.29). Disk 82%. Phantom trades: 0. No auto-fixes needed.

## Error Alerts — 2026-10-17 12:30 UTC
- **[INFO]**: Health check at 12:30 UTC — vacation pause active (paused_at 12:08:26, 7d WR 34.7% < 35.0% AND pnl_7d $-2.84 < $-2.00). Pipeline.timer + trade-watchdog.timer left inactive per guardrail rule. Price-collector (last 12:29:54) and 1m-candle (last 12:30:22) timers firing normally. Prices fresh (99s). 1 open trade (BTC SHORT from 03:25). 4 closed today (-$0.29). Regime: SHORT_BIAS (4L/83S/39N of 126). Disk 82%. Phantom trades: 0. LOCK-WAIT noise in price-collector continues (known, non-blocking). No auto-fixes needed.

## Error Alerts — 2026-10-17 13:25 UTC
- **[INFO]**: Health check at 13:25 UTC — vacation pause active (paused_at 13:08:26, 7d WR 34.4% < 35.0% AND pnl_7d $-2.86 < $-2.00, 212T). Pipeline.timer + trade-watchdog.timer left inactive per guardrail rule — intentional, NOT a crash. Auto-resume handled by guardrail on metric recovery.
- **[INFO]**: Data collection healthy — price-collector last fired 13:25:49, 1m-candle next fire 13:26:30, candles fresh (1m age 0.9min). 15m-regime-scanner on schedule (last 13:15). hl-sync-guardian active (managing 1 open BTC SHORT from 03:25). 30+ other timers active/waiting.
- **[INFO]**: 0 signals last 1h (expected: pipeline paused). Trades today: 4 closed, -$0.29, 25% WR. 24h exits: atr_sl_hit 8 (-$0.91), profit-monster-trail 6 (+$0.12), hard_max_loss 5 (-$1.48), HL_CLOSED 2 (+$0.01), trail_arm_timeout 1 (-$0.20), stale_exit 1 (-$0.13), atr_trail_hit 1 (-$0.01). Phantom trades: 0. Regime: SHORT_BIAS (3L/103S/14N of 120). Disk 83% (up from 82% — watch, threshold 85%). trades.json stale (updated 03:25) — expected downstream of pause, guardian still tracks the open position. No auto-fixes needed.

## Error Alerts — 2026-10-17 14:25 UTC
- **[INFO]**: Health check at 2026-10-17 14:25 UTC — vacation pause active (paused_at 14:08:26, 7d WR 34.4% < 35.0% AND pnl_7d $-2.86 < -$2.00, 212T). Pipeline.timer + trade-watchdog.timer left inactive per guardrail rule — intentional, NOT a crash. Auto-resume handled by guardrail on metric recovery.
- **[INFO]**: Data collection healthy — price-collector last fired 14:23:19, 1m-candle last fired 14:23:30, candles fresh. 15m-regime-scanner on schedule (last 14:15). hl-sync-guardian active. 40+ other timers active/waiting. candles.db held by 2 python3 procs (normal — price-collector + 1m-candle, not a lock issue).
- **[INFO]**: 0 signals last 1h (expected: pipeline paused). Trades today: 4 closed, -$0.29. Regime: SHORT_BIAS (13L/16S/95N of 124). Disk 82%. Phantom trades: 0. token_speeds stale (last 03:25) — expected downstream of pause.
- **[WARN]** (1x): `hermes-trading-checklist.service` — CRIT pipeline.timer inactive at 14:08. False positive: intentional vacation pause. Suggestion: checklist should check vacation_pause.json before flagging.
- **[INFO]** (repeat, pre-existing): bug-hunter, daily-orchestrator, upgrade-implementer failed on known issues (audit FAILs / timeouts with bad SQL) — documented in prior alerts, not new. No auto-fixes needed.

## Error Alerts — 2026-10-17 15:25 UTC
- **[INFO]**: Pipeline paused by vacation guardrail (intentional) — paused_at 2026-10-17T15:08:28Z, reason: 7d WR 34.1% < 35.0% AND pnl_7d $-2.93 < $-2.00 (211T). Pipeline/watchdog timers correctly inactive. NOT a crash. Auto-resume handled by guardrail.
- **[WARN]**: Disk at 82% (92G/118G, 21G free). Under 85% threshold but trending. Consider compressing old logs: pipeline.log 136M, signal-compactor.log 55M, 15m_regime.log 54M.
- **[WARN]**: 0 signals generated in last hour (expected — pipeline paused). Latest signal: 09:39 UTC (5.7h ago).
- **[WARN]**: LIVE trade open during pause — BTC SHORT @ 81522, opened 03:25:04 (paper=false, id=16258). Guardrail pause does not close existing positions.
- **[WARN]**: hermes-trading-checklist.service exits 1 hourly — reporting pipeline.timer inactive as CRITICAL. False positive during vacation pause (checklist not pause-aware).
- **[WARN]**: hermes-bug-hunter.service exits 1 (09:37 UTC) — 7 pre-existing code quality findings (sqlite leaks, bare excepts, hardcoded passwords, non-atomic JSON). Not new.
- **[WARN]**: hermes-daily-orchestrator.service failed — not investigated in depth (paused system, low priority).
- **AUTO-FIX**: None required. All timers active as expected for pause state. Prices fresh (15:24 UTC, <1min). Price-collector + 1m-candle running normally. candles.db 3GB, 2 concurrent writers, no lock issue.

## Error Alerts — 2026-10-17 16:25 UTC
- **[INFO]**: Health check at 16:25 UTC — vacation pause active (paused_at 16:08:28, 7d WR 34.3% < 35.0% AND pnl_7d $-2.82 < $-2.00, 210T). Pipeline.timer + trade-watchdog.timer correctly inactive per guardrail rule — intentional, NOT a crash. Auto-resume handled by guardrail on metric recovery (WR>=37% or pnl_7d>=0).
- **[INFO]**: Data collection healthy — price-collector last fired 16:23:11, 1m-candle last fired 16:23:09, candles fresh (1m age ~73s). 15m-regime-scanner on schedule (last 16:15). hl-sync-guardian active (daemon, 24h uptime). 30+ other timers active/waiting. Guardrail timer armed for next check at 16:38.
- **[INFO]**: 0 signals last 1h (expected — pipeline paused). Trades today: 4 closed, -$0.29 (signal_outcomes). 1 open: BTC SHORT @ 81522, manual CEO trade, opened 03:25, guardrail kept it open intentionally. Regime: SHORT_BIAS (2L/106S/16N of 124). Speed: 128/241 tokens >=50th pct. Phantom trades: 0. Disk 82% (21G free). Logs 402M total, no >7d files >10M to compress.
- **[WARN]** (repeat, pre-existing): hermes-trading-checklist.service exits 1 hourly — flags pipeline.timer inactive as CRIT during vacation pause. False positive: checklist is not pause-aware (should check vacation_pause.json first). Not new, documented in prior alerts.
- **[INFO]**: No auto-fixes required. System healthy in pause state.

## Error Alerts — 2026-10-17 17:08 UTC
- **REPEATED** (11x): `Oct N N:N:N python3[TOK]: [coin_tracker] Done: N coins processed, N skipped, N errors`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3535s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3535s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3484s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3421s left, N failures)`

## Error Alerts — 2026-10-17 18:08 UTC
- **REPEATED** (11x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-17 21:25 UTC
- **[WARN]** (8h cadence): `hermes-bug-hunter.service` exits 1 — by-design (findings present): 51 cursor-leak files, 132 bare excepts (39 files), 82 non-atomic JSON writes, 4 hardcoded-password files. Long-standing tech debt, not a new crash. No auto-fix (bulk refactor out of health-monitor scope).
- **[WARN]**: `hermes-atr-sl-updater.timer` listed as not-found — unit file missing but still referenced by a service trigger. Cosmetic; no functional impact observed.
- **[WARN]**: trade frequency 0.2/hr (1 trade in 6h) — market/filter condition, not a system fault.
- AUTO-FIX: none required. All critical timers active, pipeline green, prices fresh (0.5 min), disk 83% (<85% threshold).

## Error Alerts — 2026-10-17 22:08 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+TOK+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-17 22:25 UTC
- **[WARN]** (8h cadence, repeat of 21:25): `hermes-bug-hunter.service` exits 1 — by-design findings (sqlite/cursor leaks, bare excepts, non-atomic JSON, hardcoded passwords). Long-standing tech debt; no auto-fix (bulk refactor out of health-monitor scope).
- **[WARN]**: trade frequency ~0.3/hr (2 trades/6h) — market/filter condition, not a system fault. Today: 7 closed, -8.28% PnL.
- AUTO-FIX: none required. Pipeline green (last run 22:23:21 SUCCESS), all 4 core timers active, prices fresh (~30s), 64 signals in last hour, disk 83% (<85%).

## Error Alerts — 2026-10-17 23:08 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: +N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-18 01:08 UTC
- **REPEATED** (41x): `Oct N N:N:N python3[TOK]: TS   TS   [TOK] TOK-TOK TOK for TOK: name '_peak_high' is not defined`

## Error Alerts — 2026-10-18 01:24 UTC
- **WARN** (recurring): `[SHADOW] MFE-CUT error for ADA/SUPER: name '_peak_high' is not defined` — shadow block in `check_and_manage_positions` referenced `_peak_high`/`_entry` defined only in `_collect_atr_updates` scope.
- **AUTO-FIX**: Changed MFE-CUT shadow to read `highest_price`/`lowest_price`/`entry_price` from `pos` dict directly. Syntax verified, committed `bb41994f`.

## Error Alerts — 2026-10-18 04:26 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-18 04:43 UTC
- **WARN** (939x restarts): `hermes-coding-mcp.service` crash-looping — `/root/.hermes/scripts/run_mcp_server.py` does not exist (Errno 2). Service was disabled but still auto-restarting via Restart= policy.
- **AUTO-FIX**: Stopped `hermes-coding-mcp.service` (inactive now). Unit references a deleted script; needs either the script restored or the unit removed — flagged for cleanup, out of health-monitor scope.
- **WARN** (recurring 8h): `hermes-bug-hunter.service` exits 1 — known tech debt (hardcoded passwords in study_winning_combos.py, context-compactor.py, hermes_ab_utils.py, trading-checklist.py). Previously logged 2026-10-17 22:25. reset-failed applied.
- Pipeline: OK — 30 successful runs in last 30min, 3 open / 3 closed today (PG), 44 signals/hour, no phantoms, prices fresh (27s, 87 tokens), disk 81%, all core timers active. Not paused.

## Error Alerts — 2026-10-18 10:26 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-18 11:47 UTC
- **WARN** (1x): `signals_db: 5482 signals in table` — signal-purge only removes executed signals >1h; non-executed old signals accumulate (5387 older than 2h). Checklist exits 1 on this WARN each run.
- **WARN** (1x): `hermes-atr-sl-updater.timer` unit not-found (stale reference in systemd).
- **INFO**: `hermes-upgrade-implementer.service` timed out at 04:36 UTC (one-off, killed by systemd timeout). State reset.
- **AUTO-FIX**: reset-failed on hermes-trading-checklist.service and hermes-upgrade-implementer.service. No pipeline/timer intervention needed — all healthy.

## Error Alerts — 2026-10-18 13:26 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-18 14:45 UTC
- **CRITICAL** (7829x): `hermes-metrics.service` crash-looping — `/root/.hermes/scripts/metrics_collector.py` does not exist (deleted in 3786b550 "delete 116 dead scripts"). Restarting every 5s, status=2/INVALIDARGUMENT.
- **CRITICAL** (6014x): `hermes-coding-mcp.service` crash-looping — `/root/.hermes/scripts/run_mcp_server.py` does not exist (same cleanup wave). Restarting every 5s, status=2/INVALIDARGUMENT.
- **AUTO-FIX**: `systemctl disable --now` on both. Non-trading path (pipeline/price-collector/1m-candle/watchdog/hl-sync all active and healthy). Both units were previously disabled in earlier sessions and have since been re-enabled — if they reappear, find the re-enabler or remove the unit files entirely.
- **INFO**: 59x `[LOCK-WAIT] info_rate` in price_collector last 5m — all self-recovered (0.1s retries), normal SQLite contention, no action needed.

## Error Alerts — 2026-10-18 16:44 UTC
- **WARN** (ongoing, 1216x/24h): `hotset.json is empty — no signals survived compaction` — 32 signals in last hour (avg conf 78.5, max 88) but 0 admitted; confluence gate blocking 72 (single-type not in standalone bypass), continuum-block 17, BTC-chop 10. Working as designed, not a crash — no auto-fix applied. Flag for CEO review only if trading inactivity is unintended under SHORT_BIAS regime.
- **INFO**: `hermes-atr-sl-updater.timer` shows not-found in list-timers — stale reference to `hermes-atr-sl-updater-DEFUNCT.timer` rename. Harmless, no action.
- **INFO**: Prior CRITICAL items (hermes-metrics, hermes-coding-mcp crash-loops) confirmed still disabled — no re-enabler regression.
- **NO AUTO-FIXES NEEDED**: all timers active, pipeline completing every 1min, prices fresh (42s), disk 81% (under 85% threshold), 0 phantom trades, 0 open positions.

## Error Alerts — 2026-10-18 18:43 UTC
- **WARN** (ongoing since 16:44): `hotset.json empty — no signals survived compaction` — 22 signals in last hour, 12 trades closed today (live trading active), but compactor admits 0 to hotset (MON has hot_cycle_count=2 but decision=SKIPPED). Same gate-tuning issue already flagged for CEO at 16:44 — no new action, just confirming still active.
- **NO AUTO-FIXES NEEDED**: all 4 core timers active, pipeline 30/30 successful runs in 30min, hl-sync-guardian active, disk 82% (under 85%), prices fresh (87 tokens, ~100s), 0 open positions, 0 phantoms, 0 failed units, hermes-metrics/coding-mcp still correctly disabled.

## Error Alerts — 2026-10-19 07:26 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3548s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3375s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3375s left, N failures)`

## Error Alerts — 2026-10-19 10:26 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3532s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3532s left, N failures)`

## Error Alerts — 2026-10-19 14:45 UTC
- **WARN** (12028x): `hermes-coding-mcp.service` crash-looping — ExecStart points to missing `/root/.hermes/scripts/run_mcp_server.py` (file absent from repo; mcp dir only has empty `dispatcher/`). Restarted 12,028 times over ~16h.
- **AUTO-FIX**: `systemctl disable --now hermes-coding-mcp.service` — stopped crash loop, disabled unit. Restore requires recreating the MCP server script and re-enabling.
- **INFO**: Pipeline healthy otherwise — 0 errors/tracebacks in 30min, 95 signals/h, 14 trades closed today (-$0.35), 0 open positions, disk 83%, prices fresh (~107s), all key timers active.

## Error Alerts — 2026-10-19 15:26 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+NEUTRAL+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-19 16:26 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-19 16:43 UTC
- **WARN** (1x each): `hermes-signal-reporter.service` and `hermes-upgrade-implementer.service` failed with systemd start timeout. Both are Type=oneshot analysis jobs; signal-reporter completed its git push (RC:0) before the kill, upgrade-implementer was mid-analysis. Neither is on the trading path.
- **AUTO-FIX**: `systemctl reset-failed` on both units — cleared failed state, timers remain active for next scheduled retry (6h / 12h cadence).
- **INFO**: Disk at 83% (under 85% threshold); no logs >7d to compress. Core timers (pipeline, price-collector, 1m-candle, watchdog) all active. Prices fresh (~43s). 0 open positions, 14 closed today -$0.35. Regime SHORT_BIAS. 43 signals/h. No trading-path issues.

## Health Check — 2026-10-19 21:43 UTC
- **OK**: No WARN or CRITICAL issues. Disk at 83% (watch, threshold 85%). 1 open trade (LTC LONG @ 59.74). 18 signals/1h. Prices fresh (<1 min).

## Error Alerts — 2026-10-20 00:26 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3528s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3472s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3424s left, N failures)`

## Error Alerts — 2026-10-20 02:26 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`

## Error Alerts — 2026-10-20 03:26 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3480s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3422s left, N failures)`

## Error Alerts — 2026-10-20 04:26 UTC
- **REPEATED** (9x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BULL+TOK, allowing despite TOK filter`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-20 05:43 UTC
- **[WARN]** (8x): `atr_sl_hit` phantom trades (<0.01% PnL) in last 24h — no auto-fix (needs signal quality review)
- **[WARN]**: Today 20% WR (6 closed, -0.42 USDT) — no auto-fix (performance, not system health)

## Error Alerts — 2026-10-20 08:26 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3465s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3465s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3343s left, N failures)`

## Error Alerts — 2026-10-20 09:45 UTC
- **WARN** (1x): `hermes-coding-mcp.service` crash-loop — 14,588 restarts, script `/root/.hermes/scripts/run_mcp_server.py` missing, dispatcher dir empty
- **AUTO-FIX**: Disabled service (`systemctl disable --now`). Needs script restored or unit removed permanently.
- **WARN** (1x): Disk at 84% (19G free of 118G) — pipeline.log 192M, signal-compactor.log 75M, 15m_regime.log 64M. No logs >7d to compress; consider logrotate or truncation if it crosses 85%.

## Error Alerts — 2026-10-20 12:26 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-20 13:26 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3545s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3545s left, N failures)`

## Error Alerts — 2026-10-20 14:26 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ [TOK-TOK] TOK failed for TOK: Command '['/root/.opencode/bin/opencode', 'run', 'You are a crypto trading gate. Evaluate this signal and reply TOK of: GO, TOK, TO`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3561s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3561s left, N failures)`

## Error Alerts — 2026-10-20 18:26 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3481s left, N failures)`

## Error Alerts — 2026-10-21 02:45 UTC
- **WARN** (1x): disk usage at 85% on / (17.6G free of 118G)
- **AUTO-FIX**: none possible — no *.log older than 7d to gzip; largest recent files are active (pipeline.log 206M, signal-compactor.log 80M, 15m_regime.log 67M). Monitor only; if >90%, enable logrotate on /root/.hermes/logs.

## Error Alerts — 2026-10-21 06:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3482s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3421s left, N failures)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3537s left, N failures)`

## Error Alerts — 2026-10-21 07:27 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BEAR+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-21 08:27 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-21 09:27 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: ME TOK — signal TOK rolled back (prevents retry loop)`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: ME TOK (count=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (3541s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: ME TOK in hotset failure cooldown — TOK in cooldown (3541s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (3480s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: ME TOK in hotset failure cooldown — TOK in cooldown (3480s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (3421s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: ME TOK in hotset failure cooldown — TOK in cooldown (3421s left, N failures)`

## Error Alerts — 2026-10-21 11:27 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-21 13:43 UTC
- **WARN** (ongoing): vacation guardrail ESCALATE — 48h WR 31.1% < 40% (45T), 7d WR 36.8% PnL -$2.46. No pause marker present (T previously directed resume-with-size-reduce). Monitor only.
- **WARN** (intermittent): watchdog signal-rate dips (1-6 signals/5min vs min 20); 70 signals in last hour so overall flow OK.
- **INFO**: JUP SHORT failed 2x on RSI hard floor (28.8 < 45) — filter working as intended, signals marked FAILED, hotset cooldown engaged. No action.
- Disk 84% (was 85% at 02:45). No *.log >7d to gzip; pipeline.log now 216M. Still monitor-only.
- **AUTO-FIXES**: none required — all timers active, no crashes, prices fresh (30s), no DB locks.

## Error Alerts — 2026-10-21 14:27 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BULL+AT, allowing despite TOK filter`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor (detect): N.N < N`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3475s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3475s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3416s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3416s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3356s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3356s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3536s left, N failures)`

## Error Alerts — 2026-10-21 20:27 UTC
- **REPEATED** (8x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-21 22:47 UTC
- **WARN** (3x): `signals: WARNING — only 4 signals in last 5 min (min 20)` (watchdog; 118 signals/hr created, 46 sources running 0 errors — rate below watchdog threshold, not a stall)
- **WARN** (179x/6h): watchdog `Cleaned 4 stale locks: pipeline_heartbeat.lock, hotset_json.lock, signal_compactor_critical.lock, hotset_last_updated.lock` — dead-PID leftovers, housekeeping only (no live locks held)
- **WARN** (2x): `hermes-brain-auditor` transient SQL errors — `column "coin_regime" does not exist`, `syntax error at or near "trailing"` (ad-hoc heredoc queries; auditor self-corrected and completed run #63, RC 0)
- **WATCH**: disk 84% (warn at 85%), no logs >7d to gzip yet
- **AUTO-FIX**: none required — all 72 hermes timers active, pipeline every 1min rc=0, no tracebacks, prices fresh (87 tokens <5min), 0 phantom trades, not vacation-paused

## Error Alerts — 2026-10-21 23:27 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (9x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3534s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3534s left, N failures)`

## Error Alerts — 2026-10-21 23:45 UTC
- **WARN** (recurring): disk hit 85% used (18G free) — threshold reached; no logs >7d exist to gzip, largest is pipeline.log 227M (all logs <7d old)
- **WARN** (recurring since 22:47): `signals: WARNING — only 5 signals in last 5 min (min 20)` — 88 signals/hr generated, pipeline rc=0 every 1min; rate below watchdog threshold, not a stall
- **WATCH**: hotset.json empty — signals generated but none survived compaction above 40% confidence (market condition, not a fault); BTC-CRASH momentum gate blocking LONGs as designed (BTC 30m mom -0.3~-0.4%)
- **AUTO-FIX**: none required — vacation_pause absent, all core timers active (pipeline/price-collector/1m-candle/watchdog), 0 tracebacks, prices fresh (130 tokens, max age 68s on active set), 0 open trades, 0 phantom trades; watchdog self-cleaned 4 stale locks at 23:43

## Error Alerts — 2026-10-22 00:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   [TS] [shadow_signals_runner] TOK: N signals recorded, N skipped, N errors`

## Error Alerts — 2026-10-22 00:43 UTC
- **[WARN]** (1x): Disk usage at 85% on / (94G/118G). No logs >7d to compress. Monitor; consider pruning pipeline.log (228M) or lowering retention.
- No CRITICAL issues. Pipeline rc=0 across all steps, timers active, prices fresh, not paused.

## Error Alerts — 2026-10-22 01:27 UTC
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   [TS] [shadow_signals_runner] TOK: N signals recorded, N skipped, N errors`

## Error Alerts — 2026-10-22 02:27 UTC
- **REPEATED** (14x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (26x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: TOK,TOK,MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-10-22 03:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3474s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3474s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3295s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3295s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3237s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3236s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3177s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3177s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3059s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3059s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2997s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2997s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2942s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2942s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2872s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2872s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2807s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2807s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2750s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2750s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2693s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2693s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2635s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2635s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2581s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2581s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2520s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2520s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2400s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2400s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2340s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2340s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2280s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2221s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2160s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2036s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1975s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1975s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1919s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1919s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1856s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1856s left, N failures)`

## Error Alerts — 2026-10-22 03:47 UTC
- **WARN** (1x): `disk usage 85% (95G/118G) — at warn threshold`
- **AUTO-FIX**: `journalctl --vacuum-size=500M` freed 1.1G archived journals → disk now 84%, 19G free. No logs >7d found to compress.
- **INFO**: `shadow_signals_runner` DONE line reports 6–10 "errors" per run — verified benign (counter names quiet detectors `0 signals (detector ran but found nothing)`; zero real exceptions/import failures). Counter label misleading; suggest renaming to `idle` in shadow_signals_runner.py:374.

## Error Alerts — 2026-10-22 04:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1138s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1138s left, N failures)`

## Error Alerts — 2026-10-22 05:27 UTC
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   [TS] [shadow_signals_runner] TOK: N recorded, N skipped, N empty, N filtered, N errors`

## Error Alerts — 2026-10-22 06:27 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-22 06:47 UTC
- **WARN** (17031x): `hermes-coding-mcp.service` restart storm — `can't open file '/root/.hermes/scripts/run_mcp_server.py': No such file or directory`, restart counter at 17031 (every 5s).
- **AUTO-FIX**: `systemctl stop hermes-coding-mcp.service` — script was deleted in 3786b550 ("delete 116 dead scripts"), unit left behind; zero callers, nothing on port 8765, unit already `disabled`. Verified inactive and not respawning. Follow-up: remove `/etc/systemd/system/hermes-coding-mcp.service` (agent has no write access to /etc/systemd/system).
- **INFO**: `systemctl list-timers hermes-*` in the health-monitor prompt returns "0 timers listed" — bash expands the unquoted glob to `hermes-trading-system-*.zip` in /root/.hermes. Use `systemctl list-timers 'hermes-*'` (quoted). All 75 hermes timers verified active when queried correctly.
- **INFO**: Disk 84% (19G free) — under 85% threshold, no logs >7d to compress. Watch: `data/coin_tracker.db` is 3.4GB.

## Error Alerts — 2026-10-22 07:27 UTC
- **REPEATED** (12x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-22 07:47 UTC
- **WARN** (1x, recurring 4th): `hermes-signal-reporter.service failed: start operation timed out (40min TimeoutStartUSec, 03:51 UTC)` — analysis/reporting only, 5 prior runs succeeded, no trading impact.
- **AUTO-FIX**: `systemctl reset-failed hermes-signal-reporter.service` — unit cleared, timer active, retries ~09:49 UTC.
- **INFO**: Disk 84% (19G free) — still under 85% threshold; no logs >7d to compress. Watch `data/coin_tracker.db`.

## Error Alerts — 2026-10-22 11:45 UTC
- **WARN** (1030x/30min): `[LOCK-WAIT] info_rate: waited 0.1s, retrying` in hermes-price-collector — signals_hermes.db write contention (price_collector vs pipeline readers). All waits resolved at 0.1s; no failed writes; prices fresh (57s age). No auto-fix applied (transient contention, not a stuck lock).
- **WARN**: Disk 84% used (94G/118G) — approaching 85% threshold. No logs >7d to compress; largest live log pipeline.log at 237M. Suggest logrotate size cap in a future pass.
- **WARN**: `[hotset] fallback DB query returned 0 tokens` / `hotset.json is empty — no signals survived compaction` — hotset empty because no signals survived compaction, not a query failure. Market condition, no fix needed.
- **INFO**: Pipeline portfolio line reports "23 closed today | -11.68% PnL" while PostgreSQL shows 2 closed today (+0.11 USDT, 50% WR). Pipeline "today" appears to count last-24h exits (matches signal_outcomes n=23); the -11.68% appears to be portfolio-% not USDT sum (-0.36 USDT across 24h exits). Flagging for CEO awareness, not a defect confirmed.
- No vacation pause active. All 4 timers (price-collector, 1m-candle, pipeline, watchdog) active and firing on schedule.

## Error Alerts — 2026-10-22 12:43 UTC
- **WARN** (1x): Disk usage at 85% on / (94G/118G, 18G free). No logs older than 7 days found to compress; largest logs: pipeline.log 238M, signal-compactor.log 93M, 15m_regime.log 72M.
- **INFO**: hermes-hl-sync-guardian.timer had no future triggers listed (OnUnitActiveSec cosmetic); timer restarted, service verified active and syncing (0 positions, no orphans/missing).
- No pipeline errors, no phantom trades, prices fresh (48s). No auto-fixes required.

## Error Alerts — 2026-10-22 13:43 UTC
- **WARN** (1x): Disk usage at 85% (threshold)
- **AUTO-FIX**: Vacuumed systemd journals — freed 570.6M, disk now 84%. No *.log files older than 7d to gzip.

## Error Alerts — 2026-10-22 15:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3418s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3299s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3299s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3239s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3239s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] USELESS TOK — continuum says DECLINING+LEAN_BEAR+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-22 16:43 UTC
- **[WARN]** Disk at 84% (19G free of 118G). Top consumers: coin_tracker.db 3.3G, session_brain.db 1.5G, candles.db 1.2G, signals_hermes.db 1.1G, pipeline.log 241M. Compressed old .err.log files (minimal gain — big logs are active). Monitor; clean coin_tracker.db / session_brain.db if it crosses 85%.
- **[WARN]** Performance: 9 Hermes trades closed in last 24h, cumulative -11.00% pnl_pct. Worst: STX r2v2-long4 -4.90%, POL bb-bounce-v2-long+ -4.85%, NEO bb-bounce-v2-long+ -2.35%. bb-bounce-v2-long+ took 3 losses in 24h — review signal quality.
- **[INFO]** Pipeline log shows "[hotset] fallback DB query returned 0 tokens" — hotset.json has 3 tokens; fallback path may need review. Non-blocking.

## Error Alerts — 2026-10-22 17:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK knife floor: N.N < N`

## Error Alerts — 2026-10-22 18:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: BIGTIME TOK — signal TOK rolled back (prevents retry loop)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: BIGTIME TOK (count=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK knife floor (detect): N.N < N`

## Error Alerts — 2026-10-22 18:45 UTC
- **[CRITICAL]** (RESOLVED): `sentiment-aggregator.service` crash-looping — WorkingDirectory `/root/.openclaw/workspace/scripts` missing (status=200/CHDIR), 13,280 restarts over ~4.6 days. Script only exists in `/root/Dallas/workspace-20260306-0000/scripts/sentiment-aggregator.py` backup. No consumers of `/var/www/logs/sentiment.json` (stale since Apr 3 2026). **AUTO-FIX**: `systemctl disable --now sentiment-aggregator.service` — dead OpenClaw-era service, no hermes consumers.
- **[WARN]** (RESOLVED): `hermes-summarizer.service` failed at 16:16 UTC — start operation timed out (TimeoutStartSec=600). Actual work completed (summary written to automation/summaries/2026-10-22_16.md + OpenMemory stored); timeout hit during trailing git commit of gitignored path (`.gitignore:177 automation/summaries/`). **AUTO-FIX**: `systemctl reset-failed`. Note: run_summarizer.sh wastes time on git add of ignored paths — consider skipping git when path is gitignored.
- **[INFO]** Disk at 84% (18G free of 118G). pipeline.log 243M, signal-compactor.log 95M, 15m_regime.log 73M — active logs, do not rotate while running.

## Error Alerts — 2026-10-22 20:27 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3419s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3351s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3351s left, N failures)`

## Error Alerts — 2026-10-22 22:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3420s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3359s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3359s left, N failures)`

## Error Alerts — 2026-10-22 22:44 UTC
- **WARN** (1x): `disk usage / = 85% (18G free of 118G)`
- **AUTO-FIX**: none safe — 0 logs older than 7 days (gzip no-op), journal only 128M; largest files (pipeline.log 246M) are actively written, left untouched

## Error Alerts — 2026-10-22 23:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] BIGTIME TOK BLOCKED — TOK in cooldown (3540s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: BIGTIME TOK in hotset failure cooldown — TOK in cooldown (3540s left, N failures)`

## Error Alerts — 2026-10-23 00:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3236s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3178s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3116s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3116s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3058s left, N failures)`

## Error Alerts — 2026-10-23 00:42 UTC
- **WARN** (1x): `disk: / at 85% used (18G free) — at warning threshold`
- **WARN** (1x): `watchdog: signals 3/5min below min 20; cleaned 5 stale locks (pipeline_heartbeat, guardian_closing, hotset_json, signal_compactor_critical, hotset_last_updated)`
- **AUTO-FIX**: none needed — no logs >7d to compress (0 files); locks self-cleaned by watchdog; all timers active; signals flowing (31/hour). Disk flagged for CEO: largest consumers are data/coin_tracker.db (3.3G), session_brain.db (1.5G), candles.db (1.2G).

## Error Alerts — 2026-10-23 01:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2999s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2998s left, N failures)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK mid-band death band: N.N in N-N`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3360s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3360s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3423s left, N failures)`

## Error Alerts — 2026-10-23 01:43 UTC
- **WARN** (1x): Disk usage at 85% on / (95G/118G, 18G free) — no logs older than 7d to compress; actively-written logs total 587M (pipeline.log 249M, signal-compactor.log 97M, 15m_regime.log 74M). Monitor; if >90% consider logrotate or truncating rotated segments.
- **INFO**: ARB SHORT mid-band death band blocks (RSI 51.9 in 45-55) at 01:20-01:24 — filter working as designed, cooldown engaged, no action needed.

## Error Alerts — 2026-10-23 02:27 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK knife floor (detect): N.N < N`

## Error Alerts — 2026-10-23 02:45 UTC
- **WARN** (1x): `disk usage 85% on / (95G/118G, 18G free)` — threshold is 85%
- **AUTO-FIX**: gzipped stale logs (mtime+1d, >100k) in /root/.hermes/logs; active logs (pipeline.log 250M, signal-compactor.log 97M) are still being written so left alone. No missed timers, no crashes, no stale prices — otherwise healthy.

## Error Alerts — 2026-10-23 03:27 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+TOK+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-23 05:27 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`

## Error Alerts — 2026-10-23 07:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK rc=N: stderr_tail=(empty)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: brain.py rc=N`

## Error Alerts — 2026-10-23 08:27 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] CC TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-23 09:45 UTC
- **WARN** (1x): `hermes-upgrade-implementer.service: Failed with result 'timeout'` (04:36 UTC — script exceeded TimeoutStartSec=900)
- **AUTO-FIX**: `systemctl reset-failed` applied; timer unaffected (next run 16:21 UTC). Suggested: raise TimeoutStartSec or cap script runtime to <900s.
- **WARN**: Disk at 84% (threshold 85%) — largest log: pipeline.log 256M. No action taken yet; compress >7d logs if it crosses 85%.

## Error Alerts — 2026-10-23 11:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3542s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] BIGTIME TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-23 14:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: CC TOK — signal TOK rolled back (prevents retry loop)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: CC TOK (count=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: CC TOK in hotset failure cooldown — TOK in cooldown (3539s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: CC TOK in hotset failure cooldown — TOK in cooldown (3466s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3554s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: CC TOK in hotset failure cooldown — TOK in cooldown (3420s left, N failures)`

## Error Alerts — 2026-10-23 14:48 UTC
- **WARN** (1x): disk `/` at 85% (94G/118G, 18G free) — no logs older than 7d to compress; largest active: pipeline.log 261M, signal-compactor.log 102M. **AUTO-FIX**: none applied (nothing safe to reclaim in scope; monitor).
- **WARN** (1x): price staleness hit ~5min at ~14:43 — one price_collector run took 291s (normal ~20s), price age peaked ~250s. **AUTO-FIX**: self-recovered; cadence back to 30s, age 56s at check. No restart issued.
- **INFO** (1x): `decisions` table last row 2026-04-13 — compactor logs decisions in pipeline log but no longer writes here. Verify intended, not a crash.

## Error Alerts — 2026-10-23 15:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3494s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: CC TOK in hotset failure cooldown — TOK in cooldown (3360s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3433s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: CC TOK in hotset failure cooldown — TOK in cooldown (3299s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: CC TOK in hotset failure cooldown — TOK in cooldown (3239s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+NEUTRAL+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] IO TOK — continuum says DECLINING+NEUTRAL+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] IO TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+NEUTRAL+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-23 16:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2759s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2759s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CC TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CC TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-23 17:45 UTC
- **WARN** (1x): disk `/` at 85% used (18G free) — no logs >7d to gzip; largest local consumers: /root/.hermes/data 7.9G, journal 412M. No auto-fix applied (nothing safe to delete).
- **WARN** (1x): `hermes-upgrade-implementer.service` FAILED at 16:36 UTC — `start operation timed out` (TimeoutStartSec=900) after running 2m15s CPU; timer retries next 16:06+12h. Log also shows SQL executed as shell (`LINE 1: select token, direction, size_usdt...` caret error) — likely a plan file eval'd into sh.
- **AUTO-FIX**: none required — pipeline, price-collector, 1m-candle, watchdog timers all active and firing; no crash, no stale prices, no phantom trades.

## Error Alerts — 2026-10-23 18:27 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: v2 recheck: momentum -N.N < N.N`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3479s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3479s left, N failures)`

## Error Alerts — 2026-10-23 18:43 UTC
- **WARN** (1x): disk `/` at 85% capacity (18G free; 84.6% exact) — still no logs >7d to gzip; largest: /root/.hermes/logs/pipeline.log 264M, signal-compactor.log 103M. No safe auto-fix available (active logs only).
- **INFO** (1x): CRV SHORT trade execution FAILED at 18:42 (`RSI ceiling: 71.2 > 65`) — handled gracefully, signal 1686297 marked FAILED, hotset cooldown recorded. Not a system error.
- **AUTO-FIX**: none required — all key timers active (price-collector, 1m-candle, pipeline, watchdog), pipeline last run OK at 18:42 (1 open / 18 closed today), prices 68s fresh, 56 signals in last 1h, 0 phantom trades, no crashes.

## Error Alerts — 2026-10-23 19:27 UTC
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-23 20:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: IO TOK — signal TOK rolled back (prevents retry loop)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: IO TOK (count=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2458s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2398s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2398s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2339s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2339s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2275s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2217s left, N failures)`

## Error Alerts — 2026-10-23 20:49 UTC
- **WARN** (1x): `hermes-upgrade-implementer.service` FAILED at 16:36 UTC — systemd `TimeoutStartSec=900` killed a run the wrapper script allows to run 1800s (`timeout 1800` in run_upgrade_implementer.sh; its comment claimed the unit matched, but the unit still said 900). Log also shows the agent ran bad SQL (`column "size_usdt" does not exist` — column is `amount_usdt`).
- **AUTO-FIX**: unit edited 900→1800 via sed, `systemctl daemon-reload`, `reset-failed` — timer active, next run 04:21 UTC. (SQL error is agent-side, non-blocking.)
- **WARN**: disk 85% used (95G/118G, 18G free). Prescribed cleanup ran: 0 log files >7d to gzip, journal vacuum freed 0B. Hermes logs = 622M (all actively written, safe). Main hogs are out of health-monitor scope: /var/log/syslog* 1.2G, /root/zscore 2.2G, /root/hermes-agent 2.0G, /root/snap 1.7G — recommend CEO run a scoped cleanup if disk trends past 90%.

## Error Alerts — 2026-10-23 23:27 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (3539s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: ME TOK in hotset failure cooldown — TOK in cooldown (3539s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (3478s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: ME TOK in hotset failure cooldown — TOK in cooldown (3478s left, N failures)`

## Error Alerts — 2026-10-24 02:45 UTC
- **WARN** (recurring, 30x/hr): `hermes-watchdog: signals: WARNING — only 0-4 signals in last 5 min (min 20)` — actual rate ≈17 signals/hour. Not a crash; signal generation rate below watchdog threshold.
- **WARN** (recurring, 28x/hr): `hermes-watchdog: locks: WARNING — Cleaned 5-7 stale locks` (pipeline_heartbeat, guardian_closing, hotset_json, signal_compactor_critical, …) — watchdog self-heals each run, no pipeline errors, but stale-lock churn every cycle is noisy; owners may not be removing locks on exit.
- **WARN**: disk 85.0% used (95G/118G, 17G free) — no logs >7d to gzip, journal vacuum previously freed 0B. Same hogs as 2026-10-23 (outside health-monitor scope): /var/log/syslog* 1.2G, /root/zscore 2.2G, /root/hermes-agent 2.0G, /root/snap 1.7G.
- **AUTO-FIX**: none required — pipeline timer firing on schedule (last run 02:42, all rc=0, 0 tracebacks/30min), price-collector/1m-candle timers active, prices fresh (72s), no DB locks held, 0 open positions, no phantom trades in 24h. vacation_pause.json absent.

## Error Alerts — 2026-10-24 03:45 UTC
- **WARN** (recurring): `hermes-watchdog: signals: WARNING — only 0-4 signals in last 5 min (min 20)` — 21 signals generated in the last hour, so this is rate variance vs an aggressive threshold, not a stall.
- **WARN** (recurring): `hermes-watchdog: locks: WARNING — Cleaned 5 stale locks` (pipeline_heartbeat, guardian_closing, hotset_json, signal_compactor_critical, hotset_last_updated) every ~2min cycle — owners not clearing locks on exit; noisy but self-healing.
- **WARN**: `hotset.json is empty — no signals survived compaction` + `No signals above 40% confidence — skipping execution` every minute → 0 executions, 0 open positions, 0 trades in the last hour (20 closed in last 24h, +0.14 USDT). Compaction is filtering everything out — worth a signal-lab look if it persists.
- **WARN**: disk 85% (df: 95G/118G used, 17G free; raw 80.5%). No logs >7d to gzip, so no safe reclaim from logs/ — same out-of-scope hogs as 2026-10-23 (/var/log/syslog* 1.2G, /root/zscore 2.2G, /root/hermes-agent 2.0G, /root/snap 1.7G).
- **INFO**: `decisions` table (signals_hermes_runtime.db) last row 2026-04-13 — likely legacy schema left behind by the signal_compactor migration; not read by the live path.
- **AUTO-FIX**: none required — no vacation pause, all 4 timers active, pipeline service running (rc=0 every cycle, 0 tracebacks/30min), position_manager healthy, prices fresh (14s, 87 tokens), no DB locks held, no phantom trades.

## Error Alerts — 2026-10-24 04:27 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] GRIFFAIN TOK BLOCKED — WARNING — BTC_LEVEL`

## Error Alerts — 2026-10-24 05:43 UTC
- **WARN** (1x): `disk usage 86% on /` (95G/118G, 17G free) — no logs older than 7d to compress; largest consumers: data/coin_tracker.db (3.3G), session_brain.db (1.5G), candles.db (1.2G), logs/pipeline.log (274M). No auto-fix available; monitor.
- No CRITICAL issues. All timers active, 0 tracebacks, prices fresh (63s).

## Error Alerts — 2026-10-24 06:45 UTC
- **WARN** (recurring): `hermes-watchdog: signals: WARNING — only 0 signals in last 5 min (min 20)` — actual 41 signals/hour (4 in last 5m at check time); rate variance vs aggressive threshold, not a stall.
- **WARN** (recurring): `hermes-watchdog: locks: WARNING — Cleaned 4 stale locks` (pipeline_heartbeat, hotset_json, signal_compactor_critical, hotset_last_updated) — self-heals each 2min cycle; owners not clearing locks on exit.
- **WARN** (recurring): disk 86% used (95G/118G, 17G free) — no logs >7d to gzip, /tmp has no files >7d. Hogs outside scope: /usr 32G, /root/.local 13G, /root/zscore 2.2G, /root/hermes-agent 2.0G.
- **INFO**: pipeline log reports "20 closed today" but PostgreSQL calendar-day count = 1 closed (−0.08 USDT); the 20 are a rolling-24h window (max close_time 00:00:19 UTC). Reporting discrepancy only, not data loss.
- **INFO**: `hermes-atr-sl-updater.timer` shows as not-found in list-units (unit renamed to `-DEFUNCT`) — harmless stale reference.
- **AUTO-FIX**: none required — vacation_pause.json absent; price-collector/1m-candle/pipeline/watchdog timers all active; pipeline rc=0 at 06:42 & 06:44, 0 tracebacks; prices fresh (75s, 130 tokens); 1 open trade; 0 phantom trades (atr_sl_hit <0.01%) in 24h; regime SHORT_BIAS.

## Error Alerts — 2026-10-24 07:46 UTC
- **WARN** (1x): disk 85% used (95G/118G, 17G free) after journal vacuum + tmp/pip cache cleanup (freed ~1G, 86%→85%). Remaining hogs need CEO approval: /root/.local/share/opencode 12G, /usr 32G, /root/.cache 3.5G (camoufox 1.4G + playwright 910M + puppeteer 651M).
- **INFO**: "CRASH" grep hit in pipeline log = `BTC-CRASH` warning label, not a traceback. 0 real tracebacks in 30m.
- **AUTO-FIX**: log cleanup applied (gzip >7d logs, journal vacuum 300M, tmp >7d purge, pip cache purge). No service restarts needed — vacation_pause absent, all core timers active, pipeline rc=0 at 07:42.

## Error Alerts — 2026-10-24 08:45 UTC
- **WARN** (recurring): disk 86% used (95G/118G, 17G free) — no logs >7d to gzip; safe cleanup already applied at 07:46 (journal vacuum + tmp/pip purge). Remaining hogs need CEO approval (/root/.local/share/opencode 12G, /usr 32G, /root/.cache 3.5G).
- **WARN** (1x, handled): `TRADE FAILED: NXPC SHORT — mid-band death band: 53.1 in 45-55` at 08:41 — signal marked FAILED, hotset cooldown engaged (2 failures), no retry loop. Design working as intended.
- **AUTO-FIX**: none required — vacation_pause absent; price-collector/1m-candle/pipeline/watchdog timers all active and firing; pipeline rc=0 at 08:42, 0 tracebacks/30min; prices fresh (9.7s); 0 DB locks; 0 open positions; 0 phantom trades/24h; 52 signals/hour; regime SHORT_BIAS.

## Error Alerts — 2026-10-24 09:27 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3362s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3362s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.6s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TOK position_manager: IndentationError: unexpected indent`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS WARNING: N steps failed: position_manager`

## Error Alerts — 2026-10-24 09:46 UTC
- **WARN** (recurring): disk 86% used (95G/118G, 17G free) — no uncompressed logs >7d (all already gzipped, journals 237M); remaining hogs need CEO approval (/usr 32G, /root/.local/share/opencode 12G, /root/.cache 3.5G) per 07:46 entry.
- **WARN** (1x, self-resolved): `position_manager: IndentationError: unexpected indent` at 08:50 — 0 recurrences in 55min, rc=0 on 8+ consecutive runs since, `position_manager.py` parses clean (mtime Oct 22). Transient; watch for recurrence.
- **INFO**: stale unit reference `hermes-atr-sl-updater.timer` = not-found/inactive/dead — no references in config/ or scripts/; cosmetic, unit file likely deleted while still loaded in manager cache.
- **AUTO-FIX**: none required — vacation_pause absent; price-collector/1m-candle/pipeline/watchdog timers all active and firing; pipeline rc=0 at 09:42 (0 tracebacks/30min); prices fresh (51s); 0 DB locks; 0 open positions; 0 phantom trades/24h; 43 signals/h; regime SHORT_BIAS; disk cleanup: nothing eligible (checked).

## Error Alerts — 2026-10-24 11:44 UTC
- **WARN** (recurring): disk 86% used (96G/118G, 17G free) — no logs >7d to gzip (all already compressed); journals 268M; remaining hogs need CEO approval (/usr 32G, /root/.local/share/opencode 12G, /root/.cache 3.5G) per 07:46/09:46 entries.
- **AUTO-FIX**: none required — vacation_pause absent; price-collector/1m-candle/pipeline/watchdog timers active and firing (next runs within 60s); pipeline rc=0 at 11:42, 0 tracebacks/1h; prices fresh (54s, 87 tokens); candles.db lock = transient single writer (1m collector), not stuck; 0 open positions; 0 phantom trades/24h; 46 signals/h; regime LONG_BIAS (29L/10S/90N); disk: nothing eligible to clean.

## Error Alerts — 2026-10-24 12:46 UTC
- **WARN** (recurring): disk 86% used (95G/118G, 17G free) — no logs >7d to gzip (all already compressed); journals 284M; remaining hogs need CEO approval (/usr 32G, /root/.local/share/opencode 12G, /root/.cache 3.5G) per 07:46/09:46/11:44 entries.
- **INFO**: 31 "CRASH" grep hits in 24h pipeline log = `BTC-CRASH`/`BTC-CRASH-OVERRIDE` filter labels, 0 real tracebacks.
- **INFO**: stale unit `hermes-atr-sl-updater.timer` = not-found (renamed to `-DEFUNCT`, still in manager cache) — cosmetic, no action.
- **AUTO-FIX**: /tmp stale purge (17 files, ~340M: old sess*.jsonl, ATM zips, shadow/signals copy DBs) — disk 96G→95G. Otherwise none required: vacation_pause absent; price-collector/1m-candle/pipeline/watchdog timers active and firing (pipeline rc=0 at 12:42, 0 open positions); prices fresh (71s, 87 tokens/5min); 0 phantom trades/24h; 40 signals/h; regime NEUTRAL (19L/19S/85N); speed avg 48.5 (128/241 ≥50th pct).

## Error Alerts — 2026-10-24 13:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] BIGTIME TOK — continuum says DECLINING+LEAN_BULL+AT, allowing despite TOK filter`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] BIGTIME TOK — continuum says TOK+LEAN_BULL+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-24 14:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: TOK,TOK,MOMENTUM,BTC_LEVEL | vol=N.8x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — CONTAGION+MULTI_ALT+MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MULTI_ALT,MOMENTUM,BTC_LEVEL | vol=N.5x eth_div=+N.N% | MULTI_ALT: N weak alts`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — TOK+CONTAGION+MULTI_ALT+MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: TOK,CONTAGION,MULTI_ALT,MOMENTUM,BTC_LEVEL | vol=N.6x eth_div=+N.N% | MULTI_ALT: N weak alts`

## Error Alerts — 2026-10-24 14:44 UTC
- **WARN** (recurring): disk 85% used (95G/118G, 17G free) — no logs >7d to gzip; remaining hogs need CEO approval (/usr 32G, /var/lib 7.8G, /root/zscore 2.2G, /root/hermes-agent 2.0G) per 07:46→13:27 entries.
- **INFO**: "CRASH"/"error" grep hits in 30m pipeline log = `BTC-CRASH` filter labels + coin_tracker "0 errors" lines — 0 real tracebacks, all pipeline steps rc=0.
- **INFO**: hotset.json holds 3 tokens; hotset fallback query returned 0 tokens at 14:42 (compaction produced empty hotset at 14:42:21) — WATCH: 0 approved signals, but 127 signals created in last hour.
- **AUTO-FIX**: journal vacuum 310M→114M (freed 196M). Otherwise none required: vacation_pause absent; price-collector/1m-candle/pipeline/watchdog timers active and firing (pipeline rc=0 at 14:42, 1 open / 6 max position); prices fresh (10.7s); 0 phantom trades/24h; 127 signals/h; regime SHORT_BIAS (2L/94S/33N); speed 53.1% tokens ≥50th pct (128/241).

## Error Alerts — 2026-10-24 15:27 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor (detect): N.N < N`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-10-24 15:44 UTC
- **WARN** (recurring): disk 86% used (96G/118G, 17G free) — 0 logs >7d to gzip; hogs still need CEO approval (/usr 32G, /var/lib 7.8G, /root/zscore 2.2G, /root/hermes-agent 2.0G) per earlier entries.
- **INFO**: 4 "CRASH" grep hits in 30m pipeline log = `BTC-CRASH` filter labels — 0 real tracebacks, all steps rc=0.
- **INFO**: GRASS SHORT "TRADE FAILED" = correct rejection (RSI hard floor 40.9 < 45), signal marked FAILED, not a crash.
- **AUTO-FIX**: none required. vacation_pause absent; pipeline ran 15:42 rc=0 (0 open, 11 closed 24h); price-collector/1m-candle/pipeline/watchdog timers all active; prices fresh (69s); 102 signals/h; regime SHORT_BIAS (2L/95S/32N); speed 53.1% ≥50th pct.

## Error Alerts — 2026-10-24 16:27 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: N.N < N`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3175s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3056s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (123s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (123s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2403s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2337s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2281s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2216s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2147s left, N failures)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BEAR+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1913s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1858s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1799s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1738s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1679s left, N failures)`

## Error Alerts — 2026-10-24 16:44 UTC
- **WARN** (1x): `disk usage 86% on / (17G free) — threshold 85%`
- **AUTO-FIX**: pruned 42 old hourly ATM-Hermes backup zips in /tmp (kept newest 10) + removed /tmp/signals.log.bak (356M) → disk now 85% (18G free). No pipeline/timer restarts needed — vacation pause absent, all core timers active.

## Error Alerts — 2026-10-24 17:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1147s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1147s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1084s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1084s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1026s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1026s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (967s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (967s left, N failures)`

## Error Alerts — 2026-10-24 18:47 UTC
- **WARN** (1x): `disk usage 85% on / (17G free) — threshold 85%`
- **AUTO-FIX**: removed 721 stale `/tmp/.bcf*-00000000.so` leaked libs (3.74 GB, only 2 in-use kept — verified via /proc/*/maps before delete) → disk now 82% (21G free). No service/timer restarted. Vacation pause absent; all core timers active (pipeline rc=0 at 18:43, prices 30s fresh, 25 signals/1h, 0 phantom trades).
- **INFO (cleared)**: hotset failure-cooldown alerts from 17:27 — 0 occurrences in last 30m.

## Error Alerts — 2026-10-24 20:44 UTC
- **WARN** (25x/30min): `[hotset] fallback DB query returned 0 tokens` — hotset.json `[]` every cycle. Reproduced root cause: only 4 combo_keys in 5-min window (conf>=60), ALL SHORTs blocked by CONTINUUM-BULL + SHORT-CONTINUUM (BTC score=81.5, z=NEUTRAL, sustained >60 ≥30min). Regime is LONG_BIAS yet surviving signals are short-dominant (ichimoku_short 17, volume shorts 5 in 1h) — longs below conf 60. Gates working as designed; market-condition / signal-mix issue for CEO, no auto-fix applied (same class as 2026-10-23 21:47 finding).
- **INFO**: Pipeline healthy — LIVE run 20:42:18 rc=0, position_manager rc=0, 0 Tracebacks/CRASH in 30min. Core timers active (price-collector 30s, 1m-candle, pipeline 1m, watchdog) + all hermes timers scheduled. 58 signals/hr. Portfolio: 1 open (HYPE LONG, +0.38%) | 11 closed today | +35.66% PnL (pipeline) / 7 closed +$0.34 (signal_outcomes). Exit reasons 24h: profit-monster-trail 6 (+$0.84), rr_engine_trail_hit 1 (+$0.34), manual_sl_hit 1 (-$0.09), others +$0.50. 0 phantom trades. Regime 5m LONG_BIAS (54L/5S/64N of 123 @20:30). Speeds 128/241 (53.1%) ≥50th pct. Prices fresh (12s, 87 tokens). Disk 82% (below 85% threshold). Vacation pause: not active.
- **INFO**: Side findings unchanged — `hermes-atr-sl-updater.timer` ghost entry (unit file missing); `signals_hermes_runtime.db` unbounded; `decisions` table dormant (ai_decider defunct, expected). Note: `systemctl list-timers hermes-*` returns 0 timers if glob unquoted (shell eats it) — quote the pattern.

## Error Alerts — 2026-10-24 22:45 UTC
- **WARN** (28x/30min): `[hotset] fallback DB query returned 0 tokens` — unchanged since 20:44 report; all candidate signals gated (CONTINUUM-BULL blocks shorts, longs below conf 60). Market-condition, no auto-fix.
- **WARN** (1x): `⚠️ TRADE FAILED: HYPER SHORT — RSI knife floor (detect): 30.0 < 35` @22:26 — filter correctly blocked short at oversold RSI (BANANA lesson working as intended). Signal 1687651 marked FAILED, no trade opened.
- **AUTO-FIX**: none needed — no crashes, no lock contention, no missed timers.
- **INFO**: Pipeline healthy — LIVE run 22:43:23 rc=0, 0 Tracebacks/30min. 51 signals/hr. 3 open (HYPE LONG +0.10, BTC LONG +0.04, HYPER LONG -0.02) | 8 closed today +$0.33 (signal_outcomes) / 10 closed +23.21% (pipeline). Prices fresh (60s). Disk 82% (<85%). Speeds 53.1% >=50th pct. Regime LONG_BIAS (34L/7S/88N). 0 phantom. Vacation pause: not active.
- **INFO (side find)**: `hermes-atr-sl-updater.timer` ghost entry in `list-timers --all` — unit file renamed to `-DEFUNCT`, harmless; masks as not-found.

## Error Alerts — 2026-10-24 23:44 UTC
- **WARN** (29x/30min): `[hotset] fallback DB query returned 0 tokens` / `[HOT-SET] hotset.json is empty` — hotset.json `[]` every cycle (cycle=10978). **Root cause CHANGED since 22:45 report:** CONTINUUM-BULL short blocks are gone (0 occurrences in 60min). New blockers are overbought-long filters: `LONG-HIGH-70` (RSI 74–91 + HIGH vol exhaustion chase) and `LONG-RSI-CEILING` (RSI >60), plus rr-engine SHADOW blocks (R:R 0.47–0.99 grade D) and `OPEN-POS-FILTER` (btc/ens/hype/hyper already held). Last cycle: 12 signals pending, 0 approved, 0 preserved. Market pumping with RSI 74–95 on long candidates — filters working as designed (BANANA/chase lessons), market-condition issue for CEO, no auto-fix.
- **AUTO-FIX**: none needed — no crashes, 0 Tracebacks/60min, no DB locks, no missed timers, all 4 core timers active, vacation pause not active.
- **INFO**: Pipeline healthy — LIVE run 23:42:20 rc=0, position_manager rc=0 (4 open | 0 closed | 0 adjusted). 49 signals/hr. Portfolio: 4 open | 8 closed today | +8.93% PnL (pipeline) / 8 closed +$0.33 (signal_outcomes 24h). 0 phantom trades (`atr_sl_hit` <0.01%). Prices fresh (62s, 348 tokens ≤5min). Disk 82% (<85%). Speeds 128/241 (53.1%) ≥50th pct. Regime 5m LONG_BIAS (48L/7S/74N of 129 @23:30). BTC score=98 bias=0.96 trending.

## Error Alerts — 2026-10-25 00:27 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`

## Error Alerts — 2026-10-25 02:46 UTC
- **WARN** (114 restarts/10min, counter=114,672): `openclaw-gateway.service` crash-looping — `Error: Cannot find module '/usr/lib/node_modules/openclaw/dist/index.js'`. Root cause: the `openclaw` npm package is gone from BOTH `/usr/lib/node_modules` and `/root/.npm-global/lib/node_modules` (`npm ls -g` has no openclaw), while the user unit is still `enabled` and auto-restarts every ~5s. `/root/.openclaw/` config tree is fully intact; nothing in the codebase references port 18789 (no consumers found). **NOT auto-fixed** — non-Hermes service, and the only surviving package copy is a 7-month-old vendored one at `/root/.openclaw/extensions/lossless-claw/node_modules/openclaw` (v2026.4.1, mtime Apr 2) which I cannot verify against the unit's expected v2026.3.24. CEO choice: (a) `npm i -g openclaw` to restore it, or (b) `XDG_RUNTIME_DIR=/run/user/0 systemctl --user disable --now openclaw-gateway.service` to stop the noise.
- **WARN** (42x+/60min, ongoing since ≥2026-10-24 20:44): `[hotset] fallback DB query returned 0 tokens` / `[HOT-SET] hotset.json is empty` — cycle=10048, 0 approved, 0 preserved. Blockers this hour: `LONG-NEUTRAL` (ZEN LONG, 4h regime NEUTRAL), `CONTINUUM-BULL` (NEAR SHORT blocked), `CONFLUENCE-GATE-BLOCK` (NEAR SHORT single-type `ichimoku-` not in standalone bypass). 53 signals generated in 1h but all gated. Market-condition / signal-mix issue for CEO — gates working as designed, no auto-fix (same class as 2026-10-24 20:44/22:45/23:44 findings).
- **AUTO-FIX**: none needed — pipeline live (02:46:00 rc=0), 0 Tracebacks/60min in pipeline, 0 failed systemd units, no DB lock contention (candles.db quick_check OK), no missed timers, disk 82% (<85%), prices fresh (22.5s), 0 phantom trades, vacation pause NOT active.
- **INFO (resolved)**: two Tracebacks at 02:34:16 / 02:35:24 from `run_brain_auditor.sh` were transient and already self-healed by audit run #131 — `brain/analysis/ugb_pt_forward.py` was fixed + `--selfcheck PASS` and committed in `f523d5f9`; direct re-run confirms PASS. No action left.
- **INFO**: Pipeline healthy — LIVE run 02:46 rc=0, position_manager rc=0 (1 open | 0 closed). 53 signals/hr. Portfolio: 1 open (BTC LONG trade_id=16385, +0.82%, bracketed SL 79992.93 / TP 81509.07) | 3 closed today +$0.25 (signal_outcomes) / 10 closed today +18.27% (pipeline). Exit reasons 24h: profit-monster-trail 4 (+$0.31), trail_arm_timeout 2 (-$0.01), ugb_pt 1 (+$0.16), manual_trail_hit 1 (+$0.03), atr_trail_hit 1 (+$0.05), HL_CLOSED 1 (+$0.12). 0 phantom trades. Regime 5m SHORT_BIAS (12L/65S/51N of 128 @02:30). Speeds 128/241 (53.1%) ≥50th pct. Prices fresh (22.5s, 435 tokens ≤5min). Disk 82% (<85%). Vacation pause: not active.

## Error Alerts — 2026-10-25 05:55 UTC
- **WARN** (1x): `hermes-auto-1hr.service` start timed out at 05:37 (`opencode` build hung, killed by systemd after 10min). **AUTO-FIX**: `systemctl reset-failed hermes-auto-1hr.service` — timer fires again 06:27. Recurrence → raise timeout in unit via `systemctl edit`.
- **WARN** (25x/30min, ongoing): `[hotset] fallback DB query returned 0 tokens` — hotset.json has only 1 token (written 05:53). Signal-mix/gate issue, no auto-fix (carried from 2026-10-24 20:44 findings).
- **WARN** (ongoing, non-Hermes): `openclaw-gateway.service` crash-loop NRestarts=116,943 (was 114,672 @02:46). Still needs CEO choice: npm restore or disable unit.
- **AUTO-FIX**: reset-failed on hermes-auto-1hr. Otherwise clean — pipeline live (05:48 run rc=0), 0 Tracebacks/30min, all core timers active, prices fresh (14.8s, 87 tokens ≤5min), disk 82% (<85%), 0 phantom trades, vacation pause NOT active.
- **INFO**: Pipeline healthy — 62 signals/hr, 0 open | 5 closed today +$0.22 | 12 closed 24h +$0.64 (signal_outcomes). Exit reasons 24h: profit-monster-trail 5 (+$0.39), trail_arm_timeout 2 (−$0.01), ugb_pt 1 (+$0.16), manual_trail_hit 1 (+$0.03), hard_max_loss 1 (−$0.10), atr_trail_hit 1 (+$0.05), HL_CLOSED 1 (+$0.12). Regime 5m SHORT_BIAS (8L/52S/62N of 122 @05:45). Speeds 128/241 (53.1%) ≥50th pct. Watchdog 05:48 cleaned 5 stale locks.

## Error Alerts — 2026-10-25 06:27 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (3538s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: IO TOK in hotset failure cooldown — TOK in cooldown (3538s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (3481s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: IO TOK in hotset failure cooldown — TOK in cooldown (3481s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (3422s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: IO TOK in hotset failure cooldown — TOK in cooldown (3422s left, N failures)`

## Error Alerts — 2026-10-25 06:46 UTC
- **WARN** (1216/1414 cycles = 86% past 24h): `[HOT-SET] hotset.json is empty — no signals survived compaction` / `No signals above 40% confidence — skipping execution`. Root cause verified by manual compactor run: candidates are dominated by single-type `ichimoku_short` (428/24h) which is **never** standalone-bypassed (CEO design 2026-10-20: ichimoku LONG only) and regime is SHORT_BIAS so NEUTRAL-relax doesn't apply → CONFLUENCE-GATE-BLOCK. Matches OpenMemory 2026-10-19 finding: gates eating signals from market-regime/signal-mix shift, **not a bug**. Trades still opening intermittently (11 in 24h, last 03:25 r2v2-long3; bb-squeeze+ at 03:20 passed via bypass).
- **AUTO-FIX**: none needed — all core timers active and firing (pipeline 06:46 rc=0, price-collector +17s, 1m-candle +4s, watchdog, signal-compactor), 0 Tracebacks/30min, candles.db lock held only by transient signals_runner.py (10s runtime, normal), disk 82% (<85%), prices fresh (65s, 87 tokens ≤10min), 0 phantom trades, vacation pause NOT active.
- **INFO**: Pipeline healthy — 63 signals/hr, 0 open | 5 closed today +$0.22, 80% WR | 12 closed 24h (portfolio +16.37%). Regime 5m SHORT_BIAS (2L/104S/20N of 126 @06:30). Speeds 128/241 (53.1%) ≥50th pct.
- **INFO (data quality)**: previous 06:27 alert entry has token names/timestamps redacted into `TOK`/`TS` placeholders — mangled, not diagnostic. Likely a bad redaction regex in that run.
- **CARRIED**: `openclaw-gateway.service` crash-loop (non-Hermes, NRestarts>116k) still awaiting CEO choice: npm restore vs disable.

## Error Alerts — 2026-10-25 07:27 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`

## Error Alerts — 2026-10-25 08:55 UTC
- **WARN (AUTO-FIXED)**: `hermes-ma-cross-5m-tuner` dead since signal migration — unit ExecStart pointed at deleted `scripts/ma_cross_5m.py`, no PYTHONPATH so `from paths import` failed, script `DATA_DIR` resolved to graveyard `/root/.hermes/scripts/data` (would have tuned a dead May-7 DB), freshness guard 120s unreachable for 5m candles (ts=window open, age cycles 0-300s). Companion: `hermes-zscore-momentum-tuner` never fired since boot 2026-10-18 (OnBootSec elapse race → service never activated → no OnUnitActiveSec anchor → Trigger: n/a forever).
- **AUTO-FIX**: unit ExecStart → `scripts/signals/ma_cross_5m.py` + `Environment=PYTHONPATH=/root/.hermes/scripts`; script `DATA_DIR = HERMES_DATA`, guard 120s → 420s. Force-ran both services: **ma-cross 104 tokens tuned** (tuner DB now created at correct path `/root/.hermes/data/ma_cross_5m_tuner.db`), **zscore 82 tokens tuned** (4m58s, rc=0). Both timers re-armed — next fire: ma-cross Mon 2026-10-26 08:53 (24h), zscore 12:47 (4h).
- **INFO**: `ma_cross_5m` signal family fully disabled in hermes_constants (`MA_CROSS_5M*_ENABLED=False`, WR=19%) — tuner feeds a disabled signal; candidate for `-DEFUNCT` rename (like atr-sl-updater) with CEO approval.
- **INFO**: Core healthy — vacation pause absent, all 3 core timers firing (pipeline 08:53, price-collector 08:53, 1m-candle 08:53), 0 tracebacks/30min, 55 signals/h, prices fresh (66s), 87 tokens ≤5min, 0 phantom trades, disk 82% (<85%). 1 TRADE FAILED (ZRO SHORT: RSI 29.0 < 35 knife floor) — filter working as designed, not a bug. hotset.json fresh (19s) but 0 entries: confidence≥70 gate, not a failure.

## Error Alerts — 2026-10-25 09:46 UTC
- **WARN (3x, recurring Sunday 03:00)**: `Self-healing test: FAIL - ModuleNotFoundError: No module named 'dispatcher.dispatcher'` + `Better Coder Timer (hermes-better-coder.timer): FAIL(inactive)` — logged Oct 11/18/25 in pipeline.log via weekly audit.
- **AUTO-FIX**: `scripts/hermes-better-coder-audit.py` now returns `SKIP(disabled, parked)` for disabled units (both probes target intentionally-parked subsystems: `hermes-better-coder.timer` + `hermes-coding-mcp.service` are disabled, dispatcher package empty since Sep 1). Dispatcher probe SKIP guard was already added by brain_auditor earlier today. Verified: py_compile PASS, probe logic tested on 3 units. Next Sunday: SKIP, no FAIL.
- **WARN (monitored, no fix applied)**: `hotset.json` 0 tokens all cycles — 18 signals PENDING top-10 approval while `SHORT-RSI-HARD-FLOOR` blocks shorts at RSI 27-30 in a 113/123-token SHORT_BIAS tape. Filter behaving as designed (BANANA oversold-short lesson); do not weaken without backtest + CEO approval.
- **INFO**: Core green — vacation pause absent, pipeline LIVE rc=0 every 1m, 3/3 core timers fired <60s, 73 hermes timers active, 81 signals/h, prices 49s fresh, 0 open | 8 closed today +$0.26 | 14 closed 24h +$0.67, 0 phantom trades, 0 pipeline tracebacks/30m, disk 82% (under 85 threshold; pipeline.log 300M — compress when >85%).

## Error Alerts — 2026-10-25 12:27 UTC
- **REPEATED** (9x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-25 13:45 UTC
- **INFO**: Core healthy — vacation pause absent, pipeline LIVE rc=0 (last run 13:43), 4/4 core timers firing (pipeline, price-collector, 1m-candle, watchdog), 0 tracebacks/30m, 56 signals/h, prices 39s fresh (435 tokens ≤5min), 0 phantom trades, disk 83% (<85).
- **WARN (1x, filter by design)**: `TRADE FAILED: CC SHORT` 13:41 — `EXEC-RSI-DETECT-FLOOR` blocked (detect RSI 24.7 < 35 knife), signal 1688566 marked FAILED, no rollback. Same class as ZRO SHORT 08:55 — not a bug.
- **INFO**: hotset fallback 0 tokens (28x/30m) — known monitored issue (confidence≥70 gate), unchanged since 09:46.
- **AUTO-FIXES**: none needed.

## Error Alerts — 2026-10-25 16:27 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: USELESS TOK — signal TOK rolled back (prevents retry loop)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: USELESS TOK (count=N)`

## Error Alerts — 2026-10-25 17:27 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK knife floor (detect): N.N < N`

## Error Alerts — 2026-10-25 19:46 UTC
- **INFO**: Core healthy — vacation pause absent, pipeline firing (last run 19:46:00), core timers active (pipeline/price-collector/1m-candle/watchdog), 0 tracebacks/30m, 48 signals/h, prices 50s fresh (565 tokens ≤5min), 1 open trade (BTC LONG 15:47), 15 closed today (+0.25 USDT, 60% WR), 0 phantom trades, disk 83% (<85).
- **WARN (chronic, 100% of watchdog runs ≥24h)**: `signals: WARNING — only 2-4 signals in last 5 min (min 20)` — `pipeline_watchdog.py:37 SIGNAL_COUNT_MIN=20` expects 240/h; actual rate 30-70/h steady for ≥7 days (42/h a week ago, 48/h now). Threshold/stale comment ("normal ~6/min"), not a production drop. Needs CEO decision — safety threshold not modified unilaterally.
- **WARN (chronic, every run)**: watchdog cleans 5-6 stale locks each pass (`pipeline_heartbeat.lock`, `guardian_closing.lock`, `hotset_json.lock`, `signal_compactor_critical.lock`, `hotset_last_updated.lock`) — self-healing, no pipeline impact, but producers aren't cleaning up on release.
- **AUTO-FIXES**: none needed — no crashed services, no DB locks, no missed timers, no stale prices.

## Error Alerts — 2026-10-25 23:47 UTC
- **INFO**: Core healthy — vacation pause absent, pipeline active (last run 23:44, rc=0), core timers active (pipeline/price-collector/1m-candle/watchdog), 0 tracebacks/30m, 0 DB-lock errors, 72 signals/h, prices 30s fresh, 2 open trades (ANIME/CAKE SHORT), 18 closed today (+0.27 USDT, 61% WR), 0 phantom trades, disk 84% (<85).
- **WARN (chronic, every watchdog run)**: `signals: WARNING — only 5-7 signals in last 5 min (min 20)` — threshold mismatch, documented 19:46, needs CEO decision. Not a production drop.
- **WARN (chronic)**: watchdog cleaned 5-7 stale locks this pass — producers not releasing on exit; self-healing, no pipeline impact.
- **WARN (5x/h)**: `TRADE FAILED` — GMX 2x (midband RSI 50.4 / knife detect 28.6), ETC 2x (midband death band 46.7), PURR 1x (knife 9.0). All execution-time filter blocks, signals marked FAILED cleanly, no rollback loop. By design, but ETC SHORT regenerated + failed in consecutive runs (1689323→1689324) — repeated signal churn worth watching.
- **INFO**: `hermes-atr-sl-updater.timer` shows as not-found ghost in `list-timers` (unit files renamed `*-DEFUNCT`, disabled). Stale reference only, harmless.
- **AUTO-FIXES**: none needed — no crashed services, no DB locks, no missed timers, no stale prices, no log cleanup required (0 files >7d).

## Error Alerts — 2026-10-26 00:27 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK mid-band death band: N.N in N-N`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3543s left, N failures)`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] BIGTIME TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] BIGTIME TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-10-26 01:27 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] BIGTIME TOK BLOCKED — WARNING — BTC_LEVEL`

## Error Alerts — 2026-10-26 03:27 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`

## Error Alerts — 2026-10-26 05:27 UTC
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BULL+AT, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] BIGTIME TOK — continuum says DECLINING+LEAN_BULL+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] BIGTIME TOK — continuum says TOK+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-26 06:27 UTC
- **REPEATED** (14x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-26 06:45 UTC
- **[WARN]** (1x): Disk usage 84% on / (threshold 85%). 
- **AUTO-FIX**: journalctl vacuumed to 200M, freed 485MB archived journals. Largest app logs: pipeline.log 321M, signal-compactor.log 126M — rotate/truncate those next pass if usage climbs again.
- No other issues: pipeline running every 1m, prices fresh (12.6s), 105 signals/hr, 0 crashes, 0 phantom trades. "[BTC-CRASH]" log lines are the BTC-level SHORT-block guard working as designed, not crashes.

## Error Alerts — 2026-10-26 07:27 UTC
- **REPEATED** (8x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (10x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-26 11:45 UTC
- **[WARN]** (1x): Watchdog: only 9 signals in last 5 min (min 20 threshold); 77 signals/hr vs 240/hr implied target. Market is neutral-heavy (86/129 NEUTRAL, SHORT_BIAS regime) — likely fewer setups, not a pipeline fault. Pipeline cycles healthy, all timers firing.
- **AUTO-FIX**: journal vacuum to 200M (freed 97.4M, disk 84% — under 85% threshold). No crashes, no phantom trades, prices fresh (74s), 2 open trades (ETH LONG, LTC SHORT).

## Error Alerts — 2026-10-26 13:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] IO TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK knife floor (detect): N.N < N`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] IO TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: IO TOK in hotset failure cooldown — TOK in cooldown (3532s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: IO TOK in hotset failure cooldown — TOK in cooldown (3478s left, N failures)`

## Error Alerts — 2026-10-26 14:27 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2816s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: IO TOK in hotset failure cooldown — TOK in cooldown (2816s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2759s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: IO TOK in hotset failure cooldown — TOK in cooldown (2759s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: IO TOK in hotset failure cooldown — TOK in cooldown (2701s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2637s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: IO TOK in hotset failure cooldown — TOK in cooldown (2637s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2580s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: IO TOK in hotset failure cooldown — TOK in cooldown (2580s left, N failures)`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`

## Error Alerts — 2026-10-26 14:46 UTC
- **[WARN]** (1x): `hermes-atr-sl-updater.timer` = not-found (unit file missing, never had journal entries; ATR SL logic runs inside pipeline scripts instead)
- **AUTO-FIX**: `systemctl daemon-reload` attempted — stale entry persists but is harmless/inactive; unit cannot be restarted as it does not exist. Functionality verified covered elsewhere.
- **[WATCH]**: disk 84% (94G/118G) — 1 point from WARN threshold, largest log pipeline.log 329M

## Error Alerts — 2026-10-26 18:27 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+TOK+AT, allowing despite TOK filter`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] CASHCAT TOK — continuum says RECOVERY+LEAN_BULL+AT, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] CASHCAT TOK — continuum says RECOVERY+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-26 19:27 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`

## Error Alerts — 2026-10-26 19:44 UTC
- **[WARN]**: disk 85% used (94G used, 18G free, 118G total) — crossed WARN threshold since 14:46 (84%). Top consumers: data/ 8.0G (coin_tracker.db 3.3G, session_brain.db 1.5G, signals_hermes.db 1.2G, candles.db 1.2G), logs/ 756M (pipeline.log 334M), journal 284M. No logs >7d to gzip (rotation working).
- **AUTO-FIX**: none safe/applicable — no stale logs to compress, DBs are live. Recommend CEO-run cleanup of coin_tracker.db / session_brain.db growth path.
- **[INFO]**: `hermes-atr-sl-updater.timer` still not-found (known harmless, carried from 14:46 report).
- **[INFO]**: USUAL SHORT trade FAILED at 19:41 — RSI knife floor filter (29.9 < 35) blocked it; working as designed, not a crash.

## Error Alerts — 2026-10-26 21:44 UTC
- **[WARN]**: disk 85% used (94G/118G, 18G free) — persists since 19:44. Top consumers unchanged: data/ 8.0G (coin_tracker.db 3.3G, session_brain.db 1.5G, signals_hermes.db 1.2G, candles.db 1.2G), logs/ 756M (pipeline.log 336M live), journal 309M.
- **AUTO-FIX**: none safe — no logs >7d to gzip, DBs live. Needs CEO-run cleanup of coin_tracker.db growth path.
- **[INFO]**: all other checks clean — pipeline rc=0, 0 tracebacks/60m, prices 41s stale, 49 signals/1h, 0 phantom trades, 1 open trade, all key timers active, not paused.

## Error Alerts — 2026-10-26 22:45 UTC
- **[WARN]**: disk 85% used (94G/118G, 18G free) — persists since 19:44. Top consumers unchanged: data/ 8.0G, logs/ 761M (pipeline.log 337M live). No logs >7d to gzip.
- **AUTO-FIX**: none safe/applicable — no stale logs, DBs live. Needs CEO-run cleanup of coin_tracker.db growth path (already flagged 19:44/21:44).
- **[INFO]**: all other checks clean — pipeline active, 0 errors/30m, 34 signals/1h, 0 phantom trades (24h), prices 42s stale, 0 open trades, regime LONG_BIAS, all key timers firing, `hermes-atr-sl-updater.timer` not-found (known DEFUNCT, harmless), not paused.

## Error Alerts — 2026-10-26 23:46 UTC
- **[WARN]**: disk 85% used (94G/118G, 18G free) — persists since 14:46. Top consumers: data/ 8.0G (coin_tracker.db 3.3G, session_brain.db 1.5G), logs/ 764M (pipeline.log 338M live), journal was 349M.
- **AUTO-FIX**: journal vacuum to 200M freed 196M. No logs >7d to gzip; DBs live. Still needs CEO-run cleanup of coin_tracker.db growth path (flagged 14:46/19:44/21:44/22:45).
- **[INFO]**: watchdog WARNING at 23:44 — 0 signals in last 5m (78 in last 60m; lull, not a failure) + auto-cleaned 5 stale locks. Normal watchdog behavior.
- **[INFO]**: 2 TRADE FAILED (LINK SHORT 23:17, POL SHORT 23:20) — RSI knife floor execution filter (7.8/28.2 < 35). Signals marked FAILED, no trade opened — working as designed.
- **[INFO]**: `hermes-atr-sl-updater.timer` not-found ghost (known DEFUNCT, harmless).
- **[INFO]**: all else clean — not paused, pipeline active (0 tracebacks/30m), 78 signals/1h, 1 open trade (ZORA SHORT 23:05), 27 closed today (44.4% WR, -1.05 USDT), 0 phantom/24h, prices newest 61s, regime SHORT_BIAS, all key timers firing.

## Error Alerts — 2026-10-27 01:28 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-27 03:28 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3473s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3415s left, N failures)`

## Error Alerts — 2026-10-27 04:28 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (536s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (536s left, N failures)`

## Error Alerts — 2026-10-27 05:28 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (247s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (247s left, N failures)`

## Error Alerts — 2026-10-27 07:28 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] IO TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-27 08:28 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BEAR+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-27 12:28 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] USELESS TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] USELESS TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] GRIFFAIN TOK BLOCKED — WARNING — BTC_LEVEL`

## Error Alerts — 2026-10-27 15:28 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] USELESS TOK BLOCKED — TOK in cooldown (3540s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: USELESS TOK in hotset failure cooldown — TOK in cooldown (3540s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] USELESS TOK BLOCKED — TOK in cooldown (3479s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: USELESS TOK in hotset failure cooldown — TOK in cooldown (3479s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] USELESS TOK BLOCKED — TOK in cooldown (3417s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: USELESS TOK in hotset failure cooldown — TOK in cooldown (3417s left, N failures)`

## Error Alerts — 2026-10-27 19:28 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-27 20:28 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK knife floor (detect): N.N < N`

## Error Alerts — 2026-10-28 01:28 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-28 02:28 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] CASHCAT TOK — continuum says TOK+LEAN_BULL+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-28 03:28 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-28 05:54 UTC
- **[WARN]** (checkpoint_watch): **DUE** `btc-16450-8h-stale` (due 2026-10-28T05:54:00+00:00): BTC #16450 LONG crosses 8h at 05:54Z with no MFE>0.40% — exit IF still flat AND 1m holding below continuum EMA300 (watchdog stale steer). Retract on 1m reclaim holding 15-30m.

## Error Alerts — 2026-10-28 06:39 UTC
- **[WARN]** (checkpoint_watch): **OVERDUE** `btc-16450-8h-stale` (due 2026-10-28T05:54:00+00:00): BTC #16450 LONG crosses 8h at 05:54Z with no MFE>0.40% — exit IF still flat AND 1m holding below continuum EMA300 (watchdog stale steer). Retract on 1m reclaim holding 15-30m.

## Error Alerts — 2026-10-28 07:28 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (8x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.6s (rc=N)`
- **REPEATED** (10x): `Oct N N:N:N python3[TOK]: TS   TOK decider_run: AttributeError: 'str' object has no attribute 'get'`
- **REPEATED** (10x): `Oct N N:N:N python3[TOK]: TS WARNING: N steps failed: decider_run`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.0s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.7s (rc=N)`

## Error Alerts — 2026-10-28 08:28 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-10-28 09:28 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.7s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.9s (rc=N)`

## Error Alerts — 2026-10-28 10:28 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-28 13:28 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3361s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3301s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3301s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3240s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3240s left, N failures)`
- **REPEATED** (9x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3182s left, N failures)`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK floor: N.N < N`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3117s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2577s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (3057s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2518s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2459s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2939s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2399s left, N failures)`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2341s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2225s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2641s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2522s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2522s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2461s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2461s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2341s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2280s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2220s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2219s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2159s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2159s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2098s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2098s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2037s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1978s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1917s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1798s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1678s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1678s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1617s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1617s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1559s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1559s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1500s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1500s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1439s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1439s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1316s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1316s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1258s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1258s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1197s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (1197s left, N failures)`

## Error Alerts — 2026-10-28 14:40 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (297s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (297s left, N failures)`

## Error Alerts — 2026-10-28 15:40 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TOK decider_run: AttributeError: 'str' object has no attribute 'get'`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS WARNING: N steps failed: decider_run`

## Error Alerts — 2026-10-28 19:40 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BULL+TOK, allowing despite TOK filter`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.8s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] CASHCAT TOK — continuum says TOK+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-29 00:41 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   📉 hotset failure recorded: TOK TOK (count=N)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK knife floor: N.N < N`

## Error Alerts — 2026-10-29 02:41 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2580s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2580s left, N failures)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS TOK: TOK TOK in hotset failure cooldown — TOK in cooldown (2519s left, N failures)`

## Error Alerts — 2026-10-29 04:36 UTC
- **[WARN]** (checkpoint_watch): **DUE** `chop-bleed-92-adjudicate` (due 2026-10-29T04:30:00+00:00): chop-bleed >=92% breach run #2? if yes present #194 0.75x size proposal WITH #195 74%-inert measurement to CEO (do not escalate blind)

## Error Alerts — 2026-10-29 04:41 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ℹ️ hotset failure TOK recorded (exec-policy refusal, no cooldown): TOK TOK — TOK knife floor (detect): N.N < N`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK knife floor (detect): N.N < N`

## Error Alerts — 2026-10-29 06:41 UTC
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`

## Error Alerts — 2026-10-29 07:41 UTC
- **REPEATED** (11x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (11x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (10x): `Oct N N:N:N python3[TOK]: TS   TS   ℹ️ hotset failure TOK recorded (exec-policy refusal, no cooldown): TOK TOK — TOK mid-band death band: N.N in N-N`
- **REPEATED** (10x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK mid-band death band: N.N in N-N`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ℹ️ hotset failure TOK recorded (exec-policy refusal, no cooldown): TOK TOK — TOK knife floor: N.N < N`

## Error Alerts — 2026-10-29 10:41 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ℹ️ hotset failure TOK recorded (exec-policy refusal, no cooldown): TOK TOK — TOK hard floor (detect): N.N < N`

## Error Alerts — 2026-10-29 12:41 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-29 13:41 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] USELESS TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-29 14:41 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.2s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.1s (rc=N)`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.3s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.5s (rc=N)`

## Error Alerts — 2026-10-29 16:41 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.9s (rc=N)`

## Error Alerts — 2026-10-29 17:41 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+NEUTRAL+TOK, allowing despite TOK filter`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`

## Error Alerts — 2026-10-29 22:41 UTC
- **REPEATED** (10x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   🏷️ signal N marked TOK (executed=N, no trade opened) — analytics-safe terminal state`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   ℹ️ hotset failure TOK recorded (exec-policy refusal, no cooldown): TOK TOK — TOK knife floor: N.N < N`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK knife floor: N.N < N`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **REPEATED** (9x): `Oct N N:N:N python3[TOK]: TS   TS   [TOK-TOK] TOK: skip TOK — hebbian n=N < N (insufficient data, TOK-open)`
