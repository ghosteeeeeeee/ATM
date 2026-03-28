"""
Hyperliquid Exchange Module for Hermes
Uses hyperliquid-python-sdk (0.22.0) + eth_account
Credentials sourced from /root/.openclaw/workspace/freqtrade/config.json
"""

from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange

# Wallet credentials — loaded from local secrets file for security.
# See .secrets.local.example for the template.
import os, pathlib
_SECRETS = pathlib.Path(__file__).parent.parent / ".secrets.local"
if _SECRETS.exists():
    for line in _SECRETS.read_text().splitlines():
        k, _, v = line.strip().partition("=")
        if k and v and k not in ("SIGNING_WALLET_ADDRESS", "MAIN_ACCOUNT_ADDRESS"):
            globals()[k] = v.strip('"')

SIGNING_KEY = globals().get("SIGNING_KEY", "")
SIGNING_WALLET_ADDRESS = "0x5AB4AC1b62A255284b54230b980AbA66d882D80A"  # funding/signing wallet
MAIN_ACCOUNT_ADDRESS = "0x324a9713603863FE3A678E83d7a81E20186126E7"   # main trading account
BASE_URL = "https://api.hyperliquid.xyz"

# Cached instances
_wallet = None
_info = None
_exchange = None


def get_wallet():
    global _wallet
    if _wallet is None:
        _wallet = Account.from_key(SIGNING_KEY)
        assert _wallet.address.lower() == SIGNING_WALLET_ADDRESS.lower(), \
            f"Wallet mismatch: {_wallet.address} != {SIGNING_WALLET_ADDRESS}"
    return _wallet


def get_info():
    global _info
    if _info is None:
        _info = Info(base_url=BASE_URL, skip_ws=True)
    return _info


def get_exchange():
    global _exchange
    if _exchange is None:
        _exchange = Exchange(
            get_wallet(),
            base_url=BASE_URL,
            account_address=MAIN_ACCOUNT_ADDRESS,  # trade from main account
        )
    return _exchange


def get_prices(tokens=None):
    """Get current mid prices for given tokens (or all if None)."""
    info = get_info()
    all_mids = info.all_mids()
    if tokens:
        return {t: float(all_mids[t]) for t in tokens if t in all_mids}
    return {t: float(v) for t, v in all_mids.items()}


def get_balance():
    """Get USDT balance info via portfolio."""
    info = get_info()
    try:
        portfolio = info.portfolio(MAIN_ACCOUNT_ADDRESS)
        return portfolio
    except Exception:
        return {}


def get_account_value():
    """Get total account value."""
    info = get_info()
    try:
        state = info.user_state(MAIN_ACCOUNT_ADDRESS)
        return {
            'account_value': state.get('accountValue'),
            'margin_used': state.get('marginUsed'),
            'withdrawable': state.get('withdrawable'),
        }
    except Exception:
        return {}


def place_order(coin, side, sz, price=None, order_type="Limit", tif="Gtc",
                reduce_only=False, sl=None, tp=None):
    """
    Place an order on Hyperliquid.
    
    Args:
        coin: Token symbol (e.g. 'HYPE')
        side: 'BUY' or 'SELL'
        sz: Size (in coin units)
        price: Limit price (required for Limit orders)
        order_type: 'Limit' or 'Market'
        tif: 'Gtc' (good-till-cancel), 'Ioc' (immediate-or-cancel), 'Alo' (async-limit-only)
        reduce_only: True to only reduce position
        sl: Stop-loss price (optional)
        tp: Take-profit price (optional)
    
    Returns:
        Order result dict from Hyperliquid
    """
    wallet = get_wallet()
    exchange = get_exchange()

    if order_type == "Market":
        otype = {"type": "Market"}
    else:
        otype = {"type": "Limit", "tif": tif, "price": str(price)}

    try:
        result = exchange.order(
            coin=coin,
            is_buy=(side == "BUY"),
            sz=sz,
            price=price,
            order_type=otype,
            reduce_only=reduce_only,
        )
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def cancel_order(coin, order_id):
    """Cancel an open order by order ID."""
    exchange = get_exchange()
    try:
        result = exchange.cancel(coin=coin, oid=int(order_id))
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def close_position(coin):
    """Close an open position on a given coin by placing a market order."""
    info = get_info()
    exchange = get_exchange()
    
    # Get current position
    try:
        state = info.user_state(MAIN_ACCOUNT_ADDRESS)
        positions = state.get('assetPositions', [])
        for pos in positions:
            if pos['position']['coin'] == coin:
                sz = float(pos['position']['szi'])
                if sz == 0:
                    return {"success": True, "message": "No open position"}
                side = "SELL" if sz > 0 else "BUY"
                # Market close at 0 size (closes entire position)
                result = exchange.order(
                    coin=coin,
                    is_buy=(sz < 0),  # if short, buy to close
                    sz=abs(sz),
                    price=0,
                    order_type={"type": "Market"},
                    reduce_only=False,
                )
                return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
    
    return {"success": True, "message": "No position found"}


if __name__ == "__main__":
    wallet = get_wallet()
    print(f"Wallet: {wallet.address}")

    print("\nPrices:")
    prices = get_prices(['HYPE', 'BTC', 'ETH', 'SOL', 'ARBI', 'AVAX', 'DOGE'])
    for t, p in sorted(prices.items()):
        print(f"  {t}: ${p:.4f}")

    print("\nBalance:")
    bal = get_balance()
    print(f"  {bal}")
