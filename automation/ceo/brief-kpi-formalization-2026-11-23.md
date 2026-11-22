# BRIEF: T — "do we have any KPIs? let's formalize those" (2026-11-23)

## T's words (verbatim intent)
"Do we have any KPIs? **Let's formalize those.**"
→ Not "make new numbers" — he wants the scattered targets consolidated into ONE formal,
owned, visible KPI framework. Deliver: the formal KPI set + where it lives + who reports it.

## Current KPI surfaces (inventory — verify/extend yourself)
1. **`brain/analysis/goal_metrics_check.py`** (just restructured 2026-11-22 with T approval):
   10 lines — jup share<35% · HML 7d count<15 + net>−$2.00 · net 24h≥0 · net 72h≥0 ·
   fill ratio LONG:SHORT<2:1 · **net $/trade 7d>0 (baseline −0.0124)** · **fleet payoff 14d≥1.2
   (baseline ~1.05)** · **cost % RT 14d ≤0.15% (baseline ~0.22→measured 0.102)** · WR=info-only.
   Latest run: 5/10 PASS (jup 12%, HML 10/−1.05, net72h +0.41, cost 0.102%; FAIL: net24h −0.02,
   ratio 2.1, net/trade −0.0087, payoff 0.73).
2. **The philosophy anchor (T-approved):** "Every trade should be a winner — in expectancy:
   net-of-cost positive per trade is the only win that counts; hit rate is a diagnostic."
3. **Fold framework (standing):** fold = cum fee-net since 11-04 < −$1.50 AND verifier ≤1/7 →
   shadow-only recommendation. (Now overlaps the new metrics — reconcile.)
4. **Control tower** (`control_tower.json`, `/control_tower.html`): registry counts, overdue,
   fill_cap, lookahead — operational, not performance.
5. **auto_1hr KPI line** (prompt rewritten 11-20): net + payoff + close-reasons + arm-rate.
6. **Per-study bars** (registry 142 entries): each shadow's ship bar — the study-level KPIs
   (e.g. fell-out<10/d, approvals≥8/d, capture 0.57→0.70, Fisher p<0.05…).
7. **Arm-rate** (never-armed hole): armed 83.9% WR vs unarmed 11.3% — the MoE called it 88% of
   the 7d gap; currently a proof-line in auto_1hr, not a gated KPI.
8. **Equity/risk:** $15.51 equity, 30d DD −$11.82 (−76%!) — NO drawdown KPI exists anywhere.

## What the CEO must deliver
1. **The formal KPI framework, tiered:**
   - **North-star (1–3):** the number(s) T judges the system on — presumably net $/trade or
     equity-curve based; justify against "we want net positive".
   - **Health (the goal_metrics_check set):** which of the current 10 stay, which merge, which
     get dropped; the fold-framework reconciliation (is fold now redundant? keep both?);
     targets/baselines locked with dates.
   - **Operational (watch-not-goal):** arm-rate, approvals/day, fell-out/day, brake state,
     fill lag, compaction deaths — decide which become PRODUCTION dashboard lines (control
     tower section vs auto_1hr vs kanban alerts).
   - **Risk:** drawdown/equity KPI — the −76% 30d DD is currently unmeasured as a goal.
     Propose one (e.g. equity floor, max-DD% over rolling window, kill-switch tier).
2. **One reporting surface:** where the formal KPIs live (extend goal_metrics_check? control
   tower section? both?) and the cadence (per-run verifier vs daily packet vs kanban alert on
   breach). No new infra if an existing surface covers it.
3. **Alerting rule:** which KPI breaches produce a kanban/ceo_report line vs passively display.
4. **Deliver:** the framework table (tier, KPI, definition, baseline, target, cadence, surface,
   owner), what changes in code (minimal), what T sees and where, and the first formal KPI
   report run against today's numbers.
Constraints: builds on the T-approved 2026-11-22 restructure (don't relitigate), no new metrics
without a baseline+target+owner, protected flags, speed mandate; read-only consult — framework
+ minimal change list only.
