# === INDEPENDENT VERDICT — SHORT KILL INVESTIGATION ===
**Auditor:** independent subagent, fresh read of all code + data (2026-10-11 ~22:20 UTC)
**Scope:** SHORT signals 17:00–22:59 UTC 2026-10-11, pipeline.log, signals_hermes_runtime.db,
continuum.db, PostgreSQL trades, and a live RR-engine reconstruction on historical candles.

---

## Claim 1: "RR-ENGINE grade F killed IO and GRASS SHORTs. The R:R calculator says
## risk > reward during dumps because SL is far and TP is close."

**Verdict: AGREE (mechanism confirmed by reconstruction, with one nuance)**

Evidence (verified myself, not taken on trust):
- pipeline.log 20:45–20:48: `🎯 [RR-ENGINE] IO SHORT: RR HARD BLOCKED: grade=F (score=26.75)` every
  minute; 21:21–21:25: `GRASS SHORT: RR HARD BLOCKED: grade=F (score=25.25)`, then 21:26
  `R:R=0.66 < 0.7 (risk > reward)`. DB: IO 1671532 EXPIRED 20:48, GRASS 1671568 EXPIRED 21:26.
- I re-ran `risk_reward_engine.evaluate_rr` on the actual historical 5m/1h candles:
  - **GRASS SHORT @21:21** price 0.79372, ATR%=3.19 (EXTREME) → **SL=3.19% (full 1×ATR),
    TP=2.00% (hard-capped), R:R=0.63, Score=24.9, Grade F** — reproduces the live score 25.25.
  - **IO SHORT @20:45** ATR%=2.98 (EXTREME) → reconstruction R:R=0.54, hard block
    (live: grade F score 26.75 / later R:R=0.37).
- Root mechanics in `compute_structural_rr` (risk_reward_engine.py:482–585):
  - **SL = 1.0 × ATR with NO upper cap** (`RR_ENGINE_SL_ATR_MULT=1.0`, floor only `ATR_SL_MIN=1.3%`).
    During the dump per-token 1h-ATR14 was **3.0–4.4%** (IO 2.98%, GRASS 3.19%, CFX 4.42%).
  - **TP is hard-capped: 2.0% in HIGH and EXTREME** (`RR_ENGINE_TP_MAX_PCT_HIGH/EXTREME=0.020`).
  - ⇒ **Whenever ATR > 2%, R:R < 1 by construction.** The engine mathematically guarantees
    "risk > reward" during the dump core. Grade F (<35 score) then returns mult=0.0
    (`rr_confidence_multiplier`, risk_reward_engine.py:963).
- Nuance: grade F is not a literal instant kill. mult 0.0 → compactor multiplier product →
  SCORE-FLOOR raises it to 0.3 → decider PENALTY-GATE computes exec_conf = 99 × 0.3 = **29.7% <
  MIN_EXEC_CONFIDENCE 40** → guaranteed PENALTY-BLOCK (this is exactly what killed GOAT/AIXBT).
  GRASS/IO instead aged out as EXPIRED while being gate-blocked every minute.
- Counter-evidence check: IO's second attempt (21:22 signal) PASSED the RR engine at 21:26
  (grade D, mult 0.70, penalty 43.3%) and was then killed by a **different** gate — the
  EXEC-RSI-HARD-FLOOR (see Claim 3). So RR did not kill every IO attempt.

**Confidence: HIGH**

---

## Claim 2: "PUMP-CHAIN-SHORT-HIGH killed HYPER and IOTA."

**Verdict: AGREE as proximate cause — but it was NOT the only gate that would have killed them.**

Evidence:
- pipeline.log: `20:43–20:48 🚫 [PUMP-CHAIN-SHORT-HIGH] IOTA SHORT blocked`,
  `20:45–20:50 … HYPER SHORT blocked — HIGH vol, no pump-chain- SHORT edge (20%WR)`.
  DB: both EXPIRED within ~6 min.
- Gate code (signal_compactor.py:3028–3035): fires when source contains `pump-chain`,
  direction SHORT, and **per-token 1h-ATR regime == 'HIGH'** (1.0–1.5% ATR band;
  `classify_volatility`, volatility_gate.py:308). `PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED=True`
  (hermes_constants.py:2976). There is **no bear-structure exemption** in this gate.
- Volatility regime was per-token ATR (signal_compactor.py:2600), not whole-market.
  IOTA @20:43 ATR%=1.45 → genuinely HIGH. HYPER @20:45 ATR%=1.60 → borderline EXTREME in my
  reconstruction; the live ATR read landed in HIGH — either way it was blocked there.
- Does it block ALL pump-chain SHORTs during dumps? Not all: **EXTREME (>1.5%) passes.**
  It blocks the HIGH transition band — i.e. the *early* dump phase, exactly when pump-chain
  shorts fire. During the dump tokens migrate HIGH→EXTREME quickly.
- Is "20%WR" real data? Partially. The log string is **hardcoded**; code comment says
  "14d: HIGH 5T 20%WR -$0.60, EXTREME 32T 56.3%WR"; the constants comment (newer) says
  "14d HIGH 7T 14.3%WR | NORMAL 7T 71.4%; 30d HIGH 27T 44.4%". Real data, but **n = 5–7
  trades in 14d** — below the system's own "n<5 is noise" standard, and the 30d figure
  (44.4%WR) is much less damning.
- **Would they have survived without this gate? NO.** My reconstruction:
  IOTA SHORT R:R=0.49 → hard block (R:R<0.7); HYPER SHORT score=32.6 → grade F → hard block.
  The RR engine would have killed both one stage later.

**Confidence: HIGH**

---

## Claim 3: "These gates block shorts at the exact moment they should fire — during confirmed dumps."

**Verdict: AGREE — and the strongest killer is a gate the plan does not mention at all.**

Evidence:
- BTC continuum (continuum.db, 1m states) during the dump 21:09–21:35: z-score **STRONG_NEG
  (z=-1.97 → -5.36)**, trend_quality=STRONG_DOWN, linreg=LEAN_BEAR, ema300_position **BELOW**,
  wyckoff=ACCUMULATION, BTC price 83,680 → 83,251. BTC was unambiguously in bear structure.
- The compactor-level bear overrides **did fire** — CONTINUUM-OVERRIDE, BTC-CHOP-OVERRIDE,
  BTC-CRASH-OVERRIDE, SHORT-NEUTRAL-BYPASS, and the pump-chain RSI bear override all passed
  SHORTs through at 21:58–22:17. They work.
- But the final gate has **no bear override**: `EXEC-RSI-HARD-FLOOR` (decider_run.py:1952–1954)
  blocks any SHORT when exec RSI < 45, explicitly "no bearish override".
  **17 unique blocks in 20:00–22:59**, e.g.:
  - IO SHORT 21:26:26 — passed everything, then `RSI 41.9 < 45 … extreme oversold — no bearish
    override` → TRADE FAILED.
  - CFX SHORT 21:08/21:58/21:59/22:17 — `RSI 28.5 / 31.5 / 40.9 < 45` → TRADE FAILED.
  During a confirmed dump (z=-5, STRONG_DOWN), this floor shorts the bounce-logic of a
  *continuation* regime. It is the exact-moment blocker.
- The **decider entered ZERO trades in all 142 runs 20:00–22:59** ("0 entered" every time).
  PostgreSQL confirms: **0 SHORT trades opened 17:00–22:30**; only CAKE LONG +$0.02 (19:56)
  and a BTC continuum LONG (22:08) in the whole window.

**Confidence: HIGH**

---

## Claim 4: "The signals didn't expire because the compactor was slow — they were
## PROCESSED and killed by specific gates."

**Verdict: AGREE**

Evidence:
- 678 gate lines for the 9 named tokens between 20:30–21:29 alone; every token was processed
  **every ~60s** with explicit PASS/BLOCK lines right up to its expiry. No latency gap anywhere.
- DB "EXPIRED: no refire for 5min" is bookkeeping: the signal lived 5 minutes, was gate-blocked
  every minute, and aged out. IO 20:42→EXPIRED 20:48 (RR grade F every minute), GRASS
  21:20→EXPIRED 21:26 (RR grade F/R:R<0.7 every minute), HYPER/IOTA (PUMP-CHAIN-SHORT-HIGH
  every minute), XPL (CONFLUENCE-GATE-BLOCK "single-type not in standalone bypass
  (regime=SHORT_BIAS)" every minute 20:48–20:53).

**Confidence: HIGH**

---

## ROOT CAUSE (what is actually preventing SHORTs during dumps)

Five layers, all verified in code + logs + data. The plan names only layers 1–2:

1. **RR-engine structural asymmetry.** SL = 1× ATR uncapped (3–4.4% in the dump) vs TP
   hard-capped at 2.0% (HIGH/EXTREME) ⇒ R:R < 1 whenever ATR > 2% ⇒ grade F ⇒ mult 0.0.
   This is an artifact of the engine's own SL/TP construction, not of market structure.
   (IO, GRASS, CFX 20:36, and reconstruction of HYPER/IOTA too.)
2. **Confidence-product trap.** Compactor SCORE-FLOOR 0.3 × conf 99 = 29.7% exec_conf, which is
   **always** below MIN_EXEC_CONFIDENCE=40. Any signal whose multiplier product lands < 0.404
   can *never* execute. The 0.3 floor is illusory — it rescues nothing. This is how RR grade F
   converts into a de-facto hard kill for GOAT (29.7%), AIXBT (29.7%), CC (39.6% — a grade-B
   R:R=6.92 setup blocked 0.4 points below threshold!), BIGTIME, CHIP, ARB, KAS.
3. **EXEC-RSI-HARD-FLOOR (RSI<45, no bear override)** at decider execution time — 17 blocks
   during the dump, killing signals that passed every earlier gate. THE single biggest
   exec-time killer, absent from the plan's claims.
4. **PUMP-CHAIN-SHORT-HIGH** (no bear exemption, n=5–7 data) — proximate killer of IOTA/HYPER,
   though RR would have caught them next. Also blocks only the HIGH band; EXTREME passes.
5. **Execution infrastructure failure — not in any claim:** after all gates passed (22:14–22:40,
   ~16 events, NEO/CFX/PONS), `brain.py` failed rc=1:
   **`mirror_open FAILED: Balance too low ($5.50 < $11.0)`** — the Hyperliquid account could not
   fund the minimum position. Even a perfect SHORT signal could not have opened.

Additional verified defects (sideways finds):
- **`mark_signal_executed` runs BEFORE the trade opens.** 18 DB rows show decision=EXECUTED for
  SHORTs that never opened ("TRADE FAILED — signal NOT rolled back (prevents retry loop)").
  The DB is lying to analysts — my own first-pass query was misled by this until I read the logs.
  Should record EXEC_FAILED.
- Bear overrides exist and fire (CONTINUUM/BTC-CRASH/BTC-CHOP/NEUTRAL-BYPASS + pump-chain RSI
  bear override) but are wired ONLY into confluence/chop/crash gates — **not** into RR grade F,
  PUMP-CHAIN-SHORT-HIGH, PENALTY-BLOCK, or EXEC-RSI-HARD-FLOOR. That is why "bear overrides
  didn't fire" appears true: they did fire, then a downstream gate with no override killed it.
- Log label bug: `🚨 [BTC-CRASH] IO SHORT BLOCKED — WARNING — BTC_LEVEL` at 21:26:26 says
  BLOCKED but is warn-only (processing continued to EXEC). Misleading for log forensics.
- Stale comment: signal_compactor.py:3027 "14d: HIGH 5T 20%WR" and the hardcoded "20%WR" log
  string disagree with the newer constants comment (7T 14.3% / 30d 44.4%).

## What the RR-ENGINE is actually calculating for these SHORTs / is grade F justified?

It computes: SL = entry ± max(1×ATR, 1.3%), optionally tightened to just beyond the nearest
strong resistance (CFX: ATR 4.42% but SL tightened to 1.77% past a level); TP = min(2×ATR, 2.0%)
or nearest S/R support within the cap; R:R = TP/SL. Score = R:R×12.5 (max 50) + liquidity (0–25,
empty clusters give a flat ~12) + S/R clarity (0–25). < 35 ⇒ grade F.
**The grade F is self-consistent but not market-justified**: the SL it grades against is an
engine fiction (the actual executor uses its own ATR SL + trailing — EXEC lines show
"SL=ATR TP=ATR", RR SL/TP are never placed), and the TP cap guarantees R:R<1 in any ATR>2%
regime. It grades dump-time shorts down for being dump-time shorts.

## RECOMMENDED FIX (specific, actionable)

1. **RR engine TP/SL symmetry (kills root cause 1):** scale TP with volatility — replace the
   hard cap with `TP_MAX = max(0.020, RR_ENGINE_TP_ATR_MULT × ATR × 0.8)` for HIGH/EXTREME, or
   cap the SL used in the R:R ratio at e.g. 2.0% (mirror of the TP cap). Re-validate on the 30d
   SHORT book before enabling (RR_ENGINE_CONF_SHADOW=False is live — this is a live killer).
2. **Reconcile the confidence floor (root cause 2):** SCORE-FLOOR 0.3 can never clear
   MIN_EXEC_CONFIDENCE 40 (needs ≥0.404 at conf 99). Either floor the product at 0.41 or exempt
   grade-≥C conf≥90 signals from the penalty product. Today "floor to 0.3" = death sentence.
3. **EXEC-RSI-HARD-FLOOR bear exemption (root cause 3):** reuse the exact bear-structure test
   the RSI *ceiling* already uses (decider_run.py:1985: linreg LEAN_BEAR/BEAR AND phase
   DECLINING/STORMY AND ema BELOW) to allow SHORT below RSI 45 during confirmed bear structure
   (or lower the floor to 30 when BTC zscore_tier == STRONG_NEG). Keep the floor in neutral/bull.
4. **PUMP-CHAIN-SHORT-HIGH bear exemption (root cause 4):** skip the block when BTC continuum
   is STRONG_DOWN/STRONG_NEG (same test as above); re-collect the sample — n=5–7 trades is
   below the repo's own evidence standard. Fix the stale "20%WR" log string/comment.
5. **Execution layer (root cause 5):** investigate/fund the balance (`$5.50 < $11.0` minimum)
   — 16 SHORT entries died here after passing every gate. Also roll the signal BACK on
   TRADE FAILED so the failure is visible as EXEC_FAILED, not a false "EXECUTED" row.
6. Do NOT blanket-exempt everything during dumps — layers 1–4 with one shared bear-structure
   predicate fixes the trap without reopening the RSI<25 catastrophe band (keep a low hard
   floor, e.g. 30, for true capitulation wicks).

**Net verdict on the overall story: the four claims are substantially correct (AGREE on 1, 2, 4;
AGREE-strong on 3) but incomplete — they miss the PENALTY-BLOCK/0.3-floor trap (biggest volume
killer: GOAT/CC/AIXBT/CHIP/…), the EXEC-RSI-HARD-FLOOR (biggest exec-time killer), and the
"Balance too low" execution failure (killed even the shorts that passed everything). Zero
SHORT trades were opened during the entire 17:00–22:30 dump — the system was multi-layered
locked, not merely "gated at RR".**
