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

# Export flag so callers can check mirroring availability
HYPE_AVAILABLE = True


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


def place_order(name, side, sz, price=None, order_type="Limit", tif="Gtc",
                reduce_only=False, sl=None, tp=None):
    """
    Place an order on Hyperliquid.

    Args:
        name:         Token symbol as Hyperliquid uses it (e.g. 'HYPE')
        side:         'BUY' or 'SELL'
        sz:           Size (in coin units)
        price:        Limit price (required for Limit orders)
        order_type:   'Limit' or 'Market'
        tif:          'Gtc', 'Ioc', or 'Alo' (time-in-force)
        reduce_only:  True to only reduce position
        sl:           Stop-loss price (optional)
        tp:           Take-profit price (optional)

    Returns:
        dict with 'success', 'result'/'error'
    """
    exchange = get_exchange()

    try:
        if order_type == "Market":
            # Use market_open — handles slippage price internally
            result = exchange.market_open(
                name=name,
                is_buy=(side == "BUY"),
                sz=sz,
                px=price,  # optional limit price (None = full market)
                slippage=0.005,  # 0.5% slippage
            )
        else:
            # Limit order
            otype = {"limit": {"tif": tif}}
            result = exchange.order(
                name=name,
                is_buy=(side == "BUY"),
                sz=sz,
                limit_px=price or 0,
                order_type=otype,
                reduce_only=reduce_only,
            )
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def cancel_order(name, order_id):
    """Cancel an open order by order ID."""
    exchange = get_exchange()
    try:
        result = exchange.cancel(name=name, oid=int(order_id))
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def close_position(name):
    """Close an open position on a given coin using a market order."""
    exchange = get_exchange()
    try:
        result = exchange.market_close(
            coin=name,
            sz=None,       # None = close entire position
            slippage=0.005,
        )
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Rate Limiter ────────────────────────────────────────────────────────────
# Shared state file to prevent hammering the Hyperliquid API.
# Minimum gap between calls: 5 seconds + retry with exponential backoff.
import time, json, os as _os, math
from decimal import Decimal, ROUND_UP
_RATE_FILE = "/var/www/hermes/data/hype_rate_limit.json"

def _rate_limit():
    """Block until the rate limit gap (5s) has passed since last call."""
    _os.makedirs(_os.path.dirname(_RATE_FILE), exist_ok=True)
    try:
        with open(_RATE_FILE) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"last_call": 0}
    elapsed = time.time() - data.get("last_call", 0)
    if elapsed < 5:
        time.sleep(5 - elapsed)
    with open(_RATE_FILE, "w") as f:
        json.dump({"last_call": time.time()}, f)


def _retry_on_rate_limit(fn, max_attempts=5, base_delay=5):
    """
    Call fn() with retry + exponential backoff on 429 rate-limit errors.
    Handles ClientError from hyperliquid-python-sdk.
    """
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate limited" in err_str.lower():
                delay = base_delay * (2 ** attempt)
                print(f"[HYPE Mirror] Rate limited (attempt {attempt+1}/{max_attempts}) — sleeping {delay}s")
                time.sleep(delay)
            else:
                raise
    raise RuntimeError(f"All {max_attempts} attempts failed for {fn.__name__}")


# ─── Mirroring Config ────────────────────────────────────────────────────────
MARGIN_USAGE_PCT  = 0.07   # use 7% of withdrawable margin per trade
MIN_TRADE_USDT    = 10.0   # Hyperliquid minimum order value ($10)
# Map coin → szDecimals (from info.meta())
SZ_DECIMALS = {
    "HYPE": 2,
    "BTC":  6,
    "ETH":  4,
    "SOL":  4,
}


def _get_trade_size_usdt() -> float:
    """Return the USDT amount to trade (7% of withdrawable margin, min $10)."""
    state = get_account_value()
    withdrawable = float(state.get("withdrawable", 0) or 0)
    if withdrawable <= 0:
        withdrawable = float(state.get("account_value", 0) or 0)
    return max(withdrawable * MARGIN_USAGE_PCT, MIN_TRADE_USDT)


# ─── Mirroring Functions ─────────────────────────────────────────────────────
# Mirror paper trades to real Hyperliquid positions.
# Non-blocking: failures are logged but do not stop paper trading.

def mirror_open(token: str, direction: str, entry_price: float) -> dict:
    """
    Open a real Hyperliquid position mirroring a paper trade.

    Args:
        token:        Token symbol as used by Hyperliquid (e.g. 'HYPE')
        direction:    'LONG' or 'SHORT'
        entry_price:  Entry price from the paper trade (used for size calc)

    Returns:
        dict with 'success', 'message', 'size', 'entry_price'
    """
    _rate_limit()

    size_usdt = _get_trade_size_usdt()
    if size_usdt < MIN_TRADE_USDT:
        return {"success": False, "message": f"Account balance too low for mirroring (${size_usdt:.2f} < ${MIN_TRADE_USDT})"}

    # Get current price if not provided
    if entry_price <= 0:
        try:
            prices = get_prices([token])
            entry_price = prices.get(token)
        except Exception:
            pass
        if not entry_price or entry_price <= 0:
            return {"success": False, "message": f"Cannot determine price for {token}"}

    # Size in coin units — round UP to szDecimals so we always meet min notional
    decimals = SZ_DECIMALS.get(token.upper(), 4)
    raw_sz = size_usdt / entry_price
    if decimals > 0:
        sz = float(Decimal(str(raw_sz)).quantize(Decimal(f'0.{"0"*decimals}'), rounding=ROUND_UP))
    else:
        sz = math.ceil(raw_sz)
    if sz <= 0:
        return {"success": False, "message": f"Size too small for {token} at ${entry_price}"}

    # Determine Hyperliquid side
    # LONG → BUY (is_buy=True), SHORT → SELL (is_buy=False)
    is_buy = direction.upper() == "LONG"

    # Place market order to open
    result = place_order(
        name=token,
        side="BUY" if is_buy else "SELL",
        sz=sz,
        order_type="Market",
    )

    if result.get("success"):
        print(f"[HYPE Mirror] OPEN {direction} {sz} {token} @ ${entry_price:.4f} (${size_usdt:.2f})")
        return {
            "success": True,
            "message": f"Opened {direction} {sz} {token}",
            "size": sz,
            "entry_price": entry_price,
            "side": "BUY" if is_buy else "SELL",
            "usdt": size_usdt,
        }
    else:
        print(f"[HYPE Mirror] FAILED to open {direction} {token}: {result.get('error')}")
        return {"success": False, "message": result.get("error", "Unknown error")}


def mirror_close(token: str, direction: str, exit_price: float = None) -> dict:
    """
    Close a real Hyperliquid position mirroring a paper close.

    Args:
        token:       Token symbol as used by Hyperliquid (e.g. 'HYPE')
        direction:   'LONG' or 'SHORT' (the paper position direction)
        exit_price:  Exit price (optional — close_position uses market)

    Returns:
        dict with 'success', 'message'
    """
    _rate_limit()

    result = close_position(token)

    if result.get("success"):
        print(f"[HYPE Mirror] CLOSED {direction} {token}")
        return {"success": True, "message": f"Closed {direction} {token}"}
    else:
        print(f"[HYPE Mirror] FAILED to close {token}: {result.get('error')}")
        return {"success": False, "message": result.get("error", "Unknown error")}


def get_open_hype_positions() -> dict:
    """
    Get all open Hyperliquid positions keyed by coin.
    Returns: {coin: {'size': float, 'direction': 'LONG'|'SHORT', 'entry_px': float, 'unrealized_pnl': float}}
    """
    _rate_limit()
    info = get_info()
    try:
        state = info.user_state(MAIN_ACCOUNT_ADDRESS)
        result = {}
        for p in state.get("assetPositions", []):
            pos = p["position"]
            coin = pos["coin"]
            sz = float(pos.get("szi", 0) or 0)
            if sz == 0:
                continue
            result[coin] = {
                "size": abs(sz),
                "direction": "LONG" if sz > 0 else "SHORT",
                "entry_px": float(pos.get("entryPx", 0) or 0),
                "unrealized_pnl": float(pos.get("unrealizedPnl", 0) or 0),
            }
        return result
    except Exception as e:
        print(f"[HYPE Mirror] Error fetching positions: {e}")
        return {}


# ─── Token Symbol Mapping ─────────────────────────────────────────────────────
# Paper trades use brain token names; Hyperliquid uses its own coin names.
# Map paper token names → Hyperliquid coin names.
TOKEN_MAP = {
    "HYPE": "HYPE",
    "BTC":  "BTC",
    "ETH":  "ETH",
    "SOL":  "SOL",
}


def hype_coin(paper_token: str) -> str:
    """Convert paper token name to Hyperliquid coin name."""
    return TOKEN_MAP.get(paper_token.upper(), paper_token.upper())


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
