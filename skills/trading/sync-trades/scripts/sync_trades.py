#!/usr/bin/env python3
"""
sync_trades.py — Reconcile HL fills CSV → signals_hermes_runtime.db signal_outcomes

Safe: read-only on HL, no trades placed. Upserts by (token, pnl_usdt, closed_at).
Uses dir field to identify open/close — each row = one fill.
"""
import csv, sqlite3, sys, argparse
from collections import defaultdict, Counter
from datetime import datetime

# ── Paths ────────────────────────────────────────────────────────────────────
HL_FILLS   = "/root/.hermes/data/hl_fills_0x324a9713603863FE3A678E83d7a81E20186126E7.csv"
RUNTIME_DB = "/root/.hermes/data/signals_hermes_runtime.db"

# Known bad actors — skip recording their outcomes
SKIP_COINS = {"STG", "STRAX"}

# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_fills(path: str):
    """Load HL fills CSV. Each row = one fill. Returns list of dicts."""
    with open(path) as f:
        return list(csv.DictReader(f))


def get_existing_keys(db_path: str):
    """Return set of (token, round(pnl_usdt,4), closed_at) already in signal_outcomes."""
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()
    cur.execute("SELECT token, ROUND(pnl_usdt,4), closed_at FROM signal_outcomes")
    rows = set(cur.fetchall())
    conn.close()
    return rows


def upsert_outcomes(trades: list, db_path: str, dry_run: bool = True):
    """
    Insert trades into signal_outcomes.
    Dedup: skip if (token, round(pnl_usdt,4), closed_at) already exists.
    Returns (inserted, skipped, errors).
    """
    existing = get_existing_keys(db_path)
    inserted = skipped = errors = 0

    for t in trades:
        key = (t["token"], round(t["pnl_usdt"], 4), t["trade_date"])
        if key in existing:
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY] + {t['token']} {t['direction']} pnl={t['pnl_usdt']:+.4f} ({t['trade_date']})")
            inserted += 1
            continue

        try:
            conn = sqlite3.connect(db_path)
            cur  = conn.cursor()
            cur.execute("""
                INSERT INTO signal_outcomes
                  (token, direction, signal_type, is_win, pnl_pct, pnl_usdt,
                   confidence, created_at, closed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                t["token"], t["direction"], "hl_reconcile",
                t["is_win"], t["pnl_pct"], t["pnl_usdt"],
                50.0, t["trade_date"], t["trade_date"]
            ))
            conn.commit()
            conn.close()
            inserted += 1
        except Exception as e:
            print(f"  ERROR {t['token']}: {e}")
            errors += 1

    return inserted, skipped, errors


# ── Trade reconstruction ──────────────────────────────────────────────────────

def reconstruct_trades_by_coin(fills: list):
    """
    Group fills by coin, then reconstruct open→close pairs.

    HL fill schema:
      dir = "Open Long" | "Open Short" | "Close Long" | "Close Short"
             | "Long > Short" | "Short > Long"   (flip trades)
      side = "B" (open) or "A" (close)
      closedPnl = 0 for open fills, ≠0 for close fills

    Strategy: pair "Open*" fills with the next "Close*" fill for same coin.
    Flip trades (Long>Short / Short>Long) are treated as a single close+open.
    """
    # Group by coin, sorted by trade_date
    by_coin = defaultdict(list)
    for f in fills:
        by_coin[f["coin"]].append(f)

    for coin in by_coin:
        by_coin[coin].sort(key=lambda f: f["trade_date"])

    MIN_PNL_THRESHOLD = 0.10  # Skip fills with |pnl| < $0.10 (HFT noise)
    trades = []

    for coin, fs in by_coin.items():
        if coin in SKIP_COINS:
            continue

        i = 0
        while i < len(fs):
            f = fs[i]
            fdir = f["dir"]

            # ── Normal open ───────────────────────────────────────────────
            if fdir in ("Open Long", "Open Short"):
                direction = "LONG" if fdir == "Open Long" else "SHORT"
                entry_px  = float(f["px"])
                size      = float(f["sz"])

                # Find matching close fill
                j = i + 1
                while j < len(fs):
                    cf = fs[j]
                    cdir = cf["dir"]
                    if cdir in ("Close Long", "Close Short"):
                        # Match by direction
                        if (direction == "LONG" and cdir == "Close Long") or \
                           (direction == "SHORT" and cdir == "Close Short"):
                            break
                        # Mismatch: skip it (could be flip)
                        j += 1
                        continue
                    elif cdir in ("Long > Short", "Short > Long"):
                        # Flip = close + reverse direction immediately
                        break
                    else:
                        j += 1
                else:
                    # No close found — still open, skip
                    i += 1
                    continue

                cf          = fs[j]
                exit_px     = float(cf["px"])
                closed_pnl  = float(cf.get("closedPnl") or 0)
                fee         = float(cf.get("fee") or 0)
                trade_date  = cf["trade_date"]
                pnl_usdt    = closed_pnl
                notional    = entry_px * size
                pnl_pct     = (closed_pnl / notional * 100) if notional else 0.0
                is_win      = 1 if pnl_usdt > 0 else 0

                if abs(closed_pnl) < MIN_PNL_THRESHOLD:
                    i = j + 1
                    continue  # Skip micro-fill HFT noise

                trades.append({
                    "token":      coin,
                    "direction":  direction,
                    "entry_px":   entry_px,
                    "exit_px":    exit_px,
                    "size":       size,
                    "closed_pnl": closed_pnl,
                    "fee":        fee,
                    "pnl_pct":    pnl_pct,
                    "pnl_usdt":   pnl_usdt,
                    "is_win":     is_win,
                    "trade_date": trade_date,
                })
                i = j + 1
                continue

            # ── Flip trades (Long>Short / Short>Long) ──────────────────────
            elif fdir in ("Long > Short", "Short > Long"):
                # Flip = close old direction + open new direction
                # Treat as a single closed trade with the pnl from this fill
                old_dir    = "LONG" if fdir == "Long > Short" else "SHORT"
                closed_pnl = float(f.get("closedPnl") or 0)
                pnl_usdt   = closed_pnl
                trade_date = f["trade_date"]
                entry_px   = float(f["px"])
                size       = float(f["sz"])
                pnl_pct    = (closed_pnl / (entry_px * size) * 100) if entry_px * size else 0.0

                if abs(closed_pnl) < MIN_PNL_THRESHOLD:
                    i += 1
                    continue  # Skip micro-fill HFT noise

                trades.append({
                    "token":      coin,
                    "direction":  old_dir,
                    "entry_px":   entry_px,
                    "exit_px":    float(f["px"]),
                    "size":       size,
                    "closed_pnl": closed_pnl,
                    "fee":        float(f.get("fee") or 0),
                    "pnl_pct":    pnl_pct,
                    "pnl_usdt":   pnl_usdt,
                    "is_win":     1 if pnl_usdt > 0 else 0,
                    "trade_date": trade_date,
                })
                i += 1
                continue

            else:
                # "Close Long" / "Close Short" without a preceding open
                # (already handled by being consumed as close fill above)
                i += 1
                continue

    return trades


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Sync HL fills → Hermes signal_outcomes")
    parser.add_argument("--no-dry-run", action="store_true",
                        help="Actually insert into DB (default is dry-run)")
    parser.add_argument("--hl-fills",   default=HL_FILLS)
    parser.add_argument("--db",         default=RUNTIME_DB)
    args = parser.parse_args()

    print(f"[sync_trades] HL fills : {args.hl_fills}")
    print(f"[sync_trades] Runtime DB: {args.db}")
    print(f"[sync_trades] Dry-run   : {not args.no_dry_run}")
    print()

    # 1. Load fills
    print(f"[1] Loading fills ...")
    fills = parse_fills(args.hl_fills)
    print(f"    Total rows: {len(fills)}")

    dir_counts = Counter(f["dir"] for f in fills)
    print(f"    Breakdown:")
    for d, n in dir_counts.most_common():
        print(f"      {d}: {n}")

    # 2. Reconstruct trades
    print(f"\n[2] Reconstructing trades by coin ...")
    trades = reconstruct_trades_by_coin(fills)
    print(f"    Closed trades reconstructed: {len(trades)}")

    if not trades:
        print("    Nothing to sync — check grouping logic")
        sys.exit(0)

    # 3. Summary
    print(f"\n[3] Summary by coin:")
    by_coin = Counter(t["token"] for t in trades)
    total_pnl = sum(t["pnl_usdt"] for t in trades)
    total_wins = sum(1 for t in trades if t["is_win"])
    for coin, cnt in sorted(by_coin.items(), key=lambda x: -x[1])[:15]:
        wins = sum(1 for t in trades if t["token"] == coin and t["is_win"])
        cp   = sum(t["pnl_usdt"] for t in trades if t["token"] == coin)
        print(f"      {coin:12s} {cnt:3d} trades  {wins:2d}W/{cnt-wins:2d}L  pnl={cp:+.4f}")

    print(f"\n    TOTAL: {len(trades)} trades, {total_wins}W/{len(trades)-total_wins}L, net_pnl={total_pnl:+.4f}")

    # 4. Dedup check
    print(f"\n[4] Checking existing outcomes in DB ...")
    existing = get_existing_keys(args.db)
    print(f"    Already present: {len(existing)} outcomes")

    # 5. Upsert
    print(f"\n[5] Upserting into {args.db} ...")
    inserted, skipped, errors = upsert_outcomes(trades, args.db, dry_run=not args.no_dry_run)
    print(f"    inserted={inserted}  skipped={skipped}  errors={errors}")

    if errors > 0:
        print(f"\n⚠️  {errors} errors — review above")
        sys.exit(1)
    elif inserted == 0 and skipped > 0:
        print(f"\n✅ All {skipped} trades already in DB — nothing new to sync")
    elif not args.no_dry_run:
        print(f"\n✅ Dry run complete — {inserted} would be inserted.")
        print(f"   Run with --no-dry-run to write.")
    else:
        print(f"\n✅ Done — {inserted} outcomes written, {skipped} skipped (already present)")


if __name__ == "__main__":
    main()
