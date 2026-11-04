# BRIEF: T's HARVEST MANDATE — "figure out what works and DO IT" (2026-11-03, third consult today)

## T's words (verbatim intent)
"Looks like nothing was changed — again hours of BTC dumping and take a look at the trades,
mostly longs that lost. I wonder why. We have 6,327 closed trades, 100x that in shadow data,
still losing... again are we allergic to profit??? **Harvest the data we have, figure out what
works, and please do it — we're totally running out of time.** The hl_copy_trader and
jup_yolo_mirror seem to be carrying all the trades, which means you've phased all the old
winning signals out one by one. We're still hitting HML so we haven't figured out how to get
entries or exits right or both. You have the data, you can do this — **set it as a goal. Any
previous goals we've set have not been met.** We're 56% winrate on 200 trades and net
negative. Fix it."

→ A GOAL IS NOW FORMALLY SET (goal-704ed65e, armed, 12 rounds): sustained net-positive daily
PnL at the standing 0.3% daily target, completed ONLY by verified live numbers. This consult
must produce the EXECUTION PLAN that the goal rounds will drive. He is done with studies
that don't ship. Where data is strong → ship LIVE; where genuinely insufficient → shadow with
SHORT bars. No more open-ended collections.

## Verified numbers (gathered just now — trust, don't re-derive)
- Total closed: **6,356** (T's 6,327 grown since). Shadow reservoir: gate_shadow ~54k events +
  shadow_trades ~44k ≈ **100x the closed book**, as T says.
- **11-03 (today, BTC dumping):** LONG 40 (23W, −$0.50) vs SHORT 11 (6W, −$0.17) — 79% long
  flow, both sides negative. Since ceiling deploy (07:57): 26 LONG opens vs 6 SHORT — ratio
  still 4:1 in the first hours (ceiling 65→75 went live at 07:57 with revert rule; three
  bear-structure shadows log-only; join builder due 11-16; bars 11-10/11-17).
- **Last-200 signal mix CONFIRMS T's concentration claim:** `jup_yolo_mirrored` = **107/200
  (53.5%)**, −$0.95; then pump-chain- fades 27+4, bb-squeeze+ 11, volume-buildup- 10,
  hl_copy_trader 7, pump-chain+ 6, warrior-sr 4+2, r2v2-long3 3, continuation+ 3... The old
  winners are single-digit thin. jup alone is the book.
- **HML 7d: 33 hits = −$4.29, of which jup_yolo_mirrored 20 = −$2.95** — the HML problem IS
  the concentration problem (also vb- 3, continuation+ 2, hl_copy 3).
- Standing context: 56-57% WR with inverted R:R (capstone: "no signal tweak fixes arithmetic"),
  fees 0.09% RT (BUG-073: all quotes net-of-fees), stop-asymmetry shadow shipping (1.0% price
  backstop = the exit-side fix for exactly the jup/vb bleed), prior verdict: admission funnel
  NOT working (longs admitted 4.3x rate), fade +EV but mints longs on dumps.

## What T demands: THE HARVEST — one comprehensive what-works pass, then ship
Deliver a single ranked execution package built from ALL of: 6,356 PG trades (net-of-fees,
by signal × direction × regime × vol × entry-quality fields), ~100k shadow events (token-day
deduped per the new gate-shadow-dedup-convention — event-level n is 7-10x wrong), the
existing counterfactual machinery (gate_shadow fwd, shadow_trades exit A/B, cell_stats,
mfe/mae, arm rates), and prior verdicts (do NOT re-derive settled items — extend them).

### Required rulings
1. **Fleet composition (T's #1 structural claim):** which signals/families are NET POSITIVE
   net-of-fees over 14d/30d and deserve amplification/restoration; which are dead and should
   be phased out — INCLUDING whether jup_yolo_mirrored's 53.5% share is itself the disease
   (it is −$0.95/200 with 20 HML — is the signal bad, or its sizing/stops/exit stack?).
   Then: the "old winning signals phased out one by one" audit — identify which winners were
   phased out over the last 30-60d, WHY each was phased (data-backed vs gate-accretion),
   and which, if any, the data says to restore. Give the target fleet: a concrete list of
   signals that should make up the next 200 trades, with expected edge.
2. **HML entry/exit fix (T: "we haven't figured out entries or exits right or both"):**
   decompose the 33 HML hits — entry condition wrong (RSI/extreme at entry, staleness,
   chase) vs exit architecture (stop too wide → stop-asymmetry already fixing 1.0% price
   for jup/vb — quantify how much of the 33 that covers) vs sizing. Deliver the missing
   piece(s) with bars. Note HML fires at −4% ACCOUNT (CUT_LOSER) — 20/33 from one signal.
3. **Dump-day long bias (fourth time open):** the admission funnel verdict + fix table
   shipped today (ceiling 75 live, 3 shadows). What REMAINS unfixed after today's round
   — specifically the fade's long-minting on dumps (27/200) and the long-heavy
   STANDALONE_BYPASS list (registered `long-bypass-regime-shadow`, 11-17) — and whether any
   of it now deserves LIVE action given "running out of time" (T's override of default
   shadow-first: name which, with the metric).
4. **Why "nothing changed":** today's changes are hours old (ceiling 07:57, shadows
   log-only) — but the 4:1 ratio persists. State plainly which parts of today's package
   will move the ratio and on what timeline, and what the FIRST fill/behavior proof will be.
5. **Immediate ship list:** everything above ranked as SHIP NOW (live, with revert) vs
   SHADOW (bar + deadline ≤11-17) vs KEEP, each with the exact file:line/constant and the
   metric — sized for execution under standing delegation in the next goal rounds.

### Constraints (standing)
No blanket kills / no time-of-day blocks (route via regime+vol gates); protected flags
(CONFLUENCE_REQUIRED, knife<35, floor 45, trial pairs, family bans with negative data);
flag polarity rules; net-of-fees everywhere (0.09% RT); token-day dedup for all fwd means;
shadow→enforce unless data is overwhelming (T explicitly wants speed now); every change
gets code review + bug_hunter + registry/calendar entry. Prior settled verdicts to EXTEND,
not reopen: stop-asymmetry (shadow live), short-relax 0/25, admission funnel fix-table
(ceiling+3 shadows), fade KEEP, pc-short-high KEEP (net-saving), floor-45 KEEP.

### Deliverable
Ranked execution package: fleet target list, HML fix, remaining dump-day actions, immediate
ship list — each line: action | file:line/constant | live-or-shadow | metric | revert/bar.
This becomes the goal-round playbook; the goal completes on verified live net-positive PnL.
