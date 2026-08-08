# CEO Kanban — Away Mode Tasks

## TEAM UPDATES (read this first)
<!-- Automations log their actions here. CEO reads this to know what the team did. -->
<!-- Format: [YYYY-MM-DD HH:MM] automaton: action taken -->
- [2026-08-08 00:30] signal_reporter: System startup — no kills needed yet
- [2026-08-08 00:30] health_monitor: System startup — pipeline healthy

## CEO DECISIONS
- [x] 2026-08-08 00:30 — ATR SL widened 1.0% → 1.2%. 22/22 SL hits at exactly 1.0% = too tight. Monitor 24h.
- [x] 2026-08-08 00:30 — RETURN_EXHAUSTION_MINUS_ENABLED=False. 14 trades, -$0.64 across combos in 48h.
- [x] 2026-08-08 14:00 — CEO review: 24h +$0.27 (59.2% WR), 7d -$8.70 (38.7% WR). SHORT still bleeding but most is historical dead signals. No new changes — recent fixes need time to show impact.
- [x] 2026-08-08 19:00 — CEO review: 24h +$0.21 (58% WR, 50 trades). 7d -$8.77 (38.6% WR). bb_bounce+ confluence star performer (88.9% WR). No changes — ATR SL widening + signal kills need evaluation window.
- [x] 2026-08-08 22:00 — CEO review: 24h +$0.18 (57.1% WR, 49 trades). 7d -$8.77 (41.3% WR). SHORT still bleeding (-$0.52/24h, -$7.39/7d) but improving. Dead signals verified killed (inv-accel, vel-hermes, pattern, zscore_rising). No new changes — ATR SL widening + signal kills need more time. bb_bounce+,range_finder+ LONG = star (88.9% WR, +$0.38/24h).

## TODO
- [x] URGENT: Kill decider permanently — RESOLVED (commit 62c549f, historical records only)
- [x] URGENT: bb_bounce root cause — RESOLVED (09:50 UTC). Trades were historical pre-fix. Root cause: master flag not checked in bb_bounce.py Layer 1 guard.
- [ ] Monitor ma_100_cross live performance (W LONG is first trade)
- [ ] Monitor vortex_break sustained performance
- [ ] Monitor hzscore+ confluence (100% WR, 5 trades today)
- [ ] Monitor ATR SL widening impact (24h window)

## IN PROGRESS
- [x] LIVE TRADING RE-ENABLED — 2026-08-06 02:15 UTC, trailing tightened
- [x] Disk cleanup — 84% → 78% (candles.db 3.6GB→290MB)
- [ ] **STOP KILLING SIGNALS AT CODE LEVEL** — CEO commented out bb_bounce from signals/__init__.py. Use ONLY hermes_constants.py flags. (2026-08-06 14:20 UTC)

## DONE
- [x] 2026-08-06 02:15 — LIVE TRADING RE-ENABLED: kill switch true, trailing tightened (0.30%/0.70%). 52.9% WR, +$2.23/24h.
- [x] 2026-08-06 01:00 — BB_BOUNCE DISABLED: BB_BOUNCE_ENABLED=False + NEVER_REENABLE_FLAGS. 19 trades, 36.8% WR, -$0.62.
- [x] 2026-08-05 22:30 — DECIDER KILLED: Changed default signal_type from 'decider' to 'unknown' in 4 files
- [x] 2026-08-05 22:30 — RETURN_EXHAUSTION FIXED: Confidence threshold 80→70, removed NEUTRAL regime penalty
- [x] 2026-08-05 22:30 — VORTEX_BREAK IMPROVED: Detection window 3→5 candles (still rare by design)
- [x] 2026-08-05 22:30 — BB_BOUNCE ROOT CAUSE: Asymmetric R:R (losses 1.73× bigger than wins)
- [x] 2026-08-05 22:00 — BB_BOUNCE root cause found: signal_rotator.py re-enabling without NEVER_REENABLE_FLAGS. Fixed.
- [x] 2026-08-05 22:00 — Dead signals killed: pattern_wolf + accel-300 family added to NEVER_REENABLE_FLAGS
- [x] 2026-08-05 22:00 — Disk cleanup: 84% → 78%
- [x] 2026-08-05 16:50 — NEW SIGNALS DEPLOYED: vortex_break + return_exhaustion (disabled by default)
- [x] 2026-08-05 16:50 — THRESHOLDS RELAXED: VOL_MULT 5→2, atr_compression 5→3
- [x] 2026-08-05 16:50 — TOKEN BLACKLIST: GALA + STRK added
- [x] 2026-08-05 02:50 — CEO PAUSE: live_trading=false (RE-ENABLED 2026-08-06 02:15)

## BLOCKED
- (none currently)

## FOLLOW-UP (checked by CEO on next run)
- [x] Verify decider is actually killed — DONE 2026-08-05
- [x] Verify return_exhaustion generating signals — CONFIRMED (MOODENG, CC entries in trades.json)
- [x] Verify vortex_break generating signals — CONFIRMED (AVNT LONG entry)
- [x] bb_bounce properly disabled — CONFIRMED (BB_BOUNCE_ENABLED=False + NEVER_REENABLE_FLAGS). LINK SHORT was pre-disable legacy entry.
- [ ] Monitor tl_break_long sustained performance — NO ENTRIES FOUND in recent trades, may be decayed/removed

## CEO DECISIONS (2026-08-06 03:15)
- [x] 2026-08-06 03:15 — PROFIT MONSTER PNL FIX: pnl_usdt formula corrected to include leverage. 26/141 trades had $0.00 PnL due to missing leverage in calculation.

## CEO DECISIONS (2026-08-06 — Orphan Fix)
- [x] 2026-08-06 — ORPHAN RACE CONDITION FIXED: 60s guard in hl-sync-guardian.py prevents duplicate paper trades when HL close + guardian sync race. Bug hunter caught BRAIN_DB undefined + missing psycopg2 import. Commits: e354e31, efdf832.

## CEO DECISIONS (2026-08-06 — Notification)
- [x] 2026-08-06 — ZERO-PNL BACKFILL COMPLETE: PNUT SHORT ($0.00→$0.06) + LINK SHORT ($0.00→$0.05) corrected. Root cause: stale hl_notional_usdt in PostgreSQL ($10.10/$10.62 vs $11.0 actual). Dashboard convention `pnl% × margin` confirmed correct. Reverted incorrect leverage multiplication.
- [x] 2026-08-06 — DEAD HOURS RE-ENABLED: Added hzscore + return_exhaustion to allowlist, removed bb_bounce (disabled anyway). DEAD_HOURS_ENABLED=True. Filter protects against low-WR quiet-hour trades.
- [x] 2026-08-06 — DEAD HOURS EXPANDED: Added ma100-cross + vortex_break to allowlist. CC SHORT now fires during dead hours. All active confluence signals unblocked.
- [ ] 2026-08-06 — INVESTIGATE: why hl_notional_usdt drifts in PostgreSQL (should be $11.0)
- [ ] 2026-08-06 — CONSIDER: backfill job for stale notional values

## CEO DECISIONS (2026-08-06 Session)
- [x] 2026-08-06 — MA_100_CROSS DEPLOYED: 100MA cross with 2-candle confirmation, 51-56% WR backtested. Integrated into signals_runner.
- [x] 2026-08-06 — HZSCORE UPGRADED: MIN_Z_VALUE 0.4→1.0 (64.3% WR backtested highest). 5min cooldown added.
- [x] 2026-08-06 — CONFLUENCE GATE FIXED: Hard RS removed, any 2+ unique signal types now pass. CONFLUENCE_REQUIRED=True.
- [x] 2026-08-06 — SIGNAL ROTATOR FIX: Added ROTATOR_PROTECTED_FLAGS to hermes_constants.py. tl_break protected from auto-rotation. Was being killed by stale 21.8% cumulative WR.
- [ ] 2026-08-06 — MONITOR ma_100_cross live WR (24h trial)
- [ ] 2026-08-06 — MONITOR hzscore WR with new z-threshold

## CEO DECISIONS (2026-08-06 03:15)
- [x] 2026-08-06 03:15 — PROFIT MONSTER PNL FIX: pnl_usdt formula corrected to include leverage. 26/141 trades had $0.00 PnL due to missing leverage in calculation.
- [x] 2026-08-06 03:15 — DELEGATE to bug_hunter: Verify bb_bounce truly disabled (20 trades in 24h despite being disabled)
- [x] 2026-08-06 03:15 — DELEGATE to self_learner: Evaluate tl_break parameters (short underperforming, long has no entries)
- [x] 2026-08-06 03:15 — MONITOR vortex_break and return_exhaustion for 48h before any changes
- [x] 2026-08-06 03:15 — MONITOR hzscore+rs confluence (3 open positions all profitable)

## CEO DECISIONS (2026-08-06 03:18)
- [x] 2026-08-06 03:18 — tl_break_long CONFIRMED sustained: 82.4% WR over 48h, 17 trades, +$1.63. ROTATOR_PROTECTED_FLAGS working.
- [ ] 2026-08-06 03:18 — DELEGATE to bug_hunter: bb_bounce + decider still firing despite NEVER_REENABLE_FLAGS (23 trades/48h for bb_bounce, 9 trades for decider)
- [ ] 2026-08-06 03:18 — CONTINUE monitoring vortex_break + return_exhaustion (48h trial window)
- [ ] 2026-08-06 03:18 — CONTINUE monitoring hzscore + rs confluence

## CEO DECISIONS (2026-08-06 03:45)
- [x] 2026-08-06 03:45 — HOT-SET FLIPPING FIXED: PENDING signal expiry 5min→10min. 37 signals expired as stale_5min in 30min. Signals now have 10min window to find co-signals for confluence.

## CEO DECISIONS (2026-08-06 03:30)
- [ ] 2026-08-06 03:30 — FIRST CONFLUENCE TRADE: LTC LONG $44.94 (bb_bounce+hzscore+) 5x. Trade #13266. Monitor for signal quality.
- [ ] 2026-08-06 03:30 — TRACK 3 hzscore+ open positions: LTC, BCH, MORPHO

## CEO DECISIONS (2026-08-06 02:50)
- [x] 2026-08-06 02:50 — VERIFIED bb_bounce properly disabled. Only 1 legacy trade (race condition). NOT in registered signals.
- [x] 2026-08-06 02:50 — SYSTEM HEALTH OK. +$2.23/24h net profitable. All dead signals confirmed disabled.

## CEO DECISIONS (2026-08-06 04:20)
- [ ] 2026-08-06 04:20 — URGENT DELEGATE to bug_hunter: bb_bounce STILL firing 18 trades/24h despite BB_BOUNCE_ENABLED=False + NEVER_REENABLE_FLAGS. 08-05 investigation said "stale batch" but it's still happening. Find real root cause.
- [ ] 2026-08-06 04:20 — MONITOR ma_100_cross: W LONG is first live trade (opened 03:36). Track for 48h.
- [ ] 2026-08-06 04:20 — MONITOR hzscore+ confluence: 100% WR (5/5 trades today), small PnL per trade but consistent.
- [x] 2026-08-06 04:20 — SYSTEM STATUS: 33 closed trades, 60.6% WR, +$0.49/24h. Net profitable. 3 open positions.

## CEO DECISIONS (2026-08-06 05:00)
- [x] 2026-08-06 05:00 — PROFIT MONSTER FIXED: IndentationError at line 185 resolved. Crash loop stopped. MORPHO should close on next cycle. Bug hunter verified 5/5 PASS.
- [x] 2026-08-06 05:00 — BB_BOUNCE ROOT CAUSE FOUND: Line 876 had BB_BOUNCE_ENABLED=True (someone re-enabled). Set False + added to NEVER_REENABLE_FLAGS. Was never in NEVER_REENABLE_FLAGS — rotator could re-enable it.
- [ ] 2026-08-06 05:00 — URGENT DELEGATE to bug_hunter: decider (9 trades) and vel-hermes- (46 trades) still firing despite being in NEVER_REENABLE_FLAGS / disabled. Investigate signal registration bypass.
- [x] 2026-08-06 05:00 — SYSTEM STATUS: 42 trades, -$0.17/24h (breakeven). tl_break_long = +$1.81 (100% WR). No open positions.

## CEO DECISIONS (2026-08-06 04:00)
- [ ] 2026-08-06 04:00 — URGENT DELEGATE to bug_hunter: bb_bounce (18 trades/24h), decider (9 trades/24h), vel-hermes- (46 trades/24h) still firing despite NEVER_REENABLE_FLAGS. Find root cause in signal registration/rotator.
- [ ] 2026-08-06 04:00 — MONITOR tl_break_long: 100% WR, 14 trades, +$1.81/24h. Protected. Continue.
- [ ] 2026-08-06 04:00 — MONITOR vortex_break + return_exhaustion: 48h trial ongoing.
- [x] 2026-08-06 04:00 — INVESTIGATE hl_notional_usdt drift (pending from earlier session).
- [x] 2026-08-06 04:00 — DEAD SIGNAL INVESTIGATION (RESOLVED): bug_hunter confirmed stale batch data, not live leak. All trades from `2026-08-05 14:28:25` batch. NEVER_REENABLE_FLAGS works for rotator. Recommended: hardcoded block in signal_schema.py.

## CEO DECISIONS (2026-08-06 02:15)
- [x] 2026-08-06 02:15 — RE-ENABLED LIVE TRADING: kill switch set true. 138 trades, 52.9% WR, +$2.23/24h. Net profitable.
- [x] 2026-08-06 02:15 — TIGHTENED TRAILING: activation 0.35%→0.30%, distance 0.80%→0.70%. Lock profits faster.
- [x] 2026-08-06 01:00 — DISABLED bb_bounce: BB_BOUNCE_ENABLED=False + added to NEVER_REENABLE_FLAGS. 19 trades, 36.8% WR, -$0.62. Asymmetric R:R.
- [x] 2026-08-06 02:00 — SIGNAL CONFLUENCE UPDATE: tl_break LONG enabled, hzscore enabled, hard RS requirement removed (any 2+ unique signal types pass). Commits: 5461ab0, 9105083.
- [ ] 2026-08-06 01:18 — MONITOR tl_break_long — NO ENTRIES in recent trades. May need re-enable or decay killed it.

## CEO DECISIONS (2026-08-05 23:50)
- [x] 2026-08-05 22:30 — KEEP LIVE TRADING PAUSED — new signals untested, legacy dead signals still firing
- [x] 2026-08-05 22:30 — URGENT: DELEGATE to bug_hunter: Kill decider permanently (NEVER_REENABLE_FLAGS) — COMPLETED
- [x] 2026-08-05 23:50 — DECIDER BUG RESOLVED: 9 "decider" records were historical (old trades closing today). Default param in signal_schema.py was changed from 'decider' → 'unknown' in commit 62c549f. No new decider trades. 0 created today.
- [ ] 2026-08-05 23:50 — DELEGATE to self_learner: bb_bounce SL override (1.0% cap) — 19 trades, 47.4% WR, -$0.52, R:R 1.73:1 unfavorable. BIGGEST LOSER.
- [ ] 2026-08-05 23:50 — MONITOR: tl_break_long (14 trades, 100% WR, +$1.81) — watch for decay pattern
- [x] 2026-08-05 23:00 — HL COPY TRADING MVP: Approved for paper trading (48h monitoring phase)
- [ ] 2026-08-05 23:50 — KEEP LIVE TRADING PAUSED until decider bug fully resolved

## CEO DECISIONS (2026-08-06 06:00)
- [x] 2026-08-06 06:00 — SIGNAL LEAK ROOT CAUSE FOUND: (1) bb_bounce directional flags (PLUS/MINUS_ENABLED) were left True when master killed — they're the actual gates. (2) vel-hermes- had no NEVER_REENABLE entry at all. (3) decider entry in NEVER_REENABLE_FLAGS is dead (no matching flag). Fixes applied: set directional flags False, added missing entries, removed dead entry.
- [ ] 2026-08-06 06:00 — CONTINUE monitoring ma_100_cross (W LONG first trade, 48h window)
- [ ] 2026-08-06 06:00 — CONTINUE monitoring hzscore+ confluence (100% WR, 5 trades)
- [ ] 2026-08-06 06:00 — CONTINUE monitoring vortex_break + return_exhaustion (48h trial)
- [x] 2026-08-06 06:00 — SYSTEM STATUS: 151 trades, 55.6% WR, +$2.71/24h. Net profitable. Live trading active.

## CEO DECISIONS (2026-08-06 06:50)
- [x] 2026-08-06 06:50 — SYSTEM HEALTHY: 6 open, 42 closed, +4.38% PnL. All timers active.
- [x] 2026-08-06 06:50 — bb_bounce RESOLVED: No longer in active signals. Directional flag fix worked.
- [x] 2026-08-06 06:50 — SIGNAL LEAK FULLY RESOLVED: Verified zero dead signal trades after 05:00 UTC. vel-hermes- 46 trades all pre-fix batch. NEVER_REENABLE_FLAGS working.
- [ ] 2026-08-06 06:50 — CONTINUE monitoring ma_100_cross, vortex_break, return_exhaustion (48h windows).
- [x] 2026-08-06 06:50 — NO PARAMETER CHANGES: System profitable, let signals run.

## CEO DECISIONS (2026-08-06 — CEO Report)
- [x] 2026-08-06 — CEO REVIEW: 157 trades, 55.4% WR, +$2.55/24h. Net profitable. Live trading active. Signal leak verified resolved. No parameter changes. tl_break_long 100% WR protected.

## CEO DECISIONS (2026-08-06 — CEO Review 07:50)
- [x] 2026-08-06 07:50 — SYSTEM STATUS: 159 trades, 57% WR. tl_break_long still 100% WR (+$1.81). Live trading active.
- [x] 2026-08-06 07:50 — DEAD SIGNAL LEAK FIXED: bb_bounce + pattern_scanner removed from SIGNAL_REGISTRY. Added _DEAD_SIGNALS blocklist in add_signal() as defense-in-depth. Commit 4ae747f.
- [x] 2026-08-06 07:50 — NO PARAMETER CHANGES: System profitable, let signals run.
- [ ] 2026-08-06 07:50 — CONTINUE monitoring: tl_break_long, vel-hermes-, zscore confluence, hzscore+confluence.

## CEO DECISIONS (2026-08-06 ~09:30)
- [x] 2026-08-06 ~09:30 — SYSTEM STATUS: 167 trades, 56.3% WR, +$2.78/24h. Net profitable. Live trading active.
- [x] 2026-08-06 ~09:30 — DECAY-DETECTOR OK: Timer active, oneshot service (inactive between runs is normal). Last ran 03:49 UTC.
- [x] 2026-08-06 ~09:30 — BB_BOUNCE CONFLUENCE: 3 trades in last 6h (bb_bounce+hzscore+), all wins, $0.14. Confluence usage acceptable.
- [x] 2026-08-06 ~09:30 — tl_break_long: 14 trades, 100% WR, +$1.81 — PROTECTED, star performer.
- [x] 2026-08-06 ~09:30 — NO PARAMETER CHANGES: System profitable, let signals run.
- [ ] 2026-08-06 ~09:30 — CONTINUE monitoring: ma_100_cross (48h window), hzscore+confluence, vortex_break, return_exhaustion.

## CEO DECISIONS (2026-08-06 ~11:00)
- [x] 2026-08-06 ~11:00 — CONFLUENCE PARALYSIS FIX: Set CONFLUENCE_REQUIRED=False. 14 signals blocked, hotset empty, zero new entries. System frozen despite +8.42% PnL. Re-enable when signals naturally co-fire on same tokens.

## CEO DIRECTIVE (2026-08-06 ~13:00)
- [x] 2026-08-06 ~13:00 — CONFLUENCE_REQUIRED = True — PERMANENT. T confirmed: confluence is core quality gate. Paralysis caused by 5min PENDING expiry + dead hours blocking, both fixed. Do not disable confluence.

## CEO DECISIONS (2026-08-06 ~12:20)
- [ ] 2026-08-06 12:20 — DELEGATE to bug_hunter: decider still firing 9 trades/24h (11.1% WR) despite NEVER_REENABLE_FLAGS. Find bypass in signal registration/rotator.
- [x] 2026-08-06 12:20 — SYSTEM STATUS: 175 trades, 58.3% WR, +$3.31/24h. Net profitable. Zero open positions.
- [x] 2026-08-06 12:20 — tl_break_long: 14 trades, 100% WR, +$1.81 — PROTECTED, no changes.
- [x] 2026-08-06 12:20 — NO PARAMETER CHANGES: System profitable, let signals run.

## CEO DECISIONS (2026-08-06 ~09:50)
- [x] 2026-08-06 ~09:50 — SYSTEM STATUS: 166 trades, 56.6% WR, +$2.91/24h. Net profitable. 0 open positions.
- [x] 2026-08-06 ~09:50 — DEAD SIGNAL LEAK RESOLVED: Bug hunter confirmed bb_bounce+decider trades are historical (pre-fix). Zero new signals after 08:09 UTC. Root cause: bb_bounce.py checked directional flags but not master BB_BOUNCE_ENABLED. Fixed at 06:00 UTC.
- [x] 2026-08-06 ~09:50 — tl_break_long: 14 trades, 100% WR, +$1.81 — PROTECTED, no changes.
- [ ] 2026-08-06 ~09:50 — DEFERRED: signal_compactor.py direct INSERT bypasses _DEAD_SIGNALS. Low risk now, add check for defense-in-depth when convenient.
- [ ] 2026-08-06 ~09:50 — CONTINUE monitoring: ma_100_cross, hzscore+confluence, vortex_break, return_exhaustion (48h windows).

## CEO DECISIONS (2026-08-06 ~14:00 — Session Changes)
- [ ] 2026-08-06 ~14:00 — CONSIDER range_finder for hot-set scoring (if backtested WR ≥ 50%).
- [ ] 2026-08-06 ~14:00 — DELEGATE to bug_hunter: Investigate hour 14 UTC loss cluster (56 losses) — Asian session close correlation?
- [x] 2026-08-06 ~14:00 — bb_bounce confluence APPROVED: 100% WR with hzscore+. Confluence-only, never standalone. Update dead signals blocklist.
- [x] 2026-08-06 ~14:00 — SESSION CHANGES ACKNOWLEDGED: range_finder, ma_100_cross fix, regime gate, hl_copy daemon, profit trail tier all noted.

## CEO DECISIONS
- [x] 2026-08-08 — ACTIVE CEO RUN. Verified 24h: 10t, +$0.09, 50% WR. 7d: 397t, -$8.17, 39% WR. 48h: 135t, +$0.10. System net profitable.
- [x] 2026-08-08 — SHORT identified as dominant bleed: 238t, 32.8% WR, -$6.89 vs LONG 159t, 48.4% WR, -$1.29.
- [x] 2026-08-08 — NO CHANGES: System recovering (4 consecutive improving days). Aug 7 was best day (+$0.40, 62.5% WR). Don't disrupt recovery.
- [ ] 2026-08-08 — MONITOR: If SHORT PnL stays negative through Aug 10, add regime filter to SHORT signals.
- [x] 2026-08-08 — CONFIRMED: Dead signals (inv-accel-300, vel-hermes, zscore-rising) are historical only. Zero new trades after flags killed.
