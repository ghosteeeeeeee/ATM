# HARVEST artifact #4 — fade (pump-chain-) LONG fills by BTC tape at entry (goal round 5, 2026-11-04)
Fade flips pc- SHORT->LONG by design (CONTRARIAN_LIVE since 10-27). Question T quoted: 'half the shorts we birth, we rebrand as longs' — does it bleed on dump days?
BTC 24h-ret at entry from local candles_5m; dump day = BTC 24h <= -1.0%.

All fade LONG fills since flip: n=50 (excl 0 no-tape) net=+0.25

## On DUMP tape (BTC 24h <= -1%): n=12 net=+0.32 W=7/12
## On non-dump tape: n=38 net=-0.07 W=15/38

Dump-tape details (id, btc24h%, pnl):
  16535 -2.1% +0.03
  16536 -2.1% -0.02
  16537 -2.3% +0.04
  16554 -3.2% +0.09
  16565 -4.0% +0.13
  16579 -4.6% -0.07
  16580 -4.4% +0.06
  16581 -4.4% +0.00
  16589 -3.2% +0.02
  16601 -1.2% -0.01
  16716 -1.4% +0.07
  16735 -2.3% -0.02

## Verdict line for 11-10 (fade-btc-crash-postflip registry entry):
- If dump-tape fade-LONG net < 0 at n>=10: the rebranding DOES bleed on dumps -> the registered Z-FLIP/short-thesis guard gets a real bar.
- If net >= 0: fade LONGs are fine even on dumps -> KEEP as settled.
