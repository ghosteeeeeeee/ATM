# Stage A/C Shadow-Bypass Re-Readout — 2026-10-30

**Date:** 2026-10-30 16:20 UTC
**Executor:** daily_orchestrator (merged upgrade-implementer)
**Data:** `brain/shadow_trades.db`, decision='SHADOW_BYPASS', 17,810 rows through 2026-10-30 16:10 UTC
**Purpose:** Prior readout (2026-10-22, `stage-ac-shadow-readout-2026-10-22.md`) recommended "re-run in 7d when rs-s-broken/bb-squeeze- half2 resolves and sqx- degradation trend clarifies." That re-run is this document. Analysis only — no flags touched, no config changes.

---

## TLDR — STAGE A/C CLOSED, NO RE-TEST NEEDED

**The Oct 21-22 shadow SHORT "winners" do NOT replicate on 8 fresh days of data.** When the original cohort fully resolved, the winners held (sqx- 76.1% WR +$115 sum net, rs-s-broken 80.8% +41.4, bb-squeeze- 77.0% +15.6) — but the **fresh Oct 22→30 cohort is net-NEGATIVE for all three** (sqx- 62.8% WR **−336.4** sum, rs-s-broken 56.7% **−216.5**, bb-squeeze- 49.7% **−22.7**). Root cause: inverted R:R (sqx- wins +0.41% avg vs losses −0.98% avg = 0.42:1; breakeven WR at that R:R is 70.4%, observed 62.8%). The Oct 21-22 window was a favorable-volatility regime blip, not a durable edge. **The original disable theses are re-validated on fresh data. No throttled pilot, no flag flips, no further Stage A/C work.** LONG losers (sqx+, doji, vol-breakout+) stay confirmed losers on both windows.

---

## 1. Original Oct 21-22 Cohort — Fully Resolved (was 66% closed at Oct 22)

| Key | fired | closed | WR (was) | WR (now) | avg net | sum net (was → now) |
|-----|------:|-------:|---------:|---------:|--------:|---------------------|
| sqx- (squeeze_cross SHORT) | 694 | **694** | 73.4% | **76.1%** | +0.179 | +74.2 → **+115.0** |
| rs-s-broken (support_res SHORT) | 200 | **198** | 82.9% | **80.8%** | +0.225 | +16.6 → **+41.4** |
| bb-squeeze- (bollinger_squeeze_short) | 87 | **87** | 69.6% | **77.0%** | +0.193 | +5.0 → **+15.6** |
| sqx+ (squeeze_cross LONG) | 146 | 146 | 32.1% | 30.1% | −0.524 | −48.4 → −70.7 |
| doji-bottom-long | 62 | 62 | 31.5% | 35.5% | −0.492 | −28.9 → −30.5 |
| volume-breakout-long+ | 17 | 17 | 14.3% | 11.8% | −0.742 | −9.8 → −12.6 |

The half2 "degradation" that worried the Oct 22 readout was partly a resolution artifact: the unclosed half2 trades closed POSITIVELY. Half-split on the fully-resolved cohort:

| Key | half1 WR / avg | half2 WR / avg | Verdict |
|-----|----------------|----------------|---------|
| sqx- | 81.6% / +0.284 | 70.6% / +0.078 | still degrades but both halves net-positive |
| rs-s-broken | 81.6% / +0.145 | 80.0% / +0.308 | **stable — half2 resolved clean** |
| bb-squeeze- | 72.7% / +0.192 | 81.4% / +0.193 | **stable — half2 resolved clean, no degradation** |

On the original cohort alone, the picture looked like "edge holds, pilot worth designing." The fresh cohort killed that reading.

## 2. Fresh Cohort Oct 22 16:22 → Oct 30 16:10 (~8 days) — THE DECISIVE TEST

| Key | fired | closed | WR | avg net | sum net | fires/hr |
|-----|------:|-------:|-----:|--------:|--------:|---------:|
| sqx- | 6,983 | 6,905 | 62.8% | **−0.052** | **−336.4** | 36.4 |
| sqx+ | 5,164 | 4,998 | 55.2% | −0.160 | −735.9 | 26.9 |
| rs-s-broken | 2,428 | 2,412 | 56.7% | **−0.101** | **−216.5** | 12.7 |
| bb-squeeze- | 162 | 161 | 49.7% | **−0.151** | **−22.7** | 0.8 |
| doji-bottom-long | 271 | 261 | 60.2% | −0.179 | −46.6 | 1.4 |
| volume-breakout-long+ | 882 | 852 | 36.4% | +0.004 | +3.5 | 4.7 |

All three former "winners" flipped net-negative. sqx- sum net went from +115 (40h) to −336 (8d). bb-squeeze- fire rate collapsed 6.4→0.8/hr (detector/market change — moot, negative anyway).

### 2.1 Root cause — inverted R:R, not fees, not a data bug

sqx- fresh cohort, win/loss magnitude split:

| side | n | avg net% | sum net% |
|------|--:|---------:|---------:|
| win | 4,311 | +0.4085 | +1,761.1 |
| loss | 2,594 | −0.9824 | −2,097.5 |

Losses are **2.4x** wins. Breakeven WR at 0.42:1 R:R = 70.4%; observed 62.8% → net negative. This is the same inverted-R:R signature that got bb-squeeze+ flagged live. Fees are the standard 0.04%+0.10% model, identical to the Oct 22 window — not a fee artifact.

### 2.2 Daily sign check (sqx-, when did it flip?)

| date | n | WR | avg net |
|------|--:|-----:|--------:|
| 10-22 | 1,173 | 67.9% | +0.044 |
| 10-23 | 691 | 63.2% | −0.034 |
| 10-24 | 882 | 57.7% | −0.050 |
| 10-25 | 975 | 69.7% | +0.067 |
| 10-26 | 866 | 65.8% | −0.021 |
| 10-27 | 880 | 52.4% | −0.284 |
| 10-28 | 734 | 61.4% | −0.151 |
| 10-29 | 1,051 | 72.8% | +0.178 |
| 10-30 | 347 | 56.5% | −0.251 |

Mixed sign day-to-day with negative drift. No stable edge; the Oct 21-22 positive window is visible as the starting point before mean-reversion took over.

### 2.3 Verification (THE-PATTERN checklist)

- **Reproducibility:** re-ran the fresh sqx- aggregate — identical (6,905 / −0.0522 / −336.4). ✅
- **Significance:** n=6,905, SE of mean net ≈ 0.012 → t ≈ −4.3, p < 0.001. The negative edge is real, not noise. ✅
- **Selection-on-outcome:** none — both windows are fixed time ranges over ALL shadow_bypass trades for each source, not outcome-filtered. ✅
- **Survivorship:** all closed trades counted (win + loss sides). ✅
- **Time anchor:** recorded_at (signal creation), same field both windows. ✅
- **Sample sizes:** 6,905 / 2,412 / 161 — all above bar. ✅

## 3. Verdicts

| Key | Oct 22 verdict | Oct 30 verdict | Action |
|-----|----------------|----------------|--------|
| sqx- | fresh-evidence re-test candidate | **edge REFUTED on fresh data** (inverted R:R) | none — stays disabled; kill the throttled-pilot idea |
| rs-s-broken | re-test candidate pending half2 | half2 resolved stable BUT fresh 8d **net −216.5** | none — stays disabled |
| bb-squeeze- | re-test candidate, thin | fresh 8d **net −22.7**, fire rate collapsed | none — stays disabled |
| sqx+ / doji / vol-breakout+ | confirmed losers | re-confirmed losers (both windows negative) | none — kills stand |

**Stage A/C is closed.** The 2026-10-22 recommendation #2 ("throttled re-test design for sqx- if CEO wants it") is **withdrawn** — the data that would justify a pilot no longer exists. The disable theses from Jul-Aug were measured on a different exit stack, but under TODAY's exits + TODAY's market they are correct decisions. No open questions remain in this thread.

## 4. Sideways findings

- **Severity: INFO** — sqx- fire rate 36-45/hr is unchanged and remains operationally absurd. Any future shadow winner with this profile should be auto-flagged for throttle-design before any pilot discussion, not after.
- **Severity: INFO** — `data/shadow_trades.db` is a 0-byte stale artifact (last touch Oct 27 10:45). The live DB is `brain/shadow_trades.db` (110MB). Worth deleting the 0-byte path to prevent future confusion — not done here (out of scope for an analysis run).
