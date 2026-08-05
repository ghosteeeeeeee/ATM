# TASKS-ARCHIVE.md — Archived Tasks (Hermes)

> Moved from TASKS.md when it was trimmed on 2026-04-15.
> Keeping here for historical context — do not edit TASKS.md with these.

---

## 2026-04-14 — Bug Hunt Session (archived)

### [x] AVNT wrong SL ($0.139567 fallback instead of ATR-based $0.1345) — FIXED
**Root cause:** `SKIP_COINS` in `hl-sync-guardian.py` excluded AVNT from ATR recalculation. Only got 2%-from-entry fallback.
**Fix:** Removed all coins from SKIP_COINS. Re-enabled `replace_sl()` call to update SL on Hyperliquid.
**Status:** AVAX PASS confirmed (SL=9.380943 on HL).

### [x] Dashboard stale (pipeline crashed, 2.5h gap) — FIXED
**Root cause:** Pipeline process died, no restart mechanism.
**Fix:** Restarted pipeline. Dashboard now updating every 1 min.

### [x] BTC/XRP/PROVE "Invalid TP/SL price" errors — INVESTIGATING
HL returning `asset=X` errors for some SHORT positions. Not rate-limit-related — likely HL validation failure.
**Affected:** BTC (asset=0), XRP (asset=25), PROVE (asset=201), AVNT (asset=208)
**Status:** ARCHIVED — no resolution found before task was staleballed.

### [x] DYDX atr_sl_hit closed at -2.25% — CONFIRMED WORKING
Guardian correctly closed DYDX when ATR SL hit. This is the internal close path working as designed.
**Not a bug** — intended behavior.

---

## 2026-04-07–10 — Post-Fix Verification (archived — stale)

All of these were monitoring items from the Apr 6–10 fix cycle. They were never systematically verified and the monitoring window passed. Archive.

### [x] (P) Investigate Speed=50% anomaly — RESOLVED 2026-04-06
**Root cause:** hermes-trades-api.py line ~355 uses `e.get('speed_percentile') or e.get('momentum_score') or 50.0`. The 4 affected tokens (KSHIB, KFLOKI, KBONK, KLUNC) don't exist in SpeedTracker's price history. SpeedTracker defaults to 50.0 for unknown tokens.

### [x] (P) Verify SL ATR adjustments improved win rate — 2026-04-09
Baseline: 51.9% WR / +13.68 USDT net (7d pre-fix). After 3 days, compare WR and net PnL.
**Status:** ARCHIVED — never systematically verified.

### [x] (P) Verify trailing stops no longer false-trigger — 2026-04-09
Previously `trailing_active = True` was always set due to indentation bug.
**Status:** ARCHIVED — never systematically verified.

### [x] (P) Verify phase2 buffer ATR logic working correctly — 2026-04-09
Inspect `trailing_stops.json` for phase2 entries.
**Status:** ARCHIVED — never systematically verified.

### [x] (P) Compare pre/post fix PnL — 2026-04-09
Need baseline from before 2026-04-06.
**Status:** ARCHIVED — never done.

### [x] (P) Verify pattern_scanner detects any patterns at all — 2026-04-07
Pattern scanner has NEVER produced a signal in production (0 pattern_scanner signals in DB).
**Root causes:** (1) `_get_active_tokens()` only returns 5 tokens; (2) bull flag requires ≥3% pole move.
**Status:** ARCHIVED — pattern scanner was never fixed.

### [x] (P) Fix active_tokens so all hot-set tokens get 1m candles seeded — 2026-04-07
`_get_active_tokens()` returns only 5 tokens instead of full active universe.
**Status:** ARCHIVED — never done.

### [x] (P) Add smaller-scale pattern detection (micro-flags) — 2026-04-08
Relaxed params: FLAG_POLE_MIN_PCT=0.3, FLAG_CONSOLIDATION_MAX_PCT=0.15.
**Status:** ARCHIVED — never implemented.

### [x] (P) Measure pattern backtest accuracy — 2026-04-08
Backtest showed B_patterns=33.3% vs A_minimal=46.7% on 30 samples — patterns were WORSE.
**Status:** ARCHIVED — never pursued further.

### [x] (P) Verify pattern signals can reach ai_decider hot-set scoring — 2026-04-08
**Status:** ARCHIVED — pattern scanner never produced signals.

### [x] (P) Verify cron jobs survive sessions — 2026-04-07
**Status:** ARCHIVED — cron migrated to systemd timers, this was specific to old cron system.

### [x] (P) Verify Speed=50% fix applied — seed price history — 2026-04-10
**Status:** ARCHIVED — superseded by Speed=50% investigation being resolved.

---

## 2026-04-05–06 — Stale Sprint Items (archived)

### [x] Signal flip test — FAILED
Flip deployed 2026-04-05, ran 2 trades, both failed. WR flip test did NOT work.
Signal direction is correct as-is.
**Decision:** DECISIONS.md entry 2026-04-06 | WR flip test FAILED.

### [x] Hot-set stale — ai_decider not running — FIXED 2026-04-05
**Root cause:** ai-decider.timer dead (inactive since Mar 29) AND .service file was missing.
**Fix:** Disabled systemd timer, let run_pipeline.py be sole ai_decider caller.
**Decision:** DECISIONS.md entry 2026-04-05 | Hot-set stale — ai_decider not running.

### [x] 903 stale WAIT signals expired — FIXED 2026-04-05
**Root cause:** Old signals blocked pipeline → hot-set stayed at 4 tokens → 0 APPROVED signals.
**Fix:** signal-compaction skill run, 903 stale WAIT marked EXPIRED.
**Decision:** DECISIONS.md entry 2026-04-05 | Signal compaction.

### [x] hermes-git-release.timer restored — 2026-04-05
**Decision:** DECISIONS.md entry 2026-04-05 | hermes-git-release.timer restored.

---

*Archived: 2026-04-15. These tasks are either completed, resolved, or made obsolete by later decisions.*
