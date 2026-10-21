# Bug Hunter Verification: Wider SL Shadow Trial

**Commit verified:** `948143a5` — scripts: shadow_trader — wider SL shadow trial (CEO verdict 2026-10-21)
**Verified by:** bug_hunter, 2026-10-21, runtime-tested (real `--close` + `--report-wider` runs, temp-DB batch close, synthetic sim sweep)

## Summary
Constants, direction gating, schema and integration are all correct and the scripts run clean — but empirical testing proves the `ATR_SL_MAX 4.0` half of the trial is a **complete no-op** in the simulation (0/44 scenarios differ), the report's "Current" column misstates actual current WR by 15.2 points (35.4% vs actual 50.6%), and both HML report sections are permanently dead (query a column that never contains `hard_max_loss`).

## Verdict: FAIL

Not because anything crashes or leaks into live trading — it doesn't (shadow-only, no live impact, collection may continue). It FAILs because **as shipped, this trial cannot produce the evidence the CEO's 7d/200T review requires**: it measures only the CUT_LOSER floor change (not ATR_SL_MAX), and the report that will be shown at review prints factually wrong HML numbers plus an invalid Current-vs-Wider comparison. Fix the 3 HIGH findings before the 200-trade gate is evaluated.

## Constants Verification
- ✅ `SHADOW_TRIAL_CUT_LOSER = -6.00` (shadow_trader.py:62) — matches verdict, not -8.00
- ✅ `SHADOW_TRIAL_ATR_SL_MAX = 4.0` (shadow_trader.py:63) — matches verdict, not 2.5
- ✅ `SHADOW_TRIAL_DIRECTION = 'LONG'` (shadow_trader.py:64) — SHORT untouched
- ✅ `SHADOW_TRIAL_MIN_TRADES = 200` (line 65), `SHADOW_TRIAL_MIN_WR = 55.0` (line 66) — threshold constants correct
- ✅ Baselines match live constants: `CUT_LOSER_PNL = -4.00` (line 38) = hermes_constants.py:739; `ATR_SL_MAX = 2.5` (line 42) = hermes_constants.py:699 (0.025). Live constants **not modified** by this commit (still -4.00/2.5) — correct for a shadow trial.
- ⚠️ `SHADOW_TRIAL_REVIEW_DAYS = 7` (line 67) is defined but never used anywhere — the "7d" half of the 7d/200T review is not enforced or tracked.

## Simulation Logic Verification
- ✅ LONG only: `close_events()` gates on `SHADOW_TRIAL_ENABLED and d == SHADOW_TRIAL_DIRECTION` (line 1201); the function itself also returns early via `if direction != 'LONG'` (line 588)
- ✅ SHORT fallback verified empirically: `_simulate_atr_sl_tp_wider(..., 'SHORT', ...)` output is byte-identical to `_simulate_atr_sl_tp(...)` (tested, True)
- ✅ Uses `SHADOW_TRIAL_CUT_LOSER` for HML threshold (line 602), not `CUT_LOSER_PNL` — verified: crafted -1.5% dip → `hard_max_loss` at exactly **-1.2000%** price (= -6.00/5)
- ✅ Uses `SHADOW_TRIAL_ATR_SL_MAX` for SL cap (line 592), not `ATR_SL_MAX` — code-level correct (but see HIGH finding 3: the cap has zero runtime effect)
- ✅ Direction math correct: LONG-only branch, so `entry*(1+hml/100)` sign is right; `None` candles and `None` atr_pct guards work (tested)
- ✅ Exit types correct: `hard_max_loss`, `atr_sl_hit`, `atr_trail_hit`, `atr_tp_hit`, `no_exit` (observed in temp-DB close: 7/25 hard_max_loss, 13 atr_sl_hit, 2 atr_trail_hit, 1 atr_tp_hit, 2 no_exit)
- ✅ HML checked before ATR SL before TP each candle — consistent with spec precedence (hard_max=1 before atr=3)
- ❌ **But see HIGH-3: the wider SL cap itself is inert, and see HIGH-1/4: "Current" side and wider side are not valid comparators**

## Integration Verification
- ✅ Wider sim called in `close_events()` (line 1202), computed **outside** the `results` dict → cannot affect first-exit precedence (shadow cannot alter shadow-trade outcomes)
- ✅ Schema: CREATE TABLE includes `exit_wider_sl_json JSON` (line 143) + guarded ALTER (lines 191-194, `try/except OperationalError`) — column confirmed present in live DB
- ✅ UPDATE statement includes `exit_wider_sl_json=?` in fired branch (lines 1253, 1265)
- ✅ `report_wider_sl()` wired to `--report-wider` flag (line 2337, dispatch 2367-2368); excluded from run_all default set (line 2340-2343)
- ✅ Report queries execute without error (full run below)
- ❌ Hold branch (lines 1273-1280) and `reclose_events()` UPDATE (lines 1564-1581) do **not** write the wider column — see findings 7/8
- ⚠️ Report column set incomplete — see findings 1/2/6

## Findings

### HIGH — Report "Current" column is not actual current performance (15.2-pt WR error)
- **Location**: scripts/shadow_trader.py:2233-2242 (current query), vs actual first-exit
- **Issue**: The "Current" side compares `exit_atr_json` (ATR engine only — never sees HML, PM trail, rr_engine, etc.) while framing the table as "CURRENT vs WIDER SL". Real current LONG performance uses first-exit across all 10 engines.
- **Impact**: Measured on the live DB: report "Current" = **n=3718, WR 35.4%**; actual current LONG first-exit = **n=3748, WR 50.6%**. The table the CEO reads at the 7d/200T review shows a Current baseline that is 15.2 WR points below reality, so every Delta row (Win Rate, Total PnL, Avg PnL) is computed against a fictitious baseline. 2,869 LONG rows actually fired HML at the -0.8% floor — none of that appears in "Current".
- **Fix**: Compare actual `first_exit_pnl_pct`/`net_pnl_pct` for LONG rows vs the wider counterfactual (ideally full-engine, see finding 4), restricted to the same rows and same time window.

### HIGH — HML fire-rate and MFE-at-HML report sections are permanently dead
- **Location**: scripts/shadow_trader.py:2277-2281 (hml_current), 2283-2287 (hml_wider), 2296-2304 (mfe_at_hml)
- **Issue**: These queries look for `exit_type='hard_max_loss'` inside `exit_atr_json`. `_simulate_atr_sl_tp()` (lines 512-574) can only ever return `atr_sl_hit` / `atr_trail_hit` / `atr_tp_hit` / `no_exit` — it has no HML check. Live DB confirms: **0 rows** in `exit_atr_json` have `hard_max_loss`, while `exit_hard_max_json` has **6,737** (2,869 LONG).
- **Impact**: Report printed `Current HML fires: 0`, `Wider HML fires: 0`, never prints Reduction, and the entire "MFE AT HML" section renders empty (verified in the actual run below). The CEO's key question — "does -6.00 cut HML fires and did those trades recover?" — gets silently answered with zeros/nothing.
- **Fix**: Query `json_extract(exit_hard_max_json,'$.exit_type')='hard_max_loss'` for Current (or `first_exit_reason='hard_max_loss'`), and join rows where `exit_hard_max_json` fired against the wider result for the MFE section.

### HIGH — `ATR_SL_MAX 4.0` half of the trial is a complete no-op in the simulation
- **Location**: scripts/shadow_trader.py:592 (wider cap), 518 (normal cap); root cause is the candle-1 trailing logic at 610-614 / 535-540
- **Issue**: On the first candle, `sl_price = max(sl_price, peak*(1-1.2%))` replaces the initial ATR-capped SL whenever `atr_pct > 1.2%` (trail is tighter than any cap ≥2.5), and when `atr_pct ≤ 1.2%` the cap never binds (`min(atr, cap)=atr` for both 2.5 and 4.0). The initial SL distance — the only place `ATR_SL_MAX`/`SHADOW_TRIAL_ATR_SL_MAX` is used — is therefore discarded in every case.
- **Impact**: **Proven empirically**: wider sim with cap 4.0 vs 2.5 vs 100.0 → **0/44 scenarios differed** (atr sweep 0.4→6.0 × 4 price paths); normal sim with `ATR_SL_MAX` 2.5 vs 100 → **0/40 differed**. The trial therefore measures ONLY the CUT_LOSER -4→-6 floor change (-0.80% → -1.20% price at 5x). At the 7d/200T review the results will be labeled "CUT_LOSER -6.00 + ATR_SL_MAX 4.0" while containing zero evidence about ATR_SL_MAX 4.0 — and the live engine DOES use the cap (position_manager.py:1921 `min(effective_sl_pct, ATR_SL_MAX)`), so live behavior under 4.0 goes untested.
- **Fix**: Mirror the live engine's SL construction in the sim (initial ATR SL survives until the trail genuinely tightens past it — i.e., trail only raises the stop, never replaces a wider initial stop below it), or explicitly document that the shadow covers only the CUT_LOSER floor and split the CEO's evidence requirement.

### HIGH — Wider counterfactual models only 2 of 10 engines, yet the ✅/❌ threshold verdict is computed from it
- **Location**: scripts/shadow_trader.py:577-640 (wider sim), 2245-2273 (threshold verdict)
- **Issue**: `exit_wider_sl_json` simulates ATR-trail + wider HML only. The other 8 engines (cut_loser T1/T2 at -1.0/-2.5% close, PM trail wins, rr_engine, speed_stale, universal_hold, ...) are not re-run under the wider config, even though under a -6.00 CUT_LOSER the two-tier Cut Loser at -1.0% close becomes the *dominant* real exit path (today hard_max -0.8% preempts it: cut_loser fired first on only 4 of 3,889 LONG rows).
- **Impact**: The ✅ "THRESHOLD MET — wider SL is justified" verdict at 200 trades will be computed on a counterfactual that does not correspond to realizable performance. Concrete example from this run: row id 8967 (BTC LONG) — actual exit `pm_trail +0.47%`, wider column says `no_exit -0.07%`; a real wider-SL configuration would still run PM trail. Losses are also biased: wider sim exits at HML -1.2% where real wider config would exit cut_loser T1 at -1.0% close.
- **Fix**: For the review gate, re-simulate the full engine set with `CUT_LOSER=-6.00` / `ATR_SL_MAX=4.0`, pick first-exit with the same precedence table, and compare that vs actual first-exit on the same rows. (At minimum, relabel the current report as "ATR-engine-only" and move the verdict off it.)

### MEDIUM — Wider HML uses `MAX_LEVERAGE` (5) instead of per-row leverage → trial is TIGHTER than current for 3x rows
- **Location**: scripts/shadow_trader.py:602 (`hml_threshold_pct = SHADOW_TRIAL_CUT_LOSER / MAX_LEVERAGE`) vs line 716 (`CUT_LOSER_PNL / leverage`)
- **Issue**: Live code uses per-position leverage (position_manager.py:3594 `HARD_MAX_LOSS_PCT = CUT_LOSER_PNL_HERMES / _hml_lev`), and normal `_simulate_hard_max_loss` receives the row's `leverage_used`. The wider sim hardcodes 5.
- **Impact**: At 3x leverage the "wider" floor is -1.200% price vs current -1.333% — i.e. **tighter than current**. Measured: **303 of 3,889 closed LONG rows (7.8%) are 3x**; for those the shadow measures a stop tightening, not a widening (2x: -2.0% → -1.2%, even worse). Stats at the gate will be contaminated.
- **Fix**: Pass `leverage` into `_simulate_atr_sl_tp_wider()` and compute `SHADOW_TRIAL_CUT_LOSER / leverage`, exactly like `_simulate_hard_max_loss` does.

### MEDIUM — SHORT rows store the literal string `'null'`; headline count includes them
- **Location**: scripts/shadow_trader.py:1265 (`json.dumps(wider_sl_result)` → `'null'` when None), 2216-2219 (count without direction/pnl filter)
- **Issue**: For SHORT rows (and LONG rows with `atr_pct=None`) the UPDATE writes SQL value `'null'`, which is NOT SQL NULL, so `exit_wider_sl_json IS NOT NULL` matches it.
- **Impact**: Actual run printed `Signals with wider SL simulation: 13` when only **1** LONG row had real data (12 were SHORT `'null'` strings — verified breakdown: LONG data=1, SHORT JSON_null=12). Misleading headline; also if only `'null'` rows existed, the `wider_count==0` early-return guard would pass with zero real data while the threshold block silently no-ops (wider n=0).
- **Fix**: Write `NULL` instead of `'null'` (only bind the column when `wider_sl_result is not None`, or `json.dumps(...) if wider_sl_result is not None else None`), and filter the count to `direction='LONG' AND json_extract(exit_wider_sl_json,'$.pnl_pct') IS NOT NULL`.

### MEDIUM — Current vs Wider compares mismatched time windows and denominators
- **Location**: scripts/shadow_trader.py:2233-2254
- **Issue**: "Current" = all-time LONG rows (n=3718, months of history); "Wider" = rows closed since the trial code deployed (n=1 at launch). No shared window or row-set requirement.
- **Impact**: The Delta column prints garbage at launch and for weeks: verified run showed `Trades 3718 vs 1 (Delta -3717)`, `Total PnL -233.3% vs -0.1% (Delta +233.2%)` — a CEO could easily read "+233.2% Total PnL" as the wider SL's benefit. Deltas also drift via finding 7 (reclose rows land in Current but not Wider).
- **Fix**: Restrict both queries to the same window (`closed_at >= trial start` / `created_at >= trial start`) and the same row set (rows having both columns populated), and show trial-start date in the header.

### MEDIUM — `reclose_events()` never writes `exit_wider_sl_json`
- **Location**: scripts/shadow_trader.py:1537-1548 (wider sim not called), 1564-1581 (UPDATE lacks the column)
- **Issue**: Rows re-closed by `--reclose` (universal_hold truncated, `unclosed_no_candles` recovered) get fresh `exit_atr_json` etc. but no wider result.
- **Impact**: Those LONG rows are counted in "Current" but not in "Wider" → denominators silently diverge, and the missingness is non-random (specifically slow-engine/late-candle rows), biasing the wider sample. Compounds finding 6.
- **Fix**: Compute `wider_sl_result` in `reclose_events()` under the same LONG gate and add `exit_wider_sl_json=?` to the UPDATE.

### LOW — Hold branch (no engine fired) omits the wider result
- **Location**: scripts/shadow_trader.py:1269-1280
- **Issue**: The else-branch UPDATE writes neither `exit_atr_json` nor `exit_wider_sl_json` (75 hold rows in DB are NULL in both).
- **Impact**: Symmetric between Current and Wider, so comparators stay consistent — but the trial loses the wider `no_exit` counterfactual for exactly the trades where the wider stop made no difference, and the ≥200-trade gate counts only engine-fired rows. Minor.
- **Fix**: Write the wider result (and optionally the atr result) in the hold branch too.

### LOW — Report label bug: wider stats printed under the label "Current"
- **Location**: scripts/shadow_trader.py:2265 — `log(f"  Current: WR = {wider[1]}%, trades = {wider[0]}")`
- **Issue**: Prints wider WR/trades labeled as "Current".
- **Impact**: At review time this line directly contradicts the table above it (Current 35.4% vs "Current: WR = 0.0%"). Confusing, easy fix.
- **Fix**: `log(f"  Wider: WR = {wider[1]}%, trades = {wider[0]}")` (and consider printing both baselines).

### LOW — `log("\n═" * 60)` prints 60 separate separator lines
- **Location**: scripts/shadow_trader.py:2313
- **Issue**: The `"\n═"` is inside the multiplication, so the closing separator is 60 stacked lines instead of one line of 60 `═` (the header at 2208/2213 is correct).
- **Impact**: Cosmetic — verified in the real run: report tail is ~60 `═` lines. Clutters logs.
- **Fix**: `log("═" * 60)`.

### LOW — `SHADOW_TRIAL_REVIEW_DAYS` dead constant; 7-day review window unenforced
- **Location**: scripts/shadow_trader.py:67 (only occurrence in codebase)
- **Issue**: Defined, never read. Nothing surfaces "trial started X days ago" or blocks the verdict before day 7.
- **Impact**: The CEO's "7d/200T review" timing relies on a human remembering; the report shows trade count only.
- **Fix**: Print trial age and earliest-eligible review date in `report_wider_sl()`.

### SIDeways (pre-existing, not this commit) — `_simulate_cut_loser` hardcodes its tiers
- **Location**: scripts/shadow_trader.py:752-768 (`-3.0`, `-1.0`, `-2.5` hardcoded)
- **Issue**: Violates the "no hardcoded constants — everything in hermes_constants.py" rule; and these tiers are what a real wider-SL config would interact with most (finding 4).
- **Impact**: Tuning CUT_LOSER in constants won't update the two-tier sim; drift risk.
- **Fix**: Move tiers to hermes_constants.py while fixing finding 4.

## Verified Working
- Constants exactly match the CEO verdict (-6.00 / 4.0 / LONG / 200 / 55.0) — read from code, not commit message
- Live `hermes_constants.py` untouched (CUT_LOSER_PNL still -4.00, ATR_SL_MAX still 0.025) — trial is shadow-only
- SHORT fallback: wider function returns byte-identical results to normal sim for SHORT (tested)
- HML threshold math: wider floor = exactly -1.2000% price at 5x (crafted -1.5% dip → `hard_max_loss` -1.2)
- `None` candles / `None` atr_pct guards return None without exception
- Schema: column in CREATE TABLE + guarded ALTER; confirmed present in live `brain/shadow_trades.db`
- `python3 scripts/shadow_trader.py --close` — clean run: `close: 8 pending, 8 closed`, no errors; BTC LONG id 8967 got wider data (`no_exit -0.074%`), 7 SHORT got `'null'`
- `python3 scripts/shadow_trader.py --report-wider` — runs end-to-end without exception, threshold block prints ✅/⏳/❌ correctly wired to `SHADOW_TRIAL_MIN_WR`/`MIN_TRADES`
- Temp-DB batch close (45 reopened rows: 25 LONG fired + 10 SHORT + 10 hold): 53 rows in 0.09s → **~2 ms/row**; wider sim adds ~1 extra engine of work on top of 10 existing sims → performance impact negligible
- Wider result is computed outside the `results` dict → cannot change first-exit selection (no shadow-to-shadow contamination)
- Exit-type distribution in wider column for 25 real LONG rows: atr_sl_hit 13, hard_max_loss 7, atr_trail_hit 2, atr_tp_hit 1, no_exit 2 — all expected types present
- Report JSON extraction handles `'null'` strings gracefully (no crash; excluded by `pnl_pct IS NOT NULL` filter in the comparison queries)

## Recommendations
1. **Before the 7d/200T review (blocking):** fix HIGH-1 (compare actual first-exit vs wider on same window) and HIGH-2 (query `exit_hard_max_json` for current HML). As-is, the review would be decided on a wrong baseline and a dead HML section.
2. **Decide on HIGH-3/HIGH-4 before collecting the 200th trade:** either (a) rework the wider sim to mirror the live SL construction + full engine set with `-6.00/4.0`, or (b) formally narrow the trial to "CUT_LOSER -6.00 floor only" with the CEO and reword the report header accordingly. If (a), backfill wider results for LONG rows closed since the trial start (re-run via a one-off script — do not reopen 3,888 rows through `close_events`).
3. **Fix the MEDIUMs now — they're one-line-ish:** per-row leverage (line 602), write SQL NULL not `'null'` + direction-filter the headline count (1265/2218), same-window comparison (2233-2254), wider write in `reclose_events` (1564-1581).
4. **Fix the LOWs opportunistically:** label at 2265, `"\n═"` at 2313, surface `SHADOW_TRIAL_REVIEW_DAYS` in the report, and move `_simulate_cut_loser` tiers to hermes_constants.py.
5. **Data hygiene:** rows closed by the pre-commit run (23:22:32) and by `--reclose` lack wider data; after fixes, count denominators from rows having *both* columns so Current/Wider never diverge.
