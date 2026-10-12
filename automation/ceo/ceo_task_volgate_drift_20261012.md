# DIRECTED DECISION REQUEST — Volatility-gate v1/v2 allowlist drift (T-raised)

Work THIS brief — it replaces the default "pick your own items" scope. Answer with
verified numbers, checkpoint the decision, then dispatch edits as needed.

## The trigger (T's exact case)
Log line:
  `🚫 [CTX-GATE] ATOM SHORT blocked: volatility gate v2: storm: ATR=1.5474% > 1.5% (signal not suited)`
  `warrior-sr-confirm- is not in the EXTREME regime list.`
T's question: "what about situations like this where we basically have to re-train
the regimes so trades can actually fire?"

## What I already verified (sanity-check, don't re-derive from scratch)
1. CTX-GATE calls `should_trade_v2` (decider_run.py:1692 -> volatility_gate_v2.py:744).
2. `should_trade_v2` is DENY-BY-DEFAULT: `works_in_regime=False` (v2:767); the signal's
   literal name must be in `REGIME_SIGNALS[regime]` or it is SKIPped. NO family fallback
   in the live path (signal_family imported but not used for this gate).
3. TWO parallel REGIME_SIGNALS allowlists: volatility_gate.py:31 (v1) and
   volatility_gate_v2.py:45 (v2). They have DRIFTED.
4. `warrior-sr-confirm` IS in v1's EXTREME allowlist (volatility_gate.py:257, "works in
   extreme vol") but NEVER in v2's. Signal ENABLED=True. `git log -S warrior-sr-confirm`
   on volatility_gate_v2.py is EMPTY = never added. Genuine oversight, not a kill.
5. DRIFT magnitude (v1-allowed but MISSING from v2, normalized):
     FLAT 14, NORMAL 28, HIGH 33, EXTREME 25.
6. CRITICAL CORRECTION — the drift is NOT uniformly "valid trades suppressed." Split by
   hermes_constants enable-flag, the ENABLED (truly wrongly-blocked) counts are:
     FLAT 6, NORMAL 8, HIGH 8, EXTREME 8 — the rest are deliberate ENABLE=False kills
     (accel-300-v2/v3/v4, bb-bounce-v3, open-skies, atr-spike, sma20-dip, trend-ignition,
     trend_purity, pump-catcher, breakout-long, ema300-dip — each killed for negative
     expectancy). Those must STAY blocked; Fix A does not resurrect them because the
     ENABLE=False flag is checked independently upstream.
     EXTREME enabled-but-blocked set: accel-300, bb-bounce-short, breakout-pullback,
     pullback-entry, r2-trend-short, resistance-break, rs, warrior-sr-confirm.
7. 288 "not suited"/"storm: ATR" lines in pipeline.log — CTX-GATE is actively suppressing.
8. MAXXED tier (ATR>=4.0) was deployed TODAY by T (commits 2b6c85ca etc) as an ADDITIVE
   block on top; classify_volatility unchanged. UNRELATED to this drift — do NOT disturb it.

## The two tangled problems (keep SEPARATE in your decision)
- PROBLEM A (bug, safe): v1/v2 allowlist drift. ~6-8 ENABLED signals/regime wrongly
  suppressed (incl. warrior in all 4 regimes). Fix restores signals already curated as
  tradeable in v1. Low risk, pure correctness.
- PROBLEM B (design defect, risky): deny-by-default hand-curated allowlist with no family
  fallback = the "re-train the regimes" treadmill T is worried about. Every new signal
  needs manual allowlist edits across regimes or it can't trade when a gate runs.

## THE DECISION I NEED FROM YOU
1. PROBLEM A: Approve the sync fix? Preferred shape — make v2 the single source of truth
   and have it FALL BACK to v1's allowlist on a miss (so v1's curated intent, e.g. "warrior
   works in extreme vol", takes effect). Or copy missing entries into v2 explicitly?
   Recommend one, with rollback.
2. PROBLEM B: Approve evolving the gate to DEFAULT-ALLOW + family BLOCKLIST (keyed on
   existing FAMILY_MAP / signal_family() in market_phase_gate.py) so new signals inherit
   family behavior and never need re-training? This INVERTS the safety default (today
   unregistered=fails-safe-blocked; proposed=trades unless family blocked). If yes, it MUST
   pass own-conclusions independent verification before going live (AGENTS.md). Give gating
   conditions and who verifies.
3. Sequencing: ship A now, B as a separate verified project? Or together?
4. Metrics to prove suppressed valid trades resume WITHOUT admitting losers: 7d PnL,
   per-signal WR of revived signals, CTX-GATE block rate.

Lead with the decisions. State explicitly whether you agree the ATOM block is a bug vs a
correct kill. Note: T is actively waiting on this decision.
