#!/usr/bin/env python3
"""
favorites_updater.py — Auto-update FAVORITES set based on rolling performance.

Runs daily (06:00 UTC). Promotes/demotes tokens based on 7d rolling stats.

Promotion: 5+ trades (7d), WR >= 58%, avg PnL > 0.1%
Demotion: 7d WR < 48% OR total PnL < -$0.25 (requires 3 consecutive bad days)

Reads: brain DB (trades), hermes_constants.py (current FAVORITES),
       data/favorites_rhythm.json (cluster/correlation data for decision influence)
Writes: hermes_constants.py (updated FAVORITES), automation/trading_log.md

Run via: python3 scripts/favorites_updater.py
Timer: hermes-favorites-updater.timer (daily 06:00 UTC)

Spec: plans/favorites-daily-update-spec.md
"""
import os, sys, re, fcntl, json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from math import isnan

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA
from hermes_constants import FAVORITES, SHORT_BLACKLIST, LONG_BLACKLIST

CONSTANTS_FILE = '/root/.hermes/scripts/hermes_constants.py'
LOCK_FILE = '/tmp/hermes-favorites-updater.lock'
STATE_FILE = os.path.join(HERMES_DATA, 'favorites_updater_state.json')
RHYTHM_FILE = os.path.join(HERMES_DATA, 'favorites_rhythm.json')
LOG_FILE = '/root/.hermes/logs/favorites_updater.log'

# ── Promotion criteria (7d rolling) ─────────────────────────────────────
PROMO_MIN_TRADES = 5          # lowered from 10 — daily cadence catches faster
PROMO_MIN_WR = 58.0           # raised from 55 — need stronger signal for daily
PROMO_MIN_AVG_PNL = 0.1       # raised from 0.0 — must be actually profitable

# ── Demotion criteria (7d rolling) ──────────────────────────────────────
DEMO_WR_THRESHOLD = 48.0      # raised from 45 — catch underperformers faster
DEMO_TOTAL_PNL_THRESHOLD = -0.25  # tightened from -0.50
DEMO_CONSECUTIVE_DAYS = 3     # 3 bad evaluations = demoted (was 2 weeks)

# ── Candidates: tokens not in FAVORITES with enough history ─────────────
CANDIDATE_MIN_TRADES = 5

# ── Anti-churn ──────────────────────────────────────────────────────────
ANTI_CHURN_COOLDOWN_DAYS = 2  # must be out for ≥2 days before re-promotion

# ── Rhythm bonus thresholds ─────────────────────────────────────────────
RHYTHM_CLUSTER_BONUS_WR = 2.0  # +2% WR threshold if in same wave as 2+ favs
RHYTHM_REGIME_ADJUSTMENT = 2.0  # ±2% WR adjustment based on regime fit


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
    """Load state. Supports legacy format (bad_weeks) and new format (bad_days)."""
    try:
        state = json.loads(Path(STATE_FILE).read_text())
        # Migrate legacy format
        if 'bad_weeks' in state and 'bad_days' not in state:
            state['bad_days'] = state.pop('bad_weeks')
        if 'bad_days' not in state:
            state['bad_days'] = {}
        if 'last_demoted' not in state:
            state['last_demoted'] = {}
        if 'last_promoted' not in state:
            state['last_promoted'] = {}
        return state
    except Exception:
        return {'bad_days': {}, 'last_demoted': {}, 'last_promoted': {}}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    Path(STATE_FILE).write_text(json.dumps(state, indent=2))


def load_rhythm():
    """Load rhythm analysis data if available. Returns empty dict on failure."""
    try:
        return json.loads(Path(RHYTHM_FILE).read_text())
    except Exception:
        return {}


def get_all_token_stats():
    """Query 7d stats for all tokens with enough trades."""
    conn = None
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
        return stats

    except Exception as e:
        log(f"DB query error: {e}")
        return []
    finally:
        if conn:
            try: conn.close()
            except Exception: pass


def get_current_regime():
    """Get current market regime from the regime scanner output."""
    try:
        # Try regime_15m.json first (15m scanner output)
        regime_file = '/var/www/hermes/data/regime_15m.json'
        if os.path.exists(regime_file):
            data = json.loads(Path(regime_file).read_text())
            return data.get('aggregate', {}).get('overall', 'unknown')
        # Fallback to regime_5m.json
        regime_file = '/var/www/hermes/data/regime_5m.json'
        if os.path.exists(regime_file):
            data = json.loads(Path(regime_file).read_text())
            return data.get('aggregate', {}).get('overall', 'unknown')
        return 'unknown'
    except Exception:
        return 'unknown'


def is_blacklisted(token):
    """Check if token is in any blacklist."""
    return token in SHORT_BLACKLIST or token in LONG_BLACKLIST


def get_cluster_bonus(token, rhythm, current_favs):
    """Calculate promotion bonus if token is in same wave cluster as existing favorites."""
    if not rhythm:
        return 0

    clusters = rhythm.get('clusters', {}).get('temporal', {}).get('groups', [])
    for cluster in clusters:
        coins = cluster.get('coins', [])
        if token in coins:
            # Count how many existing favorites are in this cluster
            fav_overlap = len(set(coins) & current_favs)
            if fav_overlap >= 2:
                return RHYTHM_CLUSTER_BONUS_WR
    return 0


def get_regime_adjustment(token, rhythm, current_regime):
    """Adjust WR thresholds based on regime fit from rhythm data."""
    if not rhythm or current_regime == 'unknown':
        return 0

    regime_matrix = rhythm.get('clusters', {}).get('regime', {}).get('matrix', {})
    token_regimes = regime_matrix.get(token, {})
    if not token_regimes:
        return 0

    # Get token's performance in current regime vs average across all regimes
    # Regime values are dicts: {'trades': N, 'avg_pnl': X, 'wr': Y}
    current_regime_data = token_regimes.get(current_regime)
    if current_regime_data is None:
        return 0

    # Extract WR from regime data (handle both dict and plain float formats)
    if isinstance(current_regime_data, dict):
        current_wr = current_regime_data.get('wr', 0)
    else:
        current_wr = current_regime_data

    if isnan(current_wr):
        return 0

    all_wrs = []
    for v in token_regimes.values():
        if isinstance(v, dict):
            wr = v.get('wr', 0)
        else:
            wr = v
        if wr is not None and not isnan(wr):
            all_wrs.append(wr)

    if not all_wrs:
        return 0

    avg_wr = sum(all_wrs) / len(all_wrs)
    if current_wr > avg_wr:
        return -RHYTHM_REGIME_ADJUSTMENT  # lower WR threshold (easier to promote)
    elif current_wr < avg_wr * 0.7:
        return RHYTHM_REGIME_ADJUSTMENT   # raise WR threshold (harder to promote)
    return 0


def is_anti_churn_blocked(token, state):
    """Check if token is blocked by anti-churn cooldown."""
    last_demoted = state.get('last_demoted', {}).get(token)
    if not last_demoted:
        return False
    try:
        demote_date = datetime.fromisoformat(last_demoted)
        days_since = (datetime.now(timezone.utc) - demote_date).days
        return days_since < ANTI_CHURN_COOLDOWN_DAYS
    except Exception:
        return False


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
        new_block += "# AUTO-UPDATED daily by favorites_updater.py.\n"
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
        rhythm = load_rhythm()
        current_regime = get_current_regime()
        stats = get_all_token_stats()
        if not stats:
            log("No stats available — skipping")
            return

        current_favs = set(FAVORITES)
        new_favs = set(current_favs)
        changes = []
        today = datetime.now(timezone.utc).isoformat()

        # ── Demotions ───────────────────────────────────────────────────
        for token in list(current_favs):
            token_stats = next((s for s in stats if s['token'] == token), None)
            if not token_stats:
                # No recent trades — inactivity demotion after 7 days
                # Check how long since last trade
                conn = None
                try:
                    import psycopg2
                    from _secrets import BRAIN_DB_DICT
                    conn = psycopg2.connect(**BRAIN_DB_DICT)
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT MAX(close_time) FROM trades
                        WHERE token = %s AND server = 'Hermes' AND status = 'closed'
                    """, (token,))
                    row = cur.fetchone()
                    if row and row[0]:
                        last_trade = row[0]
                        if last_trade.tzinfo is None:
                            from datetime import timezone as tz
                            last_trade = last_trade.replace(tzinfo=tz.utc)
                        days_inactive = (datetime.now(timezone.utc) - last_trade).days
                        if days_inactive >= 7:
                            new_favs.discard(token)
                            changes.append(f"DEMOTE {token} (inactive {days_inactive}d, no trades)")
                    else:
                        # Never traded — demote
                        new_favs.discard(token)
                        changes.append(f"DEMOTE {token} (no trade history)")
                except Exception as e:
                    log(f"  Inactivity check failed for {token}: {e}")
                finally:
                    if conn:
                        try: conn.close()
                        except Exception: pass
                continue

            # Apply regime adjustment to demotion threshold
            regime_adj = get_regime_adjustment(token, rhythm, current_regime)
            adjusted_demo_wr = DEMO_WR_THRESHOLD - regime_adj  # inverted: good regime = harder to demote

            bad_day = (
                token_stats['winrate'] < adjusted_demo_wr
                or token_stats['total_pnl_usdt'] < DEMO_TOTAL_PNL_THRESHOLD
            )

            if bad_day:
                bad_days = state.get('bad_days', {})
                bad_days[token] = bad_days.get(token, 0) + 1
                state['bad_days'] = bad_days

                if bad_days[token] >= DEMO_CONSECUTIVE_DAYS:
                    new_favs.discard(token)
                    changes.append(f"DEMOTE {token} (WR={token_stats['winrate']}%, "
                                   f"PnL=${token_stats['total_pnl_usdt']}, "
                                   f"{bad_days[token]} consecutive bad days, "
                                   f"regime={current_regime})")
                    del bad_days[token]
                    state.setdefault('last_demoted', {})[token] = today
            else:
                # Good day — reset bad day counter
                state.get('bad_days', {}).pop(token, None)

        # ── Promotions ──────────────────────────────────────────────────
        for token_stats in stats:
            token = token_stats['token']
            if token in current_favs or is_blacklisted(token):
                continue

            # Anti-churn check
            if is_anti_churn_blocked(token, state):
                continue

            # Calculate adjusted promotion thresholds
            cluster_bonus = get_cluster_bonus(token, rhythm, current_favs)
            regime_adj = get_regime_adjustment(token, rhythm, current_regime)
            adjusted_min_wr = PROMO_MIN_WR - cluster_bonus - regime_adj

            if (token_stats['trades'] >= PROMO_MIN_TRADES
                    and token_stats['winrate'] >= adjusted_min_wr
                    and token_stats['avg_pnl_pct'] > PROMO_MIN_AVG_PNL):
                new_favs.add(token)
                bonus_reasons = []
                if cluster_bonus > 0:
                    bonus_reasons.append(f"cluster_bonus=+{cluster_bonus}%")
                if regime_adj != 0:
                    bonus_reasons.append(f"regime_adj={regime_adj:+.1f}%")
                bonus_str = f" [{', '.join(bonus_reasons)}]" if bonus_reasons else ""

                changes.append(f"PROMOTE {token} (WR={token_stats['winrate']}%, "
                               f"AvgPnL={token_stats['avg_pnl_pct']}%, "
                               f"Trades={token_stats['trades']}"
                               f"{bonus_str})")
                state.setdefault('last_promoted', {})[token] = today

        if not changes:
            log(f"No changes needed (FAVORITES={len(current_favs)}, regime={current_regime})")
            save_state(state)
            return

        # Apply changes
        if update_constants_file(new_favs):
            log(f"Updated FAVORITES: {len(current_favs)} → {len(new_favs)} tokens (regime={current_regime})")
            for change in changes:
                log(f"  {change}")

            # Log to trading_log.md
            try:
                log_path = '/root/.hermes/automation/trading_log.md'
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                with open(log_path, 'a') as f:
                    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
                    f.write(f"\n## FAVORITES Update — {ts}\n")
                    f.write(f"- Regime: {current_regime}\n")
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
