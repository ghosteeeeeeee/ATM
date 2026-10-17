#!/usr/bin/env python3
"""Standalone limit-order tool for manual CEO trades.

Phase 1 of plans/limit-order-capability.md — standalone script only.
brain.py --limit and guardian fill-integration are deferred until this is proven.

Usage:
  python3 scripts/limit_order.py place BTC short 82100 11.10 --lev 5 --sl 82300 --target 81500
  python3 scripts/limit_order.py list [BTC]
  python3 scripts/limit_order.py cancel BTC

When a limit fills, HL shows the position; record it via brain.py trade add
(guardian fill-integration = phase 4, not shipped).
"""
import argparse
import json
import math
import sys
import urllib.request
from decimal import Decimal, ROUND_UP

import paths  # noqa: F401 — single source of truth for paths
from hyperliquid_exchange import (
    MAIN_ACCOUNT_ADDRESS,
    MIN_TRADE_USDT,
    _sz_decimals,
    cancel_all_open_orders,
    get_exchange,
    place_order,
)


def _fetch_open_orders() -> list:
    url = "https://api.hyperliquid.xyz/info"
    payload = json.dumps({"type": "openOrders", "user": MAIN_ACCOUNT_ADDRESS}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        orders = json.loads(resp.read())
    if not isinstance(orders, list):
        orders = orders.get("orders", [])
    return orders


def cmd_place(args) -> int:
    coin = args.coin.upper()
    side = "BUY" if args.side.lower() == "long" else "SELL"
    notional = args.amount * args.lev
    if notional < MIN_TRADE_USDT - 1e-6:
        print(f"REJECTED: notional ${notional:.2f} ({args.amount} × {args.lev}x) < ${MIN_TRADE_USDT} HL minimum")
        return 1

    decimals = _sz_decimals(coin)
    raw_sz = notional / args.price
    if decimals > 0:
        sz = float(Decimal(str(raw_sz)).quantize(Decimal(f"0.{'0' * decimals}"), rounding=ROUND_UP))
    else:
        sz = math.ceil(raw_sz)
    if sz <= 0:
        print(f"REJECTED: size too small for {coin} at ${args.price}")
        return 1

    print(f"ORDER: {side} {sz} {coin} @ ${args.price} (Limit/{args.tif})")
    print(f"  margin ${args.amount} × {args.lev}x = ${notional:.2f} notional, decimals={decimals}")
    if args.sl:
        print(f"  SL  ${args.sl}  (record only — set in HL/brain after fill)")
    if args.target:
        print(f"  TP  ${args.target}  (record only — set in HL/brain after fill)")
    print("  NOTE: guardian does not yet manage limit fills — record via brain.py trade add on fill")
    if args.dry_run:
        print("DRY RUN — not placed")
        return 0
    if not args.yes:
        ans = input("Place this order? [y/N] ").strip().lower()
        if ans != "y":
            print("Aborted")
            return 1

    exchange = get_exchange()
    exchange.update_leverage(max(1, min(int(args.lev), 10)), coin, is_cross=True)
    result = place_order(name=coin, side=side, sz=sz, price=args.price,
                         order_type="Limit", tif=args.tif)
    if result.get("success"):
        print(f"PLACED: {side} {sz} {coin} @ ${args.price} ({args.tif})")
        return 0
    print(f"FAILED: {result.get('error')}")
    return 1


def cmd_list(args) -> int:
    orders = _fetch_open_orders()
    if args.coin:
        coin = args.coin.upper()
        orders = [o for o in orders if o.get("coin", "").upper() == coin]
    if not orders:
        print("No open orders")
        return 0
    for o in orders:
        side = "BUY" if o.get("side") == "B" else "SELL"
        print(f"{o.get('coin'):>8}  {side}  sz={o.get('sz')}  px=${o.get('limitPx')}  "
              f"tif={o.get('tif', '?')}  oid={o.get('oid')}  isTrigger={o.get('isTrigger', False)}")
    return 0


def cmd_cancel(args) -> int:
    result = cancel_all_open_orders(args.coin.upper())
    cancelled = result.get("cancelled", [])
    errors = result.get("errors", [])
    if errors:
        print(f"ERRORS: {errors}")
    print(f"Cancelled {len(cancelled)} order(s) for {args.coin.upper()}")
    return 0 if not errors else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Standalone Hyperliquid limit orders (manual trades)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("place", help="Place a limit order")
    pp.add_argument("coin", help="HL coin (e.g. BTC)")
    pp.add_argument("side", choices=["long", "short"])
    pp.add_argument("price", type=float, help="Limit price")
    pp.add_argument("amount", type=float, help="Margin in USDT (notional = amount × lev)")
    pp.add_argument("--lev", type=int, default=5, help="Leverage (default 5, capped 10)")
    pp.add_argument("--tif", default="Gtc", choices=["Gtc", "Ioc", "Alo"], help="Time in force")
    pp.add_argument("--sl", type=float, help="Stop loss price (record-only reminder)")
    pp.add_argument("--target", type=float, help="Target price (record-only reminder)")
    pp.add_argument("--yes", action="store_true", help="Skip confirmation")
    pp.add_argument("--dry-run", action="store_true", help="Print order, do not place")
    pp.set_defaults(func=cmd_place)

    pl = sub.add_parser("list", help="List open orders")
    pl.add_argument("coin", nargs="?", help="Filter by coin (default: all)")
    pl.set_defaults(func=cmd_list)

    pc = sub.add_parser("cancel", help="Cancel ALL open orders for a coin")
    pc.add_argument("coin", help="HL coin (e.g. BTC)")
    pc.set_defaults(func=cmd_cancel)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
