# CONSULT: Still short-starved — signals exist, BTC falling like a rock, no trades

**Budget ~30 min; print your full answer by ~minute 22 — delivered beats perfect.
Every number re-queried by you; file:line for every code claim. Same format as the
2026-10-22 UNCLOG LIST: verdict first, then a ranked list with explicit
CEO-APPROVED-TO-FLIP / KEEP-SHADOWING / KILL labels.**

## T's question (verbatim, 2026-10-24 ~15:40 UTC)

> "why we're still short starved, btc has been falling like a rock, we're getting
> signals, but we not taking any trades"

T's dashboard row (the signal he's staring at):

| Coins | Dir | Conf | Entries | Sources | Price | RSI | MACD | Z | Rounds | Survival | Speed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BTC | SHORT | 88.0% | 1x | continuum-trend- | $79,474.50 | 51.3 | +33.28 | -0.696 | r1+ | 0.5 | 11% |

## Verified grounding (re-verify; correct me plainly where wrong)

**Market:** BTC 1h 81,676 (Oct 23 10:00) → 79,540 (Oct 24 15:00), latest hour
**-0.83%** (80,214 → 79,540). Falling all session.

**The unclog DID work (post-flip fills, PostgreSQL brain):**
- Since 10-22 12:00: **30 trades** — SHORT **4 (10-22) / 13 (10-23) / 3 (10-24 so far)**
  = 20 shorts, **+$0.74**; LONG 10, −$0.23. ~10 shorts/day vs the pre-unclog 1 per 6h.
- So the question is the MARGIN: why 0 shorts during today's dump hours.

**The BTC signal's exact fate chain (signals table + pipeline.log, verified):**
1. 11:11, 12:13, 13:13, 14:14 — created, sat PENDING, **EXPIRED `compaction_stale_10min`** ×4
   (it never got approved/hotsetted for 4 hours while BTC bled).
2. 15:14 — `🚫 [EXEC-BLOCK] BTC SHORT NOT in hot-set — bypass attempt blocked`
3. 15:36/15:37 — `🗑️ [LOSERS] BTC SHORT: confidence penalty -50 → 0%` →
   `🗑️ [LOSERS-BLOCK] BLOCKED — confidence 0% < 50%` — **raw 88% → ~50% (penalties)
   → LOSERS −50 → 0%**. **BTC is on the `LOSERS` list (verified: 'BTC' in LOSERS = True,
   LOSERS_SHORT = False)** — a presumably LONG-earned losers penalty applied to its SHORT.
4. 15:38+ — `SKIP: BTC SHORT in hotset failure cooldown — 2 failures, 3541s left`
   (~58 min lockout mid-dump — **the two "failures" appear to be the LOSERS-BLOCK/SKIP
   refusals themselves** — verify: do quality-SKIPs feed `_record_hotset_failure`?).
5. 15:39 — `🚨 [BTC-CRASH] BTC SHORT BLOCKED — WARNING — BTC_LEVEL` — the crash gate
   blocks SHORTing BTC *during the crash* (note at decider:3053 says crash blocks don't
   count as failures).

**Other active short-killers since the unclog (signals.decision_reason since 10-22 16:00):**
- `SHORT mid-band death band: 53.5 / 53.1 / 45.2 in 45-55` ×3 at EXEC (midband blocks
  non-pump-chain SHORTs at RSI 45-55; T's BTC row itself sits at RSI 51.3 = inside it)
- `RSI hard floor (detect): 39.0 / 39.9 < 45` and `RSI hard floor: 40.9 / 40.3 < 45` and
  CTX-GATE `LIVE RSI 44.4 < 45` — [35,45) blocks **while BTC continuum right now is
  RECOVERY/BEAR/BELOW age 13s → bear exemption SHOULD be armed**. Either linreg was
  non-BEAR at those moments (check timestamps vs continuum history) or an exemption bug —
  determine which, with numbers (per-day census: ✅ ...-BEAR lines vs [35,45) blocks).
- `RSI knife floor (detect): 28.6 / 28.3 / 20.0 < 35` ×3 — CORRECT (knife, keep).
- 1175 SHORT EXPIRED (compaction_stale_10min) since deploy.

## Questions

1. **LOSERS list vs direction:** where did BTC's LOSERS entry come from (which trades,
   when), is it stale, and should a LOSERS penalty ever apply to the OPPOSITE direction?
   (`LOSERS_LONG`/`LOSERS_SHORT` exist — is the direction-agnostic `LOSERS` set a bug or
   intent?) Give the fix + evidence.
2. **Failure-cooldown poisoning:** trace the 2 recorded BTC SHORT failures — if
   LOSERS-BLOCK / quality SKIPs count as hotset failures, then any refusal locks the
   token+direction for ~1h mid-move. Is that the design? If not, fix (only genuine
   execution failures should count).
3. **BTC-CRASH gate vs doctrine:** which level/threshold fired (`BTC_LEVEL` WARNING),
   how often today, and does blocking SHORTs during a crash contradict "every dump is a
   SHORT opportunity"? Verdict: gate, keep, or invert.
4. **SHORT-MIDBAND 45-55:** it was on the 10-22 "don't touch" list (14d 9T 0W −$0.89).
   Re-examine with post-unclog data (20 new shorts) — is it now the top exec killer? If
   the band is still 0-win, keep; if the new data flipped it, say so with n/WR/PnL.
5. **Bear-exemption effectiveness (unclog after-action):** per-day counts of
   ✅ approval/CTX/EXEC-bear lines vs [35,45) blocks with NO exemption; if blocks with no
   exemption cluster when linreg was non-BEAR, the gate works as designed (report the
   cadence — how many hours/day is BTC linreg actually LEAN_BEAR/BEAR?). If exempted
   signals then died at later gates (LOSERS/midband/cooldown), the floors are no longer
   the binding constraint — name what IS.
6. **The 4-hour compaction expiry:** why did a live PENDING BTC SHORT never reach
   approval 11:11→14:14? (hotset empty? approval criteria? decider not looping?) — the
   signal in T's table only became actionable at 15:14, by which point it hit the wall
   above. If signals routinely expire before reaching EXEC, the unclog's gates don't
   matter — find the plumbing gap.
7. **Anything else** in today's SHORT block census that belongs on the list.

## Deliverable

Ranked **UNCLOG-2 list**: each item = gate, file:line, exact change, shadow/log evidence
(n/WR/blocks-per-day), and label **CEO-APPROVED-TO-FLIP** (implement immediately — T's
2026-10-24 message is the fresh directive; the 10-22 waiver in vacation_mode.json expired
00:00 today, so state replacement waiver wording + which rules it covers) / **KEEP** (with
threshold) / **KILL**. End with expected effect: fills/24h and shorts-per-dump-hour.
What NOT to touch stays the 10-22 list (protected flags, RSI ceiling, knife<35).

## Guardrails

- READ-ONLY; you label, we implement after.
- No blanket regime/time kills — route via regime/vol gates; no constants changes outside
  an explicitly waived scope.
- Distinguish clearly: gate bugs vs gate-working-as-designed vs plumbing gaps.
- If unclog-1 already fixed the problem and today's starvation is a NEW layer, say that
  first — don't re-approve stale items.
