## Health Report — 2026-10-02 18:47 UTC

=== Health Report ===
Time: 2026-10-02 18:47 UTC

PIPELINE: OK
- Status: completed (oneshot; inactive after run is normal)
- Last run: 18:46:25 LIVE, rc=0
- Signals (1h): 122 generated
- Trades: 0 open, 53 closed today, +11.71% PnL
- Errors: 0 (0 Tracebacks; only BTC-CRASH-OVERRIDE informational notes)
- Heartbeat: decider_run OK, position_manager OK (18:46:24-25)

MARKET:
- Regime: SHORT_BIAS (0 LONG / 32 SHORT / 85 NEUTRAL of 117 scanned)
- Speed: 129/241 tokens >= 50th percentile (53%)
- Hotset: 1 token (HYPE SHORT) — not empty

SYSTEM:
- Guardian: active
- Timers: firing (pipeline.timer last fired 16s ago; 40+ hermes timers scheduled)
- Disk: 85% used (94G/118G, 18G free) — WARN
- Prices: 86 tokens, fresh (~1.5 min)
- Speeds DB: fresh (latest 18:46:25 UTC)

AUTO-FIXES APPLIED:
- None this cycle (no CRITICAL failures)

ALERTS:
- WARN: disk at 85% — journal vacuum already clean, 0 logs >7d to gzip. Bulk is DBs (coin_tracker 3.3G, candles 2.3G, signals 0.9G, session_brain 0.9G). CEO DB-retention decision still open (recurring since 2026-10-01).
- INFO: non-critical failed units (better-coder, brain-auditor, bug-hunter, git-release, coding-mcp) — known LLM-job timeout pattern. Trading path unaffected.
