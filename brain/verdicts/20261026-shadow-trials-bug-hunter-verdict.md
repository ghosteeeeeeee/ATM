# Bug-Hunter Verdict: Shadow Trials (shadow_trader.py)

**Date:** 2026-10-26 23:05 UTC
**Verifier:** bug-hunter subagent (independent code + runtime verification)
**Scope:** Trial 1 (Wider SL, CEO Q1) and Trial 2 (Extended Time Exits, CEO Q3) in `/root/.hermes/scripts/shadow_trader.py`; data in `/root/.hermes/brain/shadow_trades.db`.

---

## === BUG-HUNTER VERDICT ===

### Trial 1 (Wider SL): PASS
**Evidence:**
- Constants correct at lines 61–67: `SHADOW_TRIAL_ENABLED=True`, `SHADOW_TRIAL_CUT_LOSER=-6.00`, `SHADOW_TRIAL_ATR_SL_MAX=4.0`, `SHADOW_TRIAL_DIRECTION='LONG'` — verified via live import.
- `_simulate_atr_sl_tp_wider()` exists (line 594), correctly gated `direction != 'LONG'` → falls back to baseline, called in `close_events()` (line 1295–1296) only when `SHADOW_TRIAL_ENABLED and d == SHADOW_TRIAL_DIRECTION`.
- CUT_LOSER=-6.00 correctly used: `hml_threshold_pct = SHADOW_TRIAL_CUT_LOSER / (leverage or MAX_LEVERAGE)` (line 625), per-row leverage.
- Data flowing: 2,528 non-NULL rows (2,500 LONG trial rows + 28 historical artifact rows), latest 2026-10-26 18:25. Exit-type distribution sensible: atr_sl_hit 1541, atr_trail_hit 437, no_exit 288, atr_tp_hit 131, hard_max_loss 103.
- Report `--report-wider` runs clean; same-window comparison (2500 vs 2500) is correct: WR 39.7% → 30.9%, ❌ threshold not met (needs 55%).

**Caveats (do not block mechanics, but material):**
1. **ATR_SL_MAX=4.0 is provably INERT** (HIGH informational). Empirically verified: identical simulation outcomes for cap 2.5 / 4.0 / 9.9 on identical candle walks. Reason: the trail band `[peak−1.2%, peak−0.3%]` supersedes the cap from candle 1, and the "hard floor" `sl_price = max(sl_price, sl_floor)` (line 640) can never bind for LONG (peak ≥ entry always ⇒ sl ≥ entry−1.2% > entry−4%). The trial therefore tests ONLY the CUT_LOSER −6.00 vs −4.00 change. Do not attribute any trial outcome to "wider ATR stops" — that half of the approved change changes nothing in the sim (and likely nothing in production either — `position_manager.py:1957` uses the same min-cap that trailing supersedes; confirm before crediting ATR_SL_MAX).
2. **Report bug (MEDIUM): mismatched windows in HML fire-rate section.** "Current HML fires: 6693" counts ALL closed LONG rows (10,139 total), while "Wider HML fires: 103" counts only the 2,500 trial-window rows. True same-window current = 1,701 ⇒ real reduction is 1,598 (94%), not "6590 (98%)". The report fixed the same-window bug for WR/PnL but not for the HML fire-rate line.
3. **28 SHORT rows contain the literal string `"null"`** in `exit_wider_sl_json` (created 2026-10-21, pre-guard artifact). Harmless — report aggregates exclude them via `pnl_pct IS NOT NULL` — but they inflate the "Signals with wider SL simulation" count by 28 (2528 vs true 2500).

### Trial 2 (Extended Time): FAIL
**Evidence:**
- Constants correct at lines 73–77: `SHADOW_TIME_TRIAL_ENABLED=True`, `SHADOW_TIME_TRIAL_ARM_TIMEOUT_MULT=2.0`, `SHADOW_TIME_TRIAL_UNIVERSAL_HOLD_EXTRA_MIN=240` — verified via live import.
- `_simulate_extended_time()` exists (line 669), called unconditionally in `close_events()` (line 1300–1301), writes `exit_extended_time_json`.
- The timeout derivations are correct: 60→120min, 45→90min, 480→720min, ride_it exemption preserved (verified at runtime: pump-chain exits at 90.0min flat).
- **BUG (HIGH, trial-corrupting) — activation threshold off by 100×:** line 709 checks `current_pnl >= PM_TRAIL_ACTIVATE_PCT * 100`. `PM_TRAIL_ACTIVATE_PCT = 0.40` is already in percent, so the check is `pnl >= 40.0%` instead of `>= 0.40%`. Runtime proof: a LONG that arms at +0.5% (minute 10) and sits at +1.0% at minute 120 gets cut with `ext_arm_timeout` at exactly 120.0min, while the baseline `_simulate_trail_arm_timeout` correctly returns `armed` (no exit). Consequences:
  - Nearly every trade is treated as "not armed," so `ext_arm_timeout` fires at 90/120min regardless of profitability.
  - `ext_universal_hold` (720min) is effectively unreachable — the arm timeout kills the trade long before.
  - The trial's stated purpose ("let winners run longer") is untestable; **all data collected under this code is biased and must be discarded and re-collected after the fix** (fix: drop the `* 100`).
- **BUG (MEDIUM) — fabricated arm timeouts for sources that have none in live:** live trail-arm-timeout applies only to bb-squeeze/pump-chain (baseline returns `no_timeout` for others), but the extended sim applies a default `60 * 2 = 120min` timeout to ALL sources. Runtime proof: flat `wyckoff-` and `ride_it` trades exit via `ext_arm_timeout` at 120min — an exit that does not exist in production. This contaminates the exit-type mix and the comparison.
- **Design caveat (MEDIUM) — apples-to-oranges comparison:** the report's "Current" column is `first_exit_pnl_pct` from the full 10-engine stack (includes TP hits and PM-trail winners, which the log shows run at WR≈100% avg +0.38%), while "Extended" is a time-exit-only simulation with no TP, no PM trail, no SL, no HML. The ≥+5pp WR-improvement gate is structurally near-impossible to clear for reasons unrelated to the hypothesis. A faithful counterfactual would simulate the full engine stack with the extended time parameters and take the first exit across all engines.
- Minor: `atr_pct` parameter is accepted but unused (cosmetic).
- Data volume: only **1 row** written so far (deployed via commit `b1e8919e` at ~22:53 UTC today; the 1 row proves the write path works). Report renders correctly at n=1 ("⏳ Collecting data: 1/100").

### Schema: PASS
**Evidence:** Both columns present in `CREATE TABLE shadow_trades` (lines 153–154: `exit_wider_sl_json JSON`, `exit_extended_time_json JSON`) AND in the `ALTER TABLE` migration guards (lines 204–211, wrapped in try/except `OperationalError`). `PRAGMA table_info` on the live 69MB DB confirms both columns exist.

### CLI wiring: PASS
**Evidence:** `--report-wider` (line 2564) and `--report-time` (line 2565) added to argparse; both included in the `run_all` exclusion expression (line 2571); both dispatched in `main()` (lines 2595–2598 → `report_wider_sl()` / `report_extended_time()`). Both commands were executed against the live DB and produced correct-format output. Note: the systemd unit (`hermes-shadow-trader.service`) runs `--record --close --report` only — trial reports are manual, which is fine, but no automated trial report is generated on the 30-min timer.

### Data collection: PASS (with gaps)
**Evidence:**
- `close_events()` writes both columns in the main UPDATE (line 1363, params lines 1375–1376: `json.dumps(...) if result is not None else None`).
- Live DB: `exit_wider_sl_json` non-NULL on 2,528 closed rows (2,500 LONG, flowing since 2026-10-21); `exit_extended_time_json` non-NULL on 1 row (deployed today 22:53; collection just started, ~300–400 rows/day expected, 100-trade threshold ≈ 1 week).
- **Gap 1 (MEDIUM):** rows closed via the no-engine-fired `else` branch (lines 1380–1391) never get either trial column — 525 rows total, 64 today. For Trial 2 these "hold" trades are exactly the long-drift trades most relevant to a time-exit trial.
- **Gap 2 (MEDIUM):** `reclose_events()` (lines 1675–1692) does not write either trial column, so re-closed rows (`unclosed_no_candles`, truncated universal_hold) keep NULLs forever — 1,167 `unclosed_no_candles` rows already lack extended data and will never be backfilled.
- Cosmetic: 28 legacy SHORT rows contain literal `"null"` strings (pre-`fac6cb45` artifact).

### Overall: FAIL
**Issues Found:**
1. **HIGH — Trial 2 activation bug:** `shadow_trader.py:709` `PM_TRAIL_ACTIVATE_PCT * 100` ⇒ arm at +40% instead of +0.40%. Corrupts the entire extended-time trial; armed winners get cut at the extended timeout; `ext_universal_hold` nearly unreachable. Discard the 1 collected row's approach — fix and restart collection.
2. **MEDIUM — Trial 2 fabricated arm timeouts** for non-bb-squeeze/pump-chain sources (default 120min applied where live has no such engine).
3. **MEDIUM — Trial 2 comparison methodology:** time-exit-only sim vs full 10-engine actuals; gate (+5pp WR) structurally biased against "extended."
4. **MEDIUM — Report window mismatch:** `--report-wider` HML fire-rate "Reduction: 6590 (98%)" uses all-history current vs trial-window wider; true same-window reduction is 1,598 (94%).
5. **MEDIUM — Data gaps:** no-engine-fired rows (else branch) and all `reclose_events` rows never receive trial columns.
6. **LOW —** ATR_SL_MAX=4.0 inert in Trial 1 (and likely in production): the wider-SL trial effectively tests only CUT_LOSER −6.00.
7. **LOW —** 28 legacy SHORT rows hold literal `"null"` strings in `exit_wider_sl_json`.

**Recommendations:**
1. Fix line 709: `if current_pnl >= PM_TRAIL_ACTIVATE_PCT:` (drop `* 100`). Delete the 1 existing `exit_extended_time_json` row (or NULL it) so biased data doesn't enter the review set; collection restarts with the next 30-min timer run.
2. In `_simulate_extended_time`, return `no_time_exit` for sources whose bare name is neither bb-squeeze nor pump-chain (mirror `_simulate_trail_arm_timeout` lines 949–955), unless the CEO explicitly wants a universal arm-timeout experiment — in which case document it as a new engine, not an extension.
3. Redesign the Trial 2 counterfactual: simulate the full 10-engine stack with extended time parameters and take first-exit across all engines, so "Current vs Extended" is same-methodology. Re-derive the +5pp gate on that basis.
4. Fix `report_wider_sl()` HML fire-rate query: add `AND exit_wider_sl_json IS NOT NULL` (same-window) to the `hml_current` query, matching the fix already applied to the WR/PnL block.
5. Add `exit_wider_sl_json` / `exit_extended_time_json` to both the else-branch UPDATE in `close_events()` and the UPDATE in `reclose_events()` so trial columns are never skipped.
6. Tell the CEO now: in Trial 1's current data, wider SL is failing badly (WR 39.7% → 30.9%, total PnL −242.6% → −561.4% over 2,500 trades, 55% threshold unreachable) — but note this verdict reflects the implemented (HML-only) widening, since ATR_SL_MAX is inert.
7. Optional: add `--report-wider` / `--report-time` to the systemd service or a daily timer so trial progress is visible without manual runs.

**Verification methods used (all executed, none from memory):** live module import (`python3 -c "import shadow_trader"`), `PRAGMA table_info` + aggregate queries on the live 69MB DB, synthetic-candle unit tests of both simulation functions (activation-threshold proof, ATR_SL_MAX inertness sweep over identical walks, source-gating proofs), and both CLI reports run end-to-end against production data.
