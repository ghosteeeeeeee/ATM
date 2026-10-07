# Error Alerts — 2026-10-07 09:48 UTC (health_monitor)

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
