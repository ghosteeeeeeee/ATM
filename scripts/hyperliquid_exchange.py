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
import pathlib, time, json, os as _os, math, sys, urllib.request, urllib.error, subprocess
from decimal import Decimal, ROUND_UP

# ─── Wallet Credentials ──────────────────────────────────────────────────────
_SECRETS = pathlib.Path(__file__).parent.parent / ".secrets.local"
if _SECRETS.exists():
    for line in _SECRETS.read_text().splitlines():
        k, _, v = line.strip().partition("=")
        if k and v and k not in ("SIGNING_WALLET_ADDRESS", "MAIN_ACCOUNT_ADDRESS"):
            globals()[k] = v.strip('"')

_SIGNING_KEY            = globals().get("SIGNING_KEY", "")
SIGNING_WALLET_ADDRESS  = "0x5AB4AC1b62A255284b54230b980AbA66d882D80A"  # funding/signing wallet

# MAIN_ACCOUNT_ADDRESS = trading account (separate from signing wallet)
# .secrets.local has it but it's filtered above, so hardcode here
# Both wallets are loaded from .secrets.local but /info queries use this address
try:
    _SECRETS2 = pathlib.Path(__file__).parent.parent / ".secrets.local"
    for line in _SECRETS2.read_text().splitlines():
        k, _, v = line.strip().partition("=")
        if k == "MAIN_ACCOUNT_ADDRESS":
            MAIN_ACCOUNT_ADDRESS = v.strip('"')
            break
    else:
        MAIN_ACCOUNT_ADDRESS = "0x324a9713603863FE3A678E83d7a81E20186126E7"
except Exception:
    MAIN_ACCOUNT_ADDRESS = "0x324a9713603863FE3A678E83d7a81E20186126E7"
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


def _round_position_sz(szi_raw, token: str) -> float:
    """
    Parse position size from HL 'szi' field and round to token's szDecimals.
    Uses Decimal to avoid float precision issues (e.g. 99.9 vs 100.0 for DYDX).

    szi_raw: the raw szi value from HL (can be string, float, int, or None)
    token:   token symbol to look up szDecimals
    Returns: rounded absolute size as float
    """
    try:
        decimals = _sz_decimals(token)
        # Parse as Decimal to avoid float precision issues
        if szi_raw is None:
            sz = Decimal("0")
        elif isinstance(szi_raw, (int, float)):
            sz = Decimal(str(szi_raw))
        else:
            sz = Decimal(str(szi_raw))
        # Round to token's szDecimals using ROUND_HALF_UP (standard rounding)
        if decimals > 0:
            quantizer = Decimal(f"0.{'0' * decimals}")
            sz = sz.quantize(quantizer, rounding=ROUND_UP)
        else:
            sz = sz.to_integral_value(rounding=ROUND_UP)
        return abs(float(sz))
    except Exception:
        # Fallback: parse as float directly
        try:
            return abs(float(szi_raw or 0))
        except Exception:
            return 0.0


# Tokens known to be non-tradable on Hyperliquid (returns 500/not in universe).
# These generate signals but can never be filled — hard block to prevent noise.
_HL_BLOCKLIST = {
    # K-tokens: meme coin forks. In HL universe but regime blindspots — pollute
    # the signals queue and block legitimate tokens. Added 2026-04-06.
    'KPEPE', 'KSHIB', 'KLUNC', 'KSHIBA', 'KLOKI', 'KNEIRO', 'KFLOKI', 'KBONK',
    # Other confirmed non-tradable
    'WCT', 'SAGA', 'GOAT', 'IOTA', 'ZORA', 'AZTEC',
    'TRX', 'RESOLV', 'HEMI', 'GMX', 'ALGO', 'HYPER',
    'SUPER',  # regime blindspot + HL blindspot
}

def is_delisted(token: str) -> bool:
    """Return True if token is delisted/halted on Hyperliquid (no new positions)."""
    # Hard blocklist first — tokens that cause 500 errors or are otherwise untradeable
    if token.upper() in _HL_BLOCKLIST:
        return True
    try:
        for coin in _get_meta().get("universe", []):
            if coin.get("name", "").upper() == token.upper():
                return bool(coin.get("isDelisted", False))
        # Token not found in HL universe — treat as delisted (non-tradeable)
        return True
    except Exception:
        return True  # On error, assume delisted to be safe


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
    """Get open positions from Hyperliquid using SDK user_state (uses MAIN_ACCOUNT_ADDRESS).
    SDK's user_state() is more reliable than raw curl for this account."""
    try:
        _exchange = get_exchange()
        state = _exchange.info.user_state(MAIN_ACCOUNT_ADDRESS)
        aps = state.get("assetPositions", [])
        out = {}
        for p in aps:
            pos = p.get("position", {})
            coin = pos.get("coin", "")
            szi_raw = pos.get("szi")
            try:
                raw_sz = float(szi_raw or 0)
            except Exception:
                raw_sz = 0
            sz = _round_position_sz(szi_raw, coin)
            if sz == 0 and raw_sz == 0:
                continue
            # BUG FIX (2026-04-02): extract leverage before dict literal
            # HL returns leverage as dict {'type': 'cross', 'value': 5}, extract numeric value
            lev_data = pos.get("leverage", {})
            if isinstance(lev_data, dict):
                lev = float(lev_data.get("value", 1)) or 1
            elif isinstance(lev_data, (int, float)):
                lev = float(lev_data)
            else:
                lev = 1
            out[coin] = {
                "size": sz,
                "direction": "LONG" if raw_sz > 0 else "SHORT",
                "entry_px": float(pos.get("entryPx", 0) or 0),
                "unrealized_pnl": float(pos.get("unrealizedPnl", 0) or 0),
                "leverage": lev,
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
    # EMERGENCY GUARD (2026-04-02): Solana tokens are indexed but NOT tradeable on HL.
    # Orders fail silently, guardian opens/closes phantom positions. Block all trades.
    if name.upper() in ('PANDORA', 'JELLY', 'FRIEND', 'FTM', 'CANTO', 'MANTA', 'LOOM',
                         'BONK', 'WIF', 'PYTH', 'JTO', 'RAY', 'SRM', 'MNGO', 'APTOS',
                         'SAGE', 'SAMO', 'DUST', 'HNT'):
        return {"success": False, "error": f"SOLANA_TOKEN_BLOCKED: {name} is not tradeable on Hyperliquid"}
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


def close_position(name, slippage=0.02):
    """
    Close an open position via /exchange.
    Gets position size from /info (separate pool), then places reduce-only
    GTC limit at current mid price (properly rounded to tick size).

    Args:
        name: token symbol
        slippage: slippage tolerance. Default 0.02 (2%) — BUG-5 fix.
                  Emergency closes (cut-loser, flip) need wider slippage
                  than normal closes to avoid partial fills in volatile markets.
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
        return exchange.market_close(coin=name, sz=None, slippage=slippage)

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
    """Get open positions. Uses subprocess curl to avoid SDK caching issues and
    because clearinghouseState can return empty for some accounts even with correct address."""
    try:
        result = subprocess.run(
            ['curl', '-s', '-X', 'POST', _INFO_ENDPOINT,
             '-H', 'Content-Type: application/json',
             '-d', json.dumps({'type': 'clearinghouseState', 'user': MAIN_ACCOUNT_ADDRESS})],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        positions = data.get("assetPositions", []) or []
        out = {}
        for p in positions:
            pos = p.get("position", {})
            coin = pos.get("coin", "")
            szi_raw = pos.get("szi")
            try:
                raw_sz = float(szi_raw or 0)
            except Exception:
                raw_sz = 0
            sz = _round_position_sz(szi_raw, coin)
            if sz == 0 and raw_sz == 0:
                continue
            out[coin] = {
                "size": sz,
                "direction": "LONG" if raw_sz > 0 else "SHORT",
                "entry_px": float(pos.get("entryPx", 0) or 0),
                "unrealized_pnl": float(pos.get("unrealizedPnl", 0) or 0),
            }
        return out
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

# ─── Trade History (for HL ground-truth sync) ─────────────────────────────────

def get_trade_history(start_time_ms: int, end_time_ms: int = None) -> list:
    """
    Fetch user's fill history from Hyperliquid /info endpoint.
    Used to sync brain.py trades with actual HL realized PnL.

    Args:
        start_time_ms: Unix timestamp in milliseconds (e.g. 1709308800000)
        end_time_ms:   Unix timestamp in ms (default: now)

    Returns list of fill dicts, newest first:
        {
            "coin": str,
            "side": str,          # "A" = Open fill, "B" = Close fill (with realized PnL)
            "dir": str,           # "L" (Long) or "S" (Short)
            "px": float,          # fill price
            "sz": float,          # fill size
            "closed_pnl": float,  # realized PnL (only on close fills)
            "hash": str,
            "oid": int,
            "time_ms": int,
        }
    """
    # Retry with exponential backoff for CloudFront / HL rate limits
    for attempt in range(4):
        _info_rate_limit()
        info = get_exchange().info
        if end_time_ms is None:
            end_time_ms = int(time.time() * 1000)
        try:
            raw = info.user_fills_by_time(MAIN_ACCOUNT_ADDRESS, start_time_ms, end_time_ms)
            fills = []
            for f in raw:
                fills.append({
                    "coin":       f["coin"],
                    "side":       f.get("side", ""),
                    "dir":        f.get("dir", ""),
                    "px":         float(f["px"]),
                    "sz":         float(f["sz"]),
                    "closed_pnl": float(f["closedPnl"]) if f.get("closedPnl") else 0.0,
                    "hash":       f.get("hash", ""),
                    "oid":        f.get("oid", 0),
                    "time_ms":    f.get("time", 0),
                })
            fills.sort(key=lambda x: x["time_ms"], reverse=True)
            return fills
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                wait = 2 ** attempt + 1
                print(f"[HL get_trade_history] 429 on attempt {attempt+1}, retrying in {wait}s...")
                time.sleep(wait)
                continue
            print(f"[HL get_trade_history] error: {e}")
            return []
    return []


def get_realized_pnl(token: str, start_time_ms: int, end_time_ms: int = None) -> dict:
    """
    Get realized PnL for a specific token within a time window.
    Returns weighted-avg entry/exit prices and total realized PnL from HL fills.
    """
    fills = get_trade_history(start_time_ms, end_time_ms)
    token_fills = [f for f in fills if f["coin"].upper() == token.upper()]
    if not token_fills:
        return {"realized_pnl": 0.0, "entry_price": 0.0, "exit_price": 0.0,
                "total_size": 0.0, "fills": 0}

    # HL uses: side="A" = open fill, side="B" = close fill (has realized PnL)
    open_fills  = [f for f in token_fills if f["side"] == "A"]
    close_fills = [f for f in token_fills if f["side"] == "B"]

    def wavg_price(fills_list):
        if not fills_list:
            return 0.0
        total = sum(f["sz"] for f in fills_list)
        return sum(f["px"] * f["sz"] for f in fills_list) / total if total else 0.0

    return {
        "realized_pnl": sum(f["closed_pnl"] for f in close_fills),
        "entry_price":  wavg_price(open_fills),
        "exit_price":   wavg_price(close_fills),
        "total_size":   sum(f["sz"] for f in token_fills),
        "fills":        len(token_fills),
    }


def mirror_get_entry_fill(token: str, start_time_ms: int, window_ms: int = 300000) -> dict:
    """
    Get actual entry fill price for a position that was just opened.
    Looks up OPEN fills (side=A for LONG, side=B for SHORT) within window_ms
    after start_time_ms. Computes size-weighted average fill price.

    Returns {"success": True, "entry_price": float, "realized_pnl": float}
            or {"success": False} if no entry fill found.
    """
    end_ms = start_time_ms + window_ms
    fills = get_trade_history(start_time_ms, end_ms)
    token_upper = token.upper()
    # side=A = opens a long or closes a short
    # side=B = opens a short or closes a long
    entry_fills = [f for f in fills
                   if f["coin"].upper() == token_upper
                   and f["side"] in ("A", "B")]
    if not entry_fills:
        return {"success": False}
    total_sz = sum(abs(f["sz"]) for f in entry_fills)
    return {
        "success":      True,
        "entry_price":  sum(f["px"] * abs(f["sz"]) for f in entry_fills) / total_sz,
        "total_sz":     total_sz,
        "fill_count":   len(entry_fills),
    }


def mirror_get_exit_fill(token: str, start_time_ms: int, window_ms: int = 300000) -> dict:
    """
    Get actual exit fill for a recently-closed position.
    Looks up fills within window_ms after start_time_ms (default: 5 min).

    Returns {"success": True, "exit_price": float, "realized_pnl": float}
            or {"success": False} if no exit fill found.
    """
    end_ms = start_time_ms + window_ms
    fills = get_trade_history(start_time_ms, end_ms)
    close_fills = [f for f in fills
                   if f["coin"].upper() == token.upper() and f["side"] == "B"]
    if not close_fills:
        return {"success": False}
    total_sz = sum(f["sz"] for f in close_fills)
    return {
        "success":      True,
        "exit_price":   sum(f["px"] * f["sz"] for f in close_fills) / total_sz,
        "realized_pnl": sum(f["closed_pnl"] for f in close_fills),
        "time_ms":      close_fills[0]["time_ms"],
    }


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
            # ── Ground truth: poll HL fill history for actual entry price ──
            order_time_ms = int(time.time() * 1000)
            entry_info = mirror_get_entry_fill(token, order_time_ms - 2000, window_ms=10000)
            if entry_info.get("success"):
                fill_price = entry_info["entry_price"]
                print(f"[HYPE Mirror] OPEN {direction} {sz} {token} @ signal=${live_price:.6f} "
                      f"→ HL_fill=${fill_price:.6f} ({entry_info.get('fill_count',1)} fills)")
            else:
                # Fall back to slippage estimate
                slippage = 0.005
                fill_price = live_price * (1 + slippage) if is_buy else live_price * (1 - slippage)
                decimals = _sz_decimals(token)
                fill_price = round(fill_price, decimals)
                print(f"[HYPE Mirror] OPEN {direction} {sz} {token} @ ${live_price:.6f} "
                      f"(no HL fill data, estimated ${fill_price:.6f})")

            return {"success": True, "message": f"Opened {direction} {sz} {token}",
                    "size": sz,
                    "entry_price": fill_price,       # actual HL fill price for PnL
                    "hl_entry_price": fill_price,     # alias
                    "mid_price": live_price,
                    "slippage_pct": abs(fill_price - live_price) / live_price if live_price else 0,
                    "side": "BUY" if is_buy else "SELL",
                    "usdt": size_usdt}
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
    RAISES RuntimeError on failure (fails loudly, never silently).
    """
    if not is_live_trading_enabled():
        raise RuntimeError(f"mirror_close({token}): live trading disabled (kill switch)")

    result = close_position(token)

    if result.get("success"):
        # BUG-17 fix: poll HL fills up to 3 times with 2s delay (was single query).
        # BUG-22 fix: warn when no fills found instead of silently returning None.
        close_start_ms = int(time.time() * 1000) - 300000  # look back 5min
        exit_info = {"success": False}
        for attempt in range(3):
            time.sleep(2)
            exit_info = mirror_get_exit_fill(token, close_start_ms)
            if exit_info.get("success"):
                break
            print(f"[HYPE Mirror] Fill poll {attempt+1}/3 for {token} — no close fills yet")

        if not exit_info.get("success"):
            print(f"[HYPE Mirror] WARN: no HL close fills found for {token} after 3 polls", file=sys.stderr)

        print(f"[HYPE Mirror] CLOSED {direction} {token} "
              f"(HL exit ${exit_info.get('exit_price', 0):.6f} pnl={exit_info.get('realized_pnl', 0):+.4f})")
        return {"success": True, "message": f"Closed {direction} {token}",
                "hl_exit_price": exit_info.get("exit_price"),
                "hl_realized_pnl": exit_info.get("realized_pnl")}
    else:
        err = result.get("error", "Unknown error")
        raise RuntimeError(f"mirror_close({token}): HL API failed — {err}")


# ─── Token Symbol Mapping ─────────────────────────────────────────────────────
TOKEN_MAP = {
    "HYPE": "HYPE", "BTC": "BTC", "ETH": "ETH", "SOL": "SOL",
}


def hype_coin(paper_token: str) -> str:
    """Convert paper token name to Hyperliquid coin name."""
    return TOKEN_MAP.get(paper_token.upper(), paper_token.upper())


# ─── Order builders ─────────────────────────────────────────────────────────────

def build_order(coin: str, side: str, sz: float, limit_px: float,
                order_type: str = "Limit", tif: str = "Gtc",
                reduce_only: bool = False) -> dict:
    """
    Build a single OrderRequest dict for bulk / individual use.
    Mirrors the signature of place_order() but returns a TypedDict dict.

    Args:
        coin:       HL coin name (e.g. 'HYPE')
        side:       'BUY' or 'SELL'
        sz:         size in coin units
        limit_px:   limit price (0 for market)
        order_type: 'Limit' or 'Market'
        tif:        'Gtc', 'Alo', or 'Ioc'
        reduce_only: True for TP/SL close-only orders
    """
    from hyperliquid.utils.signing import OrderRequest
    if isinstance(order_type, dict):
        # Already a trigger/Limit dict — use it directly
        otype = order_type
    elif order_type == "Market":
        otype = {"trigger": {"triggerPx": 0, "isMarket": True, "tpsl": "tp"}}
    else:
        otype = {"limit": {"tif": tif}}
    is_buy = side.upper() == "BUY"
    order: dict = {
        "coin": coin.upper(),
        "is_buy": is_buy,
        "sz": float(sz),
        "limit_px": float(limit_px),
        "order_type": otype,
        "reduce_only": reduce_only,
    }
    return order


def place_bulk_orders(orders: list, grouping: str = "na") -> dict:
    """
    Place multiple orders in a single POST /api/v1/batchOrders call.

    Args:
        orders:   list of OrderRequest dicts (from build_order, or raw dicts)
        grouping: 'na' | 'normalTpsl' | 'positionTpsl'  (default 'na')

    Returns:
        {"success": bool, "result": raw_response_or_error}
    """
    _exchange_rate_limit()
    exchange = get_exchange()

    def _do():
        return exchange.bulk_orders(orders, grouping=grouping)

    try:
        result = _exchange_retry(_do)
        statuses = (
            result.get("response", {})
            .get("data", {})
            .get("statuses", [])
        )
        errors = [s["error"] for s in statuses if "error" in s]
        if errors:
            return {"success": False, "errors": errors, "result": result}
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def cancel_bulk_orders(requests: list) -> dict:
    """
    Cancel multiple orders in a single POST /api/v1/batchCancels call.

    Args:
        requests: list of CancelRequest dicts, each {"coin": str, "oid": int}
                  OR CancelByCloidRequest dicts {"coin": str, "cloid": Cloid}

    Returns:
        {"success": bool, "result": raw_response_or_error}
    """
    _exchange_rate_limit()
    exchange = get_exchange()

    def _do():
        # Dispatch to the right bulk cancel variant based on key presence
        if requests and "cloid" in requests[0]:
            return exchange.bulk_cancel_by_cloid(requests)
        return exchange.bulk_cancel(requests)

    try:
        result = _exchange_retry(_do)
        statuses = (
            result.get("response", {})
            .get("data", {})
            .get("statuses", [])
        )
        errors = [s["error"] for s in statuses if "error" in s]
        if errors:
            return {"success": False, "errors": errors, "result": result}
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── TP / SL Order Placement ───────────────────────────────────────────────────

# HL tick sizes (minimum price increment for TP/SL orders)
# BTC=1, ETH=0.1, SOL=0.01, STX=0.01, AVAX=0.001, TRX=0.01
_HL_TICK_DECIMALS = {
    # Verified from order book (2026-04-08)
    # tick_size = 10 ** -N where N = decimals
    "BTC": 1,   # $71k — tick 1, order book shows 71688.0 (1 decimal)
    "ETH": 1,   # $2.2k — tick 0.1, order book shows 2250.2 (1 decimal)
    "SOL": 3,   # $84 — tick 0.001, order book shows 84.659 (3 decimals)
    "AVAX": 4,  # $9 — tick 0.0001, order book shows 9.3714 (4 decimals)
    "XRP": 4,   # $1.38 — tick 0.0001, order book shows 1.3812 (4 decimals)
    "ADA": 5,   # $0.26 — tick 0.00001, order book shows 0.25934 (5 decimals)
    "LINK": 4,  # $9 — tick 0.0001, order book shows 9.2192 (4 decimals)
    "DOT": 4,   # $1.3 — tick 0.0001, order book shows 1.3256 (4 decimals)
    "DOGE": 6,  # $0.095 — tick 0.000001, order book shows 0.094826 (6 decimals)
    "STX": 5,   # $0.23 — tick 0.00001, order book shows 0.22769 (5 decimals)
    "TRX": 5,   # $0.32 — tick 0.00001, order book shows 0.31625 (5 decimals)
    "MEGA": 5,  # $0.13 — tick 0.00001, order book shows 0.12991 (5 decimals)
    # Missing tokens — inferred from order book (2026-04-08)
    "SCR": 5,   # $0.044 — tick 0.00001, order book shows 0.04454 (5 decimals)
    "SAND": 6,  # $0.08 — tick 0.000001, order book shows 0.079833 (6 decimals)
    "ETHFI": 5, # $0.46 — tick 0.00001, order book shows 0.45978 (5 decimals)
    "AXS": 4,   # $1.14 — tick 0.0001, order book shows 1.1406 (4 decimals)
    "UMA": 5,   # $0.42 — tick 0.00001, order book shows 0.41898 (5 decimals)
    "SKY": 6,   # $0.08 — tick 0.000001, order book shows 0.079896 (6 decimals)
}


def _hl_tick_round(px: float, decimals: int) -> float:
    """Round price to HL tick size."""
    import decimal
    rounded = round(px, decimals)
    if decimals == 0:
        rounded = int(rounded)
    normalized = decimal.Decimal(str(rounded)).normalize()
    return float(normalized)


def place_tp(coin: str, direction: str, tp_price: float, size: float) -> dict:
    """Place a take-profit order on Hyperliquid. Sells if LONG, buys if SHORT.
    Uses market trigger (isMarket=True) so it executes immediately when triggered.

    Key rules learned from HL API:
    - TP must be on correct side of current price (above for LONG, below for SHORT)
    - Price must be rounded to HL tick size (coin-specific)
    - Pass limit_px = triggerPx (works for both LONG and SHORT)
    - BTC needs integer prices, ETH needs 1-decimal, SOL/STX need 2-decimal, etc."""
    exchange = get_exchange()
    is_buy = direction.upper() == "SHORT"

    decimals = _HL_TICK_DECIMALS.get(coin, 6)
    tp_rounded = _hl_tick_round(tp_price, decimals)

    order_type = {
        "trigger": {
            "triggerPx": tp_rounded,
            "isMarket": True,
            "tpsl": "tp",
        }
    }
    try:
        result = exchange.order(coin, is_buy, float(size), tp_rounded, order_type, reduce_only=True)
        statuses = result.get("response", {}).get("data", {}).get("statuses", [])
        for s in statuses:
            if "error" in s:
                return {"success": False, "error": s["error"], "coin": coin, "type": "TP",
                        "hint": "Check: price on correct side of current? price rounded to tick size?"}
            if "ok" in s:
                oid = s["ok"].get("oid") if isinstance(s["ok"], dict) else None
                return {"success": True, "coin": coin, "type": "TP", "price": tp_rounded, "size": size, "order_id": oid}
        return {"success": True, "coin": coin, "type": "TP", "price": tp_rounded, "size": size}
    except Exception as e:
        return {"success": False, "error": str(e), "coin": coin, "type": "TP"}


def place_sl(coin: str, direction: str, sl_price: float, size: float) -> dict:
    """Place a stop-loss order on Hyperliquid. Sells if LONG → triggers below entry,
    buys if SHORT → triggers above current price."""
    exchange = get_exchange()
    is_buy = direction.upper() == "SHORT"

    decimals = _HL_TICK_DECIMALS.get(coin, 6)
    sl_rounded = _hl_tick_round(sl_price, decimals)

    order_type = {
        "trigger": {
            "triggerPx": sl_rounded,
            "isMarket": True,
            "tpsl": "sl",
        }
    }
    try:
        result = exchange.order(coin, is_buy, float(size), sl_rounded, order_type, reduce_only=True)
        statuses = result.get("response", {}).get("data", {}).get("statuses", [])
        for s in statuses:
            if "error" in s:
                return {"success": False, "error": s["error"], "coin": coin, "type": "SL",
                        "hint": "Check: price on correct side of current? price rounded to tick size?"}
            if "ok" in s:
                oid = s["ok"].get("oid") if isinstance(s["ok"], dict) else None
                return {"success": True, "coin": coin, "type": "SL", "price": sl_rounded, "size": size, "order_id": oid}
        return {"success": True, "coin": coin, "type": "SL", "price": sl_rounded, "size": size}
    except Exception as e:
        return {"success": False, "error": str(e), "coin": coin, "type": "SL"}


def _find_open_trigger_order(coin: str, tpsl_type: str) -> tuple:
    """
    Find an open TP or SL order for a given coin.
    
    Args:
        coin:      HL coin name (e.g. 'BTC')
        tpsl_type: "tp" or "sl"
    
    Returns:
        (oid: int, cloid: Cloid, sz: float, trigger_px: float) or (None, None, None, None) if not found.
    """
    exchange = get_exchange()
    try:
        resp = _hl_info({"type": "open_orders", "user": MAIN_ACCOUNT_ADDRESS})
        orders = resp if isinstance(resp, list) else resp.get("orders", [])
    except Exception:
        return None, None, None, None

    coin_upper = coin.upper()
    for o in orders:
        if o.get("coin", "").upper() != coin_upper:
            continue
        ot = o.get("orderType", {})
        trig = ot.get("trigger", {}) if isinstance(ot, dict) else {}
        if trig.get("tpsl", "").lower() != tpsl_type.lower():
            continue
        return (
            o.get("oid"),
            o.get("cloid"),
            float(o.get("sz", 0)),
            float(trig.get("triggerPx", 0)),
        )
    return None, None, None, None


def cancel_tp(coin: str, direction: str = None) -> dict:
    """
    Cancel the open take-profit order for a given coin.
    Returns {"success": True} on success, {"success": False, "error": ...} on failure.
    """
    _exchange_rate_limit()
    exchange = get_exchange()
    oid, cloid, _, _ = _find_open_trigger_order(coin, "tp")
    if oid is None:
        return {"success": False, "error": f"No open TP found for {coin}"}

    try:
        if cloid:
            result = exchange.cancel_by_cloid(coin, cloid)
        else:
            result = exchange.cancel(coin, oid)
        statuses = result.get("response", {}).get("data", {}).get("statuses", [])
        for s in statuses:
            if "error" in s:
                return {"success": False, "error": s["error"]}
        return {"success": True, "coin": coin, "type": "TP", "oid": oid}
    except Exception as e:
        return {"success": False, "error": str(e), "coin": coin, "type": "TP"}


def cancel_sl(coin: str, direction: str = None) -> dict:
    """
    Cancel the open stop-loss order for a given coin.
    Returns {"success": True} on success, {"success": False, "error": ...} on failure.
    """
    _exchange_rate_limit()
    exchange = get_exchange()
    oid, cloid, _, _ = _find_open_trigger_order(coin, "sl")
    if oid is None:
        return {"success": False, "error": f"No open SL found for {coin}"}

    try:
        if cloid:
            result = exchange.cancel_by_cloid(coin, cloid)
        else:
            result = exchange.cancel(coin, oid)
        statuses = result.get("response", {}).get("data", {}).get("statuses", [])
        for s in statuses:
            if "error" in s:
                return {"success": False, "error": s["error"]}
        return {"success": True, "coin": coin, "type": "SL", "oid": oid}
    except Exception as e:
        return {"success": False, "error": str(e), "coin": coin, "type": "SL"}


def replace_tp(coin: str, direction: str, new_price: float, size: float = None) -> dict:
    """
    Replace an existing TP order with a new price (and optionally new size).
    If no existing TP is found, places a NEW TP order (handles entry-time failures).
    Returns {"success": True} on success, {"success": False, "error": ...} on failure.
    """
    _exchange_rate_limit()
    exchange = get_exchange()
    oid, cloid, existing_sz, _ = _find_open_trigger_order(coin, "tp")
    is_buy = direction.upper() == "SHORT"
    sz = float(size) if size is not None else existing_sz
    decimals = _HL_TICK_DECIMALS.get(coin, 6)
    new_px = _hl_tick_round(new_price, decimals)
    order_type = {
        "trigger": {
            "triggerPx": new_px,
            "isMarket": True,
            "tpsl": "tp",
        }
    }
    # No existing TP found — place a NEW one instead of failing
    if oid is None:
        return place_tp(coin, direction, new_px, sz)
    try:
        result = exchange.modify_order(oid, coin, is_buy, sz, new_px, order_type, reduce_only=True, cloid=cloid)
        statuses = result.get("response", {}).get("data", {}).get("statuses", [])
        for s in statuses:
            if "error" in s:
                return {"success": False, "error": s["error"], "coin": coin, "type": "TP",
                        "hint": "Check: new price on correct side of current price? price rounded to tick size?"}
        return {"success": True, "coin": coin, "type": "TP", "price": new_px, "size": sz, "old_oid": oid}
    except Exception as e:
        return {"success": False, "error": str(e), "coin": coin, "type": "TP"}


def replace_sl(coin: str, direction: str, new_price: float, size: float = None) -> dict:
    """
    Replace an existing SL order with a new price (and optionally new size).
    If no existing SL is found, places a NEW SL order (handles entry-time failures).
    Returns {"success": True} on success, {"success": False, "error": ...} on failure.
    """
    _exchange_rate_limit()
    exchange = get_exchange()
    oid, cloid, existing_sz, _ = _find_open_trigger_order(coin, "sl")
    is_buy = direction.upper() == "SHORT"
    sz = float(size) if size is not None else existing_sz
    decimals = _HL_TICK_DECIMALS.get(coin, 6)
    new_px = _hl_tick_round(new_price, decimals)
    order_type = {
        "trigger": {
            "triggerPx": new_px,
            "isMarket": True,
            "tpsl": "sl",
        }
    }
    # No existing SL found — place a NEW one instead of failing
    if oid is None:
        return place_sl(coin, direction, new_px, sz)
    try:
        result = exchange.modify_order(oid, coin, is_buy, sz, new_px, order_type, reduce_only=True, cloid=cloid)
        statuses = result.get("response", {}).get("data", {}).get("statuses", [])
        for s in statuses:
            if "error" in s:
                return {"success": False, "error": s["error"], "coin": coin, "type": "SL",
                        "hint": "Check: new price on correct side of current price? price rounded to tick size?"}
        return {"success": True, "coin": coin, "type": "SL", "price": new_px, "size": sz, "old_oid": oid}
    except Exception as e:
        return {"success": False, "error": str(e), "coin": coin, "type": "SL"}


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
