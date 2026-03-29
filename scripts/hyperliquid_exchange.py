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

# ─── Cached HL meta (coin info, expires every 6h) ───────────────────────────
_META_CACHE        = {"data": None, "ts": 0}
_META_CACHE_TTL    = 21600  # 6 hours

def _get_meta() -> dict:
    """Fetch full HL coin meta, cached for 6h to avoid hammering /info."""
    now = time.time()
    if _META_CACHE["data"] is not None and now - _META_CACHE["ts"] < _META_CACHE_TTL:
        return _META_CACHE["data"]
    try:
        result = _hl_info({"type": "meta"})
        if result:
            _META_CACHE["data"] = result
            _META_CACHE["ts"]   = now
            return result
    except Exception as e:
        print(f"[_get_meta] fetch failed: {e}")
    # Fallback: return stale cache even if expired (better than nothing)
    if _META_CACHE["data"] is not None:
        print(f"[_get_meta] using stale cache (age: {now - _META_CACHE['ts']:.0f}s)")
        return _META_CACHE["data"]
    raise RuntimeError(f"[_get_meta] Cannot fetch HL meta and no cache available")

def _sz_decimals(token: str) -> int:
    """Return szDecimals for a coin from cached meta, default 4."""
    try:
        for coin in _get_meta().get("universe", []):
            if coin.get("name", "").upper() == token.upper():
                return int(coin.get("szDecimals", 4))
        return 4
    except Exception:
        return 4


def is_delisted(token: str) -> bool:
    """Return True if token is delisted/halted on Hyperliquid (no new positions)."""
    try:
        for coin in _get_meta().get("universe", []):
            if coin.get("name", "").upper() == token.upper():
                return bool(coin.get("isDelisted", False))
        return False
    except Exception:
        return False


def is_tradeable(token: str) -> bool:
    """Return True if token can be traded on Hyperliquid."""
    return not is_delisted(token)


def get_tradeable_tokens() -> set:
    """Return set of tradeable (non-delisted) token names from HL meta."""
    try:
        return {
            c["name"] for c in _get_meta().get("universe", [])
            if not c.get("isDelisted", False)
        }
    except Exception:
        return set()


# Asset ID cache: populated from meta marginTableId (unique per coin, stable)
_ASSET_ID_CACHE = {}

def _asset_id(token: str) -> int:
    """Return asset ID for a coin from cached meta."""
    if token in _ASSET_ID_CACHE:
        return _ASSET_ID_CACHE[token]
    try:
        for coin in _get_meta().get("universe", []):
            if coin.get("name", "").upper() == token.upper():
                aid = int(coin.get("marginTableId", 0))
                _ASSET_ID_CACHE[token] = aid
                return aid
        return 0
    except Exception:
        return 0


_LEVERAGE_CACHE = {}   # {coin: max_leverage}

def _coin_max_leverage(token: str) -> int:
    """Get max leverage for a coin from cached HL meta (auto-populated)."""
    if token in _LEVERAGE_CACHE:
        return _LEVERAGE_CACHE[token]
    try:
        for coin in _get_meta().get("universe", []):
            if coin.get("name", "").upper() == token.upper():
                lev = int(coin.get("maxLeverage", 10))
                _LEVERAGE_CACHE[token] = lev
                return lev
        _LEVERAGE_CACHE[token] = 10
        return 10
    except Exception:
        _LEVERAGE_CACHE[token] = 10
        return 10


def _round_tick(token: str, price: float) -> float:
    """
    Round a price to HL's tick size for a coin.
    Uses the same formula as Exchange._slippage_price:
      perpetuals (asset_id < 10000): round to (6 - sz_decimals) dp
      spot (asset_id >= 10000):      round to (8 - sz_decimals) dp
    """
    try:
        decimals = _sz_decimals(token)
        asset_id = _asset_id(token)
        if asset_id < 10000:   # perpetual
            dp = max(0, 6 - decimals)
        else:                   # spot
            dp = max(0, 8 - decimals)
        return round(price, dp)
    except Exception:
        return round(price, 4)  # safe fallback

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
    """
    Get or create cached Exchange instance.
    Handles rate-limit errors at init time with retry + backoff.
    """
    global _exchange
    if _exchange is not None:
        return _exchange

    import time as _time
    for attempt in range(5):
        try:
            _exchange = Exchange(
                get_wallet(),
                base_url=BASE_URL,
                account_address=MAIN_ACCOUNT_ADDRESS,
            )
            return _exchange
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate limit" in err_str.lower() or "null" in err_str:
                delay = (attempt + 1) * 5
                sys.stderr.write(f"[HYPE] Exchange init rate-limited, retrying in {delay}s...\n"); sys.stderr.flush()
                _time.sleep(delay)
            else:
                raise
    # Final attempt
    _exchange = Exchange(get_wallet(), base_url=BASE_URL, account_address=MAIN_ACCOUNT_ADDRESS)
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
    """Make an HTTP POST request with exponential backoff retry on rate-limiting."""
    data = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }
    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")

    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode())
                if result is None or (isinstance(result, str) and result.strip() in ("rate limited", "null")):
                    raise Exception("Rate limited")
                return result
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            if e.code == 429 or "rate limited" in body.lower() or body.strip() in ("rate limited", "null"):
                wait = 4 ** attempt  # 1s, 4s, 16s, 64s...
                sys.stderr.write(f"[_http_post] 429 rate-limited, attempt {attempt+1}/8, waiting {wait}s...\n"); sys.stderr.flush()
                time.sleep(wait)
                continue
            raise Exception(f"HTTP {e.code}: {body}")
        except Exception as e:
            if "429" in str(e) or "rate limited" in str(e).lower():
                wait = 4 ** attempt
                sys.stderr.write(f"[_http_post] rate-limited (try {attempt+1}/8), waiting {wait}s...\n"); sys.stderr.flush()
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("[_http_post] All 8 attempts rate-limited — HL is overloaded")


# ─── /info endpoint (read-only, separate rate limit pool) ────────────────────
def _hl_info(payload: dict) -> dict:
    """Call the /info endpoint with rate limiting."""
    _info_rate_limit()
    return _http_post(_INFO_ENDPOINT, payload)


def get_prices_curl(tokens=None):
    """Get mid prices via curl to /info (bypasses SDK rate limit).

    Returns {} if HL returns empty (rate-limited) — callers must handle this.
    """
    result = _hl_info({"type": "allMids"})
    if not result:  # HL returns {} when rate-limited
        return {}
    if tokens:
        return {t: float(result[t]) for t in tokens if t in result}
    return {t: float(v) for t, v in result.items() if v}


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
        if not result:
            sys.stderr.write("[HYPE] get_open_hype_positions_curl: HL returned empty response (rate-limited?)\n"); sys.stderr.flush()
            return {}
        positions = result.get("assetPositions", []) or []
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
    """
    Close an open position via /exchange.
    Gets position size from /info (separate pool), then places reduce-only
    GTC limit at current mid price (properly rounded to tick size).
    """
    _exchange_rate_limit()

    # Get position size from /info (separate rate-limit pool from /exchange)
    positions = get_open_hype_positions_curl()
    if name not in positions:
        return {"success": False, "message": f"No open position for {name}"}
    pos = positions[name]

    exchange = get_exchange()

    def _do():
        # market_close uses SDK's internal tick rounding (always correct)
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
# Size decimal overrides — MUST match HL live meta (check via /info meta endpoint).
# These override whatever _sz_decimals() returns from the live meta.
# Only needed when _get_meta() cache is cold or the meta endpoint is unavailable.
SZ_DECIMALS = {
    "HYPE": 2, "BTC": 6, "ETH": 4, "SOL": 4,
}

# ─── Mirroring Config ─────────────────────────────────────────────────────────
MARGIN_USAGE_PCT = 0.07    # 7% of withdrawable margin per trade
MIN_TRADE_USDT   = 10.0    # Hyperliquid minimum order value ($10)
MIN_ORDER_BUFFER = 0.10    # extra $ to ensure we comfortably clear HL min ($10.10 vs $10.00)


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

def mirror_open(token: str, direction: str, entry_price: float, leverage: int = None) -> dict:
    """
    Open a real Hyperliquid position mirroring a paper trade.
    BLOCKED if live trading is disabled (kill switch).

    Args:
        token:       Hyperliquid coin name (e.g. 'HYPE')
        direction:   'LONG' or 'SHORT'
        entry_price: Entry price for size calculation
        leverage:    HL leverage to use (default: coin max up to 10x)

    Returns:
        dict with 'success', 'message', 'size', 'entry_price'
    """
    if not is_live_trading_enabled():
        return {"success": False, "message": "Live trading disabled (kill switch)"}

    if is_delisted(token):
        return {"success": False, "message": f"{token} is delisted on Hyperliquid — cannot open new positions"}

    size_usdt = _get_trade_size_usdt()
    if size_usdt < MIN_TRADE_USDT:
        return {"success": False, "message": f"Balance too low (${size_usdt:.2f} < ${MIN_TRADE_USDT})"}

    # Apply buffer to guarantee we clear HL's $10 min even with rounding edge cases
    # (e.g. SOPH at 4 decimals: 1111.1112 × $0.009 = $9.999990 — too close)
    size_usdt += MIN_ORDER_BUFFER

    # Always use LIVE HL price for size calculation — signal prices can be stale
    # Fall back to signal entry_price if live price fetch fails (rate limit, etc.)
    try:
        prices = get_prices_curl([token])
        live_price = prices.get(token)
    except Exception as e:
        print(f"[mirror_open] get_prices_curl failed for {token}: {e}")
        live_price = None
    if not live_price or live_price <= 0:
        # Fall back to signal entry_price — don't block the mirror trade
        if entry_price and entry_price > 0:
            print(f"[mirror_open] Using signal price ${entry_price:.4f} for {token} (live fetch failed)")
            live_price = entry_price
        else:
            return {"success": False, "message": f"Cannot fetch price for {token}"}

    # Size in coin units — round UP to szDecimals so we always meet min notional
    # Use live HL meta for szDecimals (VINE=0, most coins=4, BTC=6)
    decimals = _sz_decimals(token)
    raw_sz = size_usdt / live_price
    if decimals > 0:
        sz = float(Decimal(str(raw_sz)).quantize(
            Decimal(f"0.{'0' * decimals}"), rounding=ROUND_UP))
    else:
        sz = math.ceil(raw_sz)
    if sz <= 0:
        return {"success": False, "message": f"Size too small for {token} at ${live_price}"}

    is_buy = direction.upper() == "LONG"

    # Set leverage BEFORE placing the order
    # Use passed leverage, or paper trade's notional ratio, capped at coin max and 10x
    if leverage is None:
        # Derive leverage from paper trade notional: $10 × 3 = $30 notional → 3x on $10
        # Default to 3x if we can't calculate better
        leverage = 3
    leverage = max(1, min(int(leverage), _coin_max_leverage(token), 10))

    def _do():
        exchange = get_exchange()
        exchange.update_leverage(leverage, token, is_cross=True)
        return place_order(
            name=token,
            side="BUY" if is_buy else "SELL",
            sz=sz,
            order_type="Market",
        )

    try:
        result = _exchange_retry(_do)
        if result.get("success"):
            print(f"[HYPE Mirror] OPEN {direction} {sz} {token} @ ${live_price:.4f} (${size_usdt:.2f})")
            return {"success": True, "message": f"Opened {direction} {sz} {token}",
                    "size": sz, "entry_price": live_price,
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
