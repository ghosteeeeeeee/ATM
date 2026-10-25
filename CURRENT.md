# Current State — brain_auditor #141 2026-10-25 15:15 UTC
**Last Updated: 2026-10-25 15:15 UTC**
**Updated by: brain_auditor #141. Prior: #140 14:00 (preserved in git history).**

## HEADLINE — WATCHDOG HANDOFF ANSWERED: pump-chain+ EXTREME mid-band block REJECTED-WITH-DATA
The 14:14 cycle routed PATTERN 3 ("audit pump-chain EXTREME-LONG mid-band cell") here.
Result of the counterfactual block (EXTREME × meta_rsi 50-61):

| window | blocked n | WR | pnl if blocked |
|---|---|---|---|
| 30d | 21 | 7W | **+$1.00** → blocking LOSES money |
| 14d | 12 | 3W | +$0.10 (same sign) |
| conf≥30 subset 30d | 14 | 5W | +$1.40 |

The 7d `-0.76` (12T) is a **window artifact** — the same block is positive in both wider
windows. V4/V5 confirmed killed (False/NEVER_REENABLE), V6 master on, HIGH block holding
(only pre-ship HIGH trades in window). **Actual bleed = conf<30**: bare pc+ LONG conf<30 =
26T 6W `-1.29` (identical cohort at 14d and 30d) → that is the pre-registered CONF_FLOOR
target; fkA 6/27 = **22.2% still >20%** → hard floor stays held for the CEO fk ruling, and
the conf<30 size-dampen 0.25x alternative (fkA=0 by construction) remains queued.
**No new gate, no constants change (EMPTY git diff).**

## SHIPPED — component co-signal `source` stamp (closes #138 "in flight")
`decider_run.py +12L`: at trade open, `_exec_meta['source']` now carries the
component-level confluence string the COSIG-GATE sees (e.g. `bb_bounce+,ma100-cross+`).
Trades only ever had signal names in `trades.signal`, so solo-vs-confluence outcomes for
STANDALONE_BYPASS signals were unmeasurable — this was the standing blocker for the
bb-bounce bypass-removal lever (30d: solo 56T 50% `-0.56` vs combo 4T 4W `+0.46`, n=4).
py_compile PASS, self-check 5/5, **bug_hunter SHIP 6/6** (1 LOW: MAX(source) is
group-level not row-level — pre-existing aggregation quirk, analysis must know).
**VERIFY: first trade opened after 15:15Z must show `_signal_metadata.source` in PG.**

## GATE INTEGRITY (standing check) — 0 LEAKS
`gate_leak_census.py --selfcheck PASS`, `--days 7`: ALLOW 10 | WAIVER 19 |
PATH-EXEMPT 8 | PRE-RULE 0 | **LEAK 0**. Waiver active → expires **2026-10-27T00:00Z**.

## LOSING AUTOPSY 48h — WRONG-SIDE REFUTED 65th CONSECUTIVE RUN
Adverse-first `recovery_replay.py` (selfcheck PASS): **n=9 = 2 never-adverse / 4
recovered-after-adverse / 3 NEVER** (ALT vb- `-0.17`, BTC pending `-0.08`, PUMP r2v2
`-0.01` — all immaterial). 0 new patterns. Winning side = flat.
Valid refs: #61 p=0.116, #84 fwd-return t=-0.04.

## MANDATE — CHOP vs TREND (fresh)
- **7d: trail family 53T 46W 86.8% `+3.60` vs chop exits 58T 2W `-4.74`**
- **14d: trail family 118T 104W 88.1% `+10.03` vs chop exits 186T 6W `-14.83`**
- armed 7d `+3.25` / unarmed `-3.97`; armed 14d `+9.17` / unarmed `-12.89`
- 7d exits: HML 14T 0W `-1.80` (100% never armed) · atr_sl 25T 0W `-1.40` (68% never armed)
  · profit-monster-trail 44T 39W `+2.68`
- round-trips: 14d 42T `-2.23` / 30d 96T `-6.78` → post-arm floor D=0.20 (CEO GO) still
  the single largest measured recovery path

## CREATIVE (2 measured rejections + 1 ship)
1. **Lower-arm rescue CLOSED-WITH-DATA** — HML MFE ceiling: 14d only 4/68 (5.9%) ever
   reached MFE 0.30, 13/68 (19%) reached 0.20; 30d 24/155 / 41/155. A lower
   PM_TRAIL_ACTIVATE can touch ≤6% of the chop cohort → chop is entry-quality, not
   exit-timing. Do not re-propose.
2. **Universal TAT gap COLLECT** — 30d uncovered LONG HML ≥45m: n=19 `-2.17` but 5T are
   killed signals → live n=14 `-1.46` across 12 signals. Below bars → re-measure at
   n≥30 or pnl ≤ -3.00.
3. **Source stamp shipped** (top).

## SHADOW (mandate 2b) — 2/5 answerable
- contrarian outcome-join re-ran live (812 rows / 540 joinable): **pump-chain- flip
  **64.1% n=343 STANDS** → Oct 27 PROMOTE; btc-pump-rider+ 25% do NOT flip; overall 49.8%
- shadow_trader report: 20,940 signals / 20,271 closed; best gate EXEC-BLOCK (7% would_win)
- oscillator frozen / wyckoff 304 + floor_admit 1,829 pending join / rr orphaned

## LAST-RUN VERIFY (#140/#139/#135) — all PASS
Rule 4 (WITHDRAWN) **observed working**: the 14:14 cycle's pattern_alerts now carry
"MEASURED-REFUTED … Do NOT re-issue as actionable" — the #139→#140 re-affirmation did not
recur. gate_leak_census ✓ · floor still 45 ✓ · ema300_duration fix present ✓ · spider
trail tiers ✓ · constants EMPTY diff · kill flags ✓ · size-reduce file absent = 1.0x ·
0 Tracebacks Oct 25 (log's 5 all Oct 11) · session lock absent.

## STATE
24h **15T 11W 73.3% `+0.81` GREEN** (last close 11:08Z) | 48h 28T 19W `+1.20` | 7d 121T
44.6% `-0.43` (LONG `-0.85` / SHORT `+0.42`) | 14d 328T `-3.43` | 30d 690T `-2.01`.
**0 open = CORRECT** on the unresolved BTC pin (AT EMA300 ~80406 for 112+ min, vol LOW,
velocity SLOW — the exact environment where never-armed chop entries breed). EXTREME 7d
`-0.78` is pump-chain concentration, not a regime gate (30d pc+ EXTREME LONG positive).
Vacation mode still on (review-queue constraints active); waiver expires Oct 27;
size 1.0x.

**Readiness:** flat until 1m closes sustain above/below EMA300 for 15-30m; then align
entries to that side; mid-band = no trade; trail-family signals first.

**Next:** Oct 27 contrarian PROMOTE + waiver re-measure [35,45) + midband re-measure +
coin_regime (n=85) · first post-ship trade = `source` stamp verification · bb-bounce
solo-vs-confluence once n≥20 · CEO GO queue unchanged (post-arm floor D=0.20, fk ruling)
· Nov 1 self-healing SKIP · Nov 15 floor_admit · session_brain rebuild (5th) ·
`gate_leak_census.py` each run.
