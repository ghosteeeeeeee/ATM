# Current State — brain_auditor Run #33 Oct 20 04:40 UTC

**Last Updated: 2026-10-20 04:40 UTC**
**Updated by: brain_auditor #33 — 1 infra ship (coin_regime stamp, zero-behavior), 0 live filters (vacation)**

## PIPELINE STATUS

- **Trading LIVE** with size-reduce **0.5x** (marker 04:27; 7d WR 34.5% < 35 AND pnl −$3.39 < −$2). Auto-clears when WR≥35 AND pnl≥−$2, or WR≥37 AND pnl≥0.
- **24h 16T 5W −$0.58 (31.3%). | 7d 194T 67W −$3.39 (34.5%). | Trail ~$5.5 vs Chop ~−$7.9 — separation unchanged.**
- **2 open: BTC LONG #16293 ai-trader-pending +0.15% (1.4h, explicit SL/TP) HOLD | BLUR LONG #16295 pump-chain+ −0.56% (0.5h, watchdog fade warning — trail needs +0.40%) HOLD.**
- **Vacation mode ACTIVE** — shadow-first, no constants changes.
- Protected flags 13/13 INTACT.

## THIS RUN — brain_auditor #33

**1 infra ship. 0 live filters.**

**SHIPPED: coin_regime + coin_regime_conf stamp** (decider_run.py:5000-5006) — reads `_hotset_regime` (already in scope at exec time), writes into `_exec_meta` alongside gap_at_entry/staleness/final_confidence. Zero-behavior. Unlocks the watchdog's core thesis ("coin regime at entry is the discriminator") for SQL analysis once 20+ stamped trades accumulate. Metadata previously had btc_regime only — per-token regime died at decision time.

**KEY FINDINGS:**
1. **GOAT SHORT RSI 73.6 = bear-exemption working, NOT a gate bug.** 14d SHORT detect-RSI 65-75 band: n=5 W=2 +$0.09 wash. ETC +$0.14 / LTC +$0.11 won same band. CEO Fix5 design correct. n≪20, no action.
2. **Watchdog's 5 pending oversold shorts (RSI 21-33) ALREADY BLOCKED** by SHORT_RSI_HARD_FLOOR=45 at both detect and exec time. They won't fill.
3. **gap_at_entry 1.0+ LONG = only profitable gap band** (14d 45T +$2.21 42.2% vs <0.5% 126T −$3.32 37.3%). ARB's 3 losses (gap 1.1-1.5) sit in the profitable band on aggregate — ARB-specific toxicity, not gap toxicity. **Do NOT tighten chase filters.**
4. **ARB 3x LONG losses verified:** all mid-band RSI 51-59, conf≤49.5 floor-admits, gap 1.1-1.5% — known cohorts, no new pattern.

**TAT STATUS: 11 unique fires since Oct 18** (base 7 true-saves / 3 false-kills; variant-C underwater-only 6S/0FK corrected). 4 more unique fires for the 15-fire flip bar. MFE-CUT: 6 unique fires.

**LAST-RUN VERIFY:** trailing_activated COMMENT ✓ | size-reduce 0.5x ✓ | TAT + MFE-CUT shadows collecting ✓ | ARM-BE dormant ✓ | protected 13/13 ✓.

**CEO ESCALATION CARRIED: exit-ladder signal-scoped backtest P0 (13th request).**

## PREVIOUS — brain_auditor #32 (03:42 UTC, abridged)
0 config (vacation). atr_sl recovery probe: 63% wrong-side / 37% tight-SL. TAT variant-C CORRECTED 6S/0FK not 9S/0FK.
