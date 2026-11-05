# BRIEF: The capital brake doesn't work — rule a brake that does (2026-11-04, hail-mary follow-up)

## The problem (bug_hunter-verified, findings reproduced)
Your hail-mary verdict recommended "size-reduce 0.5x until first green 24h" as the capital brake.
Execution + verification revealed it CANNOT work as specified:
1. **Auto-clear conflict:** `data/vacation_size_reduce.json` was created (16:34) and the existing
   guardrail BH-SR-1 (`vacation_guardrail.py:364-381`) auto-CLEARED it at 16:42 — its rule
   `(7d WR>=37 AND 7d pnl>=-2) OR 7d pnl>=0` was satisfied (WR 55.1%, pnl −$1.72) while 24h was
   still −$0.27. Documented release ("first green 24h") ≠ actual release. Brake lived 8 min, 0 fills.
2. **Floor no-op (the structural one):** on the LIVE decider path `_get_dynamic_position_size`
   returns base **$11.00 = HL_MIN_NOTIONAL floor** (7% of withdrawable ≈ $157); ×0.5 = $5.50 →
   floored back to $11.00. Even without the auto-clear, the brake would have cut NOTHING live.
   (The brain.py mirror path DOES cut 100→50, but that's not the live HL fill path.)
3. Registry note now corrected to truth (commit 32068627): "no live risk cut in effect."

## Context for the ruling
- Book: 8 straight fee-net red days; 24h −$0.90, 7d −$4.62 (fee column), ~40 fills/day,
  avg trade notional $11-16, avg loss −$0.10, HML −$0.19 (account −4% cut).
  Fees ≈ $0.31-0.43/day are a large share of the bleed — fee bleed scales with COUNT.
- Working levers already live: Cap C (jup 1/6h), gate stack, LONG-bypass block, stop-tighten 0.75,
  amplifier on, size brake (inert). Fold-line framework stands (11-07).
- HL_MIN_NOTIONAL: unknown to us whether this is OUR constant (scripts/hermes_constants.py —
  grep it) or an exchange hard limit. That determines option (b).

## Options to rule (or replace with your own)
| # | Brake | Pros | Cons |
|---|---|---|---|
| a | **Global frequency cap: max N closes/opens per day until first green 24h** (Cap-C-style counter, decider entry check, N≈15) | directly cuts fee bleed (the cost that scales), works at any size, trivially reversible, no floor fight | needs a small code hook + gates (review+bug_hunter); counts must be robust |
| b | **Sub-floor notional exception when size_reduce active** (floor is a OUR constant?) | makes the CEO's original 0.5x actually bite | if floor is an exchange limit this is impossible; $5.50 notional may be below venue min |
| c | **Accept the $11 floor as already-minimal** — declare the brake N/A at this account size; rely on the gate stack + Cap C + 0.5x only on the brain-mirror path | zero new code | no active brake; T asked for one |
| d | **Entry-pause mode until first green 24h** (watchdog-style "no fresh entries" as a flag, not an operational whisper) | strongest preservation, exact T intent | binary; may miss the recovery day entirely; needs flag + gates |
| e | **Guardrail release fix only** (honor an explicit `release: first_green_24h` key before BH-SR-1) + pick (a) or (c) as the actual cut | fixes the honesty gap regardless | alone it doesn't cut anything live |

## Deliverable
One ruling: the brake that ships today (mechanism, exact file/flag/constant, value, release
condition, revert path), the guardrail release-semantics fix (does an explicit release key
override BH-SR-1? — yes/no + where), and whether HL_MIN_NOTIONAL is ours or the venue's
(check the constant's comment/usage before ruling option b). Under standing delegation we
implement immediately with the usual gates (review + bug_hunter). Keep it minimal — T is
counting days to the 11-07 fold line.
