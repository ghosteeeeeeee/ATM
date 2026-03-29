"""
Hyperliquid Exchange Module for Hermes
Uses hyperliquid-python-sdk (0.22.0) + eth_account
Credentials sourced from /root/.hermes/.secrets.local

Rate limit strategy:
  /exchange endpoint (trading):  use SDK with built-in rate limiting + 5s gap
  /info    endpoint (read-only):  use curl directly with 1s gap (separate pool)
"""

from eth_account import Account
from hyperliquid.exchange import Exchange
import pathlib, time, json, os as _os, math, urllib.request, urllib.error
from decimal import Decimal, ROUND_UP

# ─── Wallet Credentials ──────────────────────────────────────────────────────
_SECRETS = pathlib.Path(__file__).parent.parent / ".secrets.local"
if _SECRETS.exists():
    for line in _SECRETS.read_text().splitlines():
        k, _, v = line.strip().partition("=")
        if k and v and k not in ("SIGNING_WALLET_ADDRESS", "MAIN_ACCOUNT_ADDRESS"):
            globals()[k] = v.strip('"')

_SIGNING_KEY            = globals().get("SIGNING_KEY", "")
SIGNING_WALLET_ADDRESS  = "0x5AB4AC1b62A255284b54230b980AbA66d882D80A"  # funding/signing
MAIN_ACCOUNT_ADDRESS    = "0x324a9713603863FE3A678E83d7a81E20186126E7"   # main trading
BASE_URL                = "https://api.hyperliquid.xyz"
_INFO_ENDPOINT          = BASE_URL + "/info"
_EXCHANGE_ENDPOINT      = BASE_URL + "/exchange"

# Cached SDK instances
_wallet   = None
_exchange = None

# Export flag so callers can check mirroring availability
HYPE_AVAILABLE = True

# ─── Kill Switch ──────────────────────────────────────────────────────────────
# Stored in a file so it survives restarts and can be set by cron/CLI.
_KILL_FILE = "/var/www/hermes/data/hype_live_trading.json"


def _load_flags() -> dict:
    try:
        with open(_KILL_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"live_trading": False}


def _save_flags(flags: dict):
    _os.makedirs(_os.path.dirname(_KILL_FILE), exist_ok=True)
    with open(_KILL_FILE, "w") as f:
        json.dump(flags, f, indent=2)


def is_live_trading_enabled() -> bool:
    """Check if live trading mirroring is enabled."""
    return _load_flags().get("live_trading", False)


def enable_live_trading() -> dict:
    """
    Enable live trading mirroring. Closes all existing real positions first,
    then enables mirroring for future paper trades.
    """
    # Close all open positions before enabling
    positions = get_open_hype_positions_curl()
    closed = []
    errors = []
    for coin, pos in positions.items():
        r = close_position(coin)
        if r.get("success"):
            closed.append(coin)
        else:
            errors.append(f"{coin}: {r.get('error', 'unknown')}")
    _save_flags({"live_trading": True, "reason": "enabled", "ts": time.time()})
    result = {"live_trading": True, "closed_positions": closed}
    if errors:
        result["close_errors"] = errors
    return result


def disable_live_trading() -> dict:
    """
    Disable live trading mirroring. Closes all open real positions immediately,
    then disables mirroring for future paper trades.
    """
    positions = get_open_hype_positions_curl()
    closed = []
    errors = []
    for coin, pos in positions.items():
        r = close_position(coin)
        if r.get("success"):
            closed.append(coin)
        else:
            errors.append(f"{coin}: {r.get('error', 'unknown')}")
    _save_flags({"live_trading": False, "reason": "disabled", "ts": time.time()})
    result = {"live_trading": False, "closed_positions": closed}
    if errors:
        result["close_errors"] = errors
    return result


def trading_status() -> dict:
    """Return full trading status: flag + open positions + account value."""
    flags = _load_flags()
    live = flags.get("live_trading", False)
    positions = get_open_hype_positions_curl()
    acct = get_account_value_curl()
    return {
        "live_trading": live,
        "flag_reason": flags.get("reason", "unknown"),
        "flag_ts": flags.get("ts"),
        "open_positions": positions,
        "account_value": acct.get("account_value"),
        "withdrawable": acct.get("withdrawable"),
    }


# ─── SDK Instances ────────────────────────────────────────────────────────────
def get_wallet():
    global _wallet
    if _wallet is None:
        _wallet = Account.from_key(_SIGNING_KEY)
        assert _wallet.address.lower() == SIGNING_WALLET_ADDRESS.lower(), \
            f"Wallet mismatch: {_wallet.address} != {SIGNING_WALLET_ADDRESS}"
    return _wallet


def get_exchange():
    global _exchange
    if _exchange is None:
        _exchange = Exchange(
            get_wallet(),
            base_url=BASE_URL,
            account_address=MAIN_ACCOUNT_ADDRESS,
        )
    return _exchange


# ─── Rate Limiters ───────────────────────────────────────────────────────────
# /exchange: tracked via SDK-internal + file-backed gap
_EXCHANGE_RATE_FILE = "/var/www/hermes/data/hype_exchange_rate.json"


def _exchange_rate_limit():
    """Block until 5s have passed since last exchange call."""
    _os.makedirs(_os.path.dirname(_EXCHANGE_RATE_FILE), exist_ok=True)
    try:
        with open(_EXCHANGE_RATE_FILE) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"last_call": 0}
    elapsed = time.time() - data.get("last_call", 0)
    if elapsed < 5:
        time.sleep(5 - elapsed)
    with open(_EXCHANGE_RATE_FILE, "w") as f:
        json.dump({"last_call": time.time()}, f)


# /info: separate rate limit pool — use curl directly with 1s gap
_INFO_RATE_FILE = "/var/www/hermes/data/hype_info_rate.json"


def _info_rate_limit():
    """Block until 1s has passed since last info API call (separate pool from /exchange)."""
    _os.makedirs(_os.path.dirname(_INFO_RATE_FILE), exist_ok=True)
    try:
        with open(_INFO_RATE_FILE) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"last_call": 0}
    elapsed = time.time() - data.get("last_call", 0)
    if elapsed < 1:
        time.sleep(1 - elapsed)
    with open(_INFO_RATE_FILE, "w") as f:
        json.dump({"last_call": time.time()}, f)


def _http_post(endpoint: str, payload: dict, timeout: int = 10) -> dict:
    """Make an HTTP POST request with error handling."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            # Hyperliquid returns "null" as a string on rate limit
            if result is None or (isinstance(result, str) and result.strip() == "rate limited"):
                raise Exception("Rate limited")
            return result
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        if e.code == 429 or "rate limited" in body.lower():
            raise Exception(f"429 Rate limited: {body}")
        raise Exception(f"HTTP {e.code}: {body}")
    except Exception as e:
        raise


# ─── /info endpoint (read-only, separate rate limit pool) ────────────────────
def _hl_info(payload: dict) -> dict:
    """Call the /info endpoint with rate limiting."""
    _info_rate_limit()
    return _http_post(_INFO_ENDPOINT, payload)


def get_prices_curl(tokens=None):
    """Get mid prices via curl to /info (bypasses SDK rate limit)."""
    result = _hl_info({"type": "allMids"})
    if tokens:
        return {t: float(result[t]) for t in tokens if t in result}
    return {t: float(v) for t, v in result.items()}


def get_account_value_curl():
    """Get account value via curl to /info (separate rate limit pool)."""
    try:
        result = _hl_info({
            "type": "clearinghouseState",
            "user": MAIN_ACCOUNT_ADDRESS,
        })
        return {
            "account_value": result.get("accountValue"),
            "withdrawable": result.get("withdrawable"),
            "positions_raw": result.get("assetPositions", []),
        }
    except Exception:
        return {}


def get_open_hype_positions_curl():
    """Get open positions via curl to /info (separate rate limit pool)."""
    try:
        result = _hl_info({
            "type": "clearinghouseState",
            "user": MAIN_ACCOUNT_ADDRESS,
        })
        positions = result.get("assetPositions", [])
        out = {}
        for p in positions:
            pos = p.get("position", {})
            coin = pos.get("coin", "")
            sz = float(pos.get("szi", 0) or 0)
            if sz == 0:
                continue
            out[coin] = {
                "size": abs(sz),
                "direction": "LONG" if sz > 0 else "SHORT",
                "entry_px": float(pos.get("entryPx", 0) or 0),
                "unrealized_pnl": float(pos.get("unrealizedPnl", 0) or 0),
            }
        return out
    except Exception as e:
        print(f"[HYPE] get_open_hype_positions_curl error: {e}")
        return {}


# ─── /exchange endpoint (trading, uses SDK) ──────────────────────────────────
def _exchange_retry(fn, max_attempts=5, base_delay=5):
    """Retry fn() with exponential backoff on rate-limit errors."""
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate limited" in err_str.lower():
                delay = base_delay * (2 ** attempt)
                print(f"[HYPE Exchange] Rate limited (attempt {attempt+1}/{max_attempts}) — sleeping {delay}s")
                time.sleep(delay)
            else:
                raise
    raise RuntimeError(f"All {max_attempts} attempts failed for {fn.__name__}")


def place_order(name, side, sz, price=None, order_type="Limit", tif="Gtc",
                reduce_only=False):
    """Place an order on Hyperliquid via /exchange."""
    _exchange_rate_limit()
    exchange = get_exchange()

    def _do():
        if order_type == "Market":
            return exchange.market_open(
                name=name,
                is_buy=(side == "BUY"),
                sz=sz,
                px=price or 0,
                slippage=0.005,
            )
        else:
            otype = {"limit": {"tif": tif}}
            return exchange.order(
                name=name,
                is_buy=(side == "BUY"),
                sz=sz,
                limit_px=price or 0,
                order_type=otype,
                reduce_only=reduce_only,
            )

    try:
        result = _exchange_retry(_do)
        # Check for error inside status
        statuses = (
            result.get("response", {})
            .get("data", {})
            .get("statuses", [])
        )
        for s in statuses:
            if "error" in s:
                return {"success": False, "error": s["error"]}
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def close_position(name):
    """Close an open position using market_close via /exchange."""
    _exchange_rate_limit()
    exchange = get_exchange()

    def _do():
        return exchange.market_close(coin=name, sz=None, slippage=0.005)

    try:
        result = _exchange_retry(_do)
        statuses = (
            result.get("response", {})
            .get("data", {})
            .get("statuses", [])
        )
        for s in statuses:
            if "error" in s:
                return {"success": False, "error": s["error"]}
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def close_all_positions():
    """Close ALL open Hyperliquid positions. Returns list of closed coins."""
    positions = get_open_hype_positions_curl()
    closed = []
    for coin in list(positions.keys()):
        r = close_position(coin)
        closed.append({"coin": coin, "success": r.get("success"), "error": r.get("error")})
    return closed


# ─── Legacy SDK-based functions (still available for direct use) ─────────────
def get_prices(tokens=None):
    """Get mid prices via SDK (uses /info pool — prefer get_prices_curl)."""
    from hyperliquid.info import Info
    info = Info(base_url=BASE_URL, skip_ws=True)
    all_mids = info.all_mids()
    if tokens:
        return {t: float(all_mids[t]) for t in tokens if t in all_mids}
    return {t: float(v) for t, v in all_mids.items()}


def get_account_value():
    """Get total account value via SDK (uses /info pool — prefer get_account_value_curl)."""
    from hyperliquid.info import Info
    info = Info(base_url=BASE_URL, skip_ws=True)
    try:
        state = info.user_state(MAIN_ACCOUNT_ADDRESS)
        return {
            "account_value": state.get("accountValue"),
            "margin_used": state.get("marginUsed"),
            "withdrawable": state.get("withdrawable"),
        }
    except Exception:
        return {}


def get_open_hype_positions():
    """Get open positions via SDK (uses /info pool — prefer get_open_hype_positions_curl)."""
    from hyperliquid.info import Info
    info = Info(base_url=BASE_URL, skip_ws=True)
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
        print(f"[HYPE] get_open_hype_positions error: {e}")
        return {}


# ─── Mirroring Config ─────────────────────────────────────────────────────────
MARGIN_USAGE_PCT = 0.07    # 7% of withdrawable margin per trade
MIN_TRADE_USDT   = 10.0    # Hyperliquid minimum order value ($10)
SZ_DECIMALS = {
    "HYPE": 2, "BTC": 6, "ETH": 4, "SOL": 4,
}


def _get_trade_size_usdt() -> float:
    """Return USDT amount to trade (7% of withdrawable, min $10)."""
    state = get_account_value_curl()
    withdrawable = float(state.get("withdrawable", 0) or 0)
    if withdrawable <= 0:
        withdrawable = float(state.get("account_value", 0) or 0)
    return max(withdrawable * MARGIN_USAGE_PCT, MIN_TRADE_USDT)


# ─── Mirror Functions ─────────────────────────────────────────────────────────
# These are the ones called by brain.py and position_manager.py.
# They check the kill switch before doing anything.

def mirror_open(token: str, direction: str, entry_price: float) -> dict:
    """
    Open a real Hyperliquid position mirroring a paper trade.
    BLOCKED if live trading is disabled (kill switch).

    Args:
        token:       Hyperliquid coin name (e.g. 'HYPE')
        direction:   'LONG' or 'SHORT'
        entry_price: Entry price for size calculation

    Returns:
        dict with 'success', 'message', 'size', 'entry_price'
    """
    if not is_live_trading_enabled():
        return {"success": False, "message": "Live trading disabled (kill switch)"}

    size_usdt = _get_trade_size_usdt()
    if size_usdt < MIN_TRADE_USDT:
        return {"success": False, "message": f"Balance too low (${size_usdt:.2f} < ${MIN_TRADE_USDT})"}

    # Get current price if needed
    if entry_price <= 0:
        try:
            prices = get_prices_curl([token])
            entry_price = prices.get(token)
        except Exception:
            pass
        if not entry_price or entry_price <= 0:
            return {"success": False, "message": f"Cannot determine price for {token}"}

    # Size in coin units — round UP to szDecimals so we always meet min notional
    decimals = SZ_DECIMALS.get(token.upper(), 4)
    raw_sz = size_usdt / entry_price
    if decimals > 0:
        sz = float(Decimal(str(raw_sz)).quantize(
            Decimal(f"0.{'0' * decimals}"), rounding=ROUND_UP))
    else:
        sz = math.ceil(raw_sz)
    if sz <= 0:
        return {"success": False, "message": f"Size too small for {token} at ${entry_price}"}

    is_buy = direction.upper() == "LONG"

    def _do():
        return place_order(
            name=token,
            side="BUY" if is_buy else "SELL",
            sz=sz,
            order_type="Market",
        )

    try:
        result = _exchange_retry(_do)
        if result.get("success"):
            print(f"[HYPE Mirror] OPEN {direction} {sz} {token} @ ${entry_price:.4f} (${size_usdt:.2f})")
            return {"success": True, "message": f"Opened {direction} {sz} {token}",
                    "size": sz, "entry_price": entry_price,
                    "side": "BUY" if is_buy else "SELL", "usdt": size_usdt}
        else:
            print(f"[HYPE Mirror] FAILED open {direction} {token}: {result.get('error')}")
            return {"success": False, "message": result.get("error", "Unknown error")}
    except Exception as e:
        print(f"[HYPE Mirror] FAILED open {direction} {token}: {e}")
        return {"success": False, "message": str(e)}


def mirror_close(token: str, direction: str, exit_price: float = None) -> dict:
    """
    Close a real Hyperliquid position mirroring a paper close.
    BLOCKED if live trading is disabled (kill switch).
    """
    if not is_live_trading_enabled():
        return {"success": False, "message": "Live trading disabled (kill switch)"}

    result = close_position(token)

    if result.get("success"):
        print(f"[HYPE Mirror] CLOSED {direction} {token}")
        return {"success": True, "message": f"Closed {direction} {token}"}
    else:
        print(f"[HYPE Mirror] FAILED close {token}: {result.get('error')}")
        return {"success": False, "message": result.get("error", "Unknown error")}


# ─── Token Symbol Mapping ─────────────────────────────────────────────────────
TOKEN_MAP = {
    "HYPE": "HYPE", "BTC": "BTC", "ETH": "ETH", "SOL": "SOL",
}


def hype_coin(paper_token: str) -> str:
    """Convert paper token name to Hyperliquid coin name."""
    return TOKEN_MAP.get(paper_token.upper(), paper_token.upper())


# ─── CLI Entry Point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hyperliquid trading control")
    parser.add_argument("--status", action="store_true", help="Show trading status")
    parser.add_argument("--enable", action="store_true", help="Enable live trading")
    parser.add_argument("--disable", action="store_true", help="Disable live trading (kill switch)")
    args = parser.parse_args()

    if args.status:
        import pprint
        pprint.pprint(trading_status())
    elif args.enable:
        pprint.pprint(enable_live_trading())
    elif args.disable:
        pprint.pprint(disable_live_trading())
    else:
        parser.print_help()
