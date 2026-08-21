#!/usr/bin/env python3
"""
pnl_utils.py — CENTRALIZED P&L calculation for Hermes trading system.

Single source of truth for all PnL math. Replaces inline PnL calculations
scattered across:
  - position_manager.py (open position PnL)
  - hl-sync-guardian.py (_close_paper_trade_db close PnL)
  - profit_monster.py (live filter PnL)

All PnL is "unleveraged" = raw market return % (entry-based, not margin-based).
This makes it comparable across all leverage levels and consistent with how
HL's unrealized_pnl is computed.

Key definitions:
  pnl_pct   = raw % price change vs entry (direction-aware, unleveraged)
  pnl_usdt  = pnl_pct/100 * calc_notional (signed: + for profit, - for loss)
  calc_notional = hl_notional_usdt (if set) else amount_usdt * leverage
  hype_pnl_usdt = actual realized PnL from HL fills (ground truth on close)

Usage:
  from pnl_utils import (
      compute_live_pnl,      # live pnl_pct from prices
      compute_close_pnl,    # pnl at exit from entry/exit prices
      compute_hl_pnl_pct,   # pnl_pct from HL unrealized_pnl + position_value
      apply_pnl_ground_truth,  # use HL realized pnl when available
      Direction,             # Literal["LONG", "SHORT"]
  )
"""

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
    amount_usdt: float = 0,
) -> tuple[float, float, float]:
    """
    Compute pnl_pct and pnl_usdt at position close.

    pnl_pct = return on margin (pnl_usdt / amount_usdt * 100) when amount_usdt provided,
              else raw price move % (fallback for legacy callers).
    pnl_usdt = calc_notional * raw_price_move.

    Returns:
        (pnl_pct, pnl_usdt, net_pnl) — net_pnl subtracts standard HL fees (0.045% × 2)
    """
    if entry_price <= 0:
        return (0.0, 0.0, 0.0)

    raw_move = compute_live_pnl(entry_price, exit_price, direction)
    pnl_usdt = compute_pnl_usdt(raw_move, calc_notional)

    # pnl_pct = return on margin when amount_usdt provided
    if amount_usdt > 0:
        pnl_pct = round(pnl_usdt / amount_usdt * 100, 4)
    else:
        pnl_pct = raw_move  # fallback: raw price move

    # HL fees: 0.045% per side, so 0.09% total for a round trip
    fee_total = calc_notional * 0.0009
    net_pnl = round(pnl_usdt - fee_total, 4)

    return (round(pnl_pct, 4), pnl_usdt, net_pnl)


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