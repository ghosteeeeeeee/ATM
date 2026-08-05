# Hermes Signal Debugging — Issue Index

## Complete Issue Table

| Symptom | Likely Cause | See |
|---------|-------------|-----|
| stale signals in hot-set after regime change | Stale regime tokens not purged from approved set | `references/stale-regime-signals.md` |
| phase_accel not appearing in hot-set | phase=accel requires 4 consecutive up-periods; speed gate blocks it | `references/phase-accel-hotset.md` |
| LAYER-type move not detected | phase=accel requires 4 consecutive periods; 3-of-4 not enough | `references/phase-accel-hotset.md` |
| zscore-momentum tuner sweeps 0 tokens | Lookback sweep mode bug: `lookback += 1` each step exceeds max lookback before finding signals | `references/zscore-tuner-bug.md` |
| phase_accel fires every cycle — no cooldown | phase=accel cooldown not wired to signal type, fires every check cycle | `references/phase-accel-hotset.md` |
| switch EMA to pandas | `ema.py` currently uses raw list append; pandasTA integration needed | `references/ema-pandas-migration.md` |
| accel-300 SHORT signs verified | 2026-05-14: gap_then-gap_now SHORT positive=accelerating; delta_last>=delta_prev rejection correct | `references/accel-300-short-verified-2026-05-14.md` |
| RS picks up falling knives | RS is regime-agnostic; it picks up coins in DOWN regimes too — this is by design | `references/rs-regime-agnostic.md` |
| z=None in merged signals (zscore-pump wiped by R&S merge) | add_signal() merge UPDATE wrote None into z_score unconditionally | `references/signal-quality-fix-2026-05-21.md` |
| low-touch RS levels (20-100 touches) correlating with losses | no minimum touch threshold enforced at decider_run entry gate | `references/signal-quality-fix-2026-05-21.md` |
| zscore-pump+ every combo loses | zscore-pump fires counter-trend; signal-level is correct but execution gate needed | `references/zscore-pump-counter-trend-2026-05-17.md` |
| zscore-pump SHORT fires against uptrend | zscore_pump.py direction is CORRECT; counter-regime signals must NOT be blocked at signal level — T's rule | `references/zscore-pump-counter-trend-2026-05-17.md` |
| zscore-pump phantom SL hit 5s after open | Not staleness — wrong SL computation. SL placed 4.18% above entry for SUI SHORT. Check PostgreSQL `stop_loss` vs `entry_price` before blaming staleness. | `references/zscore-pump-staleness.md` |
| signals not combining | signals arriving from different sources with different confidences; hot-set requires confluence | `references/signal-combining.md` |
| signals not merging into hot-set | signal_compactor run too infrequent; signals expire before next compaction | `references/signal-expiry.md` |
| hot-set only has one signal type | signal_compactor applying hard source limits; mix gate filtering tokens | `references/signal-combining.md` |
| approved signals not in hotset | approved set filters applied after hot-set selection; check `APPROVED_MIN_SIGNALS` | `references/hotset-vs-approved.md` |
| approved and hotset have different tokens | approved set built before regime scan; hotset built after; regime change shifts tokens | `references/hotset-vs-approved.md` |
| hot-set shows X but APPROVED shows Y | same as above | `references/hotset-vs-approved.md` |
| why APPROVED different from hot-set | same as above | `references/hotset-vs-approved.md` |
| signals expire before reaching hot-set | compaction interval too long; signals have TTL shorter than interval | `references/signal-expiry.md` |
| signal_gen arrives after compaction mutes it | signal_gen timer and signal_compactor timer not staggered; signal arrives between compactions | `references/signal-timing.md` |
| same signal fires multiple times | no dedup on symbol+signal_type in hot-set or approved; signal appears every cycle | `references/signal-dedup.md` |
| signal_outcomes has duplicate rows | executor.py commits outcome before HL confirms fill; HL reject → no rollback → duplicate | `references/hl-db-insert-silent-failure.md` |
| same signal reopens after TP close | DASH +4% → -4% whipsaw, same accel-300+ signal reopens after TP. TP cooldown not per-token | `references/guardian-reopen-after-tp.md` |
| guardian reopens after profit | same as above | `references/guardian-reopen-after-tp.md` |
| LAYER fires then closes instantly | Guardian orphan close path; zscore_pump writes DB directly without stop_loss propagation | `references/guardian-orphan-closing-bug-2026-05-08.md` |
| ENS/OG/BERA opened+closed in seconds | Confluence gate blocked signals → decider_run empty → guardian orphan path fires | `references/guardian-orphan-closing-bug-2026-05-08.md` |
| All 13 tokens opened+closed in 8-33s | Guardian orphan closes — no PostgreSQL records exist for those tokens | `references/guardian-orphan-closing-bug-2026-05-08.md` |
| PostgreSQL only has PURR/XLM | All other tokens hit orphan close path before brain.py INSERT completed | `references/guardian-orphan-closing-bug-2026-05-08.md` |
| SKIPPED entries piling up | ai_decider timer still running | `references/hl-db-sync-debug.md` |
| phantom trade | HL has position, DB doesn't — mirror_open called before HL confirmed | `references/phantom-trade-debug.md` |
| position not syncing | 3-way mismatch HL/PG/signals DB | `references/hl-db-sync-debug.md` |
| closing marker blocks token permanently | HL close succeeds but fill polling fails → marker never cleared | `references/guardian-closing-marker-permanent-block-2026-05-08.md` |
| guardian orphan trade_id mismatch | brain.py INSERT failed → guardian created orphan → closing marker has different trade_id | `references/hl-db-insert-silent-failure.md` |
| guardian reopens same signal after TP | TP cooldown not per-token per-signal-type; guardian re-opens different signal same direction | `references/guardian-reopen-after-tp.md` |
| FIL SHORT SL=1.007 instead of ~1.043 | Initial SL set to hardcoded fallback; position_manager doesn't correct non-zero SL | `references/fil-short-initial-sl-bug-2026-05-15.md` |
| SUI SHORT closed in 5s, entry $1.0509, SL $1.007 | SL was 4.18% above entry for SHORT — wrong ATR/SL computation at entry | `references/sui-short-5s-close-2026-05-17.md` |
| SUI LONG #10051 SL=1.0923 above entry=1.064 | `compute_atr_sl_tp` new-trade gate bypassed; phase k applied from entry instead of INIT floor | `references/sui-ghost-trade-fix-2026-05-16.md` |
| GALA SHORT SL=0.00341 exactly at entry | zscore_pump writes DB directly without stop_loss propagation; HL TP/SL triggered first | `references/sui-gala-ghost-trades-2026-05-16.md` |
| ZK SHORT TP/SL ratio = 5.35x instead of 1.25x | SHORT TP computed using `atr_pct` from higher-ATR moment; trailing TP cannot tighten back | `references/zk-trade-tp-ratio-bug-2026-05-15.md` |
| ATOM SHORT loss cooldown not recorded, immediate re-entry | 3 bugs: (2a) `close_paper_position()` reason='atr_sl_hit' has no PnL% → `is_loss=False`; (2b) STALE_ROTATION path missing cooldown; (3) first trade never in DB → guardian timing race | `references/loss-cooldown-missed-atr-sl-hit-2026-05-17.md` |
| CHIP/LAYER instant reopen after guardian close | Guardian closed 39s before reopen; loss cooldown gap lets signal re-fire | `references/instant-reopen-cooldown-gap-2026-05-14.md` |
| 2Z/BLUR stuck in guardian closing in progress | HL close succeeds but fill polling fails → marker never cleared → `_is_guardian_closing()` always True | `references/guardian-closing-marker-permanent-block-2026-05-08.md` |
| MON duplicate SHORT entries | brain.py `mirror_close` rollback missing `direction` arg; rollback silently fails → HL position stays open | `references/mirror-close-rollback-silent-fail.md` |
| Stale allMids prices across all tokens | 4h_regime_scanner makes 134 candleSnapshot calls/min exhausting rate limit | `references/hl-rate-limit-debug.md` |
| wave_phase=neutral for all tokens | SpeedTracker `.update()` not called for regime tokens | `references/wave-phase-hotset-debug.md` |
| 24+ tokens permanently blocked from entering | Stale `guardian-closing-markers.json` never cleaned | `references/signal-quality-debug.md` |
| rate limit 429 on regime scanners | 4h regime scanner candleSnapshot calls; fix: regime scanners → Binance-only | `references/hl-rate-limit-debug.md` |