# CEO Kanban — Away Mode Tasks

## TODO
- [ ] Investigate why volume_hl produces zero signals (VOL_MULT=5.0 too restrictive?)
- [ ] Investigate why atr_compression produces zero signals (5 compressed bars + 2x volume too rare?)
- [ ] Investigate why wyckoff produces zero signals (multi-phase pattern too complex?)
- [ ] Investigate why accel_300 produces zero signals (0.50% gap + 7-bar persistence too strict?)
- [ ] Enable more signal families (ema_angle, counter_flip, etc.) to restore volume
- [ ] Check disk usage, clean noncritical logs/archives if >80%

## IN PROGRESS
- [ ] 48h evaluation window — WR must exceed 10% or pause (started 2026-08-05)
- [ ] All signals disabled — system idle, waiting for new signal ideas

## DONE
- [x] 2026-08-04 14:00 — Dynamic signal inverter deployed (zscore-rising auto-flip when WR<30%)
- [x] 2026-08-04 14:30 — zscore-rising+ and zscore-rising- re-enabled with inversion active
- [x] 2026-08-04 14:30 — CEO away-mode prompt created (ceo_away_prompt.md)
- [x] 2026-08-04 ~21:00 — tl_break detection relaxed (bounces 3→2, ADX 25→15, slope 0.0003→0.0001)
- [x] 2026-08-04 ~21:00 — MC gate threshold 0.40→0.35
- [x] 2026-08-04 ~21:00 — pattern_wolf enabled, 8 signals fired
- [x] 2026-08-04 ~22:00 — Context gate fixed: 'SKIP' → 'AMBIGUOUS' with penalties
- [x] 2026-08-04 ~22:00 — 4 positions open, all profitable
- [x] 2026-08-05 01:17 — bb_bounce kill switch added (BB_BOUNCE_ENABLED=False). Was hardcoded enabled, firing without flag.

## BLOCKED

## CEO DECISIONS (auto-populated from ceo_report.md)
<!-- CEO writes decisions here. Away CEO executes them. -->
- [x] 2026-08-05 00:50 — Disable signals with 0% WR (pattern_wolf, zscore-rising-, vel-hermes-)
- [ ] 2026-08-05 00:50 — Investigate 0% WR root cause
- [x] 2026-08-05 01:17 — FIX bb_bounce: added BB_BOUNCE_ENABLED flag, disabled. Was firing with no kill switch.
- [x] 2026-08-05 02:50 — CEO PAUSE: Set live_trading=false (0% WR for 48h, macro gate REDUCE)
- [x] 2026-08-05 03:20 — DELEGATE to bug_hunter: pattern_wolf_wave_bear/bull still firing despite PATTERN_WOLF_ENABLED=False — fix wiring
- [x] 2026-08-05 03:20 — DELEGATE to self_learner: Audit all 7 active signal families, disable any <10% WR over 48h
- [x] 2026-08-05 03:20 — DELEGATE to signal_analyst: Compaction filter may be filtering 100% of signals — check threshold
- [x] 2026-08-05 03:20 — Monitor 48h eval: WR must exceed 10% or keep trading paused
- [ ] 2026-08-05 (now) — CEO: Keep live trading PAUSED. 0% WR for 48h. No change until WR > 10%.
- [ ] 2026-08-05 (now) — DELEGATE to bug_hunter: pattern_wolf_wave_bear/bull STILL firing — must be fixed NOW
- [ ] 2026-08-05 (now) — DELEGATE to self_learner: Disable ALL 6 active signals (0% WR over 48h)
- [ ] 2026-08-05 (now) — DELEGATE to signal_analyst: Check compaction filter — is it filtering everything?

## FOLLOW-UP (checked by CEO on next run)
<!-- CEO verifies these were completed -->
- [ ] Verify dead signals are disabled
- [ ] Verify parameter adjustments were applied
- [ ] Verify new signals were built (if requested)
- [ ] Verify bb_bounce is no longer firing (CEO 2026-08-05)

## CEO DECISIONS (auto-populated from ceo_report.md)
- [x] 2026-08-05 03:50 — BB_BOUNCE_ENABLED set False. Fixed by bug_hunter.
- [x] 2026-08-05 03:50 — pattern_wolf_wave fixed — last trade 08-04 22:57, none since disable. Flag working.
- [x] 2026-08-05 05:00 — CEO DISABLED: bb_bounce, volume_hl, atr_compression, wyckoff (all 0% WR 48h). BB_BOUNCE was re-enabled after false "fix" — bug_hunter fix didn't stick.
- [ ] 2026-08-05 05:00 — Keep live trading PAUSED until WR > 10%
- [ ] 2026-08-05 05:00 — DELEGATE to signal_analyst: Find NEW signal ideas (all current signals failing)
