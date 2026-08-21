#!/usr/bin/env python3
"""
favorites_updater.py — Auto-update FAVORITES set based on rolling performance.

Runs weekly (Sunday 06:00 UTC). Promotes/demotes tokens based on criteria.

Promotion: 10+ trades (7d), WR >= 55%, avg PnL > 0
Demotion: 7d WR < 45% OR total PnL < -$0.50 (requires 2 consecutive weeks)

Reads: brain DB (trades), hermes_constants.py (current FAVORITES)
Writes: hermes_constants.py (updated FAVORITES), automation/trading_log.md

Run via: python3 scripts/favorites_updater.py
Timer: hermes-favorites-updater.timer (weekly)
"""
import os, sys, re, fcntl, json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA
from hermes_constants import FAVORITES, SHORT_BLACKLIST, LONG_BLACKLIST

CONSTANTS_FILE = '/root/.hermes/scripts/hermes_constants.py'
LOCK_FILE = '/tmp/hermes-favorites-updater.lock'
STATE_FILE = os.path.join(HERMES_DATA, 'favorites_updater_state.json')
LOG_FILE = '/root/.hermes/logs/favorites_updater.log'

# Promotion criteria (7d)
PROMO_MIN_TRADES = 10
PROMO_MIN_WR = 55.0
PROMO_MIN_AVG_PNL = 0.0

# Demotion criteria (7d)
DEMO_WR_THRESHOLD = 45.0
DEMO_TOTAL_PNL_THRESHOLD = -0.50
DEMO_CONSECUTIVE_WEEKS = 2  # require 2 bad weeks before demoting

# Candidates: tokens not currently in FAVORITES with enough history
CANDIDATE_MIN_TRADES = 10


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
        return {'bad_weeks': {}}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    Path(STATE_FILE).write_text(json.dumps(state, indent=2))


def get_all_token_stats():
    """Query 7d stats for all tokens with enough trades."""
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()

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
            ORDER BY total_pnl_usdt DESC
        """, (CANDIDATE_MIN_TRADES,))

        columns = [desc[0] for desc in cur.description]
        stats = [dict(zip(columns, row)) for row in cur.fetchall()]
        conn.close()
        return stats

    except Exception as e:
        log(f"DB query error: {e}")
        return []


def is_blacklisted(token):
    """Check if token is in any blacklist."""
    return token in SHORT_BLACKLIST or token in LONG_BLACKLIST


def update_constants_file(new_favorites):
    """Update the FAVORITES set in hermes_constants.py."""
    try:
        with open(CONSTANTS_FILE, 'r') as f:
            content = f.read()

        # Build the new FAVORITES block
        sorted_favs = sorted(new_favorites)
        lines = []
        for i, token in enumerate(sorted_favs):
            comma = ',' if i < len(sorted_favs) - 1 else ''
            lines.append(f"    '{token}'{comma}")

        new_block = "# ── Favorites ─────────────────────────────────────────────────────────────────\n"
        new_block += "# Proven performers — high WR + profitable + decent sample.\n"
        new_block += "# Cross-check: no token in SHORT_BLACKLIST or LONG_BLACKLIST.\n"
        new_block += "# AUTO-UPDATED weekly by favorites_updater.py.\n"
        new_block += "FAVORITES = {\n"
        new_block += '\n'.join(lines) + '\n'
        new_block += "}\n"

        # Replace existing FAVORITES block using regex
        pattern = r"# ── Favorites ─.*?^}\n"
        new_content = re.sub(pattern, new_block, content, flags=re.MULTILINE | re.DOTALL)

        if new_content == content:
            log("WARNING: regex replacement didn't match — FAVORITES block unchanged")
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
        return

    try:
        state = load_state()
        stats = get_all_token_stats()
        if not stats:
            log("No stats available — skipping")
            return

        current_favs = set(FAVORITES)
        new_favs = set(current_favs)
        changes = []

        # Check demotions (current favorites)
        for token in list(current_favs):
            token_stats = next((s for s in stats if s['token'] == token), None)
            if not token_stats:
                # No recent trades — not enough data to evaluate, keep
                continue

            bad_week = (
                token_stats['winrate'] < DEMO_WR_THRESHOLD
                or token_stats['total_pnl_usdt'] < DEMO_TOTAL_PNL_THRESHOLD
            )

            if bad_week:
                bad_weeks = state.get('bad_weeks', {})
                bad_weeks[token] = bad_weeks.get(token, 0) + 1
                state['bad_weeks'] = bad_weeks

                if bad_weeks[token] >= DEMO_CONSECUTIVE_WEEKS:
                    new_favs.discard(token)
                    changes.append(f"DEMOTE {token} (WR={token_stats['winrate']}%, "
                                   f"PnL=${token_stats['total_pnl_usdt']}, "
                                   f"{bad_weeks[token]} consecutive bad weeks)")
                    del bad_weeks[token]
            else:
                # Good week — reset bad week counter
                state.get('bad_weeks', {}).pop(token, None)

        # Check promotions (non-favorites)
        for token_stats in stats:
            token = token_stats['token']
            if token in current_favs or is_blacklisted(token):
                continue

            if (token_stats['trades'] >= PROMO_MIN_TRADES
                    and token_stats['winrate'] >= PROMO_MIN_WR
                    and token_stats['avg_pnl_pct'] > PROMO_MIN_AVG_PNL):
                new_favs.add(token)
                changes.append(f"PROMOTE {token} (WR={token_stats['winrate']}%, "
                               f"AvgPnL={token_stats['avg_pnl_pct']}%, "
                               f"Trades={token_stats['trades']})")

        if not changes:
            log("No changes needed")
            save_state(state)
            return

        # Apply changes
        if update_constants_file(new_favs):
            log(f"Updated FAVORITES: {len(current_favs)} → {len(new_favs)} tokens")
            for change in changes:
                log(f"  {change}")

            # Log to trading_log.md
            try:
                log_path = '/root/.hermes/automation/trading_log.md'
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                with open(log_path, 'a') as f:
                    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
                    f.write(f"\n## FAVORITES Update — {ts}\n")
                    for change in changes:
                        f.write(f"- {change}\n")
                    f.write(f"\nFinal set: {sorted(new_favs)}\n")
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
