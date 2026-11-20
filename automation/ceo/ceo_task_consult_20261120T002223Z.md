# CONSULT RUN 20261120T002223Z (UTC)

You are running a BOUNDED, READ-ONLY consult. Base persona/rules follow after this block.

## HARD LIMITS (this run)
- **BUDGET: ~45 minutes (extended consult: CEO_CONSULT_BUDGET=2700s). This is a DEEP consult — work the question thoroughly: read the relevant code (cite file:line) and run the SQL you need to verify every number you cite. Still READ-ONLY — recommend, do not edit. Depth welcome; the ~400-word soft cap below does not apply when the brief demands a detailed answer.**
- **READ-ONLY. Do NOT edit ANY file. Do NOT change params, flags, or blacklists.**
- Do NOT develop signals. Do NOT tune signals. Do NOT dispatch subagents.
- Do NOT write to ceo_report.md or ceo_kanban.md — answer HERE, in this session.
- No session lock is held. If you believe an edit is needed, say so as a recommendation and stop.

## THE QUESTION
Answer the directed brief below. Verify any numbers you cite with a quick query (base prompt SQL rules apply — never trust old reports). Give a clear VERDICT (approve/reject/modify + rationale). If the brief asks for a review, lead with the verdict, then the reasons.

--- BRIEF ---
# BRIEF: T forwards the MoE winrate/profitability panel — "get on it asap" (2026-11-20)

## T's instruction (verbatim intent)
"Share this MoE run with the CEO… **tell it to get on it asap.**"
→ A full 6/6 MoE panel just ran on the exact standing question (improve winrate &
profitability). T wants the CEO to consume it, rule on its phased plan, and START EXECUTING
immediately — not file it.

## The panel (read it in full yourself — it is the primary input)
**`skills/mixture-of-experts/moe-log/2026-11-19-winrate-profitability-panel.md`** (212 lines,
2026-11-19 23:50 UTC, 6/6 experts independent, weighted confidence 0.82). Summary to verify
against your own reads — DO NOT trust this compression:

**One-line diagnosis (all 6 agree):** "Not an exit problem, not a sizing problem — an
ENTRY-QUALITY problem measured wrong: expectancy **−$0.0181/trade net of fees (p=2.9e-5,
n=648)**, payoff 0.71, and the largest hole (never-armed: 53/108 trades, 11.3% WR, 88% of
the 7d net gap) is an execution-state bug, not a strategy."

**Key verified claims (spot-check each):**
- Baseline: 30d 649T WR51.9% gross −$4.80 fees $6.96 **net −$11.76**; equity $15.51 →
  **−76% 30d drawdown**. Breakeven: WR ≥65% (fees) or ≥73% (fees+slip) at payoff 0.71.
- **Dashboards label gross as net** (Risk flag) — every downstream decision inherits it.
- Never-armed 53T 11.3% −$4.10 vs armed 56T 83.9% +$4.43 (7d) — the single biggest hole.
- `hard_max_loss` 76T 0%WR net −$10.36 = **88% of 30d net bleed**; stop-family trades never
  went favorable (MFE0.246 vs MAE0.698).
- Two proven losers STILL FILLING despite disable flags: `hl_copy_trader` (p=0.017, through
  bypass while HL_COPY_TRADING_ENABLED=False) · `ai-trader-pending` (p=0.013, while
  AI_TRADER_ENABLED=False) — either flags don't cover the paths or the read is wrong; verify.
- Losing shadows not yet promoted: pump_chain_v6 n=3437 @34.2%, linreg_fade_short n=1239 @36.2%.
- **Dissent (Regime Analyst, n in thousands + OOS):** counter-regime BEATS aligned everywhere —
  any "strengthen regime matching" proposal CUTS winners. **Dissent (Statistician):** ride_it
  survives Bonferroni on atr_trend only (p=3.9e-9); reverses sign on full book (n=38,349,
  p=0.0009) — do not generalize. **Risk+Statistician jointly reject the "notional cap" thesis**
  (notional = linear multiplier; the $0.08/day premise traced a mislabeled avg-WIN column).
- Code Architect: 1 MED→HIGH (preserve-upsert re-insert = double-open path,
  signal_compactor.py:5944-5965); ride_it phase-1 can WIDEN stops and bypasses stop-tighten.
- Shadow power census: only 6 of 28 open studies powered (n≥30); 4 JSONL files have zero pnl.

**The panel's phased recommendation:**
- **Phase 0 (Day 1, no trading impact):** recompute every KPI net-of-fee with CI + payoff
  ratio (dashboards say "net" but show gross); fix the $0.08/day premise wherever cited.
- **Phase 1 (Days 1–3, highest certainty):** ① close the never-armed hole (53/108 = 88% of
  the 7d gap; verify queued arm-tripwire/prearm-BE lands — the 11-21 batch) ② kill the
  preserve-upsert re-insert (double-open path) ③ prune the two proven losers from bypass.
- **Phase 2 (Week 1, shadow-validated first):** ① entry filter on the stop family
  (174T 0%WR MFE0.246 — halving = +$10–13/30d, "the only lever that moves the sign")
  ② gate mid-band LONGs (rsi_exec 55–70 n=128 −$3.21; gap 0.5–1% n=88 −$2.29)
  ③ re-validate entry filters at EXEC time (RSI drift median 6.1pts, 23/86 >10pts)
  ④ audit CTX-GATE LONG rules (currently blocking above-baseline winners).
- **Phase 3 (Week 1–2):** extend stop-tighten beyond 53% coverage (out-of-scope stop-family
  n=54 −$5.59/14d) · halt promotion of losing shadows (PUMP_CHAIN_V6_ENABLED=False; hold
  linreg_fade until its 11-27 study).
- **Explicitly NOT:** sizing changes, regime-matching, ride_it rollout, new entry signals.

## What the CEO must deliver (T's "asap")
1. **Ratify/modify the phased plan** — each phase as a dated, owner'd execution list
   (which items are subagent builds, which are registry bars, which are T-only calls).
   Note collisions with ALREADY-shipped work (stop-tighten scope-widen 11-08, prearm-BE
   11-21 batch, win-capture collector verified, floor30/hl-copy/hotset-pin shadows,
   cap stack) — integrate, don't duplicate.
2. **Verify the panel's two oddest claims first** (they imply live bugs): (a) hl_copy fills
   through a supposedly-False flag, (b) ai-trader-pending same; (c) dashboards label gross
   as net (trades.html/API). If true, they're Phase-0/1 items — immediate.
3. **Phase-0 measurement fix** — decide the canonical net-of-fee KPI path (report field,
   dashboard, guardrail consumers) and who patches it today.
4. **The stop-family entry filter (Phase 2 item 1)** — the panel's only sign-moving lever:
   specify the exact filter (fields, thresholds) + its shadow bar + deadline; nothing ships
   live without it.
5. **State what T should see in 48h** as proof Phase 0-1 are actually running.
Constraints: no blanket kills, protected flags, net-of-fees + CI + payoff everywhere,
token-day dedup, flag polarity, speed mandate, fold framework intact. Read-only — rulings
and execution lists only.
--- END BRIEF ---

## OUTPUT
Print your answer to this session (stdout). Do NOT append to any report file. Max ~400 words unless the brief demands more detail.
