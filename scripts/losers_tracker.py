#!/usr/bin/env python3
"""
losers_tracker.py — Auto-update LOSERS set based on rolling performance.

Runs daily (06:05 UTC, after favorites_updater). Identifies underperforming coins.

Promotion: 7d WR < 50% (coins with 50%+ WR are not losers)
  - Auto-disable: < 30% WR with 10+ trades
  - Consecutive losses: 5+ in a row
  - WR collapse: dropped >20pp from 30d avg
Demotion: 7d WR >= 50% (must be out for 3 days before re-adding)

Reads: brain DB (trades), hermes_constants.py (current LOSERS)
Writes: hermes_constants.py (updated LOSERS), data/losers_performance.json

Run via: python3 scripts/losers_tracker.py
Timer: hermes-losers-tracker.timer (daily 06:05 UTC)

Spec: plans/losers-list-spec.md
"""
import os, sys, re, fcntl, json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA
from hermes_constants import (
    LOSERS, LOSERS_MIN_TRADES, LOSERS_ADD_WR_THRESHOLD, LOSERS_ADD_PNL_THRESHOLD,
    LOSERS_ADD_CONSECUTIVE_LOSSES, LOSERS_ADD_WR_COLLAPSE, LOSERS_AUTO_DISABLE_WR,
    LOSERS_AUTO_DISABLE_MIN_TRADES, LOSERS_REMOVE_WR_THRESHOLD, LOSERS_REMOVE_PNL_THRESHOLD,
    LOSERS_COOLDOWN_DAYS, PENALTY_TOKENS
)

CONSTANTS_FILE = '/root/.hermes/scripts/hermes_constants.py'
LOCK_FILE = '/tmp/hermes-losers-tracker.lock'
STATE_FILE = os.path.join(HERMES_DATA, 'losers_tracker_state.json')
OUTPUT_FILE = os.path.join(HERMES_DATA, 'losers_performance.json')
SERVED_OUTPUT = '/var/www/hermes/data/losers_performance.json'
LOG_FILE = '/root/.hermes/logs/losers_tracker.log'


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    line = f"[{ts}] {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def load_state():
    try:
        return json.loads(Path(STATE_FILE).read_text())
    except Exception:
        return {'bad_days': {}, 'last_demoted': {}, 'last_promoted': {}, 'auto_disabled': []}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    Path(STATE_FILE).write_text(json.dumps(state, indent=2))


def get_all_token_stats():
    """Query 7d and 30d stats for all tokens with enough trades."""
    conn = None
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()

        # 7d stats
        cur.execute("""
            SELECT
                token,
                COUNT(*) as trades,
                ROUND(100.0 * SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) as winrate,
                ROUND(AVG(pnl_pct), 2) as avg_pnl_pct,
                ROUND(SUM(pnl_usdt), 2) as total_pnl_usdt
            FROM trades
            WHERE status = 'closed'
              AND server = 'Hermes'
              AND pnl_pct IS NOT NULL
              AND close_time > NOW() - INTERVAL '7 days'
            GROUP BY token
            HAVING COUNT(*) >= %s
            ORDER BY total_pnl_usdt ASC
        """, (LOSERS_MIN_TRADES,))

        columns = [desc[0] for desc in cur.description]
        stats_7d = {row[0]: dict(zip(columns, row)) for row in cur.fetchall()}

        # 30d stats (for WR collapse detection)
        cur.execute("""
            SELECT
                token,
                ROUND(100.0 * SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) as winrate_30d
            FROM trades
            WHERE status = 'closed'
              AND server = 'Hermes'
              AND pnl_pct IS NOT NULL
              AND close_time > NOW() - INTERVAL '30 days'
            GROUP BY token
        """)

        stats_30d = {row[0]: row[1] for row in cur.fetchall()}

        # Consecutive losses — count losses from most recent trade backward
        consec_losses = {}
        for token in stats_7d:
            cur.execute("""
                SELECT pnl_pct FROM trades
                WHERE token = %s AND status = 'closed' AND server = 'Hermes'
                  AND close_time > NOW() - INTERVAL '7 days'
                ORDER BY close_time DESC
            """, (token,))
            losses = 0
            for (pnl,) in cur.fetchall():
                if pnl is not None and pnl <= 0:
                    losses += 1
                else:
                    break
            if losses > 0:
                consec_losses[token] = losses

        # Merge stats
        for token in stats_7d:
            stats_7d[token]['winrate_30d'] = stats_30d.get(token)
            stats_7d[token]['consecutive_losses'] = consec_losses.get(token, 0)

        return stats_7d

    except Exception as e:
        log(f"DB query error: {e}")
        return {}
    finally:
        if conn:
            try: conn.close()
            except Exception: pass


def is_blacklisted(token):
    """Check if token is in any blacklist."""
    from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
    return token in SHORT_BLACKLIST or token in LONG_BLACKLIST


def update_constants_file(new_losers):
    """Update the LOSERS set in hermes_constants.py."""
    try:
        with open(CONSTANTS_FILE, 'r') as f:
            content = f.read()

        # Build the new LOSERS block
        sorted_losers = sorted(new_losers)
        if sorted_losers:
            lines = []
            for i, token in enumerate(sorted_losers):
                comma = ',' if i < len(sorted_losers) - 1 else ''
                lines.append(f"    '{token}'{comma}")
            new_block = "LOSERS = {\n" + '\n'.join(lines) + "\n}\n"
        else:
            new_block = "LOSERS = set()\n"

        # Replace existing LOSERS block using regex
        pattern = r"^LOSERS = \{.*?\}|^LOSERS = set\(\)"
        new_content = re.sub(pattern, new_block, content, flags=re.MULTILINE | re.DOTALL)

        if new_content == content:
            log("WARNING: regex replacement didn't match — LOSERS block unchanged")
            return False

        with open(CONSTANTS_FILE, 'w') as f:
            f.write(new_content)

        return True

    except Exception as e:
        log(f"Error updating constants: {e}")
        return False


def run():
    lock_fd = None
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        log("Another instance running — skipping")
        if lock_fd:
            try: lock_fd.close()
            except Exception: pass
        return

    try:
        state = load_state()
        stats = get_all_token_stats()
        if not stats:
            log("No stats available — skipping")
            return

        current_losers = set(LOSERS)
        new_losers = set(current_losers)
        changes = []
        today = datetime.now(timezone.utc).isoformat()

        # ── Check for removals (recovery or insufficient data) ──────────
        for token in list(current_losers):
            token_stats = stats.get(token)

            # Remove if no recent trades or insufficient data
            if not token_stats or token_stats.get('trades', 0) < LOSERS_MIN_TRADES:
                new_losers.discard(token)
                state.get('bad_days', {}).pop(token, None)
                changes.append(f"REMOVE {token} (insufficient data)")
                continue

            wr = token_stats['winrate']
            pnl = token_stats['total_pnl_usdt']

            # Remove if WR >= 50% (not a loser regardless of PnL)
            if wr >= LOSERS_REMOVE_WR_THRESHOLD:
                # Check cooldown
                last_demoted = state.get('last_demoted', {}).get(token)
                if last_demoted:
                    try:
                        demote_date = datetime.fromisoformat(last_demoted)
                        days_since = (datetime.now(timezone.utc) - demote_date).days
                        if days_since < LOSERS_COOLDOWN_DAYS:
                            continue
                    except Exception:
                        pass

                new_losers.discard(token)
                state.get('bad_days', {}).pop(token, None)
                changes.append(f"REMOVE {token} (WR={wr}%, PnL=${pnl:.2f}, recovered)")

        # ── Check for additions ────────────────────────────────────────
        for token, token_stats in stats.items():
            if token in current_losers or is_blacklisted(token):
                continue

            wr = token_stats['winrate']
            pnl = token_stats['total_pnl_usdt']
            trades = token_stats['trades']
            consec = token_stats.get('consecutive_losses', 0)
            wr_30d = token_stats.get('winrate_30d')

            reason = None

            # Only add to losers if WR < 60% (coins with 60%+ WR are not losers)
            if wr >= LOSERS_ADD_WR_THRESHOLD:
                continue

            # Check auto-disable (dead zone) — worst first
            if wr < LOSERS_AUTO_DISABLE_WR and trades >= LOSERS_AUTO_DISABLE_MIN_TRADES:
                reason = f"dead_zone ({wr}% WR, {trades} trades)"
            # Check consecutive losses
            elif consec >= LOSERS_ADD_CONSECUTIVE_LOSSES:
                reason = f"consecutive_losses ({consec})"
            # Check WR collapse
            elif wr_30d and (wr_30d - wr) >= LOSERS_ADD_WR_COLLAPSE:
                reason = f"wr_collapse ({wr_30d}% → {wr}%)"
            # Check negative PnL (only if WR is already below threshold)
            elif pnl < LOSERS_ADD_PNL_THRESHOLD:
                reason = f"negative_pnl (${pnl:.2f})"
            # Default: low WR
            else:
                reason = f"low_wr ({wr}%)"

            if reason:
                new_losers.add(token)
                changes.append(f"ADD {token} (WR={wr}%, PnL=${pnl:.2f}, {reason})")

        # Always write performance JSON first
        try:
            losers_data = []
            for token in sorted(new_losers):
                token_stats = stats.get(token, {})
                losers_data.append({
                    'token': token,
                    'trades': int(token_stats.get('trades', 0)),
                    'winrate': float(token_stats.get('winrate', 0)),
                    'total_pnl_usdt': float(token_stats.get('total_pnl_usdt', 0)),
                    'consecutive_losses': int(token_stats.get('consecutive_losses', 0)),
                    'reason': 'in_losers'
                })

            output = {
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'losers_count': len(new_losers),
                'losers': losers_data,
            }

            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(output, f, indent=2)

            # Also write to served directory
            try:
                os.makedirs(os.path.dirname(SERVED_OUTPUT), exist_ok=True)
                with open(SERVED_OUTPUT, 'w') as f:
                    json.dump(output, f, indent=2)
            except Exception:
                pass
        except Exception as e:
            log(f"Error writing performance JSON: {e}")

        if not changes:
            log(f"No changes needed (losers={len(current_losers)})")
            save_state(state)
            return

        # Apply changes
        if changes:
            if update_constants_file(new_losers):
                log(f"Updated LOSERS: {len(current_losers)} → {len(new_losers)} tokens")
                for change in changes:
                    log(f"  {change}")

                # Log to trading_log.md
                try:
                    log_path = '/root/.hermes/automation/trading_log.md'
                    os.makedirs(os.path.dirname(log_path), exist_ok=True)
                    with open(log_path, 'a') as f:
                        ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
                        f.write(f"\n## LOSERS Update — {ts}\n")
                        for change in changes:
                            f.write(f"- {change}\n")
                        f.write(f"\nFinal set: {sorted(new_losers)}\n")
                except Exception:
                    pass

        save_state(state)

    except Exception as e:
        log(f"Error: {e}")
    finally:
        if lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()


if __name__ == '__main__':
    run()
