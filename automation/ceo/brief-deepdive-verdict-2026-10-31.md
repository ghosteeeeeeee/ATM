# CONSULT: T's deep dive complete — convert 3 mining lanes into the ranked action list

**Budget ~30 min; print by ~minute 22. T's ask (verbatim 2026-10-30): "we have been
collecting a lot of shadow data (100x more data), do a deep dive and see what we can do
to improve our signals, winrate and profitability. we're still net negative... again
really really surprised you (and the automation team) haven't figured this out yet."**

**The deep dive is DONE — three independent miners + my registry ledger, all read-only,
all numbers reproduced. Your deliverable: the ranked, labeled final list (everything
below already carries a candidate label — confirm/override/kill and we implement under
T's standing delegation). Numbers over comfort.**

## LANE 1 — Exits & trial (miner c2bfc632)

- 30d cohorts (n=771, gross −$3.16): PM-trail clips **$56.64 of winner foregone** (60%) — but +0.10pp giveback widen = **−$1.54..+$0.88** (naive $2.47 evaporates under 0.098pp execution lag) → **tiers stay protected (data-backed)**.
- **Coupled trial verdict DELIVERED EARLY (for its 11-03 registry entry): trial cost −$0.92** vs old params (money-leg sim on 142 closes: actual −$0.59 vs simulated-old +$0.33); ATR leg $0 (inert); per-trade worse (−$0.140 vs −$0.102); shadow Δ≈0; HML guard fired (−7.10%); brain_auditor #208 already reverted 10-31 08:59 → **REVERT-UPHELD, registry closed early**.
- Stops fire at local max-adverse (71.5% of stopped touch BE within 8h, but 61.5% go ≥1pp deeper first, −$69.76 excursion) → level isn't wrong; **reentry-study** registered (11-21).
- UGB-0.45: mean PASS (0.035→0.076) but median flat, n=13 → keep to 11-03.
- No exit variant ships (best +$0.52/30d, fails own +5pp bar). New clip: **atr_trail_hit $0.38/winner (n=31)** → atrtrail-clip-12 eval (11-14, unprotected trail).
- **⚠️ BUG-073: headline nets are gross — fees $6.05/437 trades → true 30d ≈ −$9.21.**

## LANE 2 — Log flags (miner 9e6368df)

- **CHASE-RATIO KILL executed** (enforce costs $1.27/17d; inert at consumption). **CHASE-MOVE KILL executed** (costs $0.41; was UNREGISTERED = governance gap closed) + the key insight: **signal-time edge ≠ exec-time edge** (exec shadows see only gate-survivors → blocked set = winners; every shadow gate must declare its node).
- CONF-FILTER split: wholesale KEEP (fk 76%), cap-leg → source-scoped jup conf-99 (−$0.44/17T), floor-leg DEAD (would kill +$0.55 of the live fade — landmine confirmed).
- Rider do-not-flip re-verified (27.6% n=607); oscillator fossil dead; **WYCKOFF KILL executed with polarity correction** (registry default said SHADOW_MODE=False — that would have gone LIVE; correct kill = PLUS/MINUS False at wyckoff.py:514; jsonl retired).
- Evidence protected: 41MB shadow gz → data/archive/ (survives rotation before 11-03/11-10).
- BUG-074: CTX-RULES shadow broken (str/dict).

## LANE 3 — Shadow DBs (miner 4ea6455f)

- **gate-shadow KEEP + join switch** (fwd-return 100% vs trade-join 13.9%; gates protective −$116 event/−$238-eq t=−3.4; switch implementing). **STRATEGIC: LONG blocks save ≈$528-eq (t=−12) but SHORT blocks COST ≈+$290-eq (t=+5.4) → T's over-blocking-Shorts claim now has a dollar sign.**
- **shadow-trader-bypass KILL** (sqx- sign-flipped negative t=−4.1; kills validated −0.0945% n=18,137; all 7 bypass cohorts negative). **relative-regime KILL** (collector dead 9.9d, unit never installed). **rr-engine KILL** (27.4d stale, no generator). **expiry-t5 SPLIT executed** (keep expiry fwd97.1% / t5 timer killed).
- Exit variants: none enforceable (ext_time = one-day artifact; wider_sl −0.041% t=−4.5 = revert confirmed; HML tail saves only 1.5% via exits → entry-side problem).
- Enforce candidates by bars: **NONE pass honestly** (VOL-GATE-BYPASS +$115 rejected: 82% one day).

## Registry state (the ledger)

**21 done / 44 total**; the open 23 = 9 deadline 11-03 (escalation, mid-band, ugb, chase*done…), flips fade-ctx-exempt 11-10 / storm 11-12, AMPLIFY candidates (winner-cell-150, jup-short-walk 11-14), evaluations (jup-regime 11-07, reentry 11-21, atrtrail 11-14), hygiene/zombie/momentum-cache.

## Questions (ranked, labels on the table)

1. **The single strongest structural fact: SHORT-blocking costs +$290-eq while LONG-blocking saves $528.** Per-gate: no single short gate clears a relax bar (all tiny/unstable/outlier-day), but the AGGREGATE does. Ruling: (a) commission a short-block-rate rebalance study (which gates to loosen, scoped, counterfactual-first), (b) accept the $290 as the price of the direction's poor base rates, or (c) something sharper you see from the aggregate numbers?
2. **Confirm/close the executed kills** (chase-ratio, chase-move, wyckoff, t5, bypass, relative-regime, rr-engine — all executed under failed pre-registered bars/defaults) — flag anything you want re-opened.
3. **Win-rate/profitability levers ranked by $ with your labels:** the honest top of the list is thin (BUG-073 fees truth, atrtrail-clip-12 +$0.38/winner, winner-cell already live, fade/storm flips pending bars). Is there an offense-side synthesis we're missing — the data says exits can't save the book (HML tail entry-side), gates are mostly right, and the mix is third-order. **What is FIRST-order that we haven't put on the table?** If the answer is "nothing new — execute the backlog," say that plainly: the 23 open entries + AMPLIFY cadence ARE the machine.
4. What NOT to touch (protected tiers upheld by data, knife, trial pairs, rc1 fade, family bans).

## Guardrails
READ-ONLY; labels implement immediately under T's standing delegation. No blanket kills.
