---
name: atr-trailing-debug
description: Debug ATR trailing SL/TP issues in Hermes — missing ATR, wrong k multiplier, peak tracking failures, phase misclassification, floor mismatches, and unreachable code.
tags:
  - atr
  - trailing-stop
  - stop-loss
  - profit-monster
  - position-manager
  - tpsl-utils
---

## T's preferences for TPSL changes (DO NOT VIOLATE)

**Leverage is NOT touched in this skill.** T (2026-06-25): "we want
to increase it when our signals and SL and thus win-rate get
better. so don't worry about leverage." 5x leverage is an amplifier
that grows with system quality — don't cap it as a "fix" for
losing streaks. Fix the signals and SL first; leverage follows.

**ATR TP/SL constants require T's explicit approval before any
change.** This is a hard rule from T's memory. Even when the math
is clear (e.g., the dead-code floor issue below), the constant
change is a separate decision from the bug fix. Bug fixes in code
that don't touch constants (like Bug B1 below) can be applied
directly. Changes to `hermes_constants.py` ATR_* values go through
the "ask T first" gate.

**Incremental verification (T's preference, 2026-06-25):** Don't
bundle multiple fixes. Apply Fix #1 alone first, verify on the
next 5+ trades that it works, then Fix #2, verify, etc. Each fix
gets its own measurement window before the next is applied. This
isolates the impact of each change.

## The full TPSL audit plan (2026-06-25 v1)

When a 24h audit surfaces these bugs, the canonical implementation
plan lives at:

`/root/.hermes/brain/plans/tpsl-profit-capture-2026-06-25.md`

It has 11 fixes in priority order, with the full spec for each,
verification queries, expected outcomes, and decision points for T.
Read this plan before proposing new TPSL fixes — most of the work
is already specced.

**The 11 fixes (from the plan):**
1. SHORT `lowest_price` init (one line) — see Bug B1 below
2. Profit-lock feature in `compute_atr_sl_tp` — new logic
3. Phase multiplier dead-code (floor too high) — see Bug B2 below
4. Raise `PROFIT_MIN_PCT` 0.7 → 1.0 — profit-monster clipping
5. Lower `ATR_SL_MIN_ACCEL` 1.5% → 0.7% — let phase logic bite
6. Retune K_PHASE_* from 0.01-0.08 to 0.2-0.5 — phase tightening matters
7. Backfill 12 closed trades' `lowest_price=0` to `entry_price`
8. Add MERL/ENS/FET/ASTER to SHORT_BLACKLIST
9. Time-of-day filter (skip 20:00-22:00 UTC, 1W/9L in 24h)
10. ASTER 10s re-open cooldown (block re-entry within 30min of orphan)
11. `highest_price=1.0` default for orphan trades

## Bug B1: SHORT `lowest_price` not initialized on trade open (2026-06-24) — ONE-LINE FIX

**Symptom:** Trailing SL appears to do nothing for a third of SHORT trades. The SL "moves" with current price instead of trailing from a real low.

**Root cause:** `position_manager.py` lines 2245-2248 initialize peak prices asymmetrically:
```python
if existing_high <= 0 and direction == "SHORT":
    existing_high = entry   # SHORT initialized to entry
if existing_low <= 0 and direction == "LONG":
    existing_low = entry    # LONG initialized to entry
# MISSING: SHORT initialization for lowest_price
```
For SHORT, `lowest_price` is never set to `entry`. First refresh: `new_low = min(0, cur_price) = 0` — stays 0 forever.

**Verification (2026-06-24):** 12 of 38 closed trades (31.6%) had `lowest_price=0`. See `references/2026-06-24-merl-short-lowest-trail-bug.md` for full per-trade list and pipeline log evidence.

**Fix (one line, in the "fix obvious bugs directly" category — does NOT touch ATR constants):**
```python
# position_manager.py line 2247
if existing_low <= 0 and direction in ("LONG", "SHORT"):
    existing_low = entry
```
This is NOT an ATR constant change — it falls under "fix obvious bugs directly" per T's rules.

**Related dead-code finding:** Phase multipliers (K_PHASE_*) are computed correctly but overridden by `ATR_SL_MIN_ACCEL=1.5%` floor at tpsl_utils.py:374 — see same reference. Also no profit-locking feature exists (SL can only trail to entry, never lock gain).

---

# ATR Trailing SL/TP Debug — Umbrella Skill

This is the top-level entry point for all ATR trailing stop-loss and take-profit debugging in Hermes. Each subtopic has a dedicated reference document.

## References
- [Architecture](./references/atr-architecture.md) — _collect_atr_updates flow, _force_fresh_atr fallback chain, key files
- [SL Diagnostic](./references/atr-sl-diagnostic.md) — Full diagnostic workflow: read trade → check ATR cache → trace computation → phase-based k → peak reference selection
- [SL K-Debug](./references/atr-sl-k-debug.md) — Root-cause k multiplier debugging: phase misclassification, is_new_trade gate, floor mismatches
- [In-Profit Fast Lock](./references/atr-trailing-sl-in-profit.md) — Fixed % trailing SL when in profit, SHORT TP bug, unreachable code, SHORT new_low bug
- [IP Stale Price Hit](./references/atr-ip-stale-price-hit-2026-05-12.md) — IP exit ABOVE all computed SLs but `atr_sl_hit` fired; root cause is stale `current_price` in in-memory dict at hit detection time, not ATR cache stuck
- [Peak Initialization](./references/atr-trailing-sl-peak-initialization.md) — Three-part fix: brain.py + guardian + runtime fallback; LONG highest_price never updated
- [ATR SL Direction Bug](./references/atr-sl-direction-bug.md) — SHORT SL below entry for new/in-profit trades; FIL SHORT 4s close root cause
- `references/atr-tp-sl-authority-2026-05-15.md` — ATR TP/SL authority audit: position_manager sole ATR engine, HL orders disabled, guardian defers to DB, known issues (PUMP values not in hermes_constants, guardian orphan path hardcodes ATR, `_compute_dynamic_sl/tp` unused functions). Updated 2026-05-15 v2: self_close_watcher.timer masked/inactive, tpsl_utils path dormant, no independent ATR computation found.
- `references/zk-trade-tp-ratio-bug-2026-05-15.md` — LIVE bug: ZK SHORT TP/SL ratio = 5.4x (should be 1.25x). Two different ref_prices: SL uses `_entry` (correct for new/in-profit SHORT), TP uses `current_price` (wrong — should use `_entry` when `lowest_price=0`). Root cause: `_collect_atr_updates()` line 1655 always uses `ref_price` for TP, but SL gets `_entry` anchor via line 1650-1651. TP and SL written in same UPDATE but with different ref_prices → ratio broken.
- `references/atr-authority-session-2026-05-15.md` — T's explicit directive (2026-05-15): position_manager sole authority, HL TP/SL disabled, guardian reads DB for orphan detection only, initial ATR values from hermes_constants ATR_SL_MIN_INIT/ATR_SL_MAX_INIT, PUMP constants need to move to hermes_constants.
- `references/tpsl-utils-2026-05-15-audit.md` — Audit findings from tpsl_utils.py rewrite (2026-05-15). Bugs found: (1) compute_atr_sl_price LONG anchor uses entry_price instead of current_price — will set SL too far from current after price rises; (2) ATR_UPDATE_THRESHOLD_PCT hardcoded at position_manager.py:81 not in hermes_constants — violates "no hardcoding" directive. **BOTH FIXED 2026-05-15:** compute_atr_sl_price/compute_atr_tp_price now accept optional highest_price/lowest_price params and use them as anchors (LONG→highest, SHORT→lowest) with current_price fallback; ATR_UPDATE_THRESHOLD added to hermes_constants (line 269, value 0.0015), position_manager.py:81 now references it. TP/SL formula logic, trailing gates, INIT→ACCEL migration, phase k multipliers all verified correct. See also: `references/atr-tp-sl-authority-2026-05-15.md` for prior session findings.
- `references/tp-sl-ratio-diagnostic.md` — One-liner diagnostic for TP/SL ratio consistency check. Run after any ATR TP/SL change to verify all trades maintain 1.25x ratio.
- `references/display-vs-engine-discrepancy-2026-05-18.md` — Display shows wrong SL/TP (e.g. SNX SHORT SL=$0.3042) but TPSL pipeline log shows correct values. Root cause: display layer calls `get_trade_params()` fallback (1.5%/8%) instead of reading from PostgreSQL post-ATR-engine-write. TPSL engine itself is correct.
- `references/atr-floor-overrides-phase-2026-05-21.md` — **NEW (2026-05-21):** ATR floor (0.70%) overrides phase k (0.08) for low-ATR tokens. FET case: ATR=0.047% → k×ATR=0.0019% → floor at 0.70%. Phase multiplier useless, SL always 0.70% from price. T's recent k tweaks (0.50/0.25) are correct; ATR_SL_MIN raise (0.50%→1.00%) creates the floor-lock. Four options to achieve <0.20% trailing: (A) lower floor, (B) confidence-gated floor, (C) higher-timeframe ATR, (D) manual trailing_sl per position. Closed trade evidence: atr_sl_hit on 0.5-1.4% adverse moves vs profit-monster on 0.5-0.8% favorable moves of similar magnitude. SL/TP gap only 0.40% for LOW_VOL tokens — too tight at 100× leverage.
- `references/atr-floor-override-subagent-verification.md` — **2026-05-24:** Subagent math verified against live code. INIT=ACCEL=1.0% confirmed. Phase k (0.06-0.07) overridden by floor at 1.0% on NORMAL_VOL tokens (sl_pct=0.105% vs floor=1.0%). `return base_k` bypass at tpsl_utils.py:108-109 also confirmed. True "first candle out" fix requires both lower floor AND code change to skip floor for ACCEL/EXH phases.

- `references/short-atr-discrepancy-2026-05-18.md` — SHORT trades: TPSL log correct, trades.json WRONG. ETH LONG matches exactly, all SHORT SLs are higher than TPSL SLs. Root cause: two separate ATR systems — canonical `tpsl_utils.compute_atr_sl_tp()` (correct, uses `lowest_price` anchor) and legacy `_dynSL()`/`_dynTP()` in position_manager.py (dead code, uses `current_price` anchor). Display layer may be reading from the wrong system or PostgreSQL has stale values from a broken write path for SHORT trades specifically. SNX TP frozen at 2.28% (not 1.5% INIT floor) — initial fallback value never overwritten.
- `references/short-tp-sign-error-investigation-2026-05-18.md` — **NEW INVESTIGATION**: SNX SHORT TP = $0.2964 = entry × (1 - 0.026) ≈ 2.6% from entry. ADA LONG TP = $0.2548 = entry × (1 + 0.018) ≈ 1.8% from entry (correctly uses ATR_TP_MIN=1.5% floor). Both have similar ATR (~0.70%). Expected SHORT TP% = k_tp × ATR = 1.25 × 0.70% = 0.875% → TP ≈ $0.3007. Actual SNX TP = 2.6% (3x higher than expected). Hypothesis: SHORT TP path in `compute_atr_sl_tp()` bypasses `hermes_constants` and uses a hardcoded default (~2.3%). User suspects sign error somewhere causing wrong constant to be selected. Need to trace SHORT TP branch in tpsl_utils.py (around lines 390-430) vs LONG TP branch. Key question: is `eff_tp_pct` being computed correctly for SHORT? Does it correctly use `ATR_TP_K_MULT` for `k_tp = k × 1.25`? Or is it falling into a fallback path with a different default?

- `references/ton-atr-case-2026-05-27.md` — **TON ATR TP/SL case study (2026-05-27):**
  - TON price: $1.92155, cached ATR(15m): $0.01415, ATR%: 0.736% (< 1% → LOW_VOL tier)
  - Base k tier: LOW_VOL → base_k = **0.5** (ATR_K_LOW_VOL)
  - k_tp = base_k × ATR_TP_K_MULT = 0.5 × 1.25 = **0.625**
  - Raw sl_pct = 0.5 × 0.736% = **0.368%**; raw tp_pct = 0.625 × 0.736% = **0.460%**
  - NEW trade floors: SL → max(0.368%, ATR_SL_MIN_INIT=**1.00%**) = **1.00%**; TP → max(0.460%, ATR_TP_MIN=**1.50%**) = **1.50%**
  - ESTABLISHED trade floors: SL → max(0.368%, ATR_SL_MIN_ACCEL=**5.00%**) = **5.00%**; TP → max(0.460%, ATR_TP_MIN_ACCEL=**1.50%**) = **1.50%** (Note: 5.0% = 0.05 in code)
  - Phase multipliers (base_k × mult): ACCEL stall=0.0300, ACCEL fast=0.0250, ACCEL slow=0.0200, EXH stall=0.0100, EXH fast=0.0150, EXH slow=0.0100, EXT stall=0.0050, EXT fast=0.0100
  - Key constants (from hermes_constants.py lines 273-354): ATR_TP_K_MULT=**1.25**, ATR_SL_MIN_INIT=**1.00%**, ATR_SL_MAX_INIT=**1.50%**, ATR_TP_MIN=**1.50%**, ATR_SL_MIN_ACCEL=**5.00%** (0.05), ATR_TP_MIN_ACCEL=**1.50%**, PHASE_TIER_ACCELERATING=**2**, PHASE_TIER_EXHAUSTION=**3**, PHASE_TIER_EXTREME=**4**
  - ATR cache was STALE (377,904s age vs 300s TTL) — get_atr() returned None, actual ATR would differ with fresh fetch
  - Diagnostic approach: read cache directly from /root/.hermes/data/atr_cache.json (json.load), then compute manually using tpsl_utils._atr_tier() logic — do NOT rely on get_atr() when cache is stale

- `references/short-sl-anchor-bug.md` — Losing SHORT case: `lowest_price` anchor gives SL below current; conditional anchor needed (current when losing, lowest when in profit). 2026-05-18.
- [24h Trade Audit Recipe 2026-06-25](./references/24h-trade-audit-recipe-2026-06-25.md) — Recipe for diagnosing TPSL bugs from a 24h closed-trade window: PG + 1m price_history join, MFE/MAE per trade, DB integrity checks. 2026-06-25 audit findings: 38 trades, 21W/16L, +$0.68 net; MERL/ENS/FET/ASTER blacklist candidates; ASTER 10s re-open bug. Companion script below.
- `references/2026-06-24-merl-short-lowest-trail-bug.md` — **NEW (2026-06-24)**: MERL #12177 winner + #12166 loser full SL timeline. Three layered bugs found: (1) SHORT `lowest_price` not initialized on trade open — 32% of 24h trades have `lowest_price=0`; (2) phase multipliers (K_PHASE_*) computed but overridden by `ATR_SL_MIN_ACCEL=1.5%` floor — DEAD CODE; (3) no profit-locking feature — SL can trail to entry but never below, never locks gain. Pipeline log evidence + 12 affected trade IDs + one-line fix for bug #1.

**Bug:** `_collect_atr_updates()` uses `ref_price = lowest_price` as anchor for SHORT SL computation. When a SHORT opens and price immediately falls to profit, `ref_price = lowest_price` = the best price. SL ends up ABOVE the lowest price but BELOW entry — in profit territory, not protective territory. Both SL and TP end up below entry for a SHORT.

**Root cause:** Lines 1599-1601 + 1653 in position_manager.py:

**Fix APPLIED (2026-05-15)** — see references/atr-sl-direction-bug.md

## 7. SHORT SL Anchor Bug — Losing Position (2026-05-18)

**Bug:** `tpsl_utils.compute_atr_sl_tp()` uses `lowest_price` unconditionally as SHORT SL anchor. When a SHORT is losing (price went UP from entry), `lowest_price` = old profit point (below current). SL computed from it ends up BELOW current price — if price rebounds to SL, position stops out even though it was still underwater.

**Worked example — SNX SHORT:**
```
entry=0.3034, current=0.3070 (price up = losing), lowest=0.3033
eff_sl_pct=0.70% (ACCEL floor)

TPSL SL = lowest * (1 + 0.007) = 0.3033 * 1.007 = 0.3054
Result: SL=0.3054 < current=0.3070 — WRONG
If price falls to 0.3054, position stops out even though it was losing.
```

**Why LONG is not affected:** LONG losing (price fell) → `highest_price` is above current → SL = highest * (1 - %) = below current = correct. SHORT losing (price rose) → `lowest_price` is below current → SL = lowest * (1 + %) = below current = wrong.

**Root fix location:** `tpsl_utils.py` lines 286-295 (anchor resolution) and 379-382 (price computation). Need conditional anchor:

```python
if direction == 'SHORT':
    if current_price > entry_price:    # losing — price moved against us
        sl_ref = current_price          # use current, always above it
    else:                               # in profit — price moved for us
        sl_ref = lowest_price if lowest_price > 0 else current_price
    new_sl = round(sl_ref * (1 + eff_sl_pct), 8)
```

**Related:** `_dynSL()` in position_manager.py:1487 (`current_price * (1 + ATR_SL_MIN)`) — this fallback formula actually gives the CORRECT result for losing SHORT (always above current). But it uses a fixed 0.5% with no ATR scaling, so it's only correct as a last-resort fallback, not as a trailing stop.

**Display vs TPSL discrepancy explained:** Displayed SHORT SL values (e.g., SNX=0.308540) come from `_dynSL` path which happens to be correct for losing SHORT. TPSL engine produces SL below current (wrong for losing). See `references/short-sl-anchor-bug.md`.

---

## 8. TPSL Engine vs Display Path — Dual SL Computation (2026-05-18)

Two separate SL computation paths exist for SHORT:

| Path | Function | Anchor | Status |
|------|----------|--------|--------|
| TPSL engine | `tpsl_utils.compute_atr_sl_tp()` | `lowest_price` (unconditional) | Bug: wrong when losing |
| Display/fallback | `_dynSL()` pos_mgr.py:1487 | `current_price` | Correct for losing SHORT, but fixed 0.5% (no ATR scaling) |
| Decider/guardian | `get_trade_params()` pos_mgr.py:1875 | `entry_price * (1 + SL_PCT_FALLBACK)` | Uses 1.5% fallback — wrong direction for losing SHORT |

**LONG:** Both TPSL engine and display read from DB → TPSL values used → correct (highest_price > current when losing).

**SHORT:** TPSL engine writes to DB, but display may read from wrong path or DB has stale fallback values from entry time. TPSL log shows correct values but DB never gets updated (confirmed for SNX/UNI/SKY).

**Key finding:** The TPSL engine (`compute_atr_sl_tp`) is the correct authority but has the losing-SHORT anchor bug. The display path (`_dynSL`) happens to be correct for losing SHORT by accident (uses current_price). The decider path (`get_trade_params`) uses wrong anchor (entry_price) and wrong percentage (1.5% fixed).

**Fix priority:** Fix `tpsl_utils.compute_atr_sl_tp()` anchor logic first (the authoritative path), then standardize display/decider paths to read from DB after TPSL engine has run.

**Bug:** `_collect_atr_updates()` uses `ref_price = lowest_price` as anchor for SHORT SL computation. When a SHORT opens and price immediately falls to profit, `ref_price = lowest_price` = the best price. SL ends up ABOVE the lowest price but BELOW entry — in profit territory, not protective territory. Both SL and TP end up below entry for a SHORT.

**Root cause:** Lines 1599-1601 + 1653 in position_manager.py:
```python
if direction == "SHORT":
    ref_price = _peak_low if _peak_low > 0 else ...
new_sl = round(ref_price * (1 + effective_sl_pct), 8)
```

For FIL SHORT: `ref_price = 1.0000` (price fell instantly), `SL = 1.0086` (above lowest but below entry). `check_atr_tp_sl_hits()` fires because `lowest_price=1.0 < SL=1.007` for SHORT — the trade's own profitable movement triggered the protective SL.

**FIX APPLIED (2026-05-15) — position_manager.py `_collect_atr_updates()` SHORT block (line 1647-1654):**

```python
elif direction == "SHORT":
    # For NEW or IN-PROFIT SHORTs: anchor SL to _entry so it stays ABOVE entry.
    # Using ref_price (lowest_price) would place SL below entry when price has
    # already fallen — leaving the trade with zero protective barrier.
    # Established (underwater) SHORTs continue trailing from ref_price correctly.
    if is_new_trade or _in_profit:
        new_sl = round(_entry * (1 + effective_sl_pct), 8)
    else:
        new_sl = round(ref_price * (1 + effective_sl_pct), 8)
    new_tp = round(ref_price * (1 - effective_tp_pct), 8)
```

`is_new_trade` (line 1621): True when `_in_profit AND |peak - entry| / entry < 0.001` — trade just opened with no real candle formed yet.

`_in_profit` (line 1619): `_pnl_pct > 0`.

Underwater SHORTs (`_in_profit=False`) correctly continue using `ref_price` (lowest_price) as the trailing anchor — they don't have profitable peak to protect.

- `references/atr-sl-direction-bug.md`
- `references/pump-mode-sl-staleness-2026-05-17.md` — PM [TPSL] log correct but brain DB has stale SL/TP values (display layer inherits wrong values)
- `references/signal-migration-pm-checklist.md` — Prevention checklist: when migrating a standalone executor to pipeline signal, PM exclusion filter update is FIRST action, not last. 2026-05-17 root cause of zscore-pump staleness.
- `references/atr-phase-system-live-2026-05-17.md` — Complete phase system reference: two-phase detection table (detect_phase vs _phase_from_pct), Stage 1-3 calculation flow, all adjustable K knobs, live scan of all 191 tokens (ACCEL=34, EXH=16, EXT=27). **Read this for phase questions.**
- [ATR K/Phase Calculation 2026-05-17](./references/atr-k-phase-calculation-2026-05-17.md) — T's complete reference: Stage 1 (vol tier → base k), Stage 2 (phase → multiplier), Stage 3 (floors + trailing gate).
- [Unreachable Code](./references/atr-trailing-unreachable-code.md) — continue at line 2178 blocking peak update for HL positions

## Companion Scripts

- [analyze_24h_closed_trades.py](./scripts/analyze_24h_closed_trades.py) — End-to-end 24h audit script. Reads PG + 1m `price_history` from `signals_hermes.db`, computes MFE/MAE per trade, prints per-token/leverage/time-of-day breakdown, DB integrity check (lowest_price=0 detection), and profit-monster clipping distribution. Re-run after any TPSL change to verify outcomes improved.

---

## ATR TP/SL Authority — Architecture (2026-05-15)

**position_manager is the SOLE authority for ATR-based TP/SL.**
All other components read from DB or defer — they do NOT compute ATR values independently.

| Component | Role |
|-----------|------|
| `hermes_constants.py` | SINGLE source for all ATR TP/SL constants — no hardcoding. `ATR_UPDATE_THRESHOLD=0.0015` added 2026-05-15. |
| `tpsl_utils.py` | **Sole ATR computation authority.** `compute_atr_sl_tp()` = full trailing with phase scaling, anchor logic, INIT/ACCEL floors, trailing gates. `compute_atr_sl_price()`/`compute_atr_tp_price()` = standalone helpers for guardian/self_close_watcher (no trailing, uses highest/lowest peaks if available). |
| `position_manager.py` | Orchestration only: dedup ATR/momentum/speed fetches, peak-price DB re-read, cascade-flip override, delta gate, DB persist. Calls `compute_atr_sl_tp()` then persists results. `ATR_UPDATE_THRESHOLD_PCT = ATR_UPDATE_THRESHOLD` (from hermes_constants). |
| `decider_run.py` | Non-pump: passes `sl=0, tp=0` → brain.py defers to position_manager. Pump: uses `PUMP_SL_PCT/PUMP_TP_PCT` from signal_gen.py (NOT yet in hermes_constants — pending). |
| `hl-sync-guardian.py` | Reads SL/TP from DB. Orphan detection only. Step 10 ATR reconcile disabled (line 3933). Uses `compute_atr_sl_price()`/`compute_atr_tp_price()` with optional peak anchors. |
| `self_close_watcher.py` | UNPROTECTABLE coins only. `UNPROTECTABLE_COINS = frozenset()` (empty). |
| HL TP/SL orders | **`ATR_HL_ORDERS_ENABLED = False`** — HL orders disabled, Hermes self-closes internally via `check_atr_tp_sl_hits()`. |

**Fix applied (2026-05-15):** `position_manager.py` previously had local `TP_PCT`, `SL_PCT`, `SL_PCT_MIN` definitions that shadowed hermes_constants. These have been removed — `SL_PCT_MIN` added to hermes_constants (line 281), `ATR_UPDATE_THRESHOLD` added (line 269). position_manager now imports all from hermes_constants.

**Fix applied (2026-05-15):** `compute_atr_sl_price()` and `compute_atr_tp_price()` in tpsl_utils now accept optional `highest_price`/`lowest_price` params. LONG uses `highest_price` as anchor if > 0 (else `current_price`), SHORT uses `lowest_price` as anchor if > 0 (else `current_price`). This replaces the previous bug where LONG used `entry_price` as anchor.

**Bug fixed (2026-05-15):** DASH/ZK SHORT SL was ABOVE entry (+0.70%). Fixed by refactoring into `tpsl_utils.compute_atr_sl_tp()` — SHORT SL anchor is `ref_price` = `_peak_low` (when profitable) or `current_price` (when no peak). SL always above current price AND below entry when in profit.

**Known issues (2026-05-15):**
1. `PUMP_SL_PCT/PUMP_TP_PCT` in signal_gen.py (1.5%/2.5%) — not in hermes_constants. T's intent: move to hermes_constants, pump mode should use `ATR_SL_MIN_INIT`/`ATR_TP_MIN` instead. **NOT YET DONE — pending.**
2. Guardian orphan path (lines 1012-1021) hardcodes `ATR_SL_MIN_ACCEL`/`ATR_TP_MIN_ACCEL` inline as temporary placeholders — not critical since position_manager overwrites within 1 min.
3. **`_compute_dynamic_sl` and `_compute_dynamic_tp` in position_manager are DEAD CODE** — defined at lines ~1396-1445, never called. `_collect_atr_updates()` (line ~1462) is the sole active path. Consider removing.
4. **ZK SHORT TP/SL ratio bug (LIVE)** — `_collect_atr_updates()` SHORT path: SL=0.70%, TP=2.99%, ratio=4.27x instead of 1.25x. Two different implied ATRs (0.70% vs 2.39%) from same trade. TP recomputed from different ref_price than SL. See `references/zk-trade-tp-ratio-bug-2026-05-15.md`.
5. **SUI LONG #10051 ghost trade (2026-05-16)** — `compute_atr_sl_tp` is_new_trade gate requires `pnl_pct >= 0`. Price moved against trade before first ATR cycle → `is_new_trade=False` → INIT floor bypassed → phase k applied from `highest_price=entry` → SL placed ABOVE entry for LONG → closed in 3s. Fix: when `is_new_trade=False` but `current_sl <= 0` AND `highest_price ≈ entry` → force INIT treatment with `entry_price` anchor. See `references/sui-ghost-trade-fix-2026-05-16.md`.

See `references/atr-tp-sl-authority-2026-05-15.md` for full audit.

**Pitfall — local constant overrides shadow hermes_constants:**
`position_manager.py:80-83` previously defined `TP_PCT`, `SL_PCT`, `SL_PCT_MIN` as local values with different semantics than the identically-named fallbacks in hermes_constants (`TP_PCT_FALLBACK=0.08`, `SL_PCT_FALLBACK=0.015`). This caused confusion about which value was actually in use. The fix: add missing constants to hermes_constants first, then import them. Never create local overrides of what should be centralized values. Verification: `python3 -c "from position_manager import SL_PCT_MIN; from hermes_constants import SL_PCT_MIN; assert SL_PCT_MIN == SL_PCT_MIN"`

**Pitfall — constant name mismatch causes hardcoded fallback:**
When adding a constant to hermes_constants, ensure the name used in the consuming file matches exactly. `ATR_UPDATE_THRESHOLD` (in hermes_constants) vs `ATR_UPDATE_THRESHOLD_PCT` (in position_manager) required an explicit assignment `ATR_UPDATE_THRESHOLD_PCT = ATR_UPDATE_THRESHOLD` to bridge the gap — the old name was kept to avoid rewriting all references. Prefer to use the hermes_constants name directly in all files where feasible.

---

## 1. Architecture Overview

> ⚠️ **VERIFIED against live hermes_constants.py (2026-05-12)** — inline comments and older reference docs are frequently stale. Always cross-check against the actual source.

## _collect_atr_updates Flow (position_manager.py ~1550–1620)
```
1. Deduplicate tokens — one ATR fetch per unique token
2. _force_fresh_atr(token) → fetch ATR(14) from cache / HL API / Binance
3. _atr_sl_k_scaled(token, direction, atr_pct, speed, momentum) → k multiplier
4. sl_pct = k × atr_pct
5. effective_sl_pct = max(sl_pct, MIN_SL_PCT_TRAILING) → floor applied
6. Phase-based floor: ACCEL=0.20%, INIT=1.0%, etc.
7. ref_price = highest_price (LONG) or lowest_price (SHORT)
8. new_sl = round(ref_price × (1 - effective_sl_pct), 8)
9. new_tp = round(ref_price × (1 - effective_tp_pct), 8)
10. _persist_atr_levels() → write SL/TP to DB
```

### Pattern 8: exit ABOVE computed initial SL but `atr_sl_hit` fires (trailing SL locked in profit)
**NOT a bug — trailing mechanism working as designed.**

Three trades (CAKE, ME, TIA) on 2026-05-12 had exit prices above the initial SL computed from `ATR_K_INITIAL × ATR`, yet `close_reason=atr_sl_hit`. SUI (exit below initial SL) behaved correctly.

| Token | Entry | Computed Initial SL | Exit | Exit vs Initial SL |
|-------|-------|---------------------|------|-------------------|
| CAKE | 1.5674 | 1.5614 (k=1.0, ATR=0.38%) | 1.56375 | **+0.15% ABOVE** |
| ME | 0.12192 | 0.12144 (ATR=0.39%) | 0.1215 | **+0.05% ABOVE** |
| TIA | 0.44996 | 0.44794 (ATR=0.45%) | 0.448 | **+0.02% ABOVE** |

**Explanation**: Price moved favorably → `highest_price` tracked the peak → trailing SL computed from peak using phase multiplier (k=0.05–0.15). The trailing SL = `peak × (1 - max(sl_pct, 0.50%))` was tighter than initial SL = `entry × (1 - ATR_K_INITIAL × atr_pct)`. Price reversed, hit the trailing SL. Exit is above initial SL because the trailing mechanism locked in profit before the reversal.

**Key diagnostic**: if `exit > (entry × (1 - ATR_K_INITIAL × atr_pct))` but `close_reason=atr_sl_hit`, the trailing SL had already tightened the stored SL. Check `highest_price` in DB vs entry — if peak >> entry, trailing was active.

**Second contributing factor**: `ATR_UPDATE_THRESHOLD_PCT=0.15%` blocked SL updates when delta was below threshold. Evidence from agent.log (APEX): new=0.305212 vs old=0.304555 = 0.022% < 0.15% → SKIP.

Full analysis: `references/atr-exit-price-anomaly-2026-05-12.md`

---

## 2. Diagnostic Workflow
2. HL API candles_snapshot → compute ATR(14) from 15m candles
3. Binance public API fallback
4. Save result to atr_cache.json
```
If ATR is None: trade is skipped entirely (line 1554: `if atr is None: continue`).

### Key Files
| File | Role |
|------|------|
| `position_manager.py` | _collect_atr_updates (~1550–1620), _persist_atr_levels, _atr_sl_k_scaled, refresh_current_prices |
| `brain.py` | add_trade() — peak initialization on INSERT |
| `hl-sync-guardian.py` | Guardian sync — seeds peaks on existing trades |
| `hermes_constants.py` | ATR_* constants |
| `signal_gen.py` | Phase definitions (PHASE_BUILDING=60, PHASE_ACCELERATING=75, etc.) |
| `atr_cache.json` | Live ATR values |

---

## 2. Diagnostic Workflow

### Step 1 — Read the trade
```bash
python3 -c "
import json
with open('/var/www/hermes/data/trades.json') as f:
    trades = json.load(f)
for t in trades['open']:
    if t['coin'] == 'ETH':
        print(json.dumps(t, indent=2))
"
```
Check: entry, current price, sl, tp, direction, leverage.

### Step 2 — Check ATR cache
```bash
python3 -c "
import json, time
with open('/root/.hermes/data/atr_cache.json') as f:
    data = json.load(f)
eth = data.get('ETH', {})
print(f'ATR: {eth.get(\"atr\")}, age: {time.time() - eth.get(\"ts\",0):.1f}s')
"
```

### Step 3 — Check pipeline ATR logs
```bash
tail -100 /root/.hermes/logs/pipeline.log | grep -E \"\[ATR\]|ETH\"
```
Look for: `k=X ATR=X (X.XX%) → SL=X TP=X [ref=X]`

### Step 4 — Trace ATR computation
`position_manager.py` `_collect_atr_updates()` (lines ~1550–1620):
- `atr_pct = atr / _entry`
- `k = _atr_sl_k_scaled(...)` — phase-based k multiplier
- `sl_pct = k * atr_pct`
- `effective_sl_pct = max(sl_pct, MIN_SL_PCT_TRAILING)` — floor applied here
- For LONG in profit: `ref_price = highest_price` (peak)
- `new_sl = round(ref_price * (1 - effective_sl_pct), 8)`

### Step 5 — Phase-based k
Phase thresholds in `signal_gen.py`:
- `PHASE_ACCELERATING` (percentile ≥ 75) → k = base_k × 0.05–0.25
- `PHASE_EXHAUSTION` (percentile ≥ 88) → k = base_k × 0.10–0.25
- `PHASE_EXTREME` (percentile ≥ 95) → k = base_k × 0.05–0.10

Phase multipliers only matter when `atr_pct > MIN_SL_PCT`.

### Step 6 — Check peak initialization
```sql
SELECT token, direction, entry_price, highest_price, lowest_price, stop_loss
FROM trades WHERE status='open' AND token='TOKEN';
```
- SHORT: `highest_price = 0`, `lowest_price = entry` (correct after fix)
- LONG: `highest_price = entry`, `lowest_price = 0` (correct after fix)

---

## 3. Common Failure Patterns

### Pattern 1: Missing entry_atr_14 (DB schema default 10 is inert)
`entry_atr_14 = None` means the `entry_atr_14` column wasn't populated at INSERT time. The guardian recomputes ATR live every cycle via `_force_fresh_atr()`, so this column being None doesn't mean ATR wasn't used.

`tp_multiplier = 10` in the DB is the PostgreSQL column default (`schema_brain.sql` line 86), NOT a guardian-computed value. The guardian reads `_collect_atr_updates` output, not this field.

**Verification**: Check `atr_managed = True` in DB — confirms guardian is using ATR.

### Pattern 2: SL at breakeven (low-vol token floor mismatch)
For low-vol tokens (ETH ~0.17% ATR), the `MIN_SL_PCT_TRAILING` floor (ATR_SL_MIN = 0.50% as of 2026-05-07) overrides the ATR-based sl_pct (0.17%):
```python
atr = 3.97       # ETH ATR(14)
entry = 2314.0
atr_pct = atr / entry  # 0.00172
sl_pct = atr_pct        # k=1.0
MIN_SL = 0.005          # ATR_SL_MIN (0.50% as of 2026-05-07)
effective_sl_pct = max(sl_pct, MIN_SL)  # 0.50% wins → SL too wide
```
**Key insight**: `max(atr_pct, MIN_SL_PCT)` — on low-vol tokens where `atr_pct < MIN_SL`, the floor wins and the SL sits far from current price. Raising the floor from 0.15% to 0.50% on 2026-05-07 amplifies this effect for low-vol tokens.

### Pattern 3: k=1.0 despite acceleration (phase misclassification)
Two different momentum systems use different percentiles:
- `get_momentum_stats()` uses **overall percentile** → `detect_phase()` → `phase='quiet'`
- `trend_purity+` signal uses **direction-specific percentile_long/percentile_short**

For PENGU: `percentile=1.1` (< PHASE_BUILDING=60) → 'quiet', but `percentile_long=95.5` → signal fires with accelerating momentum. Result: k=1.250 (NORMAL_VOL) with NO acceleration multiplier.

**Fix**: Override `phase` in `_atr_sl_k_scaled` using direction-specific percentile. Add `detect_phase` to imports. Rename `phase = PHASE_TIER.get(...)` to `phase_tier` to avoid string-vs-int comparison bugs.

### Pattern 4: is_new_trade gate suppressing phase multiplier
Lines 1614–1624: when `|peak - entry| / entry < 0.001` (0.1%), the gate fires and replaces `_atr_sl_k_scaled` result with base k. The phase multiplier is never applied:
```python
if is_new_trade:
    k = _dr_atr(token, atr_pct)  # ← ignores _atr_sl_k_scaled result!
    MIN_SL_PCT_TRAILING = ATR_SL_MIN_INIT  # 0.50% floor
```
**Fix**: Should still call `_atr_sl_k_scaled` but use INIT floors (0.50%/0.75%) instead of bypassing entirely.

### Pattern 5: Stale ATR cache — Binance fallback blocked by stale_cached_atr check (Bug 19, 2026-05-18)

**Symptom:** zscore-pump and rs report "stale price_history" for MORPHO/UMA. `_collect_atr_updates`
skips tokens with no ATR → guardian's initial 0.5%/1.5% fallback SL/TP persist unchallenged.

**Root cause — two interacting issues:**

1. **price_collector/write race (transient):** price_collector writes price_history to
   `signals_hermes.db` FIRST, then does 90s Binance candle backfills. signals_runner fires in
   the same timer cycle → races against backfill → sees 60-90s-old committed write → fails
   120s stale gate. ALL tokens show identical last_ts simultaneously — not token-specific.

2. **Binance fallback never fires when stale cache exists:** `_force_fresh_atr()` line 1396:
   ```python
   if atr is None and stale_cached_atr is None:  # ← BUG: blocks Binance when stale cache present
       _fetch_binance_atr(...)  # Binance only reached here
   ```
   When cache age is 300s–3600s: `stale_cached_atr` is set, HL API is tried. If HL fails,
   `atr=None` but `stale_cached_atr` is NOT None → Binance never called → `atr=None` returned →
   `_collect_atr_updates` skips token → guardian fallback persists.

   For MORPHO (5674s) and UMA (5916s): cache age > 3600s, stale copy discarded →
   `stale_cached_atr = None` → Binance fires when HL fails ✓
   For SNX (334s): cache age 300s–3600s → `stale_cached_atr` saved → if HL fails, Binance skipped ✗

**Fix:** Change `_force_fresh_atr()` line 1396 from `if atr is None and stale_cached_atr is None:`
to `if atr is None:` — Binance attempted whenever HL fails, regardless of stale cache state.
Safe: Binance is a public API, no auth required.

**Key lines:**
- `position_manager.py:1367` — fresh cache: `if atr_val is not None and age < 300: return float(atr_val)`
- `position_manager.py:1369` — stale cache saved: `elif atr_val is not None and age < 3600: stale_cached_atr = float(atr_val)`
- `position_manager.py:1396` — Binance gate: `if atr is None and stale_cached_atr is None:` ← THE BLOCKER
- `position_manager.py:1629` — token skip: `if atr is None: continue` ← consequence of blocker

See `references/price-history-race-2026-05-18.md` for full diagnostic commands.

### Pattern 6: MIN_SL_PCT_TRAILING floor mismatch (new positions get ACCEL floor instead of INIT)
`_collect_atr_updates()` uses `MIN_SL_PCT_TRAILING = ATR_SL_MIN_ACCEL = 0.20%` for ALL positions, including brand new ones. This overrides `get_trade_params()` computed `ATR_SL_MIN_INIT = 1.0%` at entry.

### Pattern 7: highest_price/lowest_price not initialized
On trade creation via `add_trade()` in `brain.py`, peak fields default to 0 instead of entry price. Runtime: `max(0, current_price)` becomes the losing price instead of entry. Three-part fix required: brain.py + guardian + runtime fallback.

### Pattern 8: is_new_trade gate requires `pnl_pct > 0` — SL placed wrong side of entry (2026-05-16)
**Bug:** `compute_atr_sl_tp()` in `tpsl_utils.py` had a gate to detect brand-new trades wrapped in an `if in_profit:` block where `in_profit = pnl_pct > 0`. For a brand-new trade at entry (pnl_pct=0), `in_profit=False` → gate never fires → INIT floor not applied → ACCEL floor applied instead (0.70% vs 0.30%) → SL placed **above** entry for LONG → `atr_sl_hit` fires in seconds → ghost trade.

**Fix:** Removed the `in_profit` wrapper. Gate fires solely on `highest_price ≈ entry` (LONG) or `lowest_price ≈ entry` (SHORT), regardless of pnl_pct. New trades always get INIT treatment (wider floor, correct anchor). `in_profit` local variable removed; result dict `in_profit` key changed to `pnl_pct > 0` inline. Debug print updated.

**Verification:** SUI LONG #10051 (entry=1.064, SL=1.0923 — ABOVE entry, closed in 3s). After fix: is_new_trade=True → state=NEW_TRADE → k=1.0 (base) → eff_sl_pct=0.30% (INIT floor) → SL=1.060808 (below entry — correct).

**Why sl_distance=0:** `sl_distance` is set at INSERT time from A/B test value (control=0.03, test_a=0.015, test_b=0.01). The `stop_loss` price column is what position_manager writes via `_persist_atr_levels()`. `sl_distance=0` means A/B field wasn't updated post-INSERT — the computed `stop_loss=1.0923` was written by ATR engine but was wrong (above entry).

See `references/sui-ghost-trade-fix-2026-05-16.md` for full pre-fix analysis and `references/atr-sl-k-debug.md` for k-multiplier debugging workflow.

### Pattern 11: Display layer uses `get_trade_params()` fallback instead of PostgreSQL values (2026-05-18)
**Symptom**: Displayed SL/TP differ from TPSL pipeline log values. Pipeline log shows correct ATR-computed values; display shows something else.

**Root cause**: `get_trade_params()` (position_manager.py:1875) has its own SL/TP computation path that uses `SL_PCT_FALLBACK=1.5%` and `TP_PCT_FALLBACK=8%` as hard fallbacks. If the display/notification layer calls this function instead of reading from PostgreSQL after ATR engine runs, it gets the fallback values instead of the actual trailed values.

**Key distinction**: `get_trade_params()` is for **initial SL/TP at trade open only**. `tpsl_utils.compute_atr_sl_tp()` is the **trailing engine** that runs every cycle. Once a trade is established, never use `get_trade_params()` output for current SL/TP.

**Fix**: Display layer must read SL/TP from PostgreSQL (`trades.stop_loss`, `trades.target`) — the values written by `_persist_atr_levels()` after each ATR cycle. Never call `get_trade_params()` for an established trade.

Full reference: `references/display-vs-engine-discrepancy-2026-05-18.md`

### Pattern 11b: `[PERSIST]` log absent — `_persist_atr_levels()` not writing to DB (2026-05-18)
See `references/persist-debug-2026-05-18.md`.

### Pattern 12: SHORT trailing gate wrong-side check INVERTED (2026-05-18)
**Symptom**: TPSL computes correct SL for SHORT trades but DB never updates. SKY SHORT: DB SL=0.070700 (fallback written at entry), TPSL SL=0.069178 (correct). Gate blocks because `new_sl < current_sl` (tightening → `needs_sl=False`). Force-write check uses `current_sl < current_price` for SHORT — WRONG direction. For SHORT: `current_sl > current_price` = loss zone (SL numerically above current). Patched code checks the opposite.

**Root cause**: In `tpsl_utils.py` trailing gate, the WRONG-SIDE check for SHORT uses `current_sl < current_price`. Should be `current_sl > current_price`. LONG check is correct.

**Fix**: `tpsl_utils.py` line ~432: change `(current_sl < current_price)` → `(current_sl > current_price)` for SHORT branch.

Full trace: `references/short-wrong-side-comparison-bug-2026-05-18.md`

### Pattern 13: `atr_sl_hit` close reason written for HL mirror close (2026-05-21)
**Symptom**: ICP SHORT trade #10234 closed via `atr_sl_hit` 12 seconds after open. But price went UP from entry (2.5339→2.53735) — for a SHORT, price going UP means it moved AGAINST the trade. The stored SL=2.5175 was never touched. Pipeline log shows `HYPE Mirror CLOSED SHORT ICP (HL exit $2.538000)` — the close was triggered by HL mirror, not by SL being hit.

**Root cause**: `check_atr_tp_sl_hits()` writes `close_reason = 'atr_sl_hit'` based on in-memory price comparison (`current_price <= sl` for SHORT). When HL closes a position externally (mirror_close), the in-memory price dict may have a stale or incorrect `current_price` that satisfies the `<=` comparison, causing `atr_sl_hit` to be written even though the actual trigger was the HL close.

**ICP SHORT #10234 specifics**:
- Entry: $2.5368, SL=2.5175 (0.78% below entry), TP=2.4725
- ATR at trade time: 0.015768 (0.62% atr_pct < ATR_PCT_LOW_THRESH=1% → LOW_VOL tier)
- SL=2.5175 exactly matches k=1.25 × 0.625% (ATR_K_NORMAL_VOL=1.25 path)
- Current constants: ATR_K_NORMAL_VOL=0.75 → would produce SL=$2.5210
- **Constants were different at execution time (k was 1.25, not 0.75)**
- 1m candles: 2.5339→2.5339→2.5339→2.53735→2.53735 (UP, never touched 2.5175)
- HL exit $2.538000 = $0.02 ABOVE stored SL — price went UP, not down

**Prevention**: When `close_reason=atr_sl_hit` but price never crossed SL, check pipeline log for `HYPE Mirror CLOSED` entries. The HL mirror close is the true cause — `atr_sl_hit` in DB is a misattribution from stale in-memory price comparison.

**Also**: `sl_distance=0.015` in DB is the A/B test control value (from `decider_run`'s `sl_pct_val=0.015`), NOT the actual SL% (0.78%). The `stop_loss` column has the real SL price.
1. **Display path**: `hermes-trades-api.py` reads `stop_loss`/`target` from PostgreSQL via `get_trades()` (line 202-223). The DB values come from `_persist_atr_levels()` SQL writes. If `_persist_atr_levels()` is not being called or the SQL write is failing, DB retains the `get_trade_params()` fallback values written at entry time.

2. **Computation path**: `_collect_atr_updates()` calls `compute_atr_sl_tp()` → `_persist_atr_levels()` → SQL UPDATE. The pipeline log shows `[Position Manager] Done` WITHOUT `[ATR] Updated X position SL/TP levels`, meaning `_atr_updates` was empty for current cycle. This can happen when:
   - Trailing gate blocks writes (`needs_sl=False` because current SL already matches ATR levels)
   - ATR fetch returns `None` for the token (cache stale + Binance fallback blocked — see Pattern 5)
   - Trade IDs missing from positions dict

3. **Legacy fallback still running**: `_compute_dynamic_sl()` (position_manager.py:1450-1493) and `get_trade_params()` (line 1875) both compute SL/TP using `current_price * (1 + ATR_SL_MIN)` or `entry_price * (1 + SL_PCT_FALLBACK=1.5%)`. These are dead code paths for the TPSL engine, but the display may be reading from them if the DB write never happened.

**Confirmed for current session (2026-05-18)**:
| Token | Direction | TPSL SL | Displayed SL | Delta |
|-------|-----------|---------|-------------|-------|
| SNX | SHORT | 0.304210 | 0.308540 | +1.4% |
| UNI | SHORT | 3.423800 | 3.492564 | +2.0% |
| SKY | SHORT | 0.069178 | 0.070700 | +2.2% |

TPSL formula: `lowest * (1 + eff_sl_pct)` — correct.
Display formula: `current * (1 + SL_PCT_FALLBACK=1.5%)` or `current * (1 + ATR_SL_MIN=0.5%)` — wrong anchor, wrong percentage.

**Verification**: `[PERSIST]` prints at position_manager.py:1740 should fire on every `_persist_atr_levels()` call. If absent from pipeline log, either `_atr_updates` is empty or the print is buffered/suppressed. Check with:
```bash
grep "PERSIST" /root/.hermes/logs/pipeline.log | tail -20
grep "ATR Updated" /root/.hermes/logs/pipeline.log | tail -10
```

**Fix needed**: (1) Add debug to `_collect_atr_updates()` to show WHY each trade is/isn't included in `_atr_updates`; (2) Add debug to `_persist_atr_levels()` to show DB before/after values; (3) ensure PostgreSQL write path from pipeline service is functional (peer auth local socket — may fail silently if connection method wrong).
**Symptom**: PostgreSQL `trades` table holds SL values 1.5% above entry for SHORT trades (PEOPLE, XMR, BSV). tpsl_utils computes correct 0.70% ACCEL-floor SL but the stored value never changes.

**Root cause**: `decider_run.execute_trade()` writes PUMP_SL_PCT=1.5% SL to PostgreSQL at entry. `position_manager._collect_atr_updates()` computes correct ATR values each cycle, but the SQL UPDATE in `_persist_atr_levels()` may be silently failing (psycopg2 auth error from sandbox — pipeline service uses peer auth local socket). Delta gate analysis: XMR delta=0.78%, BSV delta=1.6% — both above ATR_UPDATE_THRESHOLD=0.15%, so the gate would NOT block the write.

**Confirmed**: tpsl_utils IS the sole ATR computation authority. It correctly computes new SL (e.g., BSV new_sl=15.5319, XMR new_sl=396.083). The problem is the computed value is never persisted to PostgreSQL.

**Immediate fix**: Direct SQL UPDATE of the specific trades. Long-term fix: verify PostgreSQL write path from pipeline service.

See `references/pump-mode-sl-staleness-2026-05-17.md`.

### Pattern 10: `atr_managed=FALSE` — position_manager never claimed the trade (2026-05-17)

**Also: DOT SHORT #10226 (2026-05-21)** — Stored SL=1.2084, 3.06% from entry. ATR_SL_MAX_INIT=0.9%. SL is **outside all ATR bounds** — impossible to produce via `tpsl_utils.compute_atr_sl_tp()` or `get_trade_params()`. Must come from a different code path or stale data.

ICP SHORT #10234 — Stored SL=2.5175, 0.76% from entry. Within ATR_SL_MIN_INIT (0.7%) / ATR_SL_MAX_INIT (0.9%) bounds, but doesn't match forward computation (expected 2.5561). Most likely: ATR computed from ref_price ~2.4977 (lower than entry), producing wider SL than expected.

See `references/same-cycle-close-2026-05-21.md` for full analysis.

**Symptom**: Trade has wrong SL (too wide or outside all ATR caps) but `tpsl_utils.compute_atr_sl_tp` produces a correct value that never gets written to DB. All other trades from the same session have correct SLs and `atr_managed=TRUE`.

**Root cause**: `_persist_atr_levels()` sets `atr_managed = TRUE` only on successful SQL UPDATE. If position_manager never ran for this trade (exclusion filter, cycle skip, SQL error), `atr_managed` stays FALSE. The SL/TP was set at open time by brain.py Step 5 or signal defaults, not by the ATR engine. The trailing gate can only tighten — it cannot widen a too-wide SL, so the wrong value persists forever.

**Diagnosis**:
```python
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', password='Brain123')
cur = conn.cursor()
cur.execute("SELECT token, direction, entry_price, stop_loss, target, atr_managed FROM trades WHERE status='open'")
for row in cur.fetchall():
    print(f"{row[0]} {row[1]}: entry={row[2]}, SL={row[3]}, TP={row[4]}, atr_managed={row[5]}")
```
Any trade with `atr_managed=FALSE` and a wrong SL needs manual correction.

**VVV/0G case (2026-05-17)**:
- VVV: actual SL=14.772310 = `current_price + ATR` exactly (no known code produces this)
- 0G: actual SL=0.503663 ≈ `entry × 1.0153` (+1.53%, matches SL_PCT_FALLBACK=1.5%)
- Both: `atr_managed=FALSE`, computed SL=14.611 (VVV) and 0.499 (0G), gap = +1.6% and +0.95%

**Fix**: Direct SQL update of wrong SL, then verify with `SELECT token, stop_loss, atr_managed FROM trades WHERE status='open' AND token IN ('VVV','0G')`.

**Prevention**: Add `atr_managed` check to post-open audit — if FALSE after 1 position_manager cycle, alert and force-update.
**Symptom**: PostgreSQL `trades` table holds SL values 1.5% above entry for SHORT trades (PEOPLE, XMR, BSV). tpsl_utils computes correct 0.70% ACCEL-floor SL but the stored value never changes.

**Root cause**: `decider_run.execute_trade()` writes PUMP_SL_PCT=1.5% SL to PostgreSQL at entry. `position_manager._collect_atr_updates()` computes correct ATR values each cycle, but the SQL UPDATE in `_persist_atr_levels()` may be silently failing (psycopg2 auth error from sandbox — pipeline service uses peer auth local socket). Delta gate analysis: XMR delta=0.78%, BSV delta=1.6% — both above ATR_UPDATE_THRESHOLD=0.15%, so the gate would NOT block the write.

**Confirmed**: tpsl_utils IS the sole ATR computation authority. It correctly computes new SL (e.g., BSV new_sl=15.5319, XMR new_sl=396.083). The problem is the computed value is never persisted to PostgreSQL.

**Immediate fix**: Direct SQL UPDATE of the specific trades. Long-term fix: verify PostgreSQL write path from pipeline service.

See `references/pump-mode-sl-staleness-2026-05-17.md`.

---

## 5. ATR Cache Verification (2026-05-12 session)

**Cache reset on trade close: CONFIRMED WORKING.**
- `close_position()` does NOT write to `atr_cache.json` — only reads
- `atr_cache.json` TTL=300s, stale fallback=3600s
- `_force_fresh_atr()` fetches fresh ATR from HL API if cache >300s old
- `_collect_atr_updates()` calls `_force_fresh_atr()` each token per cycle
- P2 fix at line 1506: re-reads `highest_price`/`lowest_price` from DB each cycle to prevent stale in-memory peak tracking

**ATR cache is NOT stuck.** MON ATR=0.0002875, age=35min (within 3600s fallback). IP ATR=0.003956, age=14min. Both are within the stale-max window and will be refreshed on next cycle.

**IP anomaly (2026-05-12 03:40):** entry=$0.5565, computed SL=$0.555511, exit=$0.556580, close_reason=atr_sl_hit.

| SL scenario | Value | Exit vs SL |
|-------------|-------|-----------|
| ACCEL_FAST (k=0.0375, MIN_SL=0.50%) | 0.555387 | +0.21% above |
| MIN_SL floor (0.20%) | 0.555387 | +0.21% above |
| New trade INIT floor (0.50%) | 0.553740 | +0.51% above |
| ATR_K_INITIAL×ATR (k=1.0, base) | 0.555511 | +0.19% above |

Exit ($0.556580) is above ALL computed SL variants. `atr_sl_hit` should NOT have fired.

**Root cause: stale `current_price` in pos dict at hit-detection time.**
`check_atr_tp_sl_hits()` runs once per cycle reading `pos.get('current_price')` from the in-memory dict. If `refresh_current_prices()` runs AFTER `check_atr_tp_sl_hits()` in the same cycle, `current_price` in the dict is still the PREVIOUS cycle's value (possibly 0 or an old stale price). The comparison `cur <= sl` sees a stale low price and triggers a false `atr_sl_hit`. The exit price recorded in the log ($0.556580) is the HL fill price, which is correct — but the trigger was based on the stale dict value.

**Diagnostic**: When `exit > all computed SL variants` but close_reason=atr_sl_hit, check whether `refresh_current_prices()` runs before or after `check_atr_tp_sl_hits()` in the position_manager cycle. The price used for hit detection is from the in-memory dict, not the live HL price.

## 6. Phase Multiplier Map (VERIFIED 2026-05-15 against live tpsl_utils.py + hermes_constants.py)

**Three-stage computation:**

```
atr_pct = ATR / entry_price
        ↓
Stage 1: _atr_tier(atr_pct)         ← volatility tier
        ↓
Stage 2: _atr_sl_k_scaled(...)       ← phase multiplier × base_k
        ↓
Stage 3: compute_atr_sl_tp()        ← MIN/MAX floor + trailing gate
        ↓
   new_sl / new_tp → written to DB
```

**Stage 1 — ATR tier (`_atr_tier` in tpsl_utils.py:61) — VERIFIED 2026-05-27 against live hermes_constants.py:**

| atr_pct | Constant | Pre-2026-05-21 | Current (T's tweak) |
|---------|----------|----------------|---------------------|
| < 1% (LOW_VOL) | `ATR_K_LOW_VOL` | 1.0 | **0.5** |
| 1–3% (NORMAL_VOL) | `ATR_K_NORMAL_VOL` | 2.0 | **0.75** |
| > 3% (HIGH_VOL) | `ATR_K_HIGH_VOL` | 2.5 | **0.25** |

**⚠️ CRITICAL: Stage 1 table above is from the parent SKILL.md. Always verify against live hermes_constants.py — comments are frequently stale.**

**Stage 2 — Phase detection (`_phase_from_pct` in tpsl_utils.py:73) — uses direction-specific percentile:**

| Direction-specific percentile | Velocity > 0 | Velocity < 0 |
|---|---|---|
| ≥ 90 | accelerating | exhaustion |
| 70–89 | building | exhaustion |
| < 70 | neutral | neutral |

Note: `_atr_sl_k_scaled` takes `speed_percentile` as a parameter but only uses it for sub-case branching (fast/slow). Phase detection itself uses `momentum_stats['percentile_long']` or `['percentile_short']` — the direction-specific percentile, NOT the overall speed percentile.

**Stage 3 — Phase multiplier applied to base_k (current after T's 2026-05-21 tweak):**

| Phase | Stall (vel < 0) | Fast (speed_pctl ≥ 70) | Slow (speed_pctl < 70) |
|---|---|---|---|
| neutral | base_k | base_k | base_k |
| building | base_k | base_k | base_k |
| accelerating | **0.06** | **0.08** | **0.06** |
| exhaustion | **0.06** | **0.08** | **0.06** |
| extreme | **0.06** | **0.08** | **0.06** |

`stalling = (velocity < 0) and (phase_tier >= PHASE_TIER_ACCELERATING)`

**Resulting k range:** base_k × 1.0 (neutral/building) down to base_k × 0.05 (extreme-fast).

**New trade exception:** if peak ≈ entry price AND pnl > 0 (trade just opened), resets to base_k + INIT floor (wider: 0.50% SL vs 0.70% for established). Prevents 0.05× base from squeezing a brand-new position.

**⚠️ WAS: Two different phase detection systems — RESOLVED 2026-05-27 ✅**

`tpsl_utils._phase_from_pct` and `signal_gen.detect_phase` now use the same constants from hermes_constants.py:
- PHASE_BUILDING=60, PHASE_ACCELERATING=75, PHASE_EXHAUSTION=88, PHASE_EXTREME=95
- PHASE_NEUTRAL=50, PHASE_VEL_STALL_THRESH=0.0, PHASE_ACCEL_FAST_THRESH=70

See `references/phase-detector-consolidation-2026-05-27.md` for full implementation details.

**Live example (2026-05-15):**

MON (LONG): atr_pct=0.92%, percentile_long=40.5, velocity=-0.0341
→ `_phase_from_pct(40.5, -0.0341)` → 'neutral' (pct < 50) → k=1.0, mult=1.0
→ `detect_phase(40.5, -0.0341)` → 'quiet' (pct < 60 AND |vel| > 0.05... wait vel=0.0341 < 0.05, so not quiet)
   Actually: pct=40.5 < PHASE_BUILDING=60, but |vel|=0.0341 < 0.05 → 'quiet'
   The 'quiet' check comes FIRST in detect_phase.

ADA (LONG): atr_pct=0.60%, percentile_long=60.0, velocity=-0.0487
→ `_phase_from_pct(60.0, -0.0487)` → 'neutral' (pct 50-69) → k=1.0, mult=1.0
→ `detect_phase(60.0, -0.0487)` → 'building' (pct >= PHASE_BUILDING=60)

Both MON and ADA are NEUTRAL for k-scaling purposes despite being in different signal phases. The phase mult is 1.0 for both — no acceleration squeeze. The real driver of their SL (0.92% for MON, 0.70% for ADA) is the LOW_VOL tier (atr_pct < 1% → k=1.0) and the ACCEL floor (0.70% floor on ADA, raw sl_pct=0.60% gets floored up to 0.70%).

**⚠️ Stale doc error (now fixed):** Previous version said EXTREME-fast = 0.50. Actual value is **0.05** — extreme-fast is the tightest possible stop, 5% of base_k.

---

## 7. Shared ATR Module — tpsl_utils.py (2026-05-15)

**New module created 2026-05-15.** Three files now share ATR SL/TP computation via `tpsl_utils.py`:
- `position_manager.py` — authoritative (already used `atr_cache.get_atr`)
- `self_close_watcher.py` — inline ATR removed, replaced with `compute_atr_sl_price()` / `compute_atr_tp_price()`
- `hl-sync-guardian.py` — two inline ATR blocks removed, replaced with same calls

**Key design decisions:**
- Uses `atr_cache.get_atr` (read-only), not `_force_fresh_atr` (writer)
- SHORT new/in-profit: SL anchored to `entry_price` (stays above entry = protective)
- SHORT established: SL trails from `lowest_price` (correct trailing)
- `k_tp = k × 1.25` for TP computation
- Fallback: SL=1.5%, TP=8.0% if ATR unavailable

Full reference: `references/tpsl-utils-shared-module.md`

## 8. Peak Tracking Bugs

### Bug 1: highest_price/lowest_price not initialized on trade creation
**Symptom**: BCH SHORT SL moves LOWER as price falls against position (backwards behavior).

**Root cause**: `brain.py` `add_trade()` sets peaks to 0 on INSERT. Runtime: `max(0, current_price)` becomes losing price.

**Three-part fix**:
1. `brain.py` INSERT: seed peaks from entry
2. `hl-sync-guardian.py`: seed peaks when syncing
3. `position_manager.py` ATR loop: runtime fallback initializing peaks from entry

### Bug 2: continue at line 2178 blocking peak update for HL positions (unreachable code)

**Root cause**: `continue` inside `if hl_data:` block exits before peak tracking block runs for ANY position with HL data.

```python
if hl_data:
    # ... compute PnL ...
    continue   # ← BLOCKS peak tracking for HL positions!

# Below is UNREACHABLE for positions WITH HL data:
existing_high = float(pos.get('highest_price') or 0) or 0
new_high = max(existing_high, cur_price)  # never runs!
```

**Fix**: Move `continue` to `else` branch so peak tracking runs regardless of HL data availability.

### Bug 3: LONG highest_price never updated (new_high = existing_high)
**Symptom**: PENGU LONG `highest_price` stayed frozen at entry ($0.010039) even as price rose to $0.010201. TP stuck computing from entry instead of peak.

**Root cause** (`position_manager.py` ~line 2283):
```python
elif direction == "LONG":
    new_high = existing_high  # ← BUG: never updates!
    new_low  = min(existing_low, cur_price)
```

Combined with SHORT bug (Bug B above), full asymmetry:
- SHORT: `new_high = max(...)` ✓ but `new_low = existing_low` ✗
- LONG:  `new_high = existing_high` ✗ but `new_low = min(...)` ✓

**Fix**: `new_high = max(existing_high, cur_price)` for LONG branch.

### Bug 4: Stale reference price causes loose trailing (2026-05-10 — LAYER post-mortem)
**Symptom**: LAYER LONG locked in +30.56% profit but SL at 0.151584 was loose — price sliced through it on the reversal, continued to ~0.153+ before dropping to 0.136. Constants (ATR_SL_MIN_ACCEL=0.50%) were correct and binding, but the SL was still ~0.5% below the reference price used, not the true peak.

**Root cause**: The `ref_price` for trailing SL is `highest_price` from the DB (`_peak_cache` at line 1523). The DB `highest_price` is updated once per pipeline cycle (~1 minute) in `refresh_current_prices()`. When a token moves 5-10% in one cycle, the reference price used for trailing is already stale by the time `_collect_atr_updates` runs.

**Trace for LAYER (2026-05-10)**:
- Actual peak reached: ~0.153
- DB `highest_price` at last update: ~0.1524
- effective_sl_pct = 0.50% (ATR_SL_MIN_ACCEL binding)
- SL computed: 0.1524 × (1 - 0.005) = 0.1516
- True optimal SL with fresh peak: 0.153 × (1 - 0.005) = 0.1523
- Gap: ~0.07% more profit left on the table

**The constants ARE correct** — the problem is the reference price lags the real peak. The 0.50% floor is doing its job relative to the stale reference, but the stale reference itself is the bottleneck.

**Diagnosis**: When trailing SL appears loose despite correct constants, check `highest_price` in DB vs current price. If `highest_price` has not moved but price has, the DB peak is stale.

```sql
SELECT token, direction, entry_price, highest_price, current_price,
       (current_price - highest_price) / highest_price * 100 as price_vs_peak_pct
FROM trades WHERE status = 'open';
```

**Fix options** (priority order):
1. Raise pipeline frequency for peak tracking (reduce cycle time)
2. Use a faster peak source (direct HL API instead of DB write-then-read)
3. In `_collect_atr_updates`, fall back to `current_price` when `highest_price` has not been updated recently and price has diverged significantly

---

## 6. SL/TP Direction Bugs

### Bug: SHORT TP uses entry_price instead of ref_price (TP never trails)
In `_update_position_sl_tp` (~line 1665):
```python
if direction == "LONG":
    new_tp = round(ref_price * (1 - new_tp_pct), 8)   # ✓ correct
elif direction == "SHORT":
    new_tp = round(entry_price * (1 - new_tp_pct), 8)  # ✗ BUG — never trails!
```

**Fix**: `new_tp = round(ref_price * (1 - new_tp_pct), 8)` for SHORT.

### Bug: `needs_sl=False` blocks valid trailing tighten (2026-05-17)
**Symptom**: `compute_atr_sl_tp` produces a tighter SL than what's in the DB, `needs_sl=False` gets returned anyway, and the position_manager skips the update. VVV SHORT: current SL=14.772, computed=14.611 (would tighten by +1.6%), but `needs_sl=False`.

**Root cause**: The trailing gate in `compute_atr_sl_tp` sets `needs_sl=False` when the SHORT's `new_sl >= current_sl`. But for VVV, `new_sl=14.611 < current_sl=14.772` — the condition should pass. The `needs_sl=False` is coming from somewhere else in the function, possibly a phase check or the `state` field being `ESTABLISHED` with a different code path.

**Diagnosis**: Run `compute_atr_sl_tp` with debug prints on every `needs_sl` assignment:
```python
# In tpsl_utils.compute_atr_sl_tp, grep for "needs_sl"
# There are 5 places where needs_sl is set:
# 1. Default True at start
# 2. Set False when current_sl > 0 and new_sl would loosen (SHORT: new_sl >= current_sl)
# 3. Set False when new_sl would loosen (LONG: new_sl >= current_sl)
# 4. Set True when current_sl <= 0 (no existing SL)
# 5. Set True for NEW_TRADE state
```

**Fix**: Add minimum improvement threshold — if computed SL is meaningfully tighter than current SL (e.g., >0.5% improvement), set `needs_sl=True` regardless of the tighten condition.

See `references/trailing-gate-needs-sl-debug-2026-05-17.md` for full trace and SQL fix for VVV/0G.

### Bug: SHORT new_low = existing_low (trough never updates)
```python
if direction == "SHORT":
    new_high = max(existing_high, cur_price)   # ✓ correct
    new_low  = existing_low                      # ✗ BUG: never tracks new lows!
```

SHORT SL trails DOWN using `ref_price = lowest_price`. If `lowest_price` never goes below entry, SL reference never improves.

**Fix**: `new_low = min(existing_low, cur_price)` for SHORT branch.

---

## ATR TP/SL Tightening — Constants Reference (2026-05-21)

**Q: How do we tighten SL/TP when trade is going in our favor?**

The system already trails SL as price moves in our favor. The "tightening" is controlled by these constants:

| Constant | Current | Effect when decreased |
|---|---|---|
| `ATR_TP_K_MULT` | 1.25 | Lower = tighter TP (TP = k × ATR_TP_K_MULT × ATR) |
| `K_PHASE_ACCEL_STALL` | 0.06 | Lower = tighter SL in accelerating/stalling phase |
| `K_PHASE_ACCEL_FAST` | 0.10 | Lower = tighter SL in fast acceleration |
| `K_PHASE_EXH_STALL` | 0.06 | Lower = tighter SL in exhaustion/stalling |
| `K_PHASE_EXT_FAST` | 0.10 | Lower = tighter SL in extreme/fast |
| `ATR_UPDATE_THRESHOLD` | 0.0015 (0.15%) | Raise = updates less frequent, bigger increments |

**What does NOT work well:** Decreasing `ATR_SL_MIN_ACCEL` (was already raised from 0.30% to 0.70% to "stop cutting winners"). The floor was tightened before and it cut winners — it was reversed.

**What actually matters:** The `highest_price` (LONG) or `lowest_price` (SHORT) anchor. As price makes new highs/lows, SL gets raised/lowered proportionally. The system is working as designed — the bottleneck is price movement, not the constants.

**No-built-in knob:** `MIN_PNL_TIGHTEN_PCT` — currently no threshold for when trailing activates. Would need a code change to add.

**Note:** ATR trailing is already the ATR TP/SL authority. `tpsl_utils.compute_atr_sl_tp()` is the sole computation engine.

---

## Constants Reference (VERIFIED against live hermes_constants.py 2026-05-21)

**⚠️ CRITICAL: Always read actual constant values from hermes_constants.py — comments are frequently stale. Inline comments in tpsl_utils.py and position_manager.py are frequently wrong. Verify with a direct `grep` against the live file.**

**Stage 1 — ATR Volatility Tier → base_k (`_atr_tier` in tpsl_utils.py:61):**

| atr_pct range | Constant | Old (pre-2026-05-21) | Current (T's tweak) |
|---|---|---|---|
| < 1% (LOW_VOL) | `ATR_K_LOW_VOL` | 1.0 | **0.75** |
| 1–3% (NORMAL_VOL) | `ATR_K_NORMAL_VOL` | 2.0 | **0.50** |
| > 3% (HIGH_VOL) | `ATR_K_HIGH_VOL` | 2.5 | **0.25** |

**Stage 2 — Phase → k multiplier (applied on top of base_k):**

| Phase | Sub-case | Constant | 2026-05-21 tweak | 2026-06-25 retune (current) |
|---|---|---|---|---|
| accelerating | stalling | `K_PHASE_ACCEL_STALL` | 0.06 | **0.6** (10x) |
| accelerating | fast (speed_pctl ≥ 70) | `K_PHASE_ACCEL_FAST` | 0.08 | **0.5** (10x) |
| accelerating | slow | `K_PHASE_ACCEL_SLOW` | 0.06 | **0.4** (10x) |
| exhaustion | stalling | `K_PHASE_EXH_STALL` | 0.06 | **0.5** (25x) |
| exhaustion | fast | `K_PHASE_EXH_FAST` | 0.08 | **0.4** (13x) |
| exhaustion | slow | `K_PHASE_EXH_SLOW` | 0.06 | **0.3** (15x) |
| extreme | stalling | `K_PHASE_EXT_STALL` | 0.06 | **0.3** (30x) |
| extreme | fast | `K_PHASE_EXT_FAST` | 0.08 | **0.2** (10x) |

**2026-06-25 retune rationale:** the 0.06-0.08 values were being clobbered by `min(max(sl_pct, MIN_SL_PCT=0.015), ATR_SL_MAX=0.012)` — the MIN was 1.5% and MAX was 1.2%, so MAX always won. The phase multipliers produced nothing distinguishable in the output. After the retune (constants raised 10-30x, MAX dropped to 0.8%, MIN_ACCEL dropped to 0.5%), the phase logic now produces visibly different output in the 0.5-0.8% gap band, and accel-300 type signals actually trigger tighter SL. See `references/tpsl-constant-tweaks-2026-06-25.md` for full trace.

**Stage 3 — MIN/MAX floors (unchanged by T's tweak):**

| Constant | Value | Purpose |
|----------|-------|---------|
| `SL_PCT_FALLBACK` | 0.015 (1.5%) | SL if ATR unavailable |
| `TP_PCT_FALLBACK` | 0.08 (8%) | TP fallback target |
| `STOP_LOSS_DEFAULT` | 0.015 (1.5%) | Hard fallback SL |
| `SL_PCT_MIN` | 0.01 (1%) | Minimum SL (hard floor) |
| `ATR_PCT_FALLBACK` | 0.03 (3%) | Assumed ATR when unavailable |
| `ATR_TP_K_MULT` | 1.25 | TP = k × 1.25 × ATR |
| `ATR_SL_MIN` | 0.015 (1.5%) | Generic trailing SL floor |
| `ATR_SL_MAX` | 0.017 (1.7%) | Trailing SL cap |
| `ATR_TP_MIN` | 0.015 (1.5%) | TP floor |
| `ATR_TP_MAX` | 0.05 (5.0%) | TP cap |
| `ATR_SL_MIN_ACCEL` | 0.01 (1.0%) | Established trade SL floor |
| `ATR_TP_MIN_ACCEL` | 0.015 (1.5%) | Established trade TP floor |
| `ATR_SL_MIN_INIT` | 0.01 (1.0%) | New trade SL floor |
| `ATR_SL_MAX_INIT` | 0.015 (1.5%) | New trade SL cap |
| `ATR_PCT_LOW_THRESH` | 0.01 (1%) | LOW_VOL / NORMAL_VOL boundary |
| `ATR_PCT_HIGH_THRESH` | 0.015 (1.5%) | NORMAL_VOL / HIGH_VOL boundary |

**⚠️ LIVE VALUES (2026-05-24) — verify against hermes_constants.py:270-299:**
The above table reflects current live values. Older reference docs may show `ATR_SL_MIN_INIT=0.007 (0.70%)` — those are stale. Current INIT and ACCEL are both **1.0%**, meaning there is NO differentiation between new and established trades at the floor level.

**Resulting effective SL% for established trades (k × ATR%, floored at ATR_SL_MIN=0.65%):**

| ATR% | Old k | Old SL% | New k | New SL% | Binds? |
|---|---|---|---|---|---|
| 0.5% (LOW_VOL) | 1.0 | 0.50% | 0.75 | 0.375% | **floor** |
| 1.0% (NORMAL_VOL) | 2.0 | 2.00% | 0.50 | 0.50% | **floor** |
| 1.5% (NORMAL_VOL) | 2.0 | 3.00% | 0.50 | 0.75% | k×ATR |
| 2.0% (NORMAL_VOL) | 2.0 | 4.00% | 0.50 | 1.00% | k×ATR |
| 3.0% (NORMAL_VOL) | 2.0 | 6.00% | 0.50 | 1.50% | k×ATR |
| 5.0% (HIGH_VOL) | 2.5 | 12.50% | 0.25 | 1.25% | k×ATR |

**⚠️ K_PHASE_ACCEL_FAST = 0.08 — risk of cutting winners:**
For tokens in ACCELERATING phase with speed_pctl ≥ 70 (e.g., SNX pct_short=96.0, BCH pct_short=96.5): k = base_k × 0.08. With NORMAL_VOL base_k=0.50: eff_k = 0.04. At 1% ATR: SL = 0.04% of price = $0.00012 for SNX. One pullback and the trade stops out for a tiny loss. Recommend keeping K_PHASE_ACCEL_FAST at 0.12 or higher — the old value of 0.10 was already tight.

**⚠️ NORMAL_VOL k change (2.0 → 0.5) is the biggest improvement:**
Old: at 2% ATR, SL = 4% — absurdly wide, only profit_monster could capture anything. New: at 2% ATR, SL = 1% — much more reasonable, gives the trade room to run.

**T's explicit directive (2026-05-10)**: "only report, no changes." When T says this, do NOT modify anything — report only.

**T's trading philosophy**: "first candle against us we're out, book profit fast." SL floor 0.50%, cap 2%, TP 0.75–5.0%, k_tp ×1.25.

---

## 9. Loss Cooldown Import Chain (2026-05-11)

Loss cooldown system: `position_manager.py` writes to `loss_cooldowns.json` (per-coin incremental: 10min→20min→40min). `cascade_flip.py` and `signal_schema.py` read from it.

**Constant locations (as of 2026-05-11)**:
- `LOSS_COOLDOWN_BASE = 10/60` (10 min) — `hermes_constants.py:270`
- `LOSS_COOLDOWN_MAX = 40/60` (40 min) — `hermes_constants.py:271`
- `WIN_COOLDOWN_MINUTES = 5` — `hermes_constants.py:272`
- `LOSS_COOLDOWN_FILE` — `hermes_constants.py` (was only in `paths.py` before 2026-05-11)
- `FLIP_COUNTS_FILE` — `hermes_constants.py` (was only in `paths.py` before 2026-05-11)
- `RUNTIME_DB` — `hermes_constants.py` (was only in `paths.py` before 2026-05-11)

**Safe import sequence** (see also `python-gotchas/references/multi-file-import-refactor.md`):
1. Add missing constants to `hermes_constants.py` FIRST
2. Compile-check all affected files: `python3 -m py_compile cascade_flip.py`
3. Import-chain test: `cd /root/.hermes/scripts && python3 -c "from cascade_flip import ..."`
4. Check transitive importers

**ATR SL hit detection is NOT affected by loss cooldowns** — `check_atr_tp_sl_hits()` in position_manager only checks `stop_loss`/`target`/`current_price`. Loss cooldown (`is_loss_cooldown_active`) is only checked at signal generation filtering (signal_compactor), not in the position management loop. ATR SL fires regardless of loss cooldown state.

## 11. Session Findings — Open Trade SL Snapshot (2026-05-21 Evening)

All 5 open positions have ATR 0.03-0.08% (ultra-low volatility). All are floor-locked:

```
BSV   SHORT | SL from entry=0.248% | SL from current=0.131% | phase=building | conf=97
LINEA LONG  | SL from entry=0.607% | SL from current=0.607% | phase=extreme  | conf=89
IP    SHORT | SL from entry=0.461% | SL from current=0.480% | phase=quiet   | conf=98
TAO   SHORT | SL from entry=0.084% | SL from current=0.700% | phase=building | conf=98
FET   SHORT | SL from entry=0.052% | SL from current=0.570% | phase=extreme  | conf=86
```

**TAO case (most instructive):** Phase=BUILDING, conf=98. Entry=281.1, current=279.97 (in profit -0.40%).
SL from entry=0.084% — essentially at entry. Nadir tracked BELOW entry (price moved down first, SL anchored to nadir below entry, floor applied → SL ended up at entry-level distance). As price moved in our favor, nadir tracked lower — SL is now 0.700% above current (281.93 vs 279.97) because trailing followed the improving nadir.

**Key: BUILDING phase k = 1.0 (no acceleration).** Phase multipliers only apply in ACCELERATING/EXHAUSTION/EXTREME. The phase acceleration T wanted (tight trailing on strong moves) only fires in later-stage phases, not in BUILDING.

**BSV case:** Phase=BUILDING, conf=97. nadir=14.860 (below entry 14.937). SL=14.97409 (0.248% from entry). Current=14.9545. SL from current=0.131% — only 0.13% above current. A tiny 0.13% adverse move hits SL for ~0.4% loss (3× leverage). This is the "survive swings but not close on profit" pattern in microcosm.

### Closed Trade sl_dist=0.0 vs sl_dist=1.5 (New Diagnostic)

```
sl_dist=1.5 (explicit tight SL):
  PURR SHORT  +1.41% move → -140.7% loss
  ORDI SHORT  +0.65% move → -64.8% loss
  MERL SHORT  +0.46% move → -45.9% loss

sl_dist=0.0 (ATR-based SL, no explicit distance):
  BCH  SHORT  +0.37% move → -36.9% loss
  APEX SHORT  +0.34% move → -33.7% loss
  GALA SHORT  +0.85% move → -85.2% loss
```

Both groups: same problem (0.3-1.4% adverse move triggers SL). `sl_dist=0` means A/B test field wasn't updated post-INSERT (still 0), but `stop_loss` column has the real value. **Do not use `sl_distance` column for diagnostics — use `stop_loss` and `entry_price` directly.**

### Phase Classification (momentum_cache read)

```
FET:   phase=extreme,   percentile_short=81.5, velocity=0.46%, z_direction=rising
IP:    phase=quiet,     percentile_short=1.0,  velocity=1.30%, z_direction=falling
LINEA: phase=extreme,   percentile_short=81.0, velocity=0.93%, z_direction=neutral
TAO:   phase=building,  percentile_short=56.5, velocity=0.97%, z_direction=neutral
BSV:   phase=building,  percentile_short=64.0, velocity=0.45%, z_direction=neutral
```

**Critical:** `_phase_from_pct` (tpsl_utils) vs `detect_phase` (signal_gen.py) produce DIFFERENT labels.
ATR k-scaling uses `_phase_from_pct`, NOT `detect_phase`. Phase multipliers (0.06/0.08) only
apply in ACCELERATING/EXHAUSTION/EXTREME — BUILDING phase has multiplier 1.0 (no acceleration squeeze).

---

## 10. Files Reference

### position_manager.py — _collect_atr_updates (~1550–1620)
- ATR fetch per token via `_force_fresh_atr()`
- k computation via `_atr_sl_k_scaled()`
- Floor application: `max(sl_pct, MIN_SL_PCT_TRAILING)`
- SL/TP computation with phase-based k
- Persist via `_persist_atr_levels()`

### position_manager.py — _atr_sl_k_scaled()
- Phase-based k multiplier using direction-specific percentile
- Phase sub-cases: stalling, fast, slow
- base_k from `_atr_multiplier()` (vol-based: 0.5/0.75/1.0)

### position_manager.py — refresh_current_prices (~2131–2278)
- `continue` at line 2178 — **blocks peak tracking for HL positions**
- Peak tracking block (~2219–2260) — **unreachable for HL positions**
- LONG/SHORT asymmetry bugs in peak update

### brain.py — add_trade() (~393–402)
- Peak initialization on INSERT
- Must seed highest_price/lowest_price from entry on creation

### hl-sync-guardian.py — sync (~1015–1021)
- Guardian sync seeds peaks for existing trades
- Safety net for trades created before fix

### hermes_constants.py
- All ATR_* constants — VERIFY against live file; inline comments are frequently stale
- ATR_SL_MIN_INIT=0.002 (0.20%), ATR_SL_MAX_INIT=0.005 (0.50%) — confirmed 2026-05-12
- ATR_SL_MIN=0.002, ATR_SL_MAX=0.005, ATR_TP_MIN=0.015, ATR_TP_MAX=0.05
- ATR_K_LOW_VOL=0.5, ATR_K_NORMAL_VOL=0.75, ATR_K_HIGH_VOL=1.0

### signal_gen.py
- Phase definitions: PHASE_BUILDING=60, PHASE_ACCELERATING=75, PHASE_EXHAUSTION=88, PHASE_EXTREME=95
- `detect_phase(percentile, velocity)` function
- `get_momentum_stats()` — returns overall percentile vs direction-specific
