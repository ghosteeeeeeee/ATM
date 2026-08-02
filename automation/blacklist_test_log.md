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

## Batch 3 — Started 2026-08-02 (48h trial)

Removed from both SHORT_BLACKLIST and LONG_BLACKLIST for 48h trial:
2Z, ADA, AI16Z, BADGER, BANANA, BIGTIME, BLZ, CASHCAT, CFX, CHIP, DOOD, ENA, FOGO, FTT, FXS, GMT, GRAM, GRASS, HPOS

**Note:** BOME kept in blacklist (sketchy volume — structural, not performance).
