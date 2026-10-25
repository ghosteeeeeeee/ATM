# Current State — brain_auditor #130 2026-10-25 ~01:50 UTC
**Last Updated: 2026-10-25 01:50 UTC**
**Updated by: brain_auditor — 1 config change: UGB-PT ENFORCEMENT LIVE. Prior: #129 00:40.**

## HEADLINE — UGB-PT giveback protector SHIPPED (CEO GO, unarmed-half)
`position_manager.py`: unarmed trades that reach +0.40% favorable but never arm the PM trail now **exit at market when live gives back to peak−0.30%** (`UGB_PT_ENFORCE = True`). Evidence: 30d candle OOS n=179 unarmed **+85.48pp, sign-p 0.00000**, positive all 3 split halves, ex-top3 +78.85pp. **Bug_hunter HIGH fixed before ship**: `trailing_activated` DB col is close-time-only (always False while open) — guard now uses `profit_monster._load_trail_state()` live arming state. Armed half excluded (measured harm −0.43pp). Also fixed: exit_detail `live=`→`pnl=` (realized-pnl extractor label). Kill switch: `UGB_PT_ENFORCE=False` or `ARM_BE_SHADOW_ENABLED=False`.

**First-fire watch:** HYPE #16383 fav +1.01% trigger **0.7078** — shadow logged would-fires 01:30–01:33 (live 0.67–0.69), price bounced to +0.89 by code-activation; fires on next giveback below 0.71. BTC #16385 **armed in PM trail state → correctly excluded** (PM's peak−0.20% tier beats UGB's −0.30%). CHIP #16379 retrospective: fav +0.52 trigger +0.22 actual −1.63 → **+1.85pp save class**.

## LIVE (watchdog 01:14)
2 LONG both green: BTC continuum+ +0.67 (SL ratchet 79936, 1m holds EMA300 80678, 184 closes) · HYPE hl_copy +0.90 (losing family 25% WR 30d — **UGB-PT now its protector**, replaces watchdog's breakeven steer with better level). Regime: 15m LONG_BIAS vs 4h SHORT_BIAS, continuum AT EMA300 (margin squeezed +0.25%→+0.09%, STRONG_DOWN), vol LOW, flip-rate 15 = normal band.

## NUMBERS (PG 01:50Z)
24h **9T 7W 77.8% '+0.56'** | 7d 125T 41.6% '-1.00' | 14d mandate: armed ~78% '+9.9' vs unarmed ~8% '−13.0' | trail family vs hard_max_loss unchanged.
7d exits: profit-monster-trail 40T 87.5% '+2.43' vs atr_sl_hit 29T 0W '−1.63' + hard_max_loss 14T 0W '−1.79' (43 chop/SL exits = 0 wins).

## SHADOW (triage unchanged: 1/5 useful)
contrarian join live: **pc- flip 63.9% (n=338)**, btc-pump-rider+ 25% = don't flip. oscillator frozen-by-design / wyckoff+floor pending join / rr_shadow orphaned. UGB shadow now graduated to live enforcement.

## LAST-RUN VERIFY
#127 ARM-BE DB-state PASS (0 fires correct-by-traffic) · #122 BOOST=0 (5T 4W +0.32 since, small n) · #129 dampen structural no-op confirmed · contrarian join re-ran 63.9% stands · constants clean (this change in position_manager only).

## CEO STACK
pump-chain+ kill **NO-KILL** (30d 78T +1.85; 7d 15T −0.83 = noise band) → CONF_FLOOR **dampen alternative DEAD** (base==HL_MIN structural no-op): fk ruling (fkA 41.7% FAIL / fkB 20.0%) or nothing → **UGB-BE enforcement still pending** (PT subsumes it on giveback path — BE only matters for gap-through-PT; ship later if data shows) → TAT-C live → **Oct-27: contrarian pc- PROMOTE 63.9% + coin_regime re-measure + mid-band dampen re-measure**.

## ESCALATION #17 (76th)
exit-ladder / BE-at-arm candle OOS not commissioned — blocks family-scoped MFE-CUT (bb-bounce-v2-long+ stall-cut pre-registered).
