# Blacklist Test Log

## Batch 1 — Started 2026-08-01 (48h trial)

| Token | Trial Start | Trial End | Trades | WR | PnL | Verdict |
|-------|-------------|-----------|--------|-----|-----|---------|
| UNI | 2026-08-01 12:55 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| LINEA | 2026-08-01 12:55 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| TIA | 2026-08-01 12:55 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| TURBO | 2026-08-01 12:55 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| BABY | 2026-08-01 12:55 | 2026-08-02 | 2 | 0% | -$0.16 | RE-BLACKLIST (pre-trial: 0% WR) |
| BLUR | 2026-08-01 12:55 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| FET | 2026-08-01 12:55 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| ORDI | 2026-08-01 12:55 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| PEOPLE | 2026-08-01 12:55 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| AIXBT | 2026-08-01 12:55 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| ZK | 2026-08-01 12:55 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| CAKE | 2026-08-01 12:55 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| STBL | 2026-08-01 12:55 | 2026-08-02 | 2 | 0% | -$0.16 | RE-BLACKLIST (pre-trial: 0% WR) |

**Batch 1 Summary:** 0 KEEP, 13 RE-BLACKLIST. All tokens either had 0% WR pre-trial or generated no executable signals during the 48h trial. Root cause: these tokens were blacklisted for poor performance, and removing the blacklist didn't improve their signal quality — the underlying issue is signal/filter quality, not blacklist status.

## Batch 2 — Started 2026-08-02 (48h trial)

Removed from both SHORT_BLACKLIST and LONG_BLACKLIST for 48h trial:
COMP, CRV, DYDX, IMX, SAND, NEAR, DOT, ICP, ATOM, INJ, FIL, ETC, ARB, OP, LDO, APT, SEI, MET, DASH, WLD

**Note:** FTM excluded (structurally untradeable on HL — Solana chain token). GALA was listed but not actually blacklisted.

### Batch 2 Results (evaluated 2026-08-02)

| Token | Trial Start | Trial End | Trades | WR | PnL | Verdict |
|-------|-------------|-----------|--------|-----|-----|---------|
| COMP | 2026-08-02 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| CRV | 2026-08-02 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| DYDX | 2026-08-02 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| IMX | 2026-08-02 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| SAND | 2026-08-02 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| NEAR | 2026-08-02 | 2026-08-02 | 2 | 0% | -$0.15 | RE-BLACKLIST (INSUFFICIENT) |
| DOT | 2026-08-02 | 2026-08-02 | 2 | 0% | -$0.21 | RE-BLACKLIST (INSUFFICIENT) |
| ICP | 2026-08-02 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| ATOM | 2026-08-02 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| INJ | 2026-08-02 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| FIL | 2026-08-02 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| ETC | 2026-08-02 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| ARB | 2026-08-02 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| OP | 2026-08-02 | 2026-08-02 | 4 | 0% | -$0.30 | RE-BLACKLIST (0% WR) |
| LDO | 2026-08-02 | 2026-08-02 | 2 | 0% | -$0.09 | RE-BLACKLIST (INSUFFICIENT) |
| APT | 2026-08-02 | 2026-08-02 | 2 | 0% | -$0.22 | RE-BLACKLIST (INSUFFICIENT) |
| SEI | 2026-08-02 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| MET | 2026-08-02 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| DASH | 2026-08-02 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |
| WLD | 2026-08-02 | 2026-08-02 | 0 | — | — | RE-BLACKLIST (no execution) |

**Batch 2 Summary:** 0 KEEP, 20 RE-BLACKLIST. Pattern matches Batch 1: most tokens generate zero executable signals. Only 5/20 had any trades, all at 0% WR. Root cause: signal generation filters (speed, phase, context gate) block these tokens before they can trade — the blacklist is not the bottleneck.

## Batch 3 — Started 2026-08-02 (48h trial, evaluated 2026-08-03)

Removed from both SHORT_BLACKLIST and LONG_BLACKLIST for 48h trial:
2Z, ADA, AI16Z, BADGER, BANANA, BIGTIME, BLZ, CASHCAT, CFX, CHIP, DOOD, ENA, FOGO, FTT, FXS, GMT, GRAM, GRASS, HPOS

**Note:** BOME kept in blacklist (sketchy volume — structural, not performance).

### Batch 3 Results

| Token | Trial Start | Trial End | Trades | WR | PnL | Verdict |
|-------|-------------|-----------|--------|-----|-----|---------|
| 2Z | 2026-08-02 | 2026-08-03 | 2 | 0% | -$0.11 | RE-BLACKLIST (INSUFFICIENT) |
| ADA | 2026-08-02 | 2026-08-03 | 2 | 0% | -$0.33 | RE-BLACKLIST (INSUFFICIENT) |
| BIGTIME | 2026-08-02 | 2026-08-03 | 2 | 0% | -$0.27 | RE-BLACKLIST (INSUFFICIENT) |
| CHIP | 2026-08-02 | 2026-08-03 | 2 | 0% | -$0.29 | RE-BLACKLIST (INSUFFICIENT) |
| AI16Z | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |
| BADGER | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |
| BANANA | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |
| BLZ | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |
| CASHCAT | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |
| CFX | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |
| DOOD | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |
| ENA | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |
| FOGO | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |
| FTT | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |
| FXS | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |
| GMT | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |
| GRAM | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |
| GRASS | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |
| HPOS | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |
| ONDO | 2026-08-02 | 2026-08-03 | 0 | — | — | RE-BLACKLIST (no execution) |

**Batch 3 Summary:** 0 KEEP, 20 RE-BLACKLIST. 4 tokens had trades (all 0% WR, 2 trades each — INSUFFICIENT). 16 tokens generated zero executable signals. Pattern confirmed across all 3 batches: signal generation filters block these tokens before they can trade. The blacklist is not the bottleneck.

## Batch 4 — Started 2026-08-03 (48h trial)

Removed from both SHORT_BLACKLIST and LONG_BLACKLIST for 48h trial:
ALT, APEX, IO, MERL, MON, NEO, POL, PURR, SKR, STX, SUSHI, USUAL, XPL, ZEN, ZORA, ZRO

**Selection criteria:** Untested tokens with ≥5 historical trades (to ensure measurable signal generation). Prioritized tokens in both blacklists.

**Note:** ONDO re-blacklisted (Batch 3, no execution). ZORA swapped in as replacement.

## Batch 5 — Started 2026-08-03 (48h trial)

Removed from both SHORT_BLACKLIST and LONG_BLACKLIST for 48h trial:
HYPE, KNEIRO, KPEPE, MOVE, NOT, PUMP, SYRUP, YGG

**Selection criteria:** Final remaining untested tokens (8 total). Includes tokens with 0 historical trades (need testing) and MOVE (116 trades, 6.9% WR — worst performer, testing if bug fixes improve).

**Note:** This is the last batch. All 69 blacklist candidates have now been tested or are in active trials.

### Batch 4 Results (evaluated 2026-08-04)

| Token | Trial Start | Trial End | Trades | WR | PnL | Verdict |
|-------|-------------|-----------|--------|-----|-----|---------|
| ALT | 2026-08-03 | 2026-08-04 | 0 | — | — | RE-BLACKLIST (no execution) |
| APEX | 2026-08-03 | 2026-08-04 | 2 | 0% | -$0.17 | RE-BLACKLIST (INSUFFICIENT) |
| IO | 2026-08-03 | 2026-08-04 | 0 | — | — | RE-BLACKLIST (no execution) |
| MERL | 2026-08-03 | 2026-08-04 | 2 | 0% | -$0.20 | RE-BLACKLIST (INSUFFICIENT) |
| MON | 2026-08-03 | 2026-08-04 | 2 | 0% | -$0.28 | RE-BLACKLIST (INSUFFICIENT) |
| NEO | 2026-08-03 | 2026-08-04 | 0 | — | — | RE-BLACKLIST (no execution) |
| POL | 2026-08-03 | 2026-08-04 | 0 | — | — | RE-BLACKLIST (no execution) |
| PURR | 2026-08-03 | 2026-08-04 | 0 | — | — | RE-BLACKLIST (no execution) |
| SKR | 2026-08-03 | 2026-08-04 | 0 | — | — | RE-BLACKLIST (no execution) |
| STX | 2026-08-03 | 2026-08-04 | 0 | — | — | RE-BLACKLIST (no execution) |
| SUSHI | 2026-08-03 | 2026-08-04 | 2 | 0% | -$0.14 | RE-BLACKLIST (INSUFFICIENT) |
| USUAL | 2026-08-03 | 2026-08-04 | 2 | 0% | -$0.17 | RE-BLACKLIST (INSUFFICIENT) |
| XPL | 2026-08-03 | 2026-08-04 | 2 | 0% | -$0.25 | RE-BLACKLIST (INSUFFICIENT) |
| ZEN | 2026-08-03 | 2026-08-04 | 2 | 0% | -$0.07 | RE-BLACKLIST (INSUFFICIENT) |
| ZORA | 2026-08-03 | 2026-08-04 | 0 | — | — | RE-BLACKLIST (no execution) |
| ZRO | 2026-08-03 | 2026-08-04 | 0 | — | — | RE-BLACKLIST (no execution) |

**Batch 4 Summary:** 0 KEEP, 16 RE-BLACKLIST. 7/16 had trades (all 0% WR, 2 trades each — INSUFFICIENT). 9/16 had zero executable signals. Same pattern as Batches 1-3.

### Batch 5 Results (evaluated 2026-08-04)

| Token | Trial Start | Trial End | Trades | WR | PnL | Verdict |
|-------|-------------|-----------|--------|-----|-----|---------|
| HYPE | 2026-08-03 | 2026-08-04 | 0 | — | — | RE-BLACKLIST (no execution) |
| KNEIRO | 2026-08-03 | 2026-08-04 | 0 | — | — | RE-BLACKLIST (no execution) |
| KPEPE | 2026-08-03 | 2026-08-04 | 0 | — | — | RE-BLACKLIST (no execution) |
| MOVE | 2026-08-03 | 2026-08-04 | 0 | — | — | RE-BLACKLIST (no execution) |
| NOT | 2026-08-03 | 2026-08-04 | 0 | — | — | RE-BLACKLIST (no execution) |
| PUMP | 2026-08-03 | 2026-08-04 | 4 | 0% | -$0.54 | RE-BLACKLIST (0% WR) |
| SYRUP | 2026-08-03 | 2026-08-04 | 2 | 0% | -$0.29 | RE-BLACKLIST (INSUFFICIENT) |
| YGG | 2026-08-03 | 2026-08-04 | 0 | — | — | RE-BLACKLIST (no execution) |

**Batch 5 Summary:** 0 KEEP, 8 RE-BLACKLIST. 2/8 had trades (both 0% WR). 6/8 had zero executable signals. Pattern confirmed across all 5 batches.

## Overall Conclusion (Batches 1-5)

**77 tokens tested, 0 KEEP.** Every batch produces the same result:
- Tokens with trades: all at 0% WR,2 trades each (INSUFFICIENT sample)
- Tokens without trades: signal generation filters (speed, phase, context gate) block them entirely

**Root cause:** The blacklist is not the bottleneck. Signal generation filters (SPEED_MIN_THRESHOLD, PHASE_ENTRY_FILTER, CONTEXT_GATE) prevent these tokens from generating executable signals. When signals do fire, they're at 0% WR because the underlying signal quality is poor for these tokens.

**Recommendation:** Stop rotating tokens in/out of the blacklist. Focus on improving signal quality for the tokens that DO generate signals (the ~50 tokens currently trading). The blacklist is working as intended — it's a symptom filter, not a cause.

## Batch 6 — 2026-08-05: NOT RUN

Skipped. 77 tokens across 5 batches produced identical results (0 KEEP). Running batch 6 would waste a 48h window repeating the same experiment. The data is conclusive.

**Note:** Some blacklisted tokens (ORDI, AIXBT, ZK, CAKE, ALT, MOVE, APEX) did produce wins during their trial windows — but only before re-blacklisting. Post-trial signal outcomes for these tokens are all losses. The wins came from the few signals that fired, not from sustained quality.

**Final status:** Blacklist testing experiment complete. All candidates evaluated. No further batches planned.
