#!/usr/bin/env python3
"""
hl-paper-sync.py — Bidirectional sync between paper trades.json and Hyperliquid.

Paper is the source of truth:
  - New paper trade → open position on HL (buy if LONG, sell if SHORT)
  - Paper trade closed → close position on HL
  - Position exists on HL but not in paper → close it (orphan)

Usage:
  python3 hl-paper-sync.py          # dry run
  python3 hl-paper-sync.py --apply  # actually execute trades
"""
import sys, json, time, argparse
sys.path.insert(0, '/root/.hermes/scripts')
from paths import *  # single source of truth for paths
from hyperliquid_exchange import (
    get_open_hype_positions_curl,
    is_live_trading_enabled,
    get_exchange,
)


PAPER_JSON = TRADES_JSON
DRY = True
SAFE_MODE = True  # never open new positions, only close orphans
MAX_SLIPPAGE = 0.005  # 0.5%


def log(msg, tag="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{tag}] {msg}")


def get_paper_trades():
    """Load open paper trades from trades.json."""
    try:
        with open(PAPER_JSON) as f:
            data = json.load(f)
        return [p for p in data.get("open", []) if p.get("exchange", "").lower() == "hyperliquid"]
    except Exception as e:
        log(f"Failed to load paper trades: {e}", "FAIL")
        return []


def get_hl_positions():
    """Get live HL positions."""
    try:
        return get_open_hype_positions_curl()
    except Exception as e:
        log(f"Failed to fetch HL positions: {e}", "FAIL")
        return {}


def get_hl_open_orders():
    """Get open orders from HL (limit orders, not positions)."""
    try:
        wallet = "0x324a9713603863FE3A678E83d7a81E20186126E7"
        import subprocess
        payload = json.dumps({'type': 'openOrders', 'user': wallet})
        r = subprocess.run([
            'curl', '-s', '-X', 'POST', 'https://api.hyperliquid.xyz/info',
            '-H', 'Content-Type: application/json', '-d', payload
        ], capture_output=True, text=True, timeout=15)
        return json.loads(r.stdout)
    except Exception as e:
        log(f"Failed to fetch HL orders: {e}", "FAIL")
        return []


def open_position_on_hl(coin: str, direction: str, size_usdt: float, entry_price: float):
    """Open a position on HL matching the paper trade direction."""
    exchange = get_exchange()
    is_buy = direction.upper() == "LONG"  # LONG = buy, SHORT = sell

    # Size: amount_usdt / entry_price (round down to HL size precision)
    size = float(size_usdt) / float(entry_price)

    tag = "DRY" if DRY else ("SKIP-SAFE" if SAFE_MODE else "OPEN")
    log(f"  {coin}: {tag} {'LONG' if is_buy else 'SHORT'} sz={size:.6f} @ {entry_price}", "WARN")

    if DRY:
        return {"success": True, "dry": True, "coin": coin, "size": size}
    if SAFE_MODE:
        return {"success": False, "reason": "SAFE_MODE", "coin": coin}

    try:
        result = exchange.market_open(
            coin=coin,
            is_buy=is_buy,
            size=size,
            slippage=MAX_SLIPPAGE,
        )
        statuses = result.get("response", {}).get("data", {}).get("statuses", [])
        for s in statuses:
            if "error" in s:
                log(f"  {coin}: ❌ open FAILED — {s['error']}", "FAIL")
                return {"success": False, "error": s["error"], "coin": coin}
        log(f"  {coin}: ✅ OPENED {'LONG' if is_buy else 'SHORT'} sz={size:.6f}", "PASS")
        return {"success": True, "coin": coin, "size": size}
    except Exception as e:
        log(f"  {coin}: ❌ open EXCEPTION — {e}", "FAIL")
        return {"success": False, "error": str(e), "coin": coin}


def close_position_on_hl(coin: str, direction: str, size: float):
    """Close a position on HL."""
    exchange = get_exchange()
    is_buy = direction.upper() == "SHORT"  # Close LONG = sell, Close SHORT = buy

    tag = "DRY" if DRY else "CLOSE"
    log(f"  {coin}: {tag} {'LONG' if is_buy else 'SHORT'} sz={size:.6f}", "WARN")

    if DRY:
        return {"success": True, "dry": True, "coin": coin}

    try:
        result = exchange.market_close(coin=coin, slippage=MAX_SLIPPAGE)
        statuses = result.get("response", {}).get("data", {}).get("statuses", [])
        for s in statuses:
            if "error" in s:
                log(f"  {coin}: ❌ close FAILED — {s['error']}", "FAIL")
                return {"success": False, "error": s["error"], "coin": coin}
        log(f"  {coin}: ✅ CLOSED", "PASS")
        return {"success": True, "coin": coin}
    except Exception as e:
        log(f"  {coin}: ❌ close EXCEPTION — {e}", "FAIL")
        return {"success": False, "error": str(e), "coin": coin}


def cancel_orders_for_coin(coin: str, orders: list):
    """Cancel all open orders for a coin."""
    exchange = get_exchange()
    # Find OIDs for this coin
    coin_orders = [o for o in orders if o.get('coin') == coin]
    if not coin_orders:
        return

    for o in coin_orders:
        oid = o.get('oid')
        tag = "DRY" if DRY else "CANCEL"
        log(f"  {coin}: {tag} oid={oid} limitPx={o.get('limitPx')}", "WARN")
        if DRY:
            continue
        try:
            exchange.cancel(coin, oid)
            log(f"    ✅ CANCELED", "PASS")
        except Exception as e:
            log(f"    ❌ cancel EXCEPTION — {e}", "FAIL")
        time.sleep(1)


def main():
    global DRY, SAFE_MODE
    parser = argparse.ArgumentParser(description="Sync HL with paper trades.json")
    parser.add_argument("--apply", action="store_true", help="Actually execute trades (default is dry-run)")
    parser.add_argument("--unsafe", action="store_true", help="Allow opening new positions (default is safe mode)")
    args = parser.parse_args()
    DRY = not args.apply
    SAFE_MODE = not args.unsafe

    mode = "DRY RUN" if DRY else ("SAFE MODE" if SAFE_MODE else "LIVE SYNC")
    live = is_live_trading_enabled()
    log(f"hl-paper-sync starting — {mode} | Live trading: {'ON' if live else 'OFF'}", "INFO")

    paper_trades = get_paper_trades()
    hl_positions = get_hl_positions()
    hl_orders = get_hl_open_orders()

    paper_tokens = {p['coin'] for p in paper_trades}

    log(f"\\nPaper HL trades: {len(paper_trades)}", "INFO")
    for p in paper_trades:
        log(f"  {p['coin']:<12} {p['direction']:<7} entry={p['entry']} amount=${p.get('amount_usdt','?')}", "INFO")

    log(f"\\nHL positions: {len(hl_positions)}", "INFO")
    for token, p in sorted(hl_positions.items()):
        log(f"  {token:<12} {p['direction']:<7} sz={p['size']} entry={p['entry_px']:.6g}", "INFO")

    # ── Phase 1: Open missing HL positions ────────────────────────────────────
    log("\\n── Phase 1: Missing HL positions (paper → HL) ──", "INFO")
    opens_needed = []
    for p in paper_trades:
        token = p['coin']
        direction = p['direction']
        entry = p['entry']
        amount = p.get('amount_usdt', 50.0)

        if token not in hl_positions:
            # Check if there are open orders for this coin (might be TP/SL only)
            coin_orders = [o for o in hl_orders if o.get('coin') == token]
            if coin_orders:
                log(f"  {token}: exists on HL as orders only (no position) — order(s) found", "WARN")
            else:
                log(f"  {token}: MISSING on HL", "WARN")
                opens_needed.append(p)
        else:
            hp = hl_positions[token]
            if hp['direction'].upper() != direction.upper():
                log(f"  {token}: direction mismatch! paper={direction} hl={hp['direction']}", "WARN")
                opens_needed.append(p)
            else:
                log(f"  {token}: paper ↔ HL in sync ✓", "PASS")

    for p in opens_needed:
        result = open_position_on_hl(p['coin'], p['direction'], p.get('amount_usdt', 50.0), p['entry'])
        time.sleep(3)

    # ── Phase 2: Close paper orphans (HL → paper) ─────────────────────────────
    log("\\n── Phase 2: Orphan HL positions (HL → paper) ──", "INFO")
    closes_needed = []
    for token in hl_positions:
        if token not in paper_tokens:
            log(f"  {token}: on HL but NOT in paper — needs closing", "WARN")
            closes_needed.append(token)

    for token in closes_needed:
        p = hl_positions[token]
        result = close_position_on_hl(token, p['direction'], p['size'])
        time.sleep(3)

    # ── Phase 3: Paper says closed but HL still has order/position ────────────
    log("\\n── Phase 3: Stale paper positions (paper says closed, HL has open) ──", "INFO")
    # These are tokens that appear in recent closed trades but still have open orders on HL
    try:
        with open(PAPER_JSON) as f:
            data = json.load(f)
        recently_closed = {t['coin'] for t in data.get('closed', [])[-10:]}
    except:
        recently_closed = set()

    stale_orders = [o for o in hl_orders if o.get('coin') in recently_closed]
    if stale_orders:
        log(f"  Found {len(stale_orders)} stale orders for recently-closed paper trades", "WARN")
        for o in stale_orders:
            log(f"  Canceling {o['coin']} oid={o['oid']} limitPx={o.get('limitPx')}", "WARN")
            if not DRY:
                exchange = get_exchange()
                try:
                    exchange.cancel(o['coin'], o['oid'])
                    log(f"    ✅ CANCELED", "PASS")
                except Exception as e:
                    log(f"    ❌ {e}", "FAIL")
                time.sleep(1)
    else:
        log("  No stale orders found", "PASS")

    # ── Summary ───────────────────────────────────────────────────────────────
    log("\\n── Summary ──", "INFO")
    log(f"  Opens needed: {len(opens_needed)}", "INFO" if not opens_needed else "WARN")
    log(f"  Closes needed: {len(closes_needed)}", "INFO" if not closes_needed else "WARN")

    if DRY:
        log("\\nDRY RUN — re-run with --apply to execute trades", "WARN")
        log("For new positions: also add --unsafe to allow opening trades", "WARN")
    elif SAFE_MODE:
        log("\\nSAFE MODE — no new positions opened (add --unsafe to enable)", "WARN")
    else:
        log("\\nSYNC complete", "PASS")


if __name__ == "__main__":
    main()
