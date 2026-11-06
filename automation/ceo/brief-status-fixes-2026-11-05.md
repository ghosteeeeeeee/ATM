# BRIEF: T — "Are the fixes working? Full analysis and report" (2026-11-05, ceo-comm long timeout)

## T's questions (answer ALL, verbatim intent)
1. Are the fixes working? Has anything improved?
2. Are we taking more shorts (actually following the market momentum)?
3. Are we profitable? If not, why not.
4. Is the winrate any better?
5. What new insights from the shadow data?
→ "Full analysis and report."

## Pre-seeded fresh numbers (parent-verified 2026-11-05 15:03Z — trust, spot-check only)
**Verifier (goal-704ed65e): 1/7 PASS — first PASS ever:**
- ✅ **net 24h = +$0.17 (6T) — FIRST GREEN 24h** (but only 6 closes in 24h!)
- ❌ jup rolling-50 **64% → 44%** (target <35% — improving)
- ❌ HML 7d 37 / −$5.22 (target <15) — note: window still includes pre-0.75-enforce days (enforce landed 11-04 03:50)
- ❌ net 72h −$2.19 (91T)
- ❌ ratio 48h **5.0:1 (40L:8S)** — WORSE than 2.4:1, but tiny sample under throttle
- ❌ non-jup fleet WR 52.2% (270T, target ≥55%)
- Book: 7d net −$4.87 · 30d net −$14.46 · WR last-200 = **52.5%**
**Direction split:** 24h = 4 LONG (−0.16) / 2 SHORT (+0.33 — both won); 7d = 212L (−4.59) / 59S (−0.28).
**Flow collapse note:** ~40 fills/day → **6 closes in last 24h**. Fill cap (15/day while red) + gates + Cap C. Is the cap binding or did signal flow dry up? Answer this precisely — it decides whether we're protected or just idle.

## Timeline of fixes (for "are they working")
- 11-03: SHORT_RSI_CEILING 65→75 live; 3 bear-structure shadows shipped (log-only).
- 11-04 03:50: stop-tighten **0.75 ENFORCE** (HML = 46% of 30d losses) · Cap C jup 1/6h · LONG-bypass block in SHORT_BIAS · amplifier bb-squeeze/warrior · ichimoku LONG bypass killed · 2 dead trials killed · **DAILY_FILL_CAP 15 brake (17:51, self-releasing on first green)** · guardrail release-key.
- 11-04: first-ever green 24h today (+$0.17) — n=6, is it real or throttle artifact?
- Fold line still scheduled **11-07 00:00Z** (cumulative 11-04→11-07 fee-net < −$1.50 AND verifier ≤1/7 → shadow-only recommendation). Verifier now 1/7 — if it stays ≤1/7 the second limb holds; the first limb: cum fee-net since 11-04 needs computing (seed: 11-04 −0.29? use fee column).

## Shadow-data insights inventory (what's new since 11-03 — mine these, don't re-derive old ones)
- `[BEAR-SINGLE-SOURCE-SHADOW]`: pre-read 11-04 → n=3 token-days (22 lines, 7.3× replication), WR limb 100%, net +$0.022 — NOT-YET, deadline moved 11-17; rate 1.5/day → n=20 ~11-16.
- `[SHORT-REGIME-EXEMPT-SHADOW]` (A1): 181 lines and counting — needs its first join read (bar 11-17).
- `[FLIP1-OVERRIDE-SHADOW]`: 26 lines — waiver expired, shadow accumulating for a re-arm ruling (11-17).
- `[FADE-CRASH-POSTFLIP-SHADOW]`: wired 11-04 17:01, 0 lines yet (episodic fades ~4-6/day), read 11-06.
- Storm: packet **#2 was cf −$2.96 NEGATIVE (streak reset 1/3)** — but 11-05 tape is violent; check for packet #3+ and [STORM-READINESS] lines today.
- volgate/maxxed shadows: **0 lines ever** (11-17 bar) — collector reachability question still open.
- Contrarian: EXTEND to 11-11 (32 fills, gross +$0.13, fee-net −$0.205 — fee-structural).
- jup-trail: FAIL (trail own-effect −$0.056/40) — keep shadow; the shipped MFE-giveback is THE exit improvement.
- gate_shadow fwd corpus now 66k+ events; token-day convention in force; watch for what today's throttle did to block counts.
- BUG-078 (Z-FLIP vacuous) open — fix before the 11-11 contrarian read means anything.

## What to deliver
1. **Verdict per question** (fixes/shorts/profit/WR/shadow insights) with numbers.
2. **Attribution:** which of the 11-03/11-04 fixes show measurable effect (ceiling: 65-75 band fills? stop-tighten: HML trend post-03:50 11-04? Cap C: jup share 64→44 ✓? brake: fills/day + first green? LONG-bypass: SHORT_BIAS long fills −50%? amplifier: bb-squeeze/warrior share?), and which show nothing yet (too early vs broken — say which, with the diagnostic).
3. **The flow question:** why 6 fills/24h — cap binding? signal birth collapse (which gate)? weekend tape? This determines "protected vs idle".
4. **Profit path:** is +$0.17 a real turn or n=6 noise? What does the model say the next 48h look like given the stack? Restate the 11-07 fold-line inputs with fresh numbers (cum fee-net since 11-04).
5. **Shadow insights** worth acting on NOW vs at their deadlines (rank).
6. Any NEW findings from today's shadow lines that change a standing ruling.
Constraints: net-of-fees everywhere, token-day dedup for fwd means, no blanket kills, protected flags untouched, flag-polarity rules. Read-only — recommendations only.
