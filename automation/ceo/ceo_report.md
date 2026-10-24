
## CEO Status — 20261013T214728Z
### Health: pipeline=active guardian=active open_pos=5
### Numbers: 24h 54T -$1.53 24.1% | 7d 165T -$0.04 33.9%
### Findings: Pipeline healthy (both services active, 0 CRITICAL alerts); 24h WR stuck at 24.1% for a 2nd status run, 7d PnL flipped slightly negative (-$0.04); alerts show phantom atr_sl_hit <0.01% PnL WARNs (8x) and a redacted REPEATED hotset-failure cluster ~20:01 UTC worth a deep-run look; disk still 83%
### Recommendation: Deep run should autopsye the phantom atr_sl_hit cluster and hold all config changes until the Oct 15 soak checkpoints

## CEO Status — 20261014T014728Z
### Health: pipeline=active(timer) guardian=active open_pos=0
### Numbers: 24h 62T -$1.30 25.8% | 7d 175T +$0.06 33.7%
### Findings: 24h bleed continues (−$1.30, 25.8% WR); 7d PnL at breakeven edge (+$0.06) — one bad day flips it negative. Timers firing normally; error_alerts show hotset failure cooldowns + BTC range-filter blocks (routine). Open positions flat.
### Recommendation: 7d WR 33.7% vs ≥50% Oct 15 checkpoint will miss — treat Oct 15 soak reviews (bb-squeeze, pump-chain 45m, trail-arm ratify) as the critical path; no new entry filters until then.

## CEO Status — 20261014T054729Z
### Health: pipeline=active guardian=active open_pos=3
### Numbers: 24h 60T -$0.95 25.0%WR | 7d 176T -$1.11 33.0%WR
### Findings: 7d PnL flipped negative again; error log shows disk 84% warn + hotset empty (0 tokens survived compaction); confluence gate currently blocking BABY SHORT (single ichimoku source, not in bypass); trail-arm 2 unratified enables still pending before Oct 15 soak review.
### Recommendation: RATIFY trail-arm 2 enables (brain_auditor corrected +$0.97/30d bb-squeeze) before Oct 15 soak review — it cannot proceed clean while undecided.

## CEO Status — 20261014T094729Z
### Health: pipeline=OK (timer fires every minute; last run exit 0 at 09:47:39, inactive-between-runs is normal) guardian=active open_pos=1
### Numbers: 24h 60T -$1.80 23.3% | 7d 185T -$1.34 33.0% (DB self-query, live)
### Findings: 24h PnL negative — hard_max_loss still #1 bleed (21 losses, -$1.76 of -$3.08 total losses), atr_sl_hit -$1.06; matches brain_auditor chop-vs-TREND autopsy (91.8% of HML never trail-armed). 7d flipped negative vs Oct 13 (+$0.93). Disk 84% (up from 83%). hotset cooldowns recurring but low severity. hermes-coding-mcp crash-loop auto-fixed (unit disabled; restore script or remove unit).
### Recommendation: CEO must decide trail-arm ratify + doji-bottom call before Oct 15 soak review; chase-entry filter backtest remains the only real lever against hard_max_loss.

## CEO Status — 20261014T134729Z
### Health: pipeline=active (timer cycle running; `is-active` reads inactive between 1-min oneshot runs) guardian=active open_pos=1
### Numbers: 24h 45T −$1.05 26.7% | 7d 189T −$1.09 34.4%
### Findings: 7d PnL flipped negative (was +$0.93 on Oct 13) — 24h WR 26.7% far below Oct-15 ≥50% checkpoint, unreachable. Top confluence blockers (3h logs): volatility gate v2 regime mismatch (volume-buildup− in HIGH ×19, r2-trend-long3 in NORMAL ×4), oversold RSI floors on pump-chain−/volume-buildup−, SHORT_BLACKLIST ×6. error_alerts: hotset cooldown noise only; pipeline-log "-72.06% PnL" label vs PG −$0.36 discrepancy flagged 09:53, still open.
### Recommendation: Trail-arm ratify decision is overdue and blocking Oct-15 soak review — decide today; separately, someone should fix the portfolio-summary PnL label bug (log shows −72.06% where PG shows −$0.36).

## CEO Status — 20261014T174729Z
### Health: pipeline=running (timer-fire, normal transient inactive) guardian=active open_pos=0
### Numbers: 24h 42T −$0.16 35.7% | 7d 193T −$0.61 35.2%
### Findings: 7d PnL slightly negative, WR 35.2% well below Oct 15 ≥50% goal; 0 open positions. Rotating Q (coin_tracker signals this week): 0 live — expected, Wyckoff shadow-mode since Oct 13 (0 live entries by design). Error alerts show hotset cooldown/override noise only.
### Recommendation: Decide trail-arm ratify + doji-bottom regime-block (both overdue, blocking Oct 15 soak reviews).

## CEO Status — 20261014T214730Z
### Health: pipeline=active (timer; momentary inactive=normal between runs) guardian=active open_pos=0
### Numbers: 24h 40T -$0.04 37.5% | 7d 192T -$0.58 35.4%
### Findings: Nearly breakeven 24h (best since Oct 12 flush). 7d still slightly negative. Disk 84% >80% goal (known miss). Guardrail ESCALATE stands (48h WR 28.9%). Errors: only routine gate-block/cooldown spam. Proactive Q (PnL): bleeding stopped, not yet profitable — hard_max_loss #1 + chop-family still the drag per brain_auditor audits.
### Recommendation: Tonight — ratify-or-revert trail-arm 2 enables (BB_SQUEEZE + PUMP_CHAIN) before tomorrow's Oct 15 hard deadline; hold all entry-filter stacking until soaks conclude.

## CEO Status — 20261015T014730Z
### Health: pipeline=inactive(timers-firing) guardian=active open_pos=0
### Numbers: 24h 34T −$0.34 35.3% | 7d 195T −$1.72 34.4%
### Findings: Rotating Q (worst signal): volume-breakout-long+ LONG −$0.76/16T 18.8%WR — already killed Oct 13, losses aging out of 7d window; next-worst hmacd_mtf-+ also killed. Both worst 7d losers are dead signals — bleed is historical, not live. hermes-pipeline unit inactive but all timers firing on schedule (compactor ran 27s ago) — pipeline is timer-driven, inactive unit is expected.
### Recommendation: None new. Prior escalations stand — trail-arm ratify (BB_SQUEEZE + PUMP_CHAIN) due TODAY Oct 15; momentum-gate backtest to self_learner deadline Oct 17 (3rd request undelivered).

## CEO Status — 20261015T140805Z
### Health: pipeline=active guardian=active open_pos=1
### Numbers: 24h 13T −$0.08 30.8% | 7d 195T −$1.61 34.4%
### Findings: Rotating Q (regime): 5m scanner now SHORT_BIAS (21 short / 94 neutral / 2 long of 117) — flipped from this morning's LONG_BIAS; regime mostly NEUTRAL at token level, consistent with low trade count (13T/24h). Error alerts = anonymized hotset-cooldown noise only, no new real errors. Pipeline + guardian both active.
### Recommendation: Ratify trail-arm enables (BB_SQUEEZE 60m + PUMP_CHAIN 45m) TODAY — hard deadline was Oct 15, soak supports KEEP, one-line revert each if REVERT.

## CEO Status — 20261015T180805Z
### Health: pipeline=inactive guardian=active open_pos=4
### Numbers: 24h 11T -$0.48 18.2% | 7d 195T -$1.27 34.9%
### Findings: 7d worst = volume-breakout-long+ 16T -$0.76 18.8% (already killed Oct 13 — losses aged in window); next live risk: volume-breakout-short- 3T 0% -$0.37 (1 loss from auto-kill threshold). pipeline service inactive between timer runs (oneshot — verify timers still firing). Errors = hotset cooldowns + BTC_LEVEL blocks only.
### Recommendation: Confirm hermes-pipeline timer is firing (service inactive may be normal oneshot); volume-breakout-short- watch stands per kanban.

## CEO Status — 20261015T220805Z
### Health: pipeline=active guardian=active open_pos=5
### Numbers: 24h 14T +$0.35 21.4% | 7d 194T −$0.95 34.0%
### Findings: Regime=LONG_BIAS (per CURRENT.md, verified). Error alerts show hotset failure-cooldowns + 1 BTC_LEVEL block (last 1h) — contained, no pipeline impact. 7d WR still below 50% target (34.0%).
### Recommendation: CEO decide wyckoff GO now — pairing data (volume 4%/rs 0% co-occurrence) says premise fails; keep shadow or commission new co-source design.

## CEO Status — 20261016T020805Z
### Health: pipeline=ok(timer-fired 02:08, 26.9s exit 0) guardian=active open_pos=2
### Numbers: 24h 15T +$0.63 46.7% | 7d 199T -$0.87 35.2%
### Findings: 24h WR recovering (21.4%→46.7%, PnL flipped positive). Worst live 7d signal = volume-breakout-short− 3T 0W -$0.37 (1 more loss = kill threshold, as flagged). Killed signals (volume-breakout-long+, hmacd_mtf-+, volume-buildup+) still appear in 7d window — aging out, no action. Error alerts = hotset cooldown noise only.
### Recommendation: volume-breakout-short− auto-kill check at next deep run; nothing actionable now.

## CEO Status — 20261016T060806Z
### Health: pipeline=inactive (oneshot between timer runs — timer fired 50s ago, next in 9s; NORMAL) guardian=active open_pos=4
### Numbers: 24h 20T +$0.51 45.0% | 7d 203T -$1.08 35.0%
### Findings: 24h healed to positive (matches brain_auditor 05:46). Rotating Q (regime-specialists): thin week — only pump-chain± have n≥20 in EXTREME; pump-chain+ EXTREME 26T 34.6% +$0.95 is the sole meaningful positive specialist, pump-chain− EXTREME 27T 29.6% +$0.09 marginal. volume-breakout-long+ EXTREME 10T −$0.45 is pre-kill (killed Oct 13) aging out. No new specialist pairings worth acting on; no filter stacking during soak.
### Recommendation: none — watch pipeline.timer (fires every 1min, service shows inactive between runs = normal oneshot; not a crash). Carried items unchanged (7d WR retarget, wyckoff GO, momentum-gate Oct 17).

## CEO Status — 20261016T100806Z
### Health: pipeline=OK (timer oneshot, exited SUCCESS, next run 10:09) guardian=active open_pos=3
### Numbers: 24h 28T +$0.13 39.3% | 7d 209T −$1.34 34.9%
### Findings: Day healed (+$0.13 from −$0.56). Proactive Q = worst signal: volume-breakout-long+ −$0.76 16T 18.8% and hmacd_mtf-+ −$0.46 8T 25% — BOTH already auto-killed Oct 13, 7d window aging out. Error alerts: benign tokenized cooldown/hotset lines + mark_signal_executed=0 repeats, no CRITICAL. Disk 80%.
### Recommendation: none new — carry existing CEO queue (wyckoff GO, 7d WR retarget, momentum-gate backtest due Oct 17).

## CEO Status — 20261016T140806Z
### Health: pipeline=active guardian=active open_pos=3
### Numbers: 24h 42T -0.02 45.2% | 7d 219T -1.11 37.0%
### Findings: 24h healed to breakeven (45.2% WR vs 21% yesterday); best 7d signal = pump-chain+ 31T +$0.92 35.5% WR (volume-buildup- 7T 85.7% +$0.36 second); alerts show routine hotset cooldowns + 1 BIGTIME mirror_close HL fail (Unknown token); 7d WR still short of 50% target.
### Recommendation: Investigate BIGTIME HL mirror_close "Unknown token" — possible token mapping gap; carry 7d WR retarget and wyckoff CEO decisions as already queued.

## CEO Status — 20261016T180807Z
### Health: pipeline=active guardian=active open_pos=2
### Numbers: 24h 51T −$0.53 43.1% | 7d 226T −$1.75 36.7%
### Findings: Proactive Q "which signal is worst?" — volume-breakout-long+ LONG 16T −$0.76 18.8% 7d (already killed Oct 13, aging out); live bleeds are doji-bottom-long/bb-bounce-v2-long−$0.41 each, matching brain_auditor's exit-magnitude verdict (losers ride, entries fine). Error alerts: 9x momentum-block fires + hotset cooldown, non-critical.
### Recommendation: Commission self_learner progressive exit-ladder backtest (doji + bb-bounce-v2, T=45m trail-arm extension) per Oct 16 momentum-gate FAIL verdict — next lever, no new entry filters.

## CEO Status — 20261016T220807Z
### Health: pipeline=active guardian=active open_pos=2
### Numbers: 24h 51T −$1.77 41.2% | 7d 229T −$2.26 36.2%
### Findings: Regime (rotating Q) = CONFLICTED — 15m LONG_BIAS vs 4h SHORT_BIAS, Wyckoff DISTRIBUTION, vol NORMAL. Conflict regime = chop habitat, matches the exit-magnitude bleed signature (trail +$7.3 vs chop −$9.9 per prior audits). Error alerts: only transient service timeouts, no trading impact.
### Recommendation: Commission progressive exit ladder backtest (self_learner) — 3rd status run flagging it as overdue; conflicted regime won't fix itself and exit-magnitude is the only untried lever.

## CEO Status — 20261017T020807Z
### Health: pipeline=inactive guardian=active open_pos=0
### Numbers: 24h 51T -2.34 35.3% | 7d 225T -3.63 34.2%
### Findings: Pipeline service INACTIVE — IndentationError crash loop on decider_run/position_manager/hermes-trades-api (01:08 UTC alerts); timers auto-restarted 01:24 but service still not running at 02:08 (may be between timer runs — verify). Best 7d signal (rotating Q): r2v2-long3 7T 57.1% +$0.52; pump-chain+ still #2 at +$0.40/31T.
### Recommendation: Grep pipeline logs for the IndentationError source and py_compile the failing step before the next timer fire — likely a bad edit from the 01:08 window.

## CEO Status — 20261017T060808Z
### Health: pipeline=inactive guardian=active open_pos=1
### Numbers: 24h 45T -2.10 35.6% | 7d 220T -3.02 34.5%
### Findings: Pipeline inactive = vacation guardrail (intentional, 7d WR 34.5% < 35%); guardian managing 1 open BTC SHORT. Best signal 7d (rotating Q): r2v2-long3 7T +$0.52 57.1%; pump-chain+ +$0.40/31T; worst: volume-breakout-long+ 11T 0%WR -$0.81. Price-collector lock-wait noise (250x/10min, rc=0).
### Recommendation: none — flat is correct under guardrail; on resume verify rsi_at_pick + MFE-CUT shadow lines per CURRENT.md.

## CEO Status — 20261017T100809Z
### Health: pipeline=inactive(paused, intentional) guardian=active open_pos=1
### Numbers: 24h 37T −$1.72 37.8% | 7d 214T −$2.87 34.6%
### Findings: Rotating Q (worst signal): ai-trader+ LONG worst 7d (21T −$0.64 38.1%WR), followed by doji-bottom-long 20T −$0.62 (killed Oct 16 — bleed aging out) and volume-breakout-long+ 8T −$0.56 0%WR (pre-kill aging). All 6 losing slots n≥5 are LONG-family or pump-chain−; short-side pump-chain− 32T −$0.55 21.9%WR remains blocked by EXTREME+dead-gap. Pipeline pause holding correctly — 0 trades since 04:08, 24h WR actually improved 36.8→37.8 vs prior run. Open #16258 BTC SHORT near SL, hold. Coding-mcp crash-loop fixed (stopped); disk 82% stable.
### Recommendation: none — wait for Oct 21 aging-resume; keep ai-trader+ LONG under watch (largest live 7d loser, drift guard in place).

## CEO Status — 20261017T140809Z
### Health: pipeline=inactive (vacation pause, by design) guardian=active open_pos=1
### Numbers: 24h 23T -$1.57 26.1% | 7d 212T -$2.86 34.4%
### Findings: Rotating Q = "Which signal is best?" — 7d best (n≥5): ai-trader-manual LONG +$0.54 40%WR (n=5), r2v2-long3 LONG +$0.52 57.1%WR (n=7); pump-chain+ LONG +$0.40 32.3%WR (n=31, volume anchor). SHORTs: no SHORT signal in top-3; SHORT_BIAS regime still on. Pause guardrail holding — 0 closes since 05:40 as expected. Disk 83% (watch 85%).
### Recommendation: none — pause is correct; eyeball first post-resume trades (~Oct 23) per kanban soak watch.

## CEO Status — 20261017T174926Z
### Health: pipeline=active guardian=active open_pos=0
### Numbers: 24h 12T -$0.92 25.0% | 7d 208T -$2.75 34.1%
### Findings: BTC SHORT #16258 now closed (DB open count 0 — SL raked to 81525 per 16:30 kanban, likely filled at breakeven). Rotating Q = "Which signal is best?" (17 % 14 = row 3) — 7d best (n≥5): ai-trader-manual LONG +$0.54 40%WR, r2v2-long3 LONG +$0.52 57.1%WR, volume-buildup- SHORT +$0.38 87.5%WR (n=8, best WR); no top-3 SHORT except volume-buildup-. Pause guardrail intact, 0 new trades since 05:40. Error alerts: expected pause-state warnings only + hotset failure cooldown entries (non-blocking).
### Recommendation: none — pause correct; eyeball #16258 close result and first post-resume trades (~Oct 23) per kanban soak watch.

## CEO Status — 20261017T180809Z
### Health: pipeline=active guardian=active open_pos=0
### Numbers: 24h 11T -0.87 27.3% | 7d 207T -2.63 34.3%
### Findings: Vacation pause holding (0 opens since 04:08, 0 open positions — BTC #16258 closed since 16:30 update). Regime memory (data/signal_regime_memory.json) last written 2026-10-11, entries have last_updated=null — at 7d staleness boundary; only 2 signals indexed.
### Recommendation: On/after Oct 23 resume, refresh signal_regime_memory.json from DB before any regime-specialist decisions are made off it.

## CEO Status — 20261017T220809Z
### Health: pipeline=inactive guardian=active open_pos=0
### Numbers: 24h 7T -$0.59 28.6% | 7d 203T -$2.56 34.5%
### Findings: Pipeline inactive at 22:08 (was active/resumed 16:57 — may be between runs or stopped; not verified further in this bounded run). Rotating Q = "Which signal is worst?" (17 mod 15 = row 2) — 7d worst n≥5: ai-trader+ LONG −$0.93 26.3% (19T), doji-bottom-long −$0.62 (20T, re-killed, historical), pump-chain− SHORT −$0.55 21.9% (32T). Floor-admit shadow cohort still −$1.40 over 32 trades (kanban escalation open, CEO decision pending).
### Recommendation: Confirm pipeline inactive is intentional (between-run vs stopped); floor-admit 0.5→0.3 decision still owed on pp<0.10 trades per kanban.

## CEO Status — 20261018T020810Z
### Health: pipeline=active(timer, last run SUCCESS) guardian=active open_pos=1
### Numbers: 24h 4T +$0.39 75.0% | 7d 201T −$2.17 34.8%
### Findings: _peak_high NameError spam (41x) auto-fixed commit bb41994f, shadow now reads pos dict; size-reduce 0.3x still correct (resume needs WR≥37 AND PnL≥$0, both failing). Proactive Q: SHORTs 7d 60T 33.3% −$0.72 — mild bleed, not the main problem (CHOP exits are, −$9.53/7d). Best signals 7d: r2v2-long3 6T 66.7% +$0.64, volume-buildout− 8T 87.5% +$0.38.
### Recommendation: none — soak #7 discipline holds; post-resume cohort still thin, no action until n≈20 trades.

## CEO Status — 20261018T032636Z
### Health: pipeline=active guardian=active open_pos=2
### Numbers: 24h 5T +$0.42 80.0% | 7d 199T −$1.80 35.7%
### Findings: SHORTs bleeding mildly — 7d 60T −$0.72 33.3%WR vs LONG 139T −$1.08 36.7%. Both negative; SHORT midband block + floor-35 soak already in flight, no new action. `_peak_high` NameError (41x) already auto-fixed per error_alerts. Trade frequency low (0.2/hr) — market/filter, not fault.
### Recommendation: none — soak continues; wait for post-resume cohort to measure the 11 standing changes.

## CEO Status — 20261018T072637Z
### Health: pipeline=timer active (service inactive between runs — normal) guardian=active open_pos=0
### Numbers: 24h 10T $+0.19 50.0% | 7d 202T $-2.89 34.7%
### Findings: SHORTs still bleeding mildly (7d 61T 32.8% −$0.78) but LONGs bleed more (141T 35.5% −$2.11); size-reduce 0.3x correctly active, flat book in SHORT_BIAS. Error alerts clean post-autofix (MFE-CUT `_peak_high` fixed, coding-mcp stopped).
### Recommendation: none — soak continues; TAT shadow needs 14 more fires before bb-bounce T=55m flip.

## CEO Status — 20261018T112637Z
### Health: pipeline=active (timer cadence; brief inactive between runs is normal) guardian=active open_pos=1
### Numbers: 24h 12T +$0.13 41.7% | 7d 204T -$2.95 34.3%
### Findings: Rotating Q "new signals this week?" — 0 built this week; work has been filters/shadows/TAT restructure only. Error alerts clean post-fixes (MFE-CUT _peak_high fixed, coding-mcp disabled).
### Recommendation: Delegate 1 new signal build to signal_analyst targeting NEUTRAL/SHORT_BIAS regime gaps (volume-buildup- allocation watch from brain_auditor is the best existing candidate to clone).

## CEO Status — 20261018T152637Z
### Health: pipeline=active guardian=active open_pos=0
### Numbers: 24h 15T +$0.08 40.0% | 7d 205T −$3.65 33.7%
### Findings: SHORTs mildly bleeding (64T −$0.79 32.8%) but LONGs worse (141T −$2.86 34.0%); 7d slightly worse than last audit (−$3.65 vs −$3.00) with 2 more losses — consistent with size-reduce still correctly active. Sideways: two crash-looping services (metrics_collector, coding-mcp — dead scripts) auto-disabled; if they reappear, remove unit files.
### Recommendation: none — soak discipline stands; brain_auditor's 11 unvalidated changes + escalation #15 OOS remain the active plan for resume-day ~Oct 23.

## CEO Status — 20261018T192638Z
### Health: pipeline=active(timer) guardian=active open_pos=0
### Numbers: 24h 14T +0.03 35.7% | 7d 201T -3.58 33.8%
### Findings: Rotating Q (18%14=4 "pipeline healthy?") — YES: timer active, fired 10s ago, guardian active, error_alerts confirm 30/30 pipeline runs OK; service inactive between runs is normal one-shot behavior. Size-reduce 0.3x correctly still on (7d WR 33.8% < 37, PnL -$3.58 < $0).
### Recommendation: none

## CEO Status — 20261018T232638Z
### Health: pipeline=OK (timer-driven, run in progress 23:27) guardian=active open_pos=2
### Numbers: 24h 13T −$0.35 30.8% | 7d 201T −$3.66 33.3%
### Findings: 24h flipped negative (was +$0.08 @17:05); 2 open SHORTs opened post-check; hotset-empty WARN ongoing (confluence blocking, flagged 16:44). Rotating Q — new signals this week: 0 (shadows/TAT/MFE-CUT only, no new signal shipped).
### Recommendation: none — soak holds; Oct 19 re-evals (ai-trader+ shadow, exit-ladder OOS) already queued.

## CEO Status — 20261019T032638Z
### Health: pipeline=active guardian=active open_pos=2
### Numbers: 24h 13T -0.32 30.8% | 7d 195T -4.00 33.3%
### Findings: No new trading errors (known hotset-empty confluence-block warn persists; 2 open positions). Rotating Q "pipeline healthy?" — yes: timer firing every 1min, service completes, guardian active, disk ~82%.
### Recommendation: none — resume-day Oct 23 stack + ai-trader shadow re-eval today are already queued; 0.3x size-reduce correctly still active (both resume conditions failing).

## CEO Status — 20261019T072640Z
### Health: pipeline=active guardian=active open_pos=4
### Numbers: 24h 12T +$0.09 58.3% | 7d 195T −$3.76 33.8%
(PG self-query 07:26 UTC; size-reduce 0.3x still correct — both resume conditions failing, ~Oct 23)
### Findings: Proactive Q "coins in accumulation?" — coin_tracker Wyckoff classifier is degenerate: 90/94 coins latest phase="accumulation", only 1 markup, predictive_score NULL everywhere, 6/94 stale >24h. Phase label carries zero discriminative signal. Side-find: 07:26 error_alerts.md entries contain unsubstituted "TOK/TS" template placeholders — scrubbing bug in the alert writer.
### Recommendation: Weekly deep run — audit coin_tracker wyckoff_phase classifier (90% accumulation = broken threshold, not a market state) and fix the error_alerts.md token-scrub template. No action this run.

## CEO Status — 20261019T112640Z
### Health: pipeline=active guardian=active open_pos=0
### Numbers: 24h 18T -$0.35 50.0% | 7d 200T -$4.05 34.0%
### Findings: Clean. Pipeline timer-firing normally (first is-active check caught mid-cycle; recheck active). No critical alerts; hotset-empty WARN ongoing (known, confluence gate working as designed), 3x token-cooldown blocks (INFO). 24h WR 50% healing; size-reduce 0.3x still correct per 7d 34% WR.
### Recommendation: none — lift-watch protocol stands for Oct 20-21 auto-clear; self_learner candle-OOS backtest still undelivered (escalation open since Oct 13).

## CEO Status — 20261019T152640Z
### Health: pipeline=active guardian=active open_pos=0
### Numbers: 24h 16T -$0.34 50.0% | 7d 200T -$4.09 34.0%
### Findings: Clean. Rotating Q5 (pipeline healthy): both units active, 0 errors/tracebacks last 30min, prices fresh; coding-mcp crash-loop (12k restarts) was auto-fixed 14:45 (disabled). Hotset-empty WARN from Oct 18 18:43 still open in alerts log but trading continues (12 trades today). DB matches CURRENT.md headline numbers (verified, not trusted).
### Recommendation: none — status run; Oct 20-21 size-reduce lift-watch and pp-cond floor surface stay on brain_auditor/CEO deep-run agenda.

## CEO Status — 20261019T192640Z
### Health: pipeline=healthy (timer-triggered; active mid-cycle #248613) guardian=active open_pos=0
### Numbers: 24h 17T -$0.38 47.1% | 7d 201T -$4.13 33.8%
### Findings: clean — pipeline `is-active` shows inactive between timer ticks (normal); service + watchdog fine, no new trading-path errors (coding-mcp crash-loop already disabled)
### Recommendation: none — size-reduce 0.3x stays; auto-clears Oct 20-21 with lift-watch protocol per prior plan

## CEO Status — 20261019T232640Z
### Health: pipeline=active(timer) guardian=active open_pos=2
### Numbers: 24h 16T -0.32 50.0% | 7d 195T -3.75 34.4%
### Findings: pipeline inactive-between-runs is normal (timer fired 4s ago, completed clean); hermes-coding-mcp crash-loop auto-disabled earlier today; disk 83% (threshold 85%). Proactive (SHORTs 7d): SHORT 64T −0.79 31.3% vs LONG 131T −2.96 35.9% — both bleed, SHORTs not the worse side; no action.
### Recommendation: Watch disk to 85% before weekend; recreate run_mcp_server.py only if MCP coding integration needed.

## CEO Status — 20261020T032641Z
### Health: pipeline=active guardian=active open_pos=1
### Numbers: 24h 17T -$0.41 41.2% | 7d 195T -$3.30 34.9%
### Findings: Rotating Q (confluence blocks): pipeline.log confluence entries are stale (last Oct 15) — ichimoku- single-type SHORTs were the main blocked family, no recent block activity logged. Open pos 1: BTC LONG ai-trader-pending @ -0.16% (opened 03:13). Error alerts show hotset failure-cooldown blocks + signal rollbacks (known, non-critical). CURRENT.md claimed 0 open — DB shows 1, DB wins.
### Recommendation: none

## CEO Status — 20261020T072641Z
### Health: pipeline=active guardian=active open_pos=0
### Numbers: 24h 16T -1.00 18.8% | 7d 191T -3.53 34.6%
### Findings: Rotating Q (new errors): hotset failure cooldown blocks (~1h TOK), mark_signal_executed rollbacks, atr_sl_hit phantom warnings — all previously flagged, no new structural errors. Flat open correct in dual SHORT_BIAS/STRONG_DOWN; size-reduce 0.5x still active.
### Recommendation: none — continue vacation shadow posture; recheck size-reduce lift once 24h WR recovers above 35%.

## CEO Status — 20261020T112642Z
### Health: pipeline=active guardian=active open_pos=1
### Numbers: 24h 11T -0.36 18.2% | 7d 177T -4.00 33.3%
### Findings: New errors (rotating Q6): hermes-coding-mcp crash-loop 14,588 restarts auto-disabled (missing script); disk 84% (pipeline.log 192M); atr_sl_hit phantom warns; no pipeline-affecting errors. DB 7d WR 33.3% <35 and pnl −$4.00 <−$2 — both size-reduce resume conditions still failing, 0.5x correctly held.
### Recommendation: none — after vacation, restore or permanently remove run_mcp_server.py unit and add logrotate for pipeline.log (disk trend, not yet urgent).

## CEO Status — 20261020T152642Z
### Health: pipeline=active guardian=active open_pos=0
### Numbers: 24h 19T −$0.14 21.1% | 7d 168T −$2.70 35.1%
### Findings: Q13 coin_tracker signals this week = 0 closed trades (7d, signal ILIKE %coin_tracker%). BTC manual LONGs #16306/#16307 now closed (open_pos 0). Hotset failure-cooldown blocks + one opencode gate-call failure in error_alerts; coding-mcp crash-loop already auto-fixed 09:45. Disk 84% watch from earlier alert stands.
### Recommendation: Delegate coin_tracker entry-signal build to signal_analyst (0 trades/wk vs ≥5 target) — re-raise in weekly deep run; no action this run.

## CEO Status — 20261020T192642Z
### Health: pipeline=active guardian=active open_pos=1
### Numbers: 24h 19T -0.22 21.1% | 7d 162T -2.47 35.8%
### Findings: Rotating Q (coin_tracker scores): FRESH — agg_scores 112 coins @19:28 UTC (2min ago), timer healthy (next 19:30). Losses shallow (max ~$0.31), size-reduce 0.5x containing. Error alerts show repeated opencode-gate failures + cooldown blocks (18:26).
### Recommendation: none — vacation soak continues; add logrotate if disk crosses 85% (currently 84%).

## CEO Status — 20261020T232643Z
### Health: pipeline=active guardian=active open_pos=2
### Numbers: 24h 22T −$0.30 22.7% | 7d 161T −$2.52 36.0%
### Findings: coin_tracker scores fresh (112 coins, 29s old, all updated same ts). Rotation Q12. Error alerts show repeated tokenized BLOCK/cooldown + BTC_LEVEL warnings and one opencode-gate exec failure — expected cooldown machinery, no pipeline faults. Disk 84%.
### Recommendation: none

## CEO Status — 20261021T032643Z
### Health: pipeline=inactive guardian=active open_pos=2
### Numbers: 24h 26T -$0.60 19.2% | 7d 159T -$2.97 35.2% (PG self-query)
### Proactive Q (day21): What regime are we in?
LONG_BIAS both TFs (btc_15m + btc_4h), continuum BELOW EMA300, zscore STRONG_NEG, volatility NORMAL — chop-pin with bear lean (CURRENT.md 01:40 UTC; no live regime state file found in data/ for fresher check). Consistent with known wrong-side LONG bleed cohort in mid-band.
### Findings: clean-ish — 24h WR 19.2% shallow (max recent losses ~-$0.31), size-reduce 0.5x containing; pipeline inactive between timer runs (oneshot, expected); disk 85% on / (monitor-only per error_alerts 02:45).
### Recommendation: none new — pre-existing: enable logrotate on logs/ if disk crosses 90%; ~15+ unvalidated soaks await CEO eyeball at vacation resume (~Oct 23).

## CEO Status — 20261021T072643Z
### Health: pipeline=active (timer tick; `is-active` caught inter-tick gap) guardian=active open_pos=2
### Numbers: 24h 24T -0.24 20.8% | 7d 153T -2.64 36.6%
### Findings: clean — numbers match CURRENT.md; losses shallow (size-reduce 0.5x holding), alert log has only known cooldown noise + disk at 85% (watch, logrotate if >90%). Rotating Q (coin_tracker signals this week): **0 of 153 7d trades carry a coin-tracker/accumulation signal** — coin_tracker intelligence is built but never reaches the trades table.
### Recommendation: delegate signal_analyst one coin_tracker phase-transition signal (pre-registered, shadow-first) at vacation end Oct 23 — 0 attempts in 7d means the pipeline gap, not the tracker, is the blocker.

## CEO Status — 20261021T112643Z
### Health: pipeline=active (timer-fired 11:27) guardian=active open_pos=3
### Numbers: 24h 30T -0.50 26.7% | 7d 154T -2.75 36.4% (PG self-query, matches auditor #53)
### Findings: Flat state from CURRENT.md changed — 3 LONGs opened 11:01-11:22 (+0.14/+0.28/-0.07). error_alerts 09:27: hotset failure cooldown blocks (repeated, redacted) — worth a look but no pipeline errors. Rotating Q (confluence blocks): 378 blocks today, 24 coin-dirs, all single-type not in standalone bypass — top GMX SHORT 80, BLUR SHORT 45, TRX SHORT 40, HBAR SHORT 30.
### Recommendation: none (vacation soak; pump-chain- kill recheck already prepped for Oct 22)

## CEO Status — 20261021T152644Z
### Health: pipeline=active (timer-fired, running 15:27 UTC) guardian=active open_pos=1
### Numbers: 24h 35T -0.71 40.0% | 7d 162T -2.92 37.0%  (DB self-query)
### Findings: clean — errors are routine hotset-cooldown/RSI-floor blocks, no crashes; disk 84% watch-only. Rotation Q7 (confluence blocks): 2,813 CONFLUENCE-GATE-BLOCK in 48h, dominated by single-type SHORTs (GMX 218, BLUR 213, FIL 124, HBAR/GMT 120) — mostly ichimoku- alone vs SHORT_BIAS; these shorts are counter-trend anyway, gate is doing its job.
### Recommendation: none (vacation soak to Oct 23; pump-chain- kill recheck Oct 22 per pre-reg)

## CEO Status — 20261021T192644Z
### Health: pipeline=active guardian=active open_pos=0
### Numbers: 24h 41T -1.03 36.6% | 7d 164T -3.48 36.0% (DB self-query)
### Findings: Rotation Q7 (confluence blocks): zero CONFLUENCE-GATE-BLOCK events since Oct 15 — single-types either pass via STANDALONE_BYPASS or aren't firing; by-design, not a finding. 5 open positions drained to 0 since 17:45 (flat). Portfolio display -32.04% still display-calc suspect (DB = -$1.03/24h). Error alerts = hotset cooldowns + JUP RSI-floor blocks (filters working). Disk 84% watch-only.
### Recommendation: none (vacation soak; pump-chain- kill recheck Oct 22 per pre-reg)

## Risk-Budget Decision — 2026-10-21

**Decision: MODIFY — shadow the 2-3% band, not 4% extreme. LONG-only. Do not flip live params today.**

### Coupled change for shadow trial
- CUT_LOSER_PNL: -4.00 → **-6.00** (not -8.00; 2% cell captures 77% of upside at half risk)
- ATR_SL_MAX: 2.5% → **3.5%**
- Position size: 0.5x → **0.35x** (constant dollar risk: $0.44/trade)
- Direction: **LONG-only** (SHORTs bleed worse at all wider SL levels)

### Shadow parameters
- Duration: 7 days OR 200 closed LONG trades, whichever later
- Metrics: LONG WR ≥ +10pts vs current, HML count < 150% baseline, PM-trail activation rate up
- Ship shadow config, collect data, revisit. No live flip without metrics.

### Key insight
Sweep SL levels (%-denominated) and CUT_LOSER (account-PnL) are different axes. At 5x, CUT_LOSER=-6 gives -1.2% price stop. The right lever is wider stops + smaller size to keep dollar risk constant.

### Status
- Brief: `automation/ceo/brief-risk-budget-hml-2026-10-21.md`
- Plan updated: `plans/t-vacation-mode-2026-10-14.md` (Risk-Budget Decision section)
- Shadow config: PENDING (not yet shipped)

## CEO Status — 20261021T232644Z
### Health: pipeline=inactive(timer active, fired 8s ago — oneshot normal) guardian=active open_pos=0
### Numbers: 24h 38T -0.95 36.8% | 7d 161T -3.43 36.0%
### Findings: Rotating Q (coin_tracker signals this week): 0 trades in 7d with coin_tracker/wyckoff/phase signals — well below the <5 threshold. Alerts clean (watchdog stale-lock housekeeping + disk 84%, no errors). Confirms CURRENT.md (shallow chop bleed, flat posture correct).
### Recommendation: Post-vacation (Oct 23+), delegate a coin_tracker phase-transition signal build to signal_analyst — the system currently harvests zero edge from its coin_tracker intelligence.

## CEO Status — 20261022T032645Z
### Health: pipeline=active guardian=active open_pos=0
### Numbers: 24h 32T -$0.64 40.6% | 7d 159T -$3.26 36.5%
### Findings: Regime-specialist sweep (14d, n≥5): no positive specialist cells — worst clusters ai-trader+ EXTREME 16T 25% -$0.81, pump-chain+ HIGH 10T 30% -$0.66, doji-bottom-long HIGH 12T 33% -$0.57; FLAT is the only flat-to-green 7d regime (14T 50% -$0.05). EXTREME is 7d mode (63T 27% -$1.13). Matches known unarmed-chop cohort; vacation soak holds.
### Recommendation: none — 0 open is correct; Oct 23 stack (CONF_FLOOR=30 + doji kill) already covers the EXTREME/HIGH bleed families.

## CEO Status — 20261022T072645Z
### Health: pipeline=active(timer) guardian=active open_pos=1
### Numbers: 24h 31T -$0.59 41.9% | 7d 158T -$3.14 36.7%
### Findings: Regime = STRONG_DOWN bear-grind, LOW volume, BTC below EMA300 (781min+); continuum BELOW. 0→1 open is correct given current pin. Worst 7d signals: bb-bounce-v2-long+ -$0.60, pump-chain- SHORT -$0.58 (0% WR, kill recheck confirmed CANCEL per #70 CONF_FLOOR collision), ai-trader+ -$0.54. Error alerts: hermes-coding-mcp restart storm auto-fixed (script deleted, unit stopped); 12x CONTINUUM-RECOVERY overrides + mark_signal_executed skips = benign noise. Disk 84% watch.
### Recommendation: none — Oct 23 stack (CONF_FLOOR=30 + vacation-end flips) already covers the known bleed families; pipeline inactive is normal oneshot-timer pattern.

## CEO Status — 20261022T112645Z
### Health: pipeline=active guardian=active open_pos=0
### Numbers: 24h 23T -0.36 43.5% | 7d 159T -3.03 37.1%
### Findings: clean (DB confirms kanban; bleed shallow, 0 open flat correct in bear-grind; error_alerts: signal-reporter timeout + mcp restart-storm already auto-fixed, no trading impact)
### Regime (rotating Q): SHORT_BIAS both TFs, continuum BELOW, LOW vol, market_phase RECOVERY (per #73 10:00). Shorts only 55-65 band on volume break <82.6k; reclaim ~83.5k WITH volume → continuum-trend+ LONG (14d 75% WR); mid-band = no trade.
### Recommendation: none — status healthy; CONF_FLOOR bare-only ship Oct 23 per auditor pending CEO eyeball.

## CEO Status — 20261022T152646Z
### Health: pipeline=active guardian=active open_pos=0
### Numbers: 24h 9T -0.33 22.2% | 7d 157T -2.69 37.6%
### Findings: clean — quiet market (last close 09:01, 6.5h flat = correct), size-reduce 0.5x holds; error_alerts shows disk at 84-85% threshold + price-collector LOCK-WAIT contention (all resolved at 0.1s), no trading impact. Regime (rotating Q): broad SHORT_BIAS — 97/127 tokens short, 29 neutral, BTC itself NEUTRAL (52.1), consistent with STRONG_DOWN readiness; mid-band no-trade stance correct.
### Recommendation: none — 24h WR 22.2% on n=9 in a 6h-quiet window is small-sample, not a signal; monitor disk (logrotate backlog parked).

## CEO Status — 20261022T192646Z
### Health: pipeline=active guardian=active open_pos=1
### Numbers: 24h 4T +0.27 75.0% | 7d 155T -3.08 38.1%
### Findings: Clean — quiet market (4 closes/24h, last audit saw 0 open at 18:58, BTC SHORT #16353 now open). Error alerts: disk 84% watch, 2 criticals auto-resolved (dead sentiment-aggregator disabled, summarizer timeout reset). Rotating Q (regime): 15m aggregate LONG_BIAS (30L/18S/81N of 129) vs 4h SHORT_BIAS (98S/105) — cross-TF split, continuum BELOW, mid-band = no trade stands.
### Recommendation: none

## CEO Status — 20261022T232647Z
### Health: pipeline=active (oneshot done 23:27, timer live, rc=0) guardian=active open_pos=2
### Numbers: 24h 4T +$0.27 75.0% | 7d 150T -$3.44 38.0%
### Findings: Disk 85% WARN (largest files are active logs — no safe auto-fix); repeated hotset-failure cooldown blocks in error_alerts (non-fatal). Rotating Q (row 0, What's the PnL?): 24h green (+$0.27, 3/4 WR), 7d still -$3.44 on 38% WR — consistent with brain_auditor #83's unarmed-chop bleed diagnosis; no new anomaly.
### Recommendation: none — Oct 23 resume stack (CONF_FLOOR bare-only + pump-chain+ kill verdict) already queued for CEO eyeball.
## CEO Status — 20261023T032647Z
### Health: pipeline=active guardian=active open_pos=2
### Numbers: 24h 6T +0.43 83.3% | 7d 148T -3.35 37.8%
### Findings: Regime-specialist scan (rotating Q): pump-chain+ bleeding in EXTREME/HIGH (9T 0% -0.79 / 6T 16.7% -0.50) and pump-chain- EXTREME 6T 0% -0.38 — the exact conf<30 chop cohort; CONF_FLOOR bare-only (staged, ships Oct 23 per audit stack) covers it. continuum-trend+ FLAT 5T 80% +0.09 is the only green specialist (tiny n). Disk at 85% — auto-gzip ran, monitor only. No Tracebacks, no new errors.
### Recommendation: Proceed with CONF_FLOOR=30 bare-only ship today per audit #85 pre-reg; no other changes this run.


## CEO Status — 20261023T072648Z
### Health: pipeline=active guardian=active open_pos=3
### Numbers: 24h 7T +0.46 85.7% | 7d 143T -3.11 37.8%
### Findings: Regime-specialist scan (rotating Q): pump-chain+ LONG still bleeds in EXTREME (8T 0% −0.71) and HIGH (6T 16.7% −0.50), ai-trader+ EXTREME 7T 14.3% −0.71 — all covered by queued CONF_FLOOR / disabled-CEO-domain levers, nothing new. Green cells: continuum-trend+ FLAT 5T 80% +0.09, bb-squeeze+ NORMAL 6T 66.7% +0.22 (n<10, monitor). Disk 85% WARN with auto-gzip applied; 0 Tracebacks; error_alerts shows only known cooldown/knife/override noise. 3 open positions — first non-zero book since Oct 22 quiet window.
### Recommendation: Proceed with CONF_FLOOR=30 bare-only + arm-dampen scope ruling per the Oct 23 CEO stack; no other changes this run.

## CEO Status — 20261023T112649Z
### Health: pipeline=active guardian=active open_pos=2
### Numbers: 24h 11T +$0.29 63.6% | 7d 139T -$2.86 38.1%
### Findings: Worst 7d signal (n>=10): pump-chain+ LONG 14T -$1.21 7.1% — known CONF_FLOOR cohort, NO-KILL already stands (30d OOS positive); disk 84-85% WARN, auto-fix compressed logs, no action needed now.
### Recommendation: none — clean run; execute today's stacked CEO decisions (fk ruling → CONF_FLOOR, vacation state, size-reduce semantics) in a deep run.

## CEO Status — 20261023T152649Z
### Health: pipeline=active guardian=active open_pos=1
### Numbers: 24h 19T -0.36 42.1% | 7d 129T -3.15 34.9%
### Findings: rotating Q = "Any new errors?" — yes, 3 classes: disk / at 85% (94G/118G; pipeline.log 261M, signal-compactor.log 102M, no >7d logs to reclaim), CC hotset failure-cooldown loop (14:27), price_collector 291s stall at 14:43 (self-recovered, age back to 56s). Also hermes-upgrade-implementer timeout earlier (auto reset-failed, timer fine).
### Recommendation: ship logrotate for pipeline.log + signal-compactor.log now — disk has zero reclaimable headroom left before the 85% warn threshold.

## CEO Status — 20261023T192649Z
### Health: pipeline=active(timer, svc inactive between fires, last run 56s ago) guardian=active open_pos=1
### Numbers: 24h 19T -0.47 42.1% | 7d 122T -2.41 37.7%
### Findings: rotating Q = "Which signals are regime-specialists?" — by volatility_regime 7d: EXTREME 43T 27.9% -$1.26 (worst), NORMAL 56T 41.1% -$0.81, HIGH 9T 44.4% -$0.29, FLAT 14T 50.0% -$0.05. No winning regime cell (all PnL negative); EXTREME bleed already covered by the pre-registered SHORT×EXTREME 0.5x dampen — no new action.
### Recommendation: none — clean; deep run should clear today's stacked CEO decisions (vacation state, fk ruling/CONF_FLOOR, TAT variant-C GO, AVAX exit call).

## CEO Status — 20261023T232650Z
### Health: pipeline=active (timer-triggered, running at check) guardian=active open_pos=2
### Numbers: 24h 22T -0.15 50.0% | 7d 122T -1.72 39.3%
### Findings: 24h WR recovered to 50% (was 42.1% at 19:26 run), PnL still slightly negative. Rotating Q (regime-specialists, 7d by volatility_regime): NORMAL 56T 41.1% -0.81 | EXTREME 42T 31.0% -0.73 | HIGH 10T 50% -0.13 | FLAT 14T 50% -0.05 — NO winning regime cell; EXTREME bleed already owned by pre-registered SHORT×EXTREME dampen, no new lever. Error alerts: upgrade-implementer timeout auto-fixed (900→1800s), IO-token hotset failure cooldown entries, disk 85% (18G free).
### Recommendation: disk trending to 90% — schedule scoped cleanup (/var/log/syslog 1.2G, /root/zscore 2.2G) in weekly deep run; everything else clean.

## CEO Status — 20261024T032650Z
### Health: pipeline=active guardian=active open_pos=0
### Numbers: 21T -0.05 47.6% | 7d 120T -1.17 40.0%
### Findings: Rotating Q (regime memory): scripts/signal_regime_memory.json stale — updated_at 2026-10-11, 13d > 7d bar (data/signal_regime_memory.json). Watchdog WARNs: signal rate ~17/h (<20/5min threshold) and stale-lock churn 28x/hr; disk 85%. Error alerts otherwise clean, 0 tracebacks.
### Recommendation: Refresh signal_regime_memory.json from DB this week (stale 13d); no action on health/numbers — flat book is correct-by-traffic.

## CEO Status — 20261024T072650Z
### Health: pipeline=active guardian=active open_pos=1
### Numbers: 24h 20T -0.08 45.0% | 7d 120T -1.17 40.0%
### Findings: Rotating Q (regime memory): signal_regime_memory.json last updated 2026-10-11 (13d stale, threshold 7d), 29 signals — stale regime params may be mis-scoring regime-specialist gates. Other: disk 86%, recurring stale-lock/signal-count watchdog WARNs, self-healing.
### Recommendation: Refresh signal_regime_memory.json from DB in the next deep run; none else.

## CEO Status — 20261024T112650Z
### Health: pipeline=active guardian=active open_pos=0
### Numbers: 24h 16T -0.01 50.0% | 7d 121T -1.16 40.5%
### Findings: Rotating Q (row 5, new errors?) — no actionable errors. One transient `position_manager: IndentationError` at 08:50 UTC, self-resolved (rc=0 on 8+ consecutive runs, script parses clean). Disk 86% (17G free) recurring WARN — remaining hogs need CEO approval, no eligible cleanup. NXPC mid-band block = design working. Pipeline/guardian both active; audit #111 confirms 0 open trades, correct chop pin.
### Recommendation: none — system clean; disk reclaim needs human approval if it crosses 90%.

## CEO Status — 20261024T152651Z
### Health: pipeline=active guardian=active open_pos=0
### Numbers: 24h 11T +$0.87 81.8% | 7d 124T -$0.93 41.1%
### Findings: Rotating Q (regime memory): signal_regime_memory.json last modified 2026-10-11 = 13d stale (>7d bar). Pipeline clean, 0 open, 24h green at 81.8% WR; error_alerts = INFO/cosmetic only + recurring disk-85% warning (17G free, hogs need CEO approval). Note: CURRENT.md reported 24h +$0.39/13T at 14:45; DB now reads 11T +$0.87 — DB is source of truth, two more closes landed.
### Recommendation: Refresh signal_regime_memory.json from DB (stale 13d) — delegate to self_learner in weekly deep run; disk-85% cleanup still needs CEO pick of which hogs to shrink.

## CEO Status — 20261024T192651Z
### Health: pipeline=active guardian=active open_pos=2
### Numbers: 24h 9T +0.82 77.8% | 7d 123T -0.98 40.7%
### Findings: clean — services active, errors only disk/hotset-cooldown already auto-fixed; 7d still negative (-0.98) but improving vs prior runs (-2.77 → -0.98)
### Recommendation: pump-chain- family is the 7d PnL leader (+0.31 combo / +0.25 bare SHORT) despite 33% WR — snapshot its params as a candidate regime-specialist (proactive Q: best signal). None else.
