# Stage A/C Shadow-Bypass Readout — 2026-10-22

**Date:** 2026-10-22 16:30 UTC
**Executor:** upgrade_implementer
**Data:** `brain/shadow_trades.db`, decision='SHADOW_BYPASS', window 2026-10-21 00:22 → 2026-10-22 16:22 UTC (~40h)
**Purpose:** Prior upgrade session (2026-10-22 04:32) set next-candidate #1 = "Stage A/C shadow readout once n≥15 per key". Thresholds now met for 6 of 10 registry keys. Analysis only — no flags touched, no code changed.

---

## TLDR

**3 disabled SHORT signals show broad positive shadow edge that contradicts their original disable theses** (sqx- WR 73.4% n=575, rs-s-broken WR 82.9% n=105, bb-squeeze- WR 69.6% n=56 — all fee-adjusted net positive, token-spread, CI95 excludes 50%). **3 disabled LONG signals are confirmed losers** (sqx+, doji, volume-breakout-long+ — both half-splits negative, CIs include or sit below 50%). **4 registry keys have zero fires** (detector/module issues or genuinely quiet). No re-enables recommended today: vacation freeze in force, fire rates are operationally absurd (6–45 fires/hour), and all three winners DEGRADE in the more recent half-split. Forward path = throttled live re-test design for CEO, not flag flips.

---

## 1. Cohort Summary (all registry keys, shadow_bypass only)

| Key | Stage | Direction | n fired | closed | unclosed | WR | CI95 | avg net%/trade | sum net% | fires/hr |
|-----|-------|-----------|--------:|-------:|---------:|-----:|------|---------------:|---------:|---------:|
| sqx- (squeeze_cross) | C | SHORT | 694 | 575 | 119 | **73.4%** | [69.6, 76.8] | +0.141 | **+74.2** | **44.8** |
| rs-s-broken (support_resistance) | C | SHORT | 200 | 105 | 95 | **82.9%** | [74.5, 88.9] | +0.164 | +16.6 | **12.5** |
| sqx+ (squeeze_cross) | C | LONG | 146 | 109 | 37 | 32.1% | [24.1, 41.4] | −0.489 | −48.4 | 9.4 |
| bb-squeeze- (bollinger_squeeze_short) | A | SHORT | 87 | 56 | 31 | **69.6%** | [56.7, 80.1] | +0.101 | +5.0 | 6.4 |
| doji-bottom-long | A | LONG | 62 | 54 | 8 | 31.5% | [20.7, 44.7] | −0.535 | −28.9 | 4.3 |
| volume-breakout-long+ | A | LONG | 17 | 14 | 3 | 14.3% | [4.0, 39.9] | −0.700 | −9.8 | 1.5 |
| rs-s120 / rs-s32 / rs-s124 / rs-s126 (pollution, pre-HIGH-5-fix) | C | LONG | 8 | 8 | 0 | 0.0% | — | −0.800 | −6.4 | — |
| rs-r31 | C | SHORT | 1 | 0 | 1 | — | — | — | — | — |
| hmacd_mtf-+ | A | — | **0** | — | — | — | — | — | — | — |
| bb-bounce-v3-long | A | — | **0** | — | — | — | — | — | — | — |
| open-skies+ | C | — | **0** | — | — | — | — | — | — | — |

Exit engine: shadow first_exit (ATR trail primary; trail_sl 595, hard_max_loss 243 of 838 resolved). Fees/slippage modeled (0.04% + 0.10%). Net% already fee-adjusted.

## 2. The Three SHORT Winners — Detail

### 2.1 Half-split stability (recorded_at median split) — ALL THREE DEGRADE

| Key | half | n | closed | WR | avg exit% |
|-----|------|--:|-------:|-----:|----------:|
| sqx- | 1 (older) | 347 | 347 | **81.6%** | +0.424 |
| sqx- | 2 (newer) | 347 | 228 | **61.0%** | +0.068 |
| rs-s-broken | 1 | 100 | 98 | 81.6% | +0.285 |
| rs-s-broken | 2 | 100 | 7 | 100.0% | +0.560 | ← n=7 closed; 93 still open — half2 uninformative
| bb-squeeze- | 1 | 44 | 44 | 72.7% | +0.332 |
| bb-squeeze- | 2 | 43 | 12 | 58.3% | −0.048 | ← n=12 closed — thin

**sqx- degradation is the headline risk:** 81.6%→61.0% WR and +0.424%→+0.068% avg across ~20h. Could be regime shift within the window, could be edge decay. Either way, the full-window 73.4% overstates the current-state edge.

### 2.2 Token concentration — PASS (broad, not single-token)

- **sqx-**: 80+ tokens, top = SYRUP 18/694 = **2.6%**. No token >3%.
- **rs-s-broken**: 45+ tokens, top = GMT 18/200 = 9.0%.
- **bb-squeeze-**: 55+ tokens, max 4 fires/token.

Contrast with pair-anatomy findings (hmacd+pump-chain = 55% CHIP). These three are NOT token artifacts.

### 2.3 Original disable thesis vs shadow evidence

| Key | Original disable | Shadow now | Contradiction? |
|-----|------------------|------------|----------------|
| sqx- | 2026-08-02: "40% on SHORT — no edge" | 73.4% WR, +74.2% sum net | **YES — strong** |
| rs-s-broken | 2026-07-21: "broken support SHORT = 26.5% WR (53/200), massive drag" | 82.9% WR, +16.6% sum net | **YES — strong** |
| bb-squeeze- | "66.9%WR research but −$1.16/7d live; keep off until SHORT R:R fixed" | 69.6% WR (research-like), net +5.0% | **Partial** — WR matches research; shadow net now positive, but thin (+0.101%/trade) and half2 negative |

**Honest interpretation of the contradiction:** the disable theses were measured on the JUL–AUG live stack (different exit engines, different HML threshold, different RR engine, different market regime). Shadow uses today's first_exit engine on today's market. This does NOT prove "the disable was wrong" — it proves "under current exits + current regime, these detectors produce positive- expectancy paper trades." The correct framing for CEO: **fresh-evidence re-test candidates**, not vindications.

### 2.4 Fire-rate problem (operational blocker)

| Key | fires/hr | fires/day | Implied concurrent positions (55min hold) |
|-----|---------:|----------:|-------------------------------------------:|
| sqx- | 44.8 | ~1,075 | ~41 |
| rs-s-broken | 12.5 | ~300 | ~11 |
| bb-squeeze- | 6.4 | ~154 | ~6 |

Even at HL minimum notional (~$11), sqx- alone would need ~$450 concurrent and ~1,075 orders/day (fees alone ~$4.7/day at 0.04%×2×$11×1075... actually far more with slippage). **A naive flag flip is operationally impossible.** Any live re-test requires: per-token+direction cooldown (e.g. 1 fire / 30min / token), global concurrency cap (≤3), and a daily trade cap. Design work, not a flag.

## 3. The Three LONG Losers — Confirmed Stay-Disabled

| Key | n | closed | WR | CI95 | half1 WR | half2 WR | sum net% | Disable thesis validated? |
|-----|--:|-------:|-----:|------|----------|----------|---------:|--------------------------|
| sqx+ | 146 | 109 | 32.1% | [24.1, 41.4] | 34.2% | 27.8% | −48.4 | ✅ "0% WR on LONG" (2026-07-28) — direction confirmed, magnitude softer |
| doji-bottom-long | 62 | 54 | 31.5% | [20.7, 44.7] | 25.8% | 39.1% | −28.9 | ✅ RE-KILLED 2026-10-16 stands; shadow worse than the 45.5% live cohort |
| volume-breakout-long+ | 17 | 14 | 14.3% | [4.0, 39.9] | 11.1% | 20.0% | −9.8 | ✅ KILLED 2026-10-13 stands; "regime issue not signal issue" still falsified |

**Action: none. Disable flags stay False. These three now have independent shadow confirmation — the kill decisions are no longer dependent on small live cohorts alone.**

## 4. Zero-Fire Keys (sideways findings)

| Key | Module exists? | Likely cause |
|-----|----------------|--------------|
| hmacd_mtf-+ | yes (signals/mtf_macd.py) | HMACD_MTF_PLUS_ENABLED was killed Oct 13 on n=8; detector may also simply not have fired in 40h, or z-score thresholds never crossed. Not a runner bug per se — needs one dry-run check. |
| bb-bounce-v3-long | yes (signals/bb_bounce_v3_long.py) | Killed Oct 10 on 14d 19T. Zero fires in 40h = detector quiet or conditions rare. |
| open-skies+ | yes (signals/open_skies.py) | CEO-killed 2026-09-22. Zero fires. |

**Severity: LOW.** Zero fires ≠ runner failure (runners logs showed recorded/skipped/errors counters working post-HIGH-5 fix). Recommend a single `--dry-run` + forced-import check next session; not done here to keep this readout pure-analysis.

**Note:** the 8 rs-s120/s32/s124/s126 LONG rows (all −0.800%) are the pre-HIGH-5-fix pollution the prior session already identified — self-contained, exclude `source LIKE 'rs-s%'` broken-short cohort analyses or delete on next touch. Not double-counted above.

## 5. Caveats (read before acting)

1. **Shadow exit stack ≠ live exit stack.** first_exit engine only (ATR trail primary). Live has 10 engines, trailing-arm timing, RR-engine pre-exit, cell-stats multipliers, penalty gate. Realized WR/PnL will differ.
2. **40h window, one regime.** Oct 21–22 was choppy/bearish. SHORT-favoring. The same detectors in a bull week may bleed. No seasonal claim can be made.
3. **Half-split degradation on both measurable winners** (sqx-, bb-squeeze-). The most recent half is materially weaker. Re-testing "now" tests the weaker half.
4. **Unclosed share is high** (119/694 sqx-, 95/200 rs-s-broken, 31/87 bb-squeeze-) — last several hours unresolved; final numbers will move.
5. **Vacation mode freeze** (data/vacation_mode.json): no signal enable/disable without CEO. This readout is analysis, not authorization.
6. **AGENTS.md THE PATTERN:** numbers above are reproducible from the SQL in §1–2 (deterministic, single DB). No p-hacking — the three winners' CI95 all exclude 50% on n≥56 closed; the three losers' CIs sit at/below 50%. Half-splits reported whether favorable or not.

## 6. Recommendations (for CEO — none taken)

1. **Do NOT flip any ENABLED flag today.** Vacation freeze + fire-rate blocker + half2 degradation.
2. **If CEO wants a re-test:** design a throttled shadow-to-live pilot for the best of the three (rank: rs-s-broken > sqx- > bb-squeeze- by avg-net×stability, but rs-s-broken half2 is n=7 — actually rank sqx- first on closed-n, then bb-squeeze-, then rs-s-broken pending more closes). Requirements: per-token cooldown, concurrency cap ≤3, daily cap, 7d or n≥50 whichever later, pre-registered revert (net WR <55% or sum net <0 → kill).
3. **LONG losers:** no action; kills now have independent shadow backing.
4. **Zero-fire keys:** one dry-run diagnostic next session (LOW).
5. **Re-run this readout in 7d** — half2 of rs-s-broken/bb-squeeze- will have resolved; sqx- degradation trend will be clearer.

---

*Queries used: see automation/upgrade_audit.md session 2026-10-22 16:30 UTC. DB: brain/shadow_trades.db (11,372 rows total, 1,215 SHADOW_BYPASS).*
