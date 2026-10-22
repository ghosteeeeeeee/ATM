# Gate Registry — Hermes Hard-Veto Gates

**Source of truth:** CEO D2 (2026-10-12, gate-conundrum package, ALL GO).
**Policy:** New gates ship **shadow-first 14d** before hard-veto status (grade upgrades trade-level → counterfactual → shadow → live).
**Claim hygiene:** see brain/SOPs.md §10 — episode counts, first-seen dates, null-model check, direction-signed counterfactual required for any gate proposal.
**Maintained by:** upgrade implementer / signal analyst on every gate add/change. Update this file in the same commit as the gate.

## Columns

| Column | Meaning |
|--------|---------|
| Gate | Log tag / constant family |
| First seen | Date gate first observed live (or code first-seen if log unavailable) |
| Evidence grade | trade-level / counterfactual / shadow / live-n |
| n / effect | Sample and dollar or WR effect when known |
| Last verified | Date of last independent check |
| Notes | Scope, overrides, revert triggers |

## Active hard-veto / hard-block gates

| Gate | First seen | Evidence grade | n / effect | Last verified | Notes |
|------|------------|----------------|------------|---------------|-------|
| SHORT-CONTINUUM (BTC score > MAX sustained) | pre-2026-10-05 | live-n | 22,018 block lines / 1,646 eps (2wk, Oct 12 audit) | 2026-10-12 | Real #1 blocker by volume; hysteresis HYSTERESIS_MIN=30 wired (sustained-only block). Phase-2 demotion candidate (gate-conundrum) |
| CONTINUUM-BULL | 2026-10-05 21:23 | live-n | 3.1k lines / 6d (D4 census) | 2026-10-09 | Blocks LONG when BTC continuum not bullish enough; young-gate retro entry per CEO D2 |
| LONG-NEUTRAL-CHOP | 2026-10-11 04:15 | live-n (blocked-cohort unmeasured at ship) | — | 2026-10-12 | **Attacks best cohort** (chop-LONG +$3.28 / WR 53.7%). R1 shadow first-target. Remove Nov 6 if blocked cohort wins |
| SHORT-RSI-HARD-FLOOR | 2026-10-12 00:33 (v1); value history: 45→35 (CEO 10-13) → **45 reverted 10-18** | trade-level | chop&lt;45: WR 36% −$4.56 (30d); trend side ≈ neutral | 2026-10-18 | **Stays for chop** (D6). PUMP_CHAIN sub-floor also 45 (reverted 10-21). Bear-structure relax = proposal only |
| PENALTY-BLOCK | 2026-10-06 | trade-level | 1.2k lines / 6d | 2026-10-09 | Penalty-gated execution fix; live in decider_run |
| PUMP-CHAIN-VEL (deadband −0.3%) | filter pre-Aug; deadband 2026-10-12 (D4) | bug-fix class | SHORT side deadband since Aug 16; LONG side founding claim falsified (AIXBT +4.59% at vel −0.21%) | 2026-10-12 | Both sides now −0.3% measurement floor, not edge claim |
| CONFLUENCE-GATE | long-standing | shadow | conf 80-89 ex4h −0.27% n=301 (expiry_shadow early) | 2026-10-09 | Highest-frequency block (~473/6h). Do NOT weaken (only gate proven helping per shadow-registry header) |
| BTC-CHOP-GATE | ~2026-10-04 (metric redefined 30m→5m slope) | counterfactual | 14 lines / 6h (D4) | 2026-10-09 | Threshold 0.05 (post b5006cd8 ratify) |
| HALL-SHAME (30d WR floor) | long-standing | trade-level | — | 2026-10-12 | Momentum exemption = proposal only (signal-starvation P1), not shipped |
| SHORT-NEUTRAL | long-standing | live-n | 74 events (post F1 capture) | 2026-10-04 | — |

## Young-gate watchlist (shadow-first clock)

Per CEO D2: any gate added after 2026-10-12 must accrue **14d shadow** before trusted as hard veto. On ship, add a row here with ship date; flip Evidence grade only after 14d review.

| Gate | Ship date | Shadow review due | Status |
|------|-----------|-------------------|--------|
| pump-chain+ LONG HIGH block | 2026-10-22 03:38 | 2026-11-05 | Collecting (commit c9092aea) |
| CHASE_RATIO_SHADOW (comment corrected 14d/Oct 27) | pre-2026-10-12 | 2026-10-27 | True, thresholds unchanged |

## Rules for editors

1. **Never remove a gate on intuition or a &lt;2wk window** (D6). Removals at Nov 6 re-audit or on pre-registered trigger.
2. **New gate PR must include:** first-seen plan link, episode-level counts (not raw log lines), null-model check for any "always/never" claim, direction-signed counterfactual, shadow plan (default OFF / shadow-log).
3. **Constants values** still require T/CEO instruction (hermes_constants DO-NOT-MODIFY). Registry is documentation only — it does not authorize value changes.
4. Update **Last verified** whenever a gate is independently re-measured.
