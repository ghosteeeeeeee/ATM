# CONSULT RUN 20261014T185131Z (UTC)

You are running a BOUNDED, READ-ONLY consult. Base persona/rules follow after this block.

## HARD LIMITS (this run)
- **BUDGET: ~3 minutes. Do not exceed a few file/DB reads.**
- **READ-ONLY. Do NOT edit ANY file. Do NOT change params, flags, or blacklists.**
- Do NOT develop signals. Do NOT tune signals. Do NOT dispatch subagents.
- Do NOT write to ceo_report.md or ceo_kanban.md — answer HERE, in this session.
- No session lock is held. If you believe an edit is needed, say so as a recommendation and stop.

## THE QUESTION
Answer the directed brief below. Verify any numbers you cite with a quick query (base prompt SQL rules apply — never trust old reports). Give a clear VERDICT (approve/reject/modify + rationale). If the brief asks for a review, lead with the verdict, then the reasons.

--- BRIEF ---
# CONSULT — T is going on vacation: what to do now, and what folds into the vacation plan

## Situation
T is going on vacation. Duration is TBD — please give a plan that works for both a
long weekend and ~2 weeks, and state your assumption. The question:
(1) What should we do NOW, before T leaves?
(2) What can be folded into the vacation plan (autonomous work that is safe and
valuable while T is away)?

OPINION ONLY — no edits, no subagents. T is waiting on this before departing.

## Current live state (verified this session)
SHIPPED and live (each verified by bug_hunter or CEO consult before merge):
- BUG-052: FAILED signal terminal state (executed=1, decision=FAILED) — false-EXECUTED
  rows fixed; 20 remediated.
- Vol-gate v1/v2 sync (commit 48c0c4f2 + comment fixes): warrior-sr-confirm resolves
  TRADE in all four regimes; ATOM SHORT case resolved; deliberate kills untouched.
- MAXXED tier (commits 2b6c85ca etc): additive, classify_volatility unchanged.
  NOTE: threshold was RECALIBRATED 4.0->6.0 today (hermes_constants.py:760) because
  BLUR blocked every cycle at 4.0 (ATR 5.99-6.04) — the recalibration treadmill has
  already begun, on one threshold, this week.

## Pending queue (approved but NOT shipped)
1. DRIFT ALARM — you (CEO, consult 20261013T153452Z) called this the MINIMUM VIABLE
   CHANGE: alert when EXTREME/MAXXED share of the live universe leaves its historical
   band. Zero enforcement risk, read-only. Evidence: brain/vol-regime-multiyear-audit-
   2026-10-13.md (BTC EXTREME+ 55.5% of hours 2017 -> 1.8% 2026; SOL 40.3% vs BTC
   12.4% of time EXTREME — thresholds encode asset baseline, not conditions).
   Plan: plans/vol-regime-relative-thresholds-2026-10-13.md. BOTH DOCS UNCOMMITTED.
2. RELATIVE REGIME shadow mode — you approved the shape (per-asset percentile regimes
   + absolute MAXXED tail) gated on: >=7d shadow (zero enforcement), full diff of
   every (signal,regime,direction) whose block status flips with ZERO unexplained
   ADDS-trade, own-conclusions out-of-sample verification (bands 2017-2022, validate
   2023-2026), signal_regime_memory.json migration story, then T+CEO sign-off to flip
   behind VOL_REGIME_MODE flag.
3. PROBLEM B (deny-by-default vol-gate redesign) — separate, unstarted, own gating
   conditions (FAMILY_MAP gap-fill, shadow, own-conclusions, T sign-off).
4. Small cleanups flagged by bug_hunter: dead allowlist entries in v2 (trend_purity+,
   pump-catcher+, bb-bounce-short — inert, ENABLED=False); tl-bounce+ NORMAL question;
   compactor inlined ATR calc (drift risk vs get_atr_pct).

## Context you should assume
- LIVE_TRADING_ENABLED=True. Per AGENTS.md, hermes_constants.py values must not change
  without T. The pipeline reloads fresh every minute (no restart needed for script edits).
- While T is away, nobody is available for live sign-offs. The system trades autonomously.

## THE QUESTIONS FOR YOU
1. PRE-VACATION (do now, while T is present): what MUST happen before T leaves vs what
   can wait? Specifically: (a) should the drift alarm ship BEFORE vacation as shadow-only
   or full? (b) should the pending docs be committed now? (c) is there any live-trading
   risk that needs a T-present decision first (e.g. the 7d PnL position, open items you
   are tracking)?
2. VACATION PLAN: what autonomous work folds in safely? Rank: drift alarm, relative-regime
   shadow mode, own-conclusions verification, Problem B, cleanups. Shadow modes and
   analysis are zero-enforcement by design — is starting the relative-regime shadow while
   T is away safe, or does even shadow logging touch live paths?
3. GUARDRAILS: define the safe autonomous envelope while T is away — what is explicitly
   ALLOWED (analysis, shadow, bugfixes?) and what is FROZEN (any constants change? any
   enforcement flip? signal enable/disable?). Should we set a freeze flag (e.g. the session
   lock or a dedicated VACATION_MODE) so no runner edits live trading config?
4. WATCH: what should the hourly/4h automations specifically watch while T is away, and
   what thresholds should trigger a hold rather than an action (e.g. 7d PnL floor,
   hard_max_loss rate)? If something goes wrong at 3am with no human, what is the
   autonomous stop posture you recommend?

Answer with your opinion and reasoning. No edits.
--- END BRIEF ---

## OUTPUT
Print your answer to this session (stdout). Do NOT append to any report file. Max ~400 words unless the brief demands more detail.
