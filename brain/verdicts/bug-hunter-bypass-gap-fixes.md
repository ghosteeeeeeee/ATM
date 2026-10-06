# bug_hunter Verdict — Bypass Gap Fixes (commit 61bec3b8)

**Date:** 2026-10-06
**Scope:** `scripts/hermes_constants.py` (PROFIT_MONSTER_BYPASS_SIGNALS), `scripts/position_manager.py` (_is_ride_it, _match_exit_config), `scripts/cut_loser.py`, `scripts/profit_monster.py`, PostgreSQL brain DB
**Method:** Executed logic tests against the real imported constants + verbatim replication of `_match_exit_config` (rev-2), live DB queries against the brain DB, `py_compile` on all four files. No mental-only testing.

---

## VERDICT: **SAFE TO SHIP** ✅

Both fixes verified correct: bypass list covers underscore variants, `_is_ride_it` no longer over-matches `mover+`, all 12 specified test cases pass, no production regression, working tree clean at HEAD. Three WARN findings are latent or pre-existing — none blocks ship.

---

## Check 1: Bypass List Coverage — **PASS**

| Item | Evidence |
|------|----------|
| `'volume-breakout'` present | `hermes_constants.py:1600` ✅ |
| `'volume_breakout'` present | `hermes_constants.py:1601` (the fix, added by 61bec3b8) ✅ |
| Query mechanism | **SQL LIKE, not Python `in`.** `cut_loser.py:66-68` and `profit_monster.py:86-89` both build `AND NOT (signal LIKE %s OR ...)` with params `f"%{s}%"` per bypass entry — substring semantics via `LIKE '%...%'` ✅ |

**Executed LIKE-equivalence tests** (Python containment == `LIKE '%needle%'` for wildcard-free needles; verified against real constants):

| Signal string | Bypassed? | By which entry |
|---|---|---|
| `volume_breakout_long` | ✅ now bypassed | `volume_breakout` (the fix) |
| `volume-breakout-long+` | ✅ (was already) | `volume-breakout` (also `breakout-long`) |
| `volume_breakout` | ✅ now bypassed | `volume_breakout` |
| `rs_s,volume_breakout_long` (combo) | ✅ now bypassed | `volume_breakout` |
| `volume_breakout_short_` | ✅ now bypassed | `volume_breakout` |
| `mover+` / `mover-` / `mover` | ❌ not bypassed | (not in list — pre-existing, see WARN-3) |
| `pump-chain+` | ✅ (pre-existing) | `pump-chain`, `pump-chain+` |
| `bb-squeeze+` | ❌ correct | — |

**Root-cause confirmation (DB):** Trade 15115 SOL, signal `rs_s,volume_breakout_long`, closed `cut-loser-CL-T1` at −5.37% pnl (2026-09-08). Trade 14782 ONDO, same pattern, −4.35%. Before the fix, `LIKE '%volume-breakout%'` (hyphen) could not match these underscore strings — exactly the reported gap. After the fix, `LIKE '%volume_breakout%'` matches (executed). ✅

**Note (INFO-4, latent):** SQL `LIKE` treats `_` as a single-char wildcard, so the new `'%volume_breakout%'` pattern also matches hyphen variants (`volume-breakout-long+`) and any single-char substitution (`volumexbreakout`). Broader than Python substring semantics. DB check for non-family matches: **none exist**. Zero practical impact today.

## Check 2: `_is_ride_it` Logic — **PASS**

Code at `position_manager.py:3301-3305`: tuple is `('ride_it', 'trend-ride', 'trend_ride', 'volume-breakout', 'volume_breakout', 'mover-')` — `'mover'` → `'mover-'` change confirmed in diff. Executed all task-specified cases against the real logic:

| Signal | Result | Expected | Verdict |
|---|---|---|---|
| `trend-ride+` | True | True | ✅ |
| `trend_ride_long` | True | True | ✅ |
| `volume-breakout+` | True | True | ✅ |
| `volume-breakout-long+` | True | True | ✅ |
| `volume_breakout_long` | True | True | ✅ |
| `volume_breakout` | True | True | ✅ |
| `mover-` | True | True | ✅ |
| `mover+` | **False** | False | ✅ (was True pre-fix — over-match fixed) |
| `mover` (bare) | False | False (accepted) | ✅ |
| `rs_s,volume_breakout_long` | True | True | ✅ |
| `pump-chain+` | False | False | ✅ |
| `bb-squeeze+` | False | False | ✅ |

**Bare `mover` realism (DB + code):** `mover.py:41-44` emits only `SOURCE_LONG='mover+'` / `SOURCE_SHORT='mover-'` today. DB: 9 historical trades with bare `'mover'` signal, **last one 2026-09-09** (~1 month stale); last-7d mover trades are exclusively `mover+`. Bare `mover` is legacy, not emitted by current code. **Trade-off is acceptable.**

## Check 3: Cross-check with `_match_exit_config` — **PASS** (with WARNs)

Executed `_match_exit_config` rev-2 logic verbatim (`position_manager.py:2729-2767`) against real `SIGNAL_EXIT_CONFIG`:

| Part | Config | `_is_ride_it` | Consistent? |
|---|---|---|---|
| `trend-ride+` | ride_it | True | ✅ |
| `trend_ride_long` | ride_it | True | ✅ |
| `volume-breakout+` | ride_it | True | ✅ |
| `volume-breakout-long+` | ride_it | True | ✅ |
| `volume_breakout_long` | ride_it (via `volume_breakout`+`_` prefix, line 2754) | True | ✅ |
| `volume_breakout` / `+` / `-` | ride_it | True | ✅ |
| `mover-` | ride_it (exact, config:1667) | True | ✅ |
| `mover+` | **None** (no ride_it match — correctly removed) | False | ✅ |
| `mover` (bare) | ride_it (config:1668) | False | ⚠️ DIVERGENCE (accepted, see below) |
| `mover_long` | ride_it (via `mover`+`_` prefix branch) | False | ⚠️ DIVERGENCE — see WARN-1 |
| `volume-breakout-short-` | **None** | True | ⚠️ DIVERGENCE — pre-existing, see WARN-2 |
| `mover-v2` | ride_it (version-stripped stem) | True | ✅ |
| `pump-chain+` | pump_exit | False | ✅ |
| `rs_s` | rr_engine | False | ✅ |

- `mover-` → ride_it in config ✅ (`SIGNAL_EXIT_CONFIG['mover-']`, hermes_constants.py:1667)
- `mover+` → **no ride_it mapping** ✅ (exact match fails; `mover` key's `_`/`-` prefix branches don't match `mover+`; stem equality fails). Default PM-trail path. Correct per 2026-09-25 decision.
- Bare `mover` gap: **config maps it to ride_it but `_is_ride_it` returns False** → 8h universal hold applies. Not a practical problem — see Impact Assessment below.

## Check 4: Impact Assessment

- **`volume_breakout*` (underscore) that now bypass cut_loser:** managed by **ride_it** — `_match_exit_config` returns `ride_it` for `volume_breakout_long`, `volume_breakout_short_`, bare `volume_breakout`, and the `+`/`-` variants (executed). The `use_ride_it` path at `position_manager.py:2919-2928` keys off exactly this. Fix closes the double-management bug (SOL 15115 class). ✅
  - Exception: hyphen SHORT form `volume-breakout-short-` → config `None` — see WARN-2 (pre-existing, not part of this fix).
- **`mover+`:** now PM trail + universal hold at 8h (480 min, constants:1032). DB exit evidence for recent `mover+` trades: `profit-monster-trail`, `atr_sl_hit`, `hard_max_loss` — all exit well before 8h. One historical `UNIVERSAL_MAX_HOLD` (trade 15623 CFX, closed +7.36%) shows the hold can bind on a winner, but that is the pre-existing design for non-ride_it signals, and it is the correct alignment with the 2026-09-25 decision (mover+ removed from ride_it). ✅
- **Bare `mover`:** config=ride_it but `_is_ride_it`=False → 8h universal hold applies. **Not a problem:** (a) generator no longer emits it; (b) last bare-`mover` trade closed 2026-09-09; (c) historical bare-`mover` trades exited via `profit-monster-trail` anyway (PM manages mover since it is not in the bypass list), so the 8h hold is a non-binding safety net, not an exit path; (d) **0 open positions at verification time** — zero live exposure.

## Check 5: Regression Check — **PASS**

- **Bypass list addition:** DB scan for non-volume-breakout-family signals matching `LIKE '%volume_breakout%'`: **none**. No other signal family is unintentionally exempted from cut_loser/PM trail.
- **`_is_ride_it` change:** only signals containing `mover` but not `mover-` are affected: `mover+` (intended), bare `mover` + stale August combos (`hzscore+,mover` etc. — all legacy, none in last 30d except `mover+`), and `mover_long`/`mover_short` (0 production trades — latent, WARN-1). No other substring members (`ride_it`, `trend-ride`, `trend_ride`, `volume-breakout`, `volume_breakout`) changed behavior.
- **Syntax:** `py_compile` OK on all four files: `hermes_constants.py`, `position_manager.py`, `cut_loser.py`, `profit_monster.py`.
- **Working tree:** clean — committed state at HEAD 61bec3b8 matches working files (no uncommitted drift).
- **Live exposure:** 0 open Hermes positions at verification time.

---

## Issues Found

| # | Severity | Location | Issue |
|---|---|---|---|
| WARN-1 | **MEDIUM (latent)** | `hermes_constants.py:1668` + `position_manager.py:3301-3305` | **`mover_long`/`mover_short` diverge.** `_match_exit_config('mover_long')` → `ride_it` via the `key+'_'` prefix branch (line 2754, matching the legacy bare `mover` key), but `_is_ride_it('mover_long')` → **False** (contains `mover_`, not `mover-`). A ride_it-managed trade would get the 8h universal hold — the same bug class as SOL 15115. **0 production trades today**, but `mover.py:41-42` sets `SIGNAL_TYPE_LONG='mover_long'` and signal_type strings DO land in the trades.signal column inside combos (precedent: trade 15115 = `rs_s,volume_breakout_long`). Suggested fix: add `'mover_long', 'mover_short'` to the `_is_ride_it` tuple, **or** remove the legacy bare `'mover'` key from `SIGNAL_EXIT_CONFIG` (the generator emits only `mover+`/`mover-` — bare key is dead config). |
| WARN-2 | **MEDIUM (pre-existing)** | `position_manager.py:2753-2767` vs `volume_breakout.py:53` | **`volume-breakout-short-` (current SHORT source) manages via nothing.** `_is_ride_it` → True (substring `volume-breakout`), but `_match_exit_config` → `None` (rev-2 deliberately rejects direction-word remainders). Net: bypassed from cut_loser AND PM trail (via bypass list), exempt from universal hold, but `use_ride_it` (line 2922) never fires → **no exit engine at all** except raw ATR SL/TP. Production: 1 trade (`rs-r69,volume-breakout-short-`). Flagged in `brain/verdicts/independent-fixed-ride-it-audit.md` §C — **not introduced by this fix, and not fixed by it either.** Suggested fix: add `'volume-breakout-short-'` (and/or stem) to `SIGNAL_EXIT_CONFIG` → `ride_it`. |
| WARN-3 | **LOW-MED (pre-existing)** | `hermes_constants.py:1563-1606` | **`mover-` still double-managed.** `mover-` maps to ride_it (`SIGNAL_EXIT_CONFIG:1667`) but is **not** in `PROFIT_MONSTER_BYPASS_SIGNALS` — cut_loser and PM trail still race ride_it. DB evidence: trade 15700 CFX `mover-` closed via `profit-monster-trail` while ride_it-managed. Same bug class this commit closed for `volume_breakout*`; `mover-` left exposed (n=12 historical trades). Suggest CEO decision: add `'mover-'` to the bypass list for consistency. |
| INFO-4 | LOW (latent) | `cut_loser.py:68`, `profit_monster.py:89` | SQL `LIKE` `_`-wildcard means `'%volume_breakout%'` matches any single-char variant, not just underscore forms. Zero non-family matches in DB today; normalization would make semantics explicit someday. |
| INFO-5 | INFO | `hermes_constants.py:1668` | Bare `'mover': 'ride_it'` config key is legacy dead config — current `mover.py` never emits bare `mover`. Cleaning it up would also resolve WARN-1's root cause. |

## Bare `mover` Gap Assessment

**Not a problem — accept the trade-off.** Evidence: (1) `mover.py` emits only `mover+`/`mover-` as SOURCE strings today; (2) bare `mover` trades ceased 2026-09-09 (9 historical, all pre-dating the current signal code); (3) those historical trades exited via `profit-monster-trail`, i.e. PM already managed them — the ride_it mapping for bare `mover` was never the operative exit path; (4) 8h universal hold on such a trade would simply be the default safety net; (5) zero open positions at deploy time. The commit message's "acceptable trade-off" claim is supported by data. The residual divergence worth acting on is **WARN-1 (`mover_long`/`mover_short`)**, not bare `mover`.

## Deployment Note

No restart required for this fix to take effect:
- `cut-loser.service` / `profit-monster.service` run as fresh systemd timer processes every ~45–60s (verified firing; next tick in 14s at verification time) — new constants load on next cycle.
- `position_manager` runs as a subprocess via `run_pipeline.py` every minute (`STEPS_EVERY_MIN`) — fresh code each cycle.
- Per AGENTS.md: 0 open trades now; if trades open before the next cycle boundary they would still be managed by pre-fix code only until the next subprocess invocation (≤1 min lag — negligible).

---

**bug_hunter** — independent verification executed against live code + brain DB. All PASS claims backed by executed tests or DB rows cited above.
