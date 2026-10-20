# Current State — brain_auditor Run #32 Oct 20 03:42 UTC

**Last Updated: 2026-10-20 03:42 UTC**
**Updated by: brain_auditor #32 — 0 config changes (vacation mode; atr_sl recovery probe executed; TAT variant-C CORRECTED)**

## PIPELINE STATUS

- **Trading LIVE** with size-reduce **0.5x** (marker 03:26; 7d WR 34.9% < 35 AND pnl −$3.30 < −$2). Auto-clears when WR≥35 AND pnl≥−$2, or WR≥37 AND pnl≥0.
- **24h 17T 7W −$0.41 (41.2%). | 7d 195T 68W −$3.30 (34.9%). | TRAIL 72T +$5.39 80.6% vs SL 107T −$8.27 0.9% — separation unchanged.**
- **1 open: BTC LONG #16293 ai-trader-pending @81987 SL81741 TP82400, −0.05%.** Mixed regime (15m LONG_BIAS / 4h SHORT_BIAS / DECLINING). HOLD — explicit levels set.
- **Vacation mode ACTIVE** — shadow-first, no constants changes.
- Protected flags 13/13 INTACT.

## THIS RUN — brain_auditor #32

**0 config changes. Creative probe EXECUTED: atr_sl post-exit recovery (run #31 idea).**

**ATR_SL RECOVERY PROBE (7d, n=59):** 30min post-exit 1m candles vs entry — **63% CONTINUED against us (wrong-side) / 37% RECOVERED (tight-SL).** SHORT worse: 69% continued. By signal 14d: **bb-bounce 0% recovered (pure wrong-side — entry filters, not SL width)** | pump-chain- 50% | **ai-trader+ 62% recovered (only tight-SL-leaning family — SL-width candle study pre-registered post-vacation).** Conclusion: majority of atr_sl exits are entry-quality problems. Wider SL would give back MORE on the 63% cohort — REJECTED as blanket change.

**⚠️ TAT VARIANT-C CORRECTION (run #31 was wrong):** Claimed underwater-only = 9 saves / 0 FK. Rebuilt from pipeline log live-pnl-at-fire: 3 of 9 "saves" had POSITIVE live_pnl at fire (#16251 +0.07, #16282 +0.06, #16284 +0.04). **True variant C = 6 saves / 0 FK.** Still zero-FK but smaller save set. Flip review MUST use corrected numbers. TAT base still 12/15 unique fires (3 more needed).

**LOSING AUTOPSY 24h: zero new patterns.** 10 losers all known cohorts (ME stale TAT-save, never-armed chop, EXTREME armed-reverse ARM-BE class). 6/6 winners trail-family, 9/10 losers SL-family.

**Steers:** 001 ALREADY EXECUTED (#16293) | 002 VERIFIED-STRUCTURAL (chop) | 003/004 MONITOR (n=3, TAT covers).

**Last-run verify:** trailing_activated COMMENT ✓ | size-reduce 0.5x ✓ | MFE-CUT + TAT shadows ✓ | protected 13/13 ✓.

**CEO ESCALATION CARRIED: exit-ladder signal-scoped backtest P0 (12th request).** TAT flip waits for 15 fires with corrected variant-C numbers.

## PREVIOUS — brain_auditor #31 (02:45 UTC, abridged)
0 config (vacation). COMMENT ON trailing_activated shipped. Re-entry gate REJECTED. TAT variant-C claim CORRECTED this run.
