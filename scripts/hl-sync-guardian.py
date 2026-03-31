#!/usr/bin/env python3
"""
hl-sync-guardian.py — Continuous watchdog that keeps HL positions in sync with paper DB.

Runs as a background daemon. Every 60s:
  1. Fetch live HL positions
  2. Fetch paper DB open trades (exchange = 'Hyperliquid')
  3. Any position in HL but not in DB → CLOSE IT (orphan = unknown position, too risky)
  4. Any position in DB but not in HL → CLOSE IT (position no longer exists)
  5. Log sync status

This is a safety net. The primary sync is done by hl-paper-sync.py.
"""
import sys, time, json, subprocess, argparse
sys.path.insert(0, '/root/.hermes/scripts')

from hyperliquid_exchange import get_open_hype_positions_curl, get_exchange

DRY = True
INTERVAL = 60  # seconds between checks
LOG_FILE = '/root/.hermes/logs/sync-guardian.log'


def log(msg, level='INFO'):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] [{level}] {msg}'
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass


def get_db_open_trades():
    """Get open trades from paper DB where exchange = Hyperliquid."""
    r = subprocess.run([
        'psql', '-U', 'postgres', '-d', 'brain', '-t', '-c',
        "SELECT token, direction, entry_price, leverage, amount_usdt FROM trades WHERE status = 'open' AND exchange = 'Hyperliquid'"
    ], capture_output=True, text=True, timeout=10)
    trades = []
    for line in r.stdout.strip().splitlines():
        if '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 5:
                trades.append({
                    'token': parts[0],
                    'direction': parts[1],
                    'entry_price': float(parts[2]) if parts[2] else 0,
                    'leverage': float(parts[3]) if parts[3] else 1,
                    'amount_usdt': float(parts[4]) if parts[4] else 50,
                })
    return trades


def close_position_hl(coin: str, reason: str) -> bool:
    """Close a position on HL. Returns True on success."""
    if DRY:
        log(f'  [DRY] Would close {coin} ({reason})', 'WARN')
        return True

    try:
        exchange = get_exchange()
        result = exchange.market_close(coin=coin, slippage=0.01)
        statuses = result.get('response', {}).get('data', {}).get('statuses', [])
        for s in statuses:
            if 'error' in s:
                log(f'  ❌ {coin}: {s["error"]}', 'FAIL')
                return False
        log(f'  ✅ {coin} closed ({reason})', 'PASS')
        return True
    except Exception as e:
        log(f'  ❌ {coin}: EXCEPTION {e}', 'FAIL')
        return False


def _poll_hl_fills_for_close(token: str, close_start_ms: int):
    """
    Poll get_trade_history() up to 3 times with 2s delay to get actual HL fill data
    for a recently-closed position.
    Returns (hl_exit_price, realized_pnl) or (0.0, 0.0) if no fills found.
    """
    from hyperliquid_exchange import get_trade_history
    for attempt in range(3):
        time.sleep(2)
        fills = get_trade_history(close_start_ms, int(time.time() * 1000))
        token_closes = [f for f in fills
                        if f['coin'].upper() == token.upper() and f['side'] == 'B']
        if token_closes:
            total_sz = sum(f['sz'] for f in token_closes)
            wavg_exit = sum(f['px'] * f['sz'] for f in token_closes) / total_sz
            realized_pnl = sum(f['closed_pnl'] for f in token_closes)
            return wavg_exit, realized_pnl
        log(f'  Fill poll attempt {attempt+1}/3 — no close fills yet for {token}', 'WARN')
    log(f'  No HL close fills found for {token} after 3 polls', 'FAIL')
    return 0.0, 0.0


def record_closed_trade(token: str, direction: str, entry_px: float, exit_px: float,
                        pnl_pct: float, lev: float, amount: float, reason: str,
                        use_hl_fills: bool = True):
    """
    Record (or update) a closed trade in the paper DB.

    If use_hl_fills=True (default): poll HL get_trade_history() for actual exit price
    and realized_pnl, then UPDATE the existing orphan record (or INSERT a new one).
    Falls back to signal-based prices if HL fills not available.

    close_reason will be set to '{reason}_hl_verified' if HL fills were found,
    otherwise just '{reason}'.
    """
    hl_exit_px  = 0.0
    real_pnl    = 0.0
    hl_verified = False

    if use_hl_fills and not DRY:
        close_start_ms = int(time.time() * 1000) - 300000  # look back 5 min
        hl_exit_px, real_pnl = _poll_hl_fills_for_close(token, close_start_ms)

    # Compute pnl_pct from HL or signal prices
    if hl_exit_px > 0 and entry_px > 0:
        if direction == 'SHORT':
            computed_pnl_pct = round((entry_px - hl_exit_px) / entry_px * 100, 4)
        else:
            computed_pnl_pct = round((hl_exit_px - entry_px) / entry_px * 100, 4)
        computed_exit = hl_exit_px
        computed_pnl_usdt = real_pnl if real_pnl != 0 else round(amount * computed_pnl_pct / 100, 4)
        hl_verified = (real_pnl != 0) or (hl_exit_px != exit_px)
    else:
        computed_pnl_pct  = pnl_pct
        computed_exit     = exit_px
        computed_pnl_usdt = round(amount * pnl_pct / 100, 2)

    actual_reason = reason if not hl_verified else f'{reason}_hl_verified'

    if DRY:
        log(f'  [DRY] Would record {token}: exit={computed_exit:.6f}, '
            f'pnl={computed_pnl_pct:.4f}%, hl_verified={hl_verified}', 'WARN')
        return

    try:
        import subprocess
        sql = f"""
        INSERT INTO trades (token, direction, entry_price, exit_price, status,
            pnl_pct, pnl_usdt, leverage, amount_usdt, exchange, paper,
            hl_entry_price, hl_exit_price, hype_pnl_usdt, hype_pnl_pct,
            close_time, close_reason, exit_reason, last_updated, updated_at)
        VALUES ('{token}', '{direction}', {entry_px}, {computed_exit}, 'closed',
            {computed_pnl_pct}, {computed_pnl_usdt}, {lev}, {amount}, 'Hyperliquid', false,
            {entry_px}, {computed_exit}, {real_pnl}, {computed_pnl_pct},
            NOW(), '{actual_reason}', '{actual_reason}', NOW(), NOW())
        """
        r = subprocess.run(['psql', '-U', 'postgres', '-d', 'brain', '-c', sql],
            capture_output=True, text=True)
        if r.returncode == 0:
            log(f'  DB recorded: {token} exit={computed_exit:.6f} '
                f'pnl={computed_pnl_pct:.4f}% hl_verified={hl_verified}', 'PASS')
        else:
            log(f'  DB record failed: {r.stderr[:100]}', 'FAIL')
    except Exception as e:
        log(f'  DB record exception: {e}', 'FAIL')


def sync():
    """Run one sync cycle."""
    log(f'── Sync cycle ──')

    # Step 1: Get HL positions
    try:
        hl_pos = get_open_hype_positions_curl()
    except Exception as e:
        log(f'Failed to fetch HL positions: {e}', 'FAIL')
        return

    # Step 2: Get paper DB open trades
    try:
        db_trades = get_db_open_trades()
    except Exception as e:
        log(f'Failed to fetch DB trades: {e}', 'FAIL')
        return

    hl_tokens = set(hl_pos.keys())
    db_tokens = {t['token'] for t in db_trades}

    orphans = sorted(hl_tokens - db_tokens)      # on HL, not in DB
    missing = sorted(db_tokens - hl_tokens)     # in DB, not on HL

    log(f'HL: {len(hl_tokens)} positions | DB: {len(db_tokens)} open trades')
    log(f'Orphans (HL only):  {orphans or "none"}')
    log(f'Missing (DB only): {missing or "none"}')

    # Step 3: Close orphans
    if orphans:
        log(f'Closing {len(orphans)} orphan(s)...', 'WARN')
        exchange = get_exchange()
        mids = exchange.info.all_mids()

        for coin in orphans:
            p = hl_pos[coin]
            entry_px = float(p['entry_px'])
            exit_px = float(mids.get(coin, 0))
            direction = p['direction']
            lev = float(p.get('leverage', 1))
            amount = float(p.get('amount_usdt', 50)) or 50

            if exit_px > 0 and entry_px > 0:
                raw = ((entry_px - exit_px) / entry_px * 100) if direction == 'SHORT' else ((exit_px - entry_px) / entry_px * 100)
                pnl_pct = round(raw * lev, 4)
            else:
                pnl_pct = 0

                success = close_position_hl(coin, 'guardian_orphan')
                if success:
                    # Wait up to 6s for fills to appear on HL before recording
                    time.sleep(6)
                    record_closed_trade(coin, direction, entry_px, exit_px, pnl_pct, lev, amount, 'guardian_orphan')
            time.sleep(3)

    # Step 4: Close missing (positions that no longer exist on HL)
    if missing:
        log(f'Syncing {len(missing)} DB-only trade(s) (position no longer on HL)...', 'WARN')
        for t in db_trades:
            if t['token'] in missing:
                sql = f"""
                UPDATE trades SET status='closed', exit_price=entry_price,
                    pnl_pct=0, pnl_usdt=0, close_time=NOW(),
                    close_reason='guardian_missing', exit_reason='guardian_missing',
                    last_updated=NOW(), updated_at=NOW()
                WHERE token='{t['token']}' AND status='open'
                """
                r = subprocess.run(['psql', '-U', 'postgres', '-d', 'brain', '-c', sql],
                    capture_output=True, text=True)
                if r.returncode == 0:
                    log(f'  DB closed: {t["token"]} (position not on HL)', 'PASS')
                else:
                    log(f'  DB close failed: {r.stderr[:100]}', 'FAIL')

    log(f'── Sync done ──')


def main():
    global DRY

    parser = argparse.ArgumentParser(description='HL sync guardian daemon')
    parser.add_argument('--apply', action='store_true', help='Actually close positions (default is dry-run)')
    parser.add_argument('--interval', type=int, default=60, help='Seconds between checks (default: 60)')
    args = parser.parse_args()

    DRY = not args.apply
    INTERVAL = args.interval

    mode = 'DRY RUN' if DRY else 'LIVE SYNC'
    log(f'hl-sync-guardian starting — {mode}, interval={INTERVAL}s', 'INFO')
    log(f'PID: {__import__("os").getpid()}', 'INFO')

    while True:
        try:
            sync()
        except Exception as e:
            log(f'Sync cycle error: {e}', 'FAIL')

        log(f'Sleeping {INTERVAL}s...', 'INFO')
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()