#!/usr/bin/env python3
"""
Binance Futures Volume Alert
Alerts when a coin's volume exceeds Nx its 10-period SMA.
"""

import json
import requests
import time
from datetime import datetime, timezone
from typing import List, Optional

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL     = "https://fapi.binance.com"   # <-- change if using proxy/gateway
SCAN_SECS    = 60          # loop every N seconds
VOL_MULT     = 5.0         # fire when current_vol >= sma_vol * VOL_MULT
LIMIT        = 11          # klines: need 10 closed + 1 current
MIN_VOL      = 50_000      # minimum current volume (USD) to trigger alert
# ─────────────────────────────────────────────────────────────────────────────

session = requests.Session()
session.headers.update({"User-Agent": "volume_alert/1.0"})


def get_futures_symbols() -> List[str]:
    """Fetch all USDT-margined perpetual futures symbols. Retries on truncate."""
    for attempt in range(3):
        try:
            resp = session.get(f"{BASE_URL}/fapi/v1/exchangeInfo", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return [
                s["symbol"] for s in data["symbols"]
                if s["quoteAsset"] == "USDT"
                and s["contractType"] == "PERPETUAL"
                and s["status"] == "TRADING"
            ]
        except (json.JSONDecodeError, requests.exceptions.RequestException) as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise
    return []


def get_klines(symbol: str, limit: int = LIMIT) -> Optional[List[dict]]:
    """Fetch last N 1-minute klines. Retries on rate limit or truncate."""
    for attempt in range(3):
        try:
            resp = session.get(
                f"{BASE_URL}/fapi/v1/klines",
                params={"symbol": symbol, "interval": "1m", "limit": limit},
                timeout=10,
            )
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return [
                {
                    "open":  float(r[1]),
                    "high":  float(r[2]),
                    "low":   float(r[3]),
                    "close": float(r[4]),
                    "volume":float(r[5]),
                    "qv":    float(r[7]),
                }
                for r in resp.json()
            ]
        except (json.JSONDecodeError, requests.exceptions.RequestException):
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            return None
    return None


def fmt(n: float) -> str:
    if n >= 1_000_000_000: return f"{n/1e9:.1f}B"
    if n >= 1_000_000:    return f"{n/1e6:.1f}M"
    if n >= 1_000:        return f"{n/1e3:.1f}K"
    return f"{n:.0f}"


def main():
    print()
    print("BINANCE FUTURES VOLUME ALERT")
    print(f"  BASE_URL : {BASE_URL}")
    print(f"  Threshold: {VOL_MULT}x SMA | Min vol: ${fmt(MIN_VOL)} | Scan: {SCAN_SECS}s")
    print()

    symbols = get_futures_symbols()
    print(f"  → {len(symbols)} symbols loaded\n")

    while True:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        alert_count = 0
        errors = 0

        print(f"[{ts}] Scanning {len(symbols)} symbols...", end=" ", flush=True)

        for sym in symbols:
            try:
                klines = get_klines(sym)
                if not klines or len(klines) < LIMIT:
                    continue

                closed = klines[:10]
                cur    = klines[10]

                sma   = sum(c["qv"] for c in closed) / 10
                ratio = cur["qv"] / sma if sma else 0

                if ratio >= VOL_MULT and cur["qv"] >= MIN_VOL:
                    pct = ((cur["close"] - closed[0]["open"]) / closed[0]["open"] * 100)
                    print()
                    print(
                        f"  🚨 {sym:<12} ${cur['close']:>14,.4f}  {pct:+.2f}%  "
                        f"vol:{fmt(cur['qv'])}  sma:{fmt(sma)}  {ratio:.1f}x  "
                        f"h:{cur['high']:.4f}  l:{cur['low']:.4f}"
                    )
                    alert_count += 1

            except requests.exceptions.RequestException:
                errors += 1
            except Exception:
                errors += 1

        print(f"done | alerts:{alert_count} errors:{errors}\n")
        time.sleep(SCAN_SECS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")
        exit(0)
