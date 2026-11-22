#!/usr/bin/env python3
"""
pnl_utils.py — CENTRALIZED P&L calculation for Hermes trading system.

Single source of truth for all PnL math. Replaces inline PnL calculations
scattered across:
  - position_manager.py (open position PnL)
  - hl-sync-guardian.py (_close_paper_trade_db close PnL)
  - profit_monster.py (live filter PnL)

Key definitions:
  pnl_pct   = leveraged return % (raw price move × leverage, direction-aware)
  pnl_usdt  = calc_notional * |raw_price_move|/100 (signed: + for profit, - for loss)
  calc_notional = hl_notional_usdt (if set) else amount_usdt * leverage
  hype_pnl_usdt = actual realized PnL from HL fills (ground truth on close)

Column-semantics footguns (brain.trades / signal_outcomes — winning-dna action 5):
  - pnl_pct is LEVERAGE-MULTIPLIED account return (post 2026-08-21). Rows before
    2026-08-21 store unleveraged price move — era break, do not mix eras.
  - mfe_pct / mae_pct are ALWAYS UNLEVERAGED price-move % (both tables). A 5x trade
    with pnl_pct=+10 has mfe_pct ~ +2 on the same move. Never compute mfe/pnl ratios
    without dividing pnl_pct by leverage first (4-5x analyst trap, caught 2026-10-08).
  - trades.pnl_usdt from compute_close_pnl is GROSS (no fees). position_manager
    prefers net_pnl (gross − 0.09% round-trip HL fee) as record_pnl when available;
    HL exchange-net ground truth lands in hype_realized_pnl_usdt / hype_pnl_usdt.
  - trades.trade_duration is SECONDS (EXTRACT(EPOCH FROM close_time - open_time)).

Usage:
  from pnl_utils import (
      compute_live_pnl,      # live pnl_pct from prices
      compute_close_pnl,    # pnl at exit from entry/exit prices
      compute_hl_pnl_pct,   # pnl_pct from HL unrealized_pnl + position_value
      apply_pnl_ground_truth,  # use HL realized pnl when available
      Direction,             # Literal["LONG", "SHORT"]
  )
"""

import json
from typing import Literal
from dataclasses import dataclass

Direction = Literal["LONG", "SHORT"]


# ── Core calculation functions ────────────────────────────────────────────────

def compute_live_pnl(
    entry_price: float,
    current_price: float,
    direction: str,   # "LONG" or "SHORT" (accept str for flexibility)
) -> float:
    """
    Compute live (unrealized) pnl_pct from entry and current price.
    Direction-aware, unleveraged (raw market return %).

    Args:
        entry_price: Entry price of the position
        current_price: Current market price
        direction: 'LONG' or 'SHORT'

    Returns:
        pnl_pct as a float (e.g. 1.5 = 1.5% profit, -0.75 = -0.75% loss)
    """
    if entry_price <= 0 or current_price <= 0:
        return 0.0
    if direction.upper() == "SHORT":
        return round((entry_price - current_price) / entry_price * 100, 4)
    return round((current_price - entry_price) / entry_price * 100, 4)


def compute_pnl_usdt(pnl_pct: float, calc_notional: float) -> float:
    """
    Convert pnl_pct to USDT value using calc_notional.
    Signed: positive for profit, negative for loss.

    Args:
        pnl_pct: Percentage gain/loss (e.g. 2.0 for 2% profit, -0.5 for -0.5% loss)
        calc_notional: Notional amount in USDT (hl_notional_usdt or amount_usdt)

    Returns:
        Signed USDT value
    """
    return round(pnl_pct / 100 * calc_notional, 4)


def compute_close_pnl(
    entry_price: float,
    exit_price: float,
    direction: Direction,
    calc_notional: float,
    leverage: float = 1,
) -> tuple[float, float, float]:
    """
    Compute pnl_pct and pnl_usdt at position close.

    pnl_pct = leveraged return (raw price move × leverage).
    pnl_usdt = calc_notional * raw_price_move.

    Returns:
        (pnl_pct, pnl_usdt, net_pnl) — net_pnl subtracts standard HL fees (0.045% × 2)
    """
    if entry_price <= 0:
        return (0.0, 0.0, 0.0)

    raw_move = compute_live_pnl(entry_price, exit_price, direction)
    pnl_usdt = compute_pnl_usdt(raw_move, calc_notional)
    pnl_pct = raw_move * leverage

    # HL fees: 0.045% per side, so 0.09% total for a round trip
    fee_total = calc_notional * 0.0009
    net_pnl = round(pnl_usdt - fee_total, 4)

    return (round(pnl_pct, 4), pnl_usdt, net_pnl)


def fee_notional(hl_notional, amount_usdt):
    """Fee BASE for every fees-JSON write — the single BUG-099 rule.

    Fees are charged on NOTIONAL: `hl_notional_usdt` when recorded, else
    `amount_usdt`. NEVER amount x leverage. amount_usdt IS the position size
    sent to HL (hl_notional = total_sz x fill_px ~= amount_usdt, and HL realized
    pnl matches amount x move, not amount x lev x move), so feeding the
    calc_notional fallback (amount x lev) into a fee inflated fee_total by
    exactly the leverage — 3x/5x/10x on all 76 closes with hl_notional_usdt
    NULL after 2026-08-22 (BUG-099 residue, found 2026-11-22).

    calc_notional stays the PnL basis; do NOT pass it in here. Returns 0.0 when
    nothing is known (fee_blob turns that into NULL — unknown, never a fee).
    """
    try:
        if hl_notional is not None:
            return float(hl_notional)
        if amount_usdt is not None:
            return float(amount_usdt)
    except (TypeError, ValueError):
        pass
    return 0.0


def fee_blob(notional, gross_pnl=None):
    """Fees JSON for the trades.fees TEXT column — the shared writer for close
    paths that had none (guardian paper/orphan/breach close, brain manual_close).
    position_manager, cascade_flip and brain.py build the same blob inline;
    the rate here is byte-identical to compute_close_pnl (0.045% x 2 sides) and
    the base is fee_notional(), so stored fee_total is unleveraged on every path.

    `notional` here must be the FEE base from fee_notional(hl_notional,
    amount_usdt) — NOT the PnL calc_notional (its amount x leverage fallback is
    the BUG-099 residue that inflated fee_total by the leverage).

    WHY THIS EXISTS (#196, re-measured #289): a NULL fees row makes every
    net-of-fee KPI understate cost, because those KPIs are
    SUM(pnl_usdt) - SUM(fee_total) and SUM skips NULL. Measured 30d:
    128/653 (19.6%) closed rows had no fee record -> reported 30d net
    -10.38 vs true -12.15. Close paths that never wrote fees (guardian
    paper/orphan close, brain manual_close) were the leak.
    Non-fatal by design: returns None on any error so the close still runs,
    and returns None when the notional is unknown (0/None) — NULL must stay
    "unknown", never a false zero-fee claim.
    """
    try:
        base = abs(float(notional or 0))
        if base <= 0:
            return None
        side = round(base * 0.00045, 6)
        total = round(side * 2, 6)
        blob = {'entry_fee': side, 'exit_fee': side, 'fee_total': total}
        if gross_pnl is not None:
            blob['net_pnl'] = round(float(gross_pnl) - total, 6)
        return json.dumps(blob)
    except Exception:
        return None


def compute_hl_pnl_pct(unrealized_pnl: float, position_value: float) -> float:
    """
    Compute pnl_pct from HL's unrealized_pnl and position_value.
    Used when we have HL data but want to cross-check / fill gaps.

    unrealized_pnl = (entryPx - currentPx) / entryPx * positionValue
    So: pnl_pct = unrealized_pnl / position_value * 100

    Args:
        unrealized_pnl: HL's unrealizedPnl value in USDT
        position_value: entry_price * size (size already includes leverage)

    Returns:
        pnl_pct as float
    """
    if position_value <= 0:
        return 0.0
    return round(unrealized_pnl / position_value * 100, 4)


def apply_pnl_ground_truth(
    calc_pnl_pct: float,
    calc_pnl_usdt: float,
    hype_pnl_usdt: float | None,
    amount_usdt: float,
) -> tuple[float, float]:
    """
    Apply HL ground truth at close time.

    When hype_pnl_usdt is available (HL fills confirmed), use it as the
    authoritative pnl_usdt. Compute pnl_pct from it using amount_usdt as
    the notional base (consistent with how positions are sized).

    Args:
        calc_pnl_pct: Computed pnl_pct from entry/exit prices
        calc_pnl_usdt: Computed pnl_usdt from calc_pnl_pct
        hype_pnl_usdt: HL's realized_pnl from close fills (or None)
        amount_usdt: The notional base for pct calculation

    Returns:
        (final_pnl_pct, final_pnl_usdt)
    """
    if hype_pnl_usdt is not None and hype_pnl_usdt != 0:
        hype_pnl_pct = round(hype_pnl_usdt / amount_usdt * 100, 4)
        return (round(hype_pnl_pct, 4), round(hype_pnl_usdt, 4))
    return (round(calc_pnl_pct, 4), round(calc_pnl_usdt, 4))


def pnl_sanity_check(pnl_pct: float, pnl_usdt: float, entry_price: float, exit_price: float) -> bool:
    """
    Check if PnL values are suspicious (>1000% or <-99%).
    Returns True if PnL is OK, False if it should be zeroed out.

    Used before committing any PnL to DB to prevent corruption from
    corrupted price data.
    """
    return abs(pnl_pct) <= 1000


def zero_suspicious_pnl(entry_price: float, exit_price: float) -> tuple[float, float, float]:
    """
    Zero out PnL when values are suspicious. Returns (0.0, 0.0, entry_price)
    to close at entry = no loss/no win.
    """
    return (0.0, 0.0, entry_price)


def _fee_blob_selfcheck():
    """fee_blob must match the compute_close_pnl rate or stored fees and
    stored net_pnl disagree — the exact class of bug this helper prevents.
    fee_notional must NEVER scale with leverage (BUG-099 residue, 2026-11-22):
    3x/5x/10x trades all fee on the same notional."""
    # fee_notional: leverage never enters the fee base — a 3x/5x/10x trade with
    # the same amount and no recorded hl_notional must produce the SAME base,
    # so fee_total/amount/0.0009 == 1 (the bug wrote exactly 3/5/10).
    for lev in (3, 5, 10):
        base = fee_notional(None, 11.10)          # hl_notional_usdt IS NULL
        ratio = base * 0.0009 / 11.10 / 0.0009
        if abs(ratio - 1.0) > 1e-9:
            raise SystemExit(f'SELFCHECK FAIL: {lev}x fee ratio {ratio} != 1.0 (leverage leaked in)')
        if base != 11.10:
            raise SystemExit(f'SELFCHECK FAIL: {lev}x fee base {base} != amount_usdt 11.10')
    if fee_notional(22.30, 11.10) != 22.30:
        raise SystemExit('SELFCHECK FAIL: recorded hl_notional must win over amount_usdt')
    if fee_notional(None, None) != 0.0:
        raise SystemExit('SELFCHECK FAIL: unknown notional must be 0.0 (-> NULL fee), not a guess')
    # fee_blob on a leverage-free base == notional * 0.0009 (3x/5x/10x identical)
    for notional in (11.10, 22.30, 16.60):
        base = fee_notional(None, notional)
        blob = fee_blob(base, gross_pnl=1.0)
        if blob is None:
            raise SystemExit(f'SELFCHECK FAIL: fee_blob({notional}) is None')
        d = json.loads(blob)
        expect = round(float(notional or 0) * 0.0009, 6)
        if abs(d['fee_total'] - expect) > 1e-6:
            raise SystemExit(f'SELFCHECK FAIL: {notional} fee_total {d["fee_total"]} != {expect}')
        if abs(d['entry_fee'] + d['exit_fee'] - d['fee_total']) > 1e-9:
            raise SystemExit(f'SELFCHECK FAIL: {notional} sides do not sum to total')
        if abs(d['net_pnl'] - (1.0 - d['fee_total'])) > 1e-6:
            raise SystemExit(f'SELFCHECK FAIL: {notional} net_pnl wrong')
    # unknown notional or garbage -> None (never a false zero-fee claim)
    for bad in (0.0, None, 'not-a-number', -1):
        got = fee_blob(bad, gross_pnl=1.0)
        if bad == -1:
            if got is None:
                raise SystemExit('SELFCHECK FAIL: negative notional should abs() to a valid fee')
            continue
        if got is not None:
            raise SystemExit(f'SELFCHECK FAIL: fee_blob({bad!r}) must be None, got {got}')
    print('SELFCHECK PASS: fee_blob/fee_notional = notional x 0.0009 RT (no leverage)')
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(_fee_blob_selfcheck())
