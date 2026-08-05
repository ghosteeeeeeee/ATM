# System Automation Audit — 2026-08-02 23:30 UTC

## Core trading path (OK)
| Unit | Role | Status |
|------|------|--------|
| hermes-pipeline.timer/service | 1m: compact→signals→decider→PM→API | active (oneshot between runs) |
| hermes-price-collector.timer | 1m prices | active |
| hermes-hl-sync-guardian.service | long-running daemon | active (timer intentionally inactive) |
| hermes-15m / 4h regime | regime files | active |
| candles.db 1m | fresh (max ts recent) | OK |

signal_compactor is **inside pipeline**, not its own timer (timer disabled by design).

## Fixed this audit
1. Stuck guardian closing markers (JUP from Jul 29, GALA/ME/XMR) — cleared + 30min age expiry
2. hermes-signal-purge.timer invalid OnCalendar `*:0/1:00:00` → `hourly`
3. hermes-metrics.service Restart keys in wrong section → fixed + restarted
4. ACCEL_300_MINUS added to NEVER_REENABLE_FLAGS
5. param_auto_tuner CEO freeze hard-guard (even if timer re-enabled)
6. run_ceo.sh stale kill-switch assumptions updated

## Still broken / noisy (not fixed — lower urgency)
| Issue | Severity | Notes |
|-------|----------|-------|
| hermes-git-release fails hourly | MED | dirty tree / deleted skills; backup not landing |
| hermes-bug-hunter exits 1 on low WR | LOW | treats performance as failure; confuses monitoring |
| hermes-trading-checklist exits 1 on WARN | LOW | 20k signals "need cleanup"; purge was broken |
| hermes-mtf-macd-tuner IndexError | MED | list assignment OOR at ema init |
| hermes-1m-candle.timer **disabled** | MED | candles still fresh via other path — confirm who writes |
| 8× opencode runners share port **4099** | HIGH | CEO/health/orchestrator/auto-1hr/etc can collide |
| CEO/auto thrash risk via signal_rotator | MED | still enabled every 4h; can flip non-frozen flags |
| ATR_SL_MIN (0.8%) ≠ ATR_SL_MIN_INIT (2.0%) | INFO | open positions still show eff_sl~0.8% from floor |
| pipeline Type=simple + timer | INFO | works but races if run >60s |
| bugs.json empty | LOW | no tracking |

## Freeze state (intentional)
- hermes-auto-1hr.timer: disabled
- hermes-param-auto-tuner.timer: disabled
- Locked: SL init 2.0%, trail 0.25/0.50, speed 45, ACCEL_300_MINUS=False

## Design as intended?
**Mostly yes for live path.** Compaction+decider+guardian+price loop healthy.
**Automation layer is overbuilt and half-broken:** many LLM timers on one port, checklist/bug-hunter fail-on-metric, git-release red, purge was dead, metrics unit misconfigured.
