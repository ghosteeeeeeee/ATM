# CONSULT RECORD — CEO consult `20261108T180116Z` — "the payoff fix" (2026-11-08)

**Verdict (as executed): APPROVE scope-widen + combo-substring fix + CAP-0.50 shadow; no amplifier revert.**
Standing delegation = CEO label = go. Brief: `automation/ceo/brief-payoff-fix-2026-11-08.md`.
This file is the on-disk authorization record for the live, money-adjacent constant edit
below (registry `amplify-stoptighten-scope-widen.default_action` requires a CEO record for
any `STOP_TIGHTEN_SOURCES` tuple edit).

## What was shipped (CHANGE-NOW, live, with revert)

| # | Change | File:line (post-ship) | Revert |
|---|---|---|---|
| 1 | Scope-widen: `STOP_TIGHTEN_SOURCES` 2 → 8 names, verdict order (`pump-chain+`, `pump-chain-`, `bb-squeeze+`, `volume-breakout-long+`, `bb-bounce-v2-long+`, `r2v2-long3`), each verified against PG `SELECT DISTINCT signal` | `scripts/hermes_constants.py:761` | remove the 6 appended entries |
| 2 | Combo-signal scope bug: exact match → substring membership (`any(name and name in (source or '') ...)`) | `scripts/tpsl_utils.py:1138` | restore `source not in STOP_TIGHTEN_SOURCES` |
| 3 | No amplifier revert (verdict Q3) — no code change; noted in registry `amplify-bbsqueeze-warrior-uninert.notes` | — | — |
| 4 | CAP-0.50 counterfactual SHADOW: log-only `[STOP-TIGHTEN-CAP050-SHADOW]` line when `ENFORCE=True` and `0.50 < dist <= cap`, loss-side only, own hour-dedup, double-guarded, never changes the returned SL | `scripts/tpsl_utils.py:1157+`, flag `scripts/hermes_constants.py:776` | `STOP_TIGHTEN_CAP050_SHADOW = False` (shadow-only either way; the actual 0.75→0.50 flip happens only at the bar, with a CEO label) |
| 5 | Registry dispositions (`data/shadow_disposition.json`): scope-widen → done; CAP050 bar appended to `stop-tighten-enforce-eval` (deadline stays 2026-11-14); 3 NEW entries `stop-tighten-slippage-column` (build, 11-14), `win-side-capture-shadow` (shadow, 11-15), `hml-vol-atr-mult-shadow` (shadow, 11-18) | `data/shadow_disposition.json` | per-entry |

**Code commit:** `6740b6fb3f1409f6615b5ad9df8c5537ce35a3ae` (registry commit follows this file).

## Gates actually run (all real, 2026-11-08)

- `python3 brain/analysis/stop_tighten_scope_cf_2026-11-08.py` → **ALL BARS PASS**
  (n=55→56 drift, ceiling +$1.13→+$1.14/14d, net +$0.88→+$0.89/14d, fk 3.9%, 5/5 weeks same-sign);
  `--selfcheck` → `SELFCheck PASS`.
- `python3 brain/analysis/payoff_fix_probes_2026-11-08.py` → **48/48 PASS** (scope substring,
  5 false-positive/negative cases, exact in-scope clamp, ENFORCE=False identity, CAP050 window
  + dedup + revert flag, constants diff = tuple + comment + 1 flag, `CEO_PROTECTED_FLAGS`
  byte-identical).
- `py_compile` all changed files · `stale_comment_linter.py --strict` clean ·
  `shadow_disposition.py --selfcheck` SELFCHECK PASS · `tpsl_utils` import probe OK.
- **Adversarial code review → `VERDICT: APPROVE-WITH-FIXES`** (4 MUST-FIX / 4 SHOULD-FIX — all
  applied: guardian restarted, comments corrected to state what actually passed, CAP050 bar
  registered in the registry, this consult record written; SHOULD-FIX items documented in the
  registry rather than code-changed where noted).
- **bug_hunter → `VERDICT: PASS-WITH-FIXES`** (1 MUST-FIX = guardian restart, done 19:16:49Z;
  4 SHOULD-FIX documented: pm-site-only CAP050 reachability, pump-chain v5/v6 substring
  over-match, registry stale text, pre-existing log-raise clamp-drop at HEAD).

## Caveats carried into the registry (do not lose them)

1. **Candle-walk not run this session.** The bars that PASS are the walk script's *ceiling math*
   over ALL out-of-scope stop-family trades — the population the verdict adjudicated. The
   threshold's 1m/5m candle-walk limb (i) is still owed before **2026-11-21**.
2. **Covered-population limb.** Restricted to what the change actually covers (new 6 + jup
   combos: n=31, ceiling $0.62, fk 3.0%) the net is **$0.88/30d pace vs the +$1.00/30d bar**
   (full out-of-scope population = $1.88/30d pace, PASS). If the candle-walk or a re-read fails
   there → REVERT = drop the 6 appended entries.
3. **Substring over-match:** `pump-chain-v5/v6+/v6-` match via the literal `pump-chain-`
   (19 trades/90d, 5/30d, 0 open) — same family, priced into the fk/ceiling bars; token-exact
   alternative documented in the registry entry.
4. **CAP050 site coverage:** reachable mainly from `pm_collect_atr` (guardian/scw pre-gate on
   `dist>cap`; decider places ≥1.00%). Bar feed proxy 93 distinct in-scope trades/14d ≫ n≥30.

## 48h log proofs T should see

```bash
grep -a 'STOP-TIGHTEN-CAP050-SHADOW' logs/pipeline.log | head          # first CAP050 line (expect site=pm_collect_atr)
grep -a 'STOP-TIGHTEN-SHADOW' logs/pipeline.log | grep -E 'src=[^ ]*,'  # first combo-source clamp line
grep -a 'STOP-TIGHTEN-ENFORCE' logs/pipeline.log | tail -5              # new-scope clamps (day-0: id=16826 bb-squeeze+ 18:37:35Z)
grep -ac 'helper error\|hook error' logs/pipeline.log                   # must stay 0
ps -eo pid,lstart,cmd | grep hl-sync-guardian                           # must show start > 2026-11-08 18:25Z (restarted 19:16:49Z)
```
