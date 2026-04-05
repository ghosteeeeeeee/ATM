#!/usr/bin/env python3
"""
Stale Trades Audit — check and fix stale signals and positions.
Usage: python3 check.py        # audit only
       python3 check.py --fix   # audit + apply fixes
"""
import sys, time, argparse
from datetime import datetime

sys.path.insert(0, '/root/.hermes/scripts')

# ── Signal Staleness ──────────────────────────────────────────────────────────
import sqlite3

SIGNALS_DB = '/root/.hermes/data/signals_hermes_runtime.db'

def audit_signals(fix=False):
    """Check and optionally fix stale signals."""
    conn = sqlite3.connect(SIGNALS_DB)
    cur = conn.cursor()
    results = {}

    # 1. Stale APPROVED (>1h not executed)
    cur.execute("""
        SELECT id, token, direction, created_at, confidence
        FROM signals
        WHERE decision='APPROVED' AND executed=0
        AND created_at < datetime('now', '-1 hour')
    """)
    stale_approved = cur.fetchall()
    results['stale_approved'] = len(stale_approved)
    if stale_approved:
        print(f"[SIGNAL] Stale APPROVED (>1h, not executed): {len(stale_approved)}")
        for r in stale_approved:
            print(f"  {r[1]:10} {r[2]:6} {r[3]} conf={r[4]:.0f}%")
        if fix:
            ids = [str(r[0]) for r in stale_approved]
            placeholders = ','.join(['?' for _ in ids])
            cur.execute(f"""
                UPDATE signals
                SET decision='EXPIRED', executed=1, deescalation_reason='stale_approved_1h'
                WHERE id IN ({placeholders})
            """, [r[0] for r in stale_approved])
            print(f"  -> Marked {cur.rowcount} as EXPIRED")

    # 2. Stale PENDING (>3h, never reviewed rc=0)
    cur.execute("""
        SELECT id, token, direction, created_at, review_count, confidence
        FROM signals
        WHERE decision='PENDING' AND executed=0 AND review_count=0
        AND created_at < datetime('now', '-3 hours')
    """)
    stale_pending = cur.fetchall()
    results['stale_pending'] = len(stale_pending)
    if stale_pending:
        print(f"[SIGNAL] Stale PENDING (>3h, never reviewed rc=0): {len(stale_pending)}")
        for r in stale_pending:
            print(f"  {r[1]:10} {r[2]:6} {r[3]} conf={r[5]:.0f}%")
        if fix:
            ids = [str(r[0]) for r in stale_pending]
            placeholders = ','.join(['?' for _ in ids])
            cur.execute(f"""
                UPDATE signals
                SET decision='EXPIRED', executed=1, deescalation_reason='stale_pending_3h'
                WHERE id IN ({placeholders})
            """, [r[0] for r in stale_pending])
            print(f"  -> Marked {cur.rowcount} as EXPIRED")

    # 3. PURGE candidates (rc>=5)
    cur.execute("""
        SELECT id, token, direction, compact_rounds, created_at, confidence
        FROM signals
        WHERE decision='PENDING' AND executed=0
        AND compact_rounds >= 5
    """)
    purge = cur.fetchall()
    results['purge'] = len(purge)
    if purge:
        print(f"[SIGNAL] PURGE candidates (PENDING, rc>=5): {len(purge)}")
        from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
        from tokens import is_solana_only
        for r in purge:
            tok = r[1]; direction = r[2]; conf = r[5]
            sol = is_solana_only(tok)
            blk = (direction.upper() == 'SHORT' and tok in SHORT_BLACKLIST) or \
                  (direction.upper() == 'LONG' and tok in LONG_BLACKLIST)
            print(f"  {tok:10} {direction:6} cr={r[3]} {r[4]} conf={conf:.0f}% sol={sol} blk={blk}")
        if fix:
            ids = [str(r[0]) for r in purge]
            placeholders = ','.join(['?' for _ in ids])
            cur.execute(f"""
                UPDATE signals
                SET decision='EXPIRED', executed=1, deescalation_reason='purge-rc5'
                WHERE id IN ({placeholders})
            """, [r[0] for r in purge])
            print(f"  -> PURGED {cur.rowcount} signals")

    if not any(results.values()):
        print("[SIGNAL] No stale signals found ✅")

    conn.commit()
    conn.close()
    return results


# ── Position Staleness ────────────────────────────────────────────────────────
def audit_positions(fix=False):
    """Check and optionally fix stale positions."""
    from position_manager import (
        check_and_manage_positions, SPEED_TRACKER,
        STALE_LOSER_MAX_LOSS, STALE_WINNER_MIN_PROFIT,
        STALE_LOSER_TIMEOUT_MINUTES, STALE_WINNER_TIMEOUT_MINUTES,
        STALE_VELOCITY_THRESHOLD
    )
    from hyperliquid_exchange import get_open_hype_positions_curl

    print(f"\n[POSITION] Staleness thresholds:")
    print(f"  Loser: pnl<={STALE_LOSER_MAX_LOSS}%, stalled {STALE_LOSER_TIMEOUT_MINUTES}+min -> CUT")
    print(f"  Winner: pnl>={STALE_WINNER_MIN_PROFIT}%, stalled {STALE_WINNER_TIMEOUT_MINUTES}+min -> CUT")
    print(f"  Stall: speed_pctl<33 AND vel<{STALE_VELOCITY_THRESHOLD}%/5m")

    # Update speed tracker once
    if SPEED_TRACKER is not None:
        SPEED_TRACKER.update()
        print(f"  SpeedTracker updated ✅")
    else:
        print(f"  SpeedTracker DISABLED ⚠️  (cannot detect staleness)")

    positions = get_open_hype_positions_curl()
    print(f"\n[POSITION] Open: {len(positions)}")

    stale_cuts = []
    ok_count = 0

    for tok, pos in sorted(positions.items()):
        entry = float(pos.get('entry_px', 0))
        cur_p = float(pos.get('current_px', 0))
        direction = pos.get('direction', 'LONG')
        if entry > 0 and cur_p > 0:
            pnl = ((cur_p - entry) / entry * 100) if direction == 'LONG' else ((entry - cur_p) / entry * 100)
        else:
            pnl = 0.0

        if SPEED_TRACKER:
            spd = SPEED_TRACKER.get_token_speed(tok)
            if spd:
                vel = spd.get('price_velocity_5m', 0)
                pctl = spd.get('speed_percentile', 50)
                last_move = spd.get('last_move_at', None)
                stalled = pctl < 33 and abs(vel) < STALE_VELOCITY_THRESHOLD
                stale_min = 0
                if last_move:
                    try:
                        lm = datetime.fromisoformat(last_move.replace('Z', '+00:00'))
                        stale_min = int((time.time() - lm.timestamp()) / 60)
                    except:
                        pass

                loser_stale = pnl <= STALE_LOSER_MAX_LOSS and stalled and stale_min >= STALE_LOSER_TIMEOUT_MINUTES
                winner_stale = pnl >= STALE_WINNER_MIN_PROFIT and stalled and stale_min >= STALE_WINNER_TIMEOUT_MINUTES
                would_cut = loser_stale or winner_stale

                status = '🔴 CUT' if would_cut else '✅ OK'
                reason = ''
                if loser_stale:
                    reason = f'loser_stall pnl={pnl:+.1f}% spd={pctl:.0f} vel={vel:+.3f}% {stale_min}m'
                elif winner_stale:
                    reason = f'winner_stall pnl={pnl:+.1f}% spd={pctl:.0f} vel={vel:+.3f}% {stale_min}m'

                print(f"  {tok:10} {direction:6} pnl={pnl:+.2f}% speed={pctl:.0f} vel={vel:+.3f}% stale={stale_min}m stalled={stalled} -> {status}" +
                      (f' [{reason}]' if reason else ''))

                if would_cut:
                    stale_cuts.append((tok, direction, pnl, reason))
                else:
                    ok_count += 1
            else:
                print(f"  {tok:10} {direction:6} pnl={pnl:+.2f}% speed=NO DATA ⚠️")
                ok_count += 1
        else:
            print(f"  {tok:10} {direction:6} pnl={pnl:+.2f}% SpeedTracker=None -> skipped")
            ok_count += 1

    print(f"\n  Summary: {ok_count} OK | {len(stale_cuts)} would-cut")

    if stale_cuts and fix:
        print(f"\n[POSITION] Running check_and_manage_positions() with fix=True...")
        try:
            open_n, closed_n, adjusted_n = check_and_manage_positions()
            print(f"  Result: open={open_n} closed={closed_n} adjusted={adjusted_n}")
        except Exception as e:
            print(f"  ERROR: {e}")

    return stale_cuts


def main():
    parser = argparse.ArgumentParser(description='Stale trades audit')
    parser.add_argument('--fix', action='store_true', help='Apply fixes')
    args = parser.parse_args()

    print("=" * 60)
    print("STALE TRADES AUDIT")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    sig_results = audit_signals(fix=args.fix)
    pos_cuts = audit_positions(fix=args.fix)

    print("\n" + "=" * 60)
    if not any(sig_results.values()) and not pos_cuts:
        print("All clean ✅")
    else:
        if sig_results.get('stale_approved') or sig_results.get('stale_pending') or sig_results.get('purge'):
            print(f"Signal issues: {sum(sig_results.values())} total — run with --fix to resolve")
        if pos_cuts:
            print(f"Position cuts needed: {len(pos_cuts)} — run with --fix to execute")
    print("=" * 60)


if __name__ == '__main__':
    main()
