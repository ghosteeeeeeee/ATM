# CONSULT RUN 20261031T143310Z (UTC)

You are running a BOUNDED, READ-ONLY consult. Base persona/rules follow after this block.

## HARD LIMITS (this run)
- **BUDGET: ~15 minutes (extended consult: CEO_CONSULT_BUDGET=900s). This is a DEEP consult — work the question thoroughly: read the relevant code (cite file:line) and run the SQL you need to verify every number you cite. Still READ-ONLY — recommend, do not edit. Depth welcome; the ~400-word soft cap below does not apply when the brief demands a detailed answer.**
- **READ-ONLY. Do NOT edit ANY file. Do NOT change params, flags, or blacklists.**
- Do NOT develop signals. Do NOT tune signals. Do NOT dispatch subagents.
- Do NOT write to ceo_report.md or ceo_kanban.md — answer HERE, in this session.
- No session lock is held. If you believe an edit is needed, say so as a recommendation and stop.

## THE QUESTION
Answer the directed brief below. Verify any numbers you cite with a quick query (base prompt SQL rules apply — never trust old reports). Give a clear VERDICT (approve/reject/modify + rationale). If the brief asks for a review, lead with the verdict, then the reasons.

--- BRIEF ---
# Decision Request: Mirror exit asymmetry — losses vol-scaled, wins fixed-arm

**Ask:** Approve / amend / reject the two proposed exit changes for the
`jup_yolo_mirrored` signal (HML tighten + vol-scaled trail arm), and settle
whether to ship immediately or via automatic-implementation shadow rollout.

---

## The complaint (user, verbatim)

*"what's the deal here HYPE jup_yolo_mirrored signal keeps accumulating big
losses"* — citing #16617 HYPE LONG -4.58% `hard_max_loss`.

## Verified numbers (PostgreSQL, run today)

Mirror book since inception: **43 trades, 42 closed, net -$0.67, 58% WR.**

| Token | closed | W/L | WR | Net $ | ATR% |
|---|---|---|---|---|---|
| SOL | 14 | 8/6 | 57% | -0.32 | 0.53 |
| HYPE | 20 | 13/7 | 65% | **-0.19** | **1.24** |
| ETH | 4 | 3/1 | 75% | -0.10 | 0.28 |
| BTC | 4 | 2/2 | 50% | -0.06 | 0.27 |

Exit-type split (last 15 closed):
- `profit-monster-trail`: 9W/0L, **+$0.73** (avg +2.4% lev / +0.48% price)
- `atr_sl_hit`: 0W/5L, **-$0.74** (avg -4.3% lev / -0.85% price)
- `hard_max_loss`: 0W/1L -$0.19 (#16617: fired at -0.85% price vs thresh
  -0.80%, ATR 1.19 — the vol-scaled account cap worked as configured; first
  ever mirror fire, NOT a malfunction)

## The finding: asymmetric exit design

```
LOSS side: VOL-SCALED — HML vol floor = -0.5 × ATR (→ -0.85% price on HYPE)
WIN side:  FIXED      — profit-monster trail arms at +0.40% price for ALL tokens
```

In HYPE (ATR 1.24% ≈ 4.5× BTC): fixed 0.4% arm trails out on noise (winners
average +0.48% price), while the vol-scaled stop grants losses 0.85-1.2%.
Payoff ratio ≈ 0.55 → **breakeven WR ≈ 65%; actual 58%.**

Recent 6 losses: 4× HYPE + 2× SOL, **zero on BTC/ETH** (low-ATR) — consistent
with the asymmetry being vol-driven, not token-curse.

### Ruled out (verified, not assumed)
- Cluster size: winners AND losers at cluster 2-5 (no separation)
- Pro win rate: 0.18-0.43 both sides
- Rep carve-out (giants-light): no quality shift visible post-change
- HML bug: exit_conditions shows exact threshold math; guard fired correctly
- Entry quality as sole cause: ATR-loser MFE ≈ 0 (they never went favorable) —
  same as the earlier independent audit's finding on hl_copy

## Proposed changes

**#1 (strongest evidence): mirror-specific HML tighten to -0.5% price
(-2.5% account at 5x).** Evidence: ATR-stopped losers show MFE≈0 — cutting
earlier rarely preempts a future winner; saves ~0.35% price per loss (~40%
of each bleed). Rough expectancy math: 14 losses × ~$0.035 saved ≈ +$0.5
on a -$0.67 book → near breakeven. Scope: source='jup_yolo*' only, via a
carve-out constant (pattern precedent: SHORT_RSI_HARD_FLOOR_JUP_YOLO).

**#2 (hypothesis, needs validation): vol-scale the profit trail arm for
mirror trades** (arm ≈ 1×ATR instead of fixed 0.40%) so high-ATR winners
ride trends instead of noise-trailing at +0.5%. Cannot be verified from
closed-trade data alone — needs counterfactual (MFE beyond trail-arm per
trade is in the DB via mfe_price). Recommend automatic-implementation
shadow rollout per repo skill (ship OFF, collect counterfactuals, flip
with approval).

**#3: no change** — mirror is ~breakeven, n=50 re-eval standing.

## Questions

1. Ship #1 now (source-scoped carve-out, like Option D), or shadow first?
2. #2: approve shadow rollout via automatic-implementation, or skip?
3. Anything else you see in these numbers that we're missing?
4. The trailing-stop architecture (CUT_LOSER account limit, HML_VOL_ATR_MULT,
   trail arm/distance) is SYSTEM-WIDE — all trades use it. Confirm we scope
   changes to jup_yolo only and leave system-wide architecture untouched.

## Constraints

- HL min notional $11 still binds; sizing can't shrink.
- Protected flags: your verdict authorizes the carve-out edits this session.
- Every change gets bug_hunter verification (repo rule).
- Current live state: 2 open mirror trades (BTC LONG conf95.5, SOL LONG
  conf99 cluster x7) — no intervention needed on them.

## Context you asked for last time

- Mirror WR trajectory: 55% (first 11) → 67% (42 trades) — the 89% batch
  was small-sample trending luck; now converging to ~58% real.
- Giants-light fixes are live ~14h: rep carve-out + churn kill + dedupe +
  policy(b) freshness + sticky wallets. Signal flow healthy (42 signals/3h
  → now ~3× higher approval throughput). The new trades that flowed in are
  where the asymmetry shows.
--- END BRIEF ---

## OUTPUT
Print your answer to this session (stdout). Do NOT append to any report file. Max ~400 words unless the brief demands more detail.
