# BTC Hedge Account Spec — dual-account opposite-position experiment

**Date:** 2026-11-23 · **Status:** SPEC (not implemented) · **Scope v1:** BTC only, `ai-trader-pending` + `ai-trader-auto` signals only

## TLDR

HL nets one position per coin per account, so hedging requires a second HL
account. When Hermes opens an ai-trader BTC trade on the main account, an
opposite-position hedge leg (1:1 notional) opens simultaneously on account 2.
Each leg is its **own trades row** with its **own SL/TP/trailing**, managed by
the existing exit machinery (`manual_exit_manager` + `position_manager` +
guardian) — no coupling logic between the legs. The pair pays ~2× fees; the
thesis pays only if the survivor rides past the loser's stop + fees.

## CEO decisions (locked 2026-11-23)

| Decision | Answer |
|---|---|
| Scope | `ai-trader-pending` + `ai-trader-auto` only (NOT `ai-trader-manual`) |
| Coins | BTC only in v1; other coins later |
| Sizing | 1:1 same notional as the main leg |
| Exits | **Independent per leg** — each leg honors the trade's own SL/TP/trailing rules (`manual_sl_hit` / `manual_tp_hit` / `manual_trail_hit`). No cross-leg coupling, no survivor policy. |
| Tracking | Two separate rows, tracked independently, both stops honored |
| Account 2 | API wallet + USDC funded, ready to go |

## Honest math (read before building)

Equal-size opposite positions are **zero-sum minus fees** at every instant *until
one leg exits and the other keeps riding*:

- **Trend** (price runs one way): loser stops at −Y, winner rides to TP/trail
  beyond Y → net positive. This is the entire edge.
- **Chop that hits both stops** (the zap): loser −Y, then survivor reverses and
  stops → **−2Y − fees**. Accepted exposure in v1 — CEO's answer puts each leg
  under existing per-trade rules, which is exactly what creates this. Possible
  later mitigation (NOT in v1): tighten survivor's SL to breakeven after the
  first leg stops.
- **Chop that hits neither**: both hold, funding roughly cancels (opposite sides
  of the same rate), fees already paid on 4 taker sides.

**Fees:** taker 0.045%/side × 4 sides (2 legs in + 2 legs out) ≈ **0.18% of
notional per pair round-trip**. Maker entries would halve it (mirror_open already
supports ALO). On current sizes (~$11–30 notional) that's ~$0.02–0.05/pair in
absolute terms — trivial, but it must come out of the survivor's ride, so the
survivor must travel materially past the loser's stop distance to be net-positive.

## Architecture

### Credentials (the only thing needed from you)

`.secrets.local` gains two keys — values pasted by CEO:

```
HEDGE_SIGNING_KEY=***          # API wallet key for account 2
HEDGE_ACCOUNT_ADDRESS=0x...    # main wallet address of account 2
```

Nothing else: same box, same pipeline, same HL API. No new infra, no extra
permissions — an API wallet on account 2 is a self-contained trading identity.

### Account parameterization — `hyperliquid_exchange.py`

Today everything is hardcoded to `MAIN_ACCOUNT_ADDRESS` (~20 call sites, plus
cached module singletons `_wallet` / `_exchange`). Change:

- `get_exchange(account_address=None)` → cache **per address** (`{addr: Exchange}`).
- Thread optional `account_address=None` (default → main, zero behavior change
  for all existing callers) through only what the hedge path needs:
  `mirror_open`, `place_order`, `close_position`, `place_tp_sl_batch`,
  `replace_sl`, `replace_tp`, position/fills queries (`get_open_hype_positions`,
  `get_realized_pnl`/fills), `user_state`.

### Open flow — hook in `brain.py` `add_trade` Step 2 (HL-first)

`brain.py add_trade` is the single choke point: both `ai-trader-pending`
(armed → triggered → `brain.py trade add ... --signal ai-trader-pending`) and
`ai-trader-auto` flows open through it, so one hook covers both. **The hedge
fires at fill time, not at arm time.**

After the main `mirror_open` succeeds:

```
if HEDGE_ENABLED
   and signal in HEDGE_SIGNALS            # ('ai-trader-pending', 'ai-trader-auto')
   and hype_token in HEDGE_COINS          # ('BTC',)
   and not paper:
    mirror_open(opposite direction, size_usdt_override=<same notional>,
                same leverage, account_address=HEDGE_ACCOUNT_ADDRESS)
    → insert hedge trades row (direct insert — NOT via add_trade gates)
```

- **Failure policy:** hedge open fails → log loud + audit + **no rollback** of
  the main leg (status quo = unhedged trade). Retry once inside the same call.
- Main-leg gates (blacklist, dup, orphan, min-notional, directional block) have
  already run — the hedge leg inherits their verdict, it does not re-run them.

### DB representation — separate row, no schema change

One new `trades` row per hedge leg:

| Field | Value |
|---|---|
| `token` / `exchange` | `BTC` / `Hyperliquid` |
| `direction` | opposite of main |
| `signal` | `<original>-hedge` (e.g. `ai-trader-pending-hedge`) |
| `paper` | false (live) |
| `hl_entry_price`, `leverage`, `sl`, `target`, trailing params | mirrored from main leg (direction-flipped) |
| `signal_metadata` | `{"hedge_of": <main_trade_id>}` — the pairing link, no new column |

Why the `-hedge` suffix (exact-match vs substring matters downstream):

- `manual_exit_manager.is_managed_signal` uses substring match → **matches** →
  the dynamic SL/BE-lock/tiered trail applies to the hedge leg automatically. ✅
- `ladder_api` uses exact `IN ('ai-trader-pending','ai-trader-auto')` →
  **excluded** → main-leg stats stay uncontaminated; hedge legs are queryable
  separately (`signal LIKE '%-hedge'`). ✅
- `auto_trader` attribution uses `LIKE 'ai-trader-auto%'` → **includes** hedge
  rows. Acceptable (they're real auto-cohort trades); filterable by suffix.

### Exit flow — reuse everything, route the account

The good news, verified in code:

- **Hit detection is price-based against DB levels** (`position_manager.py:641-699`),
  direction-aware, per-row → works for a hedge row with zero changes.
- **Trailing state is keyed by `trade_id`** (`manual_trail_state.json`) → the
  hedge row trails independently, automatically. ✅ Exactly what CEO asked for.

What must change: anything that **places trigger orders or closes** for a hedge
row must address the hedge account:

- guardian `place_tp_sl_batch` / `replace_sl` / `replace_tp` for hedge rows →
  `account_address=HEDGE_ACCOUNT_ADDRESS`
- `close_position` for hedge rows → hedge account
- guardian **reconciliation** (DB↔HL position matching, orphan detection,
  `_check_hard_stops`) must query the hedge account for rows whose signal ends
  in `-hedge` — otherwise every hedge row looks like an orphan with no HL
  position on the main account, and guardian will try to "clean it up".

### Kill switch / close-all

- `is_live_trading_enabled` gates hedge opens exactly as it gates main opens. ✅
- `close ALL positions` (kill switch path) must iterate **both** accounts.

## Integration hazards (the real work)

Token-keyed assumptions break when two BTC rows exist with opposite directions
on two accounts. Every `WHERE token=...` / close-by-coin path needs review:

1. **`brain.py` dup check** — `token+server+status='open'` would reject the
   hedge row (main BTC row already open). Hedge insert bypasses `add_trade`
   gates (by design).
2. **`brain.py` stale-orphan check** — same: bypass for hedge inserts.
3. **`position_manager` leader logic** (`_leader.get(token, ...)` gates SL hits
   per token) — with main LONG + hedge SHORT on the same token, only the
   "leader" row may get SL hits. Must be made direction/hedge-aware or the
   hedge leg's stop silently never fires. **Highest-risk item.**
4. **Guardian orphan creation / coin-keyed closes** — must discriminate
   `-hedge` rows (reconcile against account 2, never against main).
5. **`cascade_flip` / close-all-by-coin** paths — `close_position(BTC)` closes
   per-account; ensure callers specify which account's leg they mean.
6. **Duplicate/tranche logic** (`--force` second tranche on same token) — must
   not treat the hedge row as a tranche of the main trade.

Rule for implementation: grep every consumer of `token` + `status='open'` and
classify: *safe (direction-aware or per-account)* vs *needs hedge discriminator*.

## Constants (hermes_constants.py — no hardcoded values)

```python
HEDGE_ENABLED   = False   # master kill for the experiment
HEDGE_MODE      = 'off'   # 'off' | 'shadow' | 'live'
HEDGE_SIGNALS   = ('ai-trader-pending', 'ai-trader-auto')
HEDGE_COINS     = ('BTC',)
HEDGE_SIZE_MULT = 1.0     # 1:1 notional
```

## Rollout

1. **off** — constants in place, hook inert.
2. **shadow** — hedge leg opened as a **paper trade** (`paper=true`,
   signal `-hedge`): the existing paper machinery records fills, runs the same
   trailing/SL/TP rules, and produces paired P&L vs the real main leg. Zero new
   simulation code needed. Bypass of dup-check required (see hazard 1).
3. **live** — `HEDGE_MODE='live'`, real account 2 orders. CEO approves after
   shadow numbers.

## What's needed from you

1. **Paste two values** into `.secrets.local`: `HEDGE_SIGNING_KEY` and
   `HEDGE_ACCOUNT_ADDRESS` (I'll add the keys; you paste the values).
2. **Confirm USDC in account 2's perp wallet** covers concurrent hedge legs:
   margin ≈ (max concurrent BTC hedge legs × notional ÷ leverage) + fee buffer.
   With current sizing (~$11–30/leg, ≤5x) — **~$100–150 USDC** is comfortable.
3. Nothing else. Same box, same pipeline, HL API handles multi-account natively.

## Accepted risks / deferred

- **Double-stopout chop (the zap):** possible under v1's independent-rules
  design. Mitigation deferred: survivor SL → breakeven after first leg stops.
- **Funding** on opposite sides ≈ cancels; not modeled.
- **Non-BTC coins:** add to `HEDGE_COINS` later (per-coin szDecimals/leverage
  already handled by existing helpers).
- **Maker entries for the hedge leg:** later optimization (halves entry fees).
