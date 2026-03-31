#!/usr/bin/env python3
"""
WASP — Hermes System Health & Anomaly Wasp 🐝
Checks every layer of the trading pipeline for bugs, inconsistencies,
and silent failures. Runs every 30 minutes via cron.

Bug severity: CRITICAL > ERROR > WARNING > INFO
"""
import sys, os, time, json, sqlite3, subprocess
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

# ── Config ──────────────────────────────────────────────────────────────────
STATIC_DB   = "/root/.hermes/data/signals_hermes.db"
RUNTIME_DB  = "/root/.hermes/data/signals_hermes_runtime.db"
BRAIN_DSN   = "host=/var/run/postgresql dbname=brain user=postgres"
PRICES_JSON = "/root/.hermes/data/prices.json"
HL_CACHE    = "/var/www/hermes/data/hl_cache.json"
LIVESWITCH  = "/var/www/hermes/data/hype_live_trading.json"
PIPELINE_LOG = "/root/.hermes/logs/pipeline.log"
ERRORS_LOG  = "/root/.hermes/logs/errors.log"
TRADES_API  = "/var/www/hermes/data/trades.json"

Bugs = []  # collected issues

def bug(level: str, component: str, msg: str, detail: str = ""):
    prefix = {"CRITICAL": "🚨", "ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}[level]
    entry = f"  {prefix} [{level}] {component}: {msg}"
    if detail:
        entry += f"\n          → {detail}"
    Bugs.append(({"CRITICAL": 0, "ERROR": 1, "WARNING": 2, "INFO": 3}[level], entry))

def ts(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ── Helpers ──────────────────────────────────────────────────────────────────
def psql(sql: str) -> list:
    try:
        import psycopg2
        conn = psycopg2.connect(BRAIN_DSN)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        bug("ERROR", "brain-db", f"PSQL query failed: {e}", sql[:80])
        return []

def sqlite(db: str, sql: str) -> list:
    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        bug("ERROR", f"sqlite:{Path(db).name}", f"Query failed: {e}", sql[:80])
        return []

def file_age(path: str) -> float:
    try:
        return time.time() - os.path.getmtime(path)
    except: return 9999

def read_json(path: str, default=None):
    try:
        with open(path) as f: return json.load(f)
    except: return default or {}

# ═══════════════════════════════════════════════════════════════════════════
# 1. PRICE COLLECTION
# ═══════════════════════════════════════════════════════════════════════════
def check_prices():
    # prices.json freshness
    age = file_age(PRICES_JSON)
    if age > 120:
        bug("CRITICAL", "prices", f"prices.json is {age:.0f}s old (expected <120s)")
    else:
        data = read_json(PRICES_JSON, {})
        prices = data.get("prices", {})
        tokens = data.get("tokens", {})
        count = len(prices)
        if count < 200:
            bug("ERROR", "prices", f"Only {count} tokens in prices.json (expected ~229)")
            bug("WARNING", "prices", f"prices.json has top-level keys: {list(data.keys())}")
        # check for stale entries (price = 0 or null)
        stale = [k for k, v in prices.items() if not v or v == 0]
        if stale:
            bug("WARNING", "prices", f"{len(stale)} tokens with zero/null price", ", ".join(stale[:5]))

    # HL cache freshness
    cache = read_json(HL_CACHE, {})
    cache_age = time.time() - cache.get("_ts", 0)
    if cache_age > 90:
        bug("ERROR", "hl-cache", f"HL cache is {cache_age:.0f}s old (expected <90s)")
    else:
        if not cache.get("allMids"):
            bug("CRITICAL", "hl-cache", "Cache has no allMids data")
        if not cache.get("meta"):
            bug("WARNING", "hl-cache", "Cache has no meta data")

    # Static DB integrity — prices table
    rows = sqlite(STATIC_DB, "SELECT COUNT(*) as cnt FROM price_history")
    if rows:
        cnt = rows[0]["cnt"]
        if cnt < 100000:
            bug("ERROR", "price-history", f"Only {cnt} rows in price_history (should be ~200k+)")

    # Check for NULL prices in recent history
    nulls = sqlite(STATIC_DB,
        "SELECT COUNT(*) as cnt FROM price_history WHERE price IS NULL OR price = 0")
    if nulls and nulls[0]["cnt"] > 0:
        bug("WARNING", "price-history", f"{nulls[0]['cnt']} NULL/zero prices in history")

# ═══════════════════════════════════════════════════════════════════════════
# 2. SIGNAL GENERATION
# ═══════════════════════════════════════════════════════════════════════════
def check_signals():
    now = datetime.now().isoformat()
    hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()

    # Pending queue health
    pending = sqlite(RUNTIME_DB,
        "SELECT COUNT(*) as cnt FROM signals WHERE decision='PENDING' AND executed=0")
    pending_cnt = pending[0]["cnt"] if pending else 0

    # Check for stale PENDING signals (created > 2h ago, never reviewed)
    stale_pending = sqlite(RUNTIME_DB, """
        SELECT token, direction, confidence, created_at,
               ROUND((julianday('now') - julianday(created_at)) * 24, 1) as age_h
        FROM signals
        WHERE decision='PENDING' AND executed=0
          AND created_at < datetime('now', '-2 hours')
        ORDER BY created_at
        LIMIT 10
    """)
    if stale_pending:
        bug("WARNING", "signals", f"{len(stale_pending)} PENDING signals stale >2h",
            ", ".join(f"{r['token']}({r['age_h']:.0f}h)" for r in stale_pending[:3]))

    # APPROVED but never executed (> 1h)
    stuck_approved = sqlite(RUNTIME_DB, """
        SELECT token, direction, decision, executed, created_at
        FROM signals
        WHERE decision='APPROVED' AND executed=0
          AND created_at < datetime('now', '-1 hours')
    """)
    if stuck_approved:
        bug("WARNING", "signals", f"{len(stuck_approved)} APPROVED signals stuck >1h",
            ", ".join(f"{r['token']} {r['direction']}({r['age_h']:.0f}h)" for r in stuck_approved))

    # decision=EXECUTED but executed=0 (inconsistent — the old bug)
    inconsistent = sqlite(RUNTIME_DB,
        "SELECT COUNT(*) as cnt FROM signals WHERE decision='PENDING' AND executed=1")
    if inconsistent and inconsistent[0]["cnt"] > 0:
        bug("CRITICAL", "signals", "PENDING+executed=1 inconsistency still present!",
            f"{inconsistent[0]['cnt']} rows")

    # Check for duplicate recent signals (same token+dir within 5 min)
    dups = sqlite(RUNTIME_DB, """
        SELECT token, direction, COUNT(*) as cnt, MAX(confidence) as max_conf
        FROM signals
        WHERE created_at > datetime('now', '-30 minutes')
        GROUP BY token, direction
        HAVING cnt > 3
    """)
    if dups:
        bug("WARNING", "signals", "Rapid-fire duplicate signals",
            ", ".join(f"{r['token']}({r['cnt']}x)" for r in dups[:5]))

    # Very low confidence signals
    low_conf = sqlite(RUNTIME_DB,
        "SELECT COUNT(*) as cnt FROM signals WHERE confidence < 55 AND created_at > datetime('now', '-1 hour')")
    if low_conf and low_conf[0]["cnt"] > 5:
        bug("INFO", "signals", f"{low_conf[0]['cnt']} signals below 55% confidence in last hour")

    # Check for NaN/None confidence
    nan_conf = sqlite(RUNTIME_DB,
        "SELECT COUNT(*) as cnt FROM signals WHERE confidence IS NULL OR confidence = ''")
    if nan_conf and nan_conf[0]["cnt"] > 0:
        bug("ERROR", "signals", f"{nan_conf[0]['cnt']} signals with NULL/empty confidence")

    # Decision distribution sanity check
    dist = sqlite(RUNTIME_DB,
        "SELECT decision, COUNT(*) as cnt FROM signals GROUP BY decision")
    total = sum(r["cnt"] for r in dist)
    for r in dist:
        pct = r["cnt"] / max(total, 1) * 100
        if pct > 90 and r["decision"] == "PENDING":
            bug("INFO", "signals", f"Decision skew: {pct:.0f}% PENDING (normal if AI review is slow)")

# ═══════════════════════════════════════════════════════════════════════════
# 3. AI DECIDER / OLLAMA
# ═══════════════════════════════════════════════════════════════════════════
def check_ai_decider():
    # Check if signals are getting reviewed in last 2h
    reviewed = sqlite(RUNTIME_DB,
        "SELECT COUNT(*) as cnt FROM signals WHERE decision IN ('APPROVED','WAIT') "
        "AND updated_at > datetime('now', '-2 hours')")
    if reviewed and reviewed[0]["cnt"] == 0:
        bug("WARNING", "ai-decider", "No signals reviewed by AI in last 2h — Ollama may be down")

    # Check for WAIT signals that have been stuck > 30 min (should be re-reviewed)
    stuck_wait = sqlite(RUNTIME_DB,
        "SELECT token, direction, confidence, updated_at FROM signals "
        "WHERE decision='WAIT' AND updated_at < datetime('now', '-30 minutes') LIMIT 5")
    if stuck_wait:
        bug("INFO", "signals", f"{len(stuck_wait)} WAIT signals never re-reviewed",
            ", ".join(f"{r['token']}({r['direction']})" for r in stuck_wait))

    # Check Ollama availability
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        if r.status_code != 200:
            bug("ERROR", "ollama", f"Ollama returned {r.status_code}")
        else:
            models = r.json().get("models", [])
            if not models:
                bug("WARNING", "ollama", "No models loaded")
    except Exception as e:
        bug("ERROR", "ollama", f"Ollama unreachable: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# 4. PAPER POSITIONS / BRAIN
# ═══════════════════════════════════════════════════════════════════════════
def check_positions():
    open_trades = psql("""
        SELECT token, direction, status, entry_price, signal, confidence,
               open_time, leverage, pnl_usdt, pnl_pct
        FROM trades WHERE status='open' AND server='Hermes'
        ORDER BY open_time DESC
    """)

    if not open_trades:
        bug("INFO", "positions", "No open positions")
        return

    # Check for NULL entry_price or zero amount
    null_entry = [t for t in open_trades if not t[3]]
    if null_entry:
        bug("CRITICAL", "positions", f"{len(null_entry)} open trades with NULL entry_price",
            ", ".join(f"{t[0]}({t[1]})" for t in null_entry))

    # Check for NULL open_time (entry recorded but time not set — rate limit bug)
    null_time = [t for t in open_trades if not t[6]]
    if null_time:
        bug("WARNING", "positions", f"{len(null_time)} open trades with NULL open_time",
            ", ".join(f"{t[0]}({t[1]})" for t in null_time))

    # Check for unreasonably old positions (> 7 days)
    old = psql("""
        SELECT token, direction, open_time
        FROM trades WHERE status='open' AND server='Hermes'
          AND open_time < NOW() - INTERVAL '7 days'
    """)
    if old:
        bug("WARNING", "positions", f"{len(old)} open positions older than 7 days",
            ", ".join(f"{t[0]}({t[1]})" for t in old))

    # Check for positions at position limit
    count = len(open_trades)
    if count >= 10:
        bug("INFO", "positions", f"At position limit: {count}/10")

    # Check for trades with NULL leverage
    null_lev = [t for t in open_trades if not t[7]]
    if null_lev:
        bug("WARNING", "positions", f"{len(null_lev)} trades with NULL leverage")

    # Check for negative pnl_pct with no trailing_activation set
    bad_trailing = psql("""
        SELECT t.token, t.direction, t.pnl_pct, t.open_time
        FROM trades t
        WHERE t.status='open' AND t.server='Hermes'
          AND t.pnl_pct < -3
          AND (t.trailing_activation IS NULL OR t.trailing_activation = 0)
    """)
    if bad_trailing:
            bug("WARNING", "positions", "Deeply underwater positions without trailing stop set",
            ", ".join(f"{t[0]}({t[2]:.1f}%)" for t in bad_trailing[:3]))

    # Check for huge pnl_pct (suspicious — might be calculation error)
    sus = psql("SELECT token, pnl_pct FROM trades WHERE status='open' AND server='Hermes' AND (pnl_pct > 50 OR pnl_pct < -20)")
    if sus:
        bug("WARNING", "positions", f"Suspicious open PnL%: {sus}")

    # Check closed trades for NULL close_reason
    null_reason = psql("""
        SELECT COUNT(*) as cnt FROM trades
        WHERE status='closed' AND server='Hermes'
          AND close_time > NOW() - INTERVAL '24 hours'
          AND (close_reason IS NULL OR close_reason = '')
    """)
    if null_reason and null_reason[0][0] > 0:
        bug("WARNING", "positions", f"{null_reason[0][0]} closed trades in 24h with NULL close_reason")

    # Check for orphaned AB results (variant_id = '' or NULL)
    orphan_ab = psql("SELECT COUNT(*) FROM ab_results WHERE variant_id IS NULL OR variant_id = ''")
    if orphan_ab and orphan_ab[0][0] > 0:
        bug("WARNING", "ab-testing", f"{orphan_ab[0][0]} orphaned AB result rows")

# ═══════════════════════════════════════════════════════════════════════════
# 5. HYPERLIQUID MIRROR SYNC
# ═══════════════════════════════════════════════════════════════════════════
def check_mirror():
    # Live trading switch
    switch = read_json(LIVESWITCH, {})
    if not switch.get("live_trading"):
        bug("INFO", "hl-mirror", "Live trading is OFF")
        return  # don't check mirror sync if live is disabled

    # Get brain open positions (paper)
    brain_pos = {r[0]: r[1] for r in psql(
        "SELECT token, direction FROM trades WHERE status='open' AND server='Hermes'")}

    if not brain_pos:
        bug("INFO", "hl-mirror", "No brain positions to check")
        return

    # Try to get HL positions
    try:
        from hyperliquid_exchange import get_open_hype_positions_curl
        import requests
        r = requests.post("https://api.hyperliquid.xyz/info",
            json={"type": "allMids"}, timeout=8)
        mids = r.json() if r.ok else {}
    except Exception as e:
        bug("WARNING", "hl-mirror", f"Cannot fetch HL mids to check mirror: {e}")
        return

    if not mids:
        bug("INFO", "hl-mirror", "HL allMids returned empty — likely rate-limited, skipping check")
        return

    # Check: every brain LONG should have positive szi on HL, SHORT should have negative
    # (approximate — exact matching would need accountState)
    missing = []
    for token, direction in brain_pos.items():
        hype_t = {
            "AAVE":"AAVE","MON":"MON","LISTA":"LISTA","CYBER":"CYBER",
            "YGG":"YGG","STX":"STX","VINE":"VINE","CATI":"CATI",
            "NTRN":"NTRN","TRX":"TRX","REQ":"REQ","ILV":"ILV"
        }.get(token, token)
        if hype_t not in mids:
            missing.append(f"{token}→{hype_t}(not on HL)")

    if missing:
        bug("WARNING", "hl-mirror", f"Tokens in brain but not found on HL: {', '.join(missing)}")

# ═══════════════════════════════════════════════════════════════════════════
# 6. TRAILING STOP / TSL MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════
def check_trailing_stops():
    # Check for open positions with NULL or 0 trailing_activation
    no_ts = psql("""
        SELECT token, direction, pnl_pct, entry_price
        FROM trades
        WHERE status='open' AND server='Hermes'
          AND (trailing_activation IS NULL OR trailing_activation = 0)
    """)
    if no_ts:
        bug("WARNING", "trailing-stop", f"{len(no_ts)} positions without trailing stop configured",
            ", ".join(f"{t[0]}({t[2]:.1f}%)" for t in no_ts[:3]))

    # Check trades table for trailing_distance = 0 when trailing_activation is set
    bad_dist = psql("""
        SELECT token, trailing_activation, trailing_distance
        FROM trades
        WHERE status='open' AND server='Hermes'
          AND trailing_activation > 0
          AND (trailing_distance IS NULL OR trailing_distance = 0)
    """)
    if bad_dist:
        bug("ERROR", "trailing-stop", "Trailing activation set but distance is 0/NULL",
            str(bad_dist[:3]))

    # Check momentum_cache freshness (proxy for whether trailing stop state is being updated)
    stale_trail = sqlite(RUNTIME_DB, """
        SELECT token, updated_at
        FROM momentum_cache
        WHERE updated_at < datetime('now', '-2 hours')
        LIMIT 5
    """)
    if stale_trail:
        bug("WARNING", "trailing-stop", f"{len(stale_trail)} stale momentum_cache entries > 2h old")

# ═══════════════════════════════════════════════════════════════════════════
# 7. A/B TESTING / LEARNING
# ═══════════════════════════════════════════════════════════════════════════
def check_ab_testing():
    ab = psql("""
        SELECT test_name, variant_id, trades, wins, losses,
               ROUND(total_pnl_pct::numeric, 4) as total_pnl_pct
        FROM ab_results
        ORDER BY test_name, trades DESC
    """)
    if not ab:
        bug("INFO", "ab-testing", "No AB results recorded yet")
        return

    # Check for zero-trade variants (should be cleaned up)
    zero_trade = [r for r in ab if r[2] == 0]
    if zero_trade:
        bug("WARNING", "ab-testing", f"{len(zero_trade)} zero-trade variants should be deleted",
            ", ".join(f"{r[0]}:{r[1]}" for r in zero_trade[:3]))

    # Check for low-sample tests being used for decisions
    low_sample = [r for r in ab if 0 < r[2] < 5 and r[2] > 0]
    if low_sample:
        bug("INFO", "ab-testing", f"{len(low_sample)} variants with < 5 trades",
            ", ".join(f"{r[0]}:{r[1]}(n={r[2]})" for r in low_sample))

    # Check for statistically impossible win rates (wins > trades)
    bad_wr = [r for r in ab if r[3] > r[2]]
    if bad_wr:
        bug("CRITICAL", "ab-testing", "AB results with wins > trades — DB corruption!",
            str(bad_wr))

# ═══════════════════════════════════════════════════════════════════════════
# 8. REGIME / REGIME LEARNING
# ═══════════════════════════════════════════════════════════════════════════
def check_regime():
    # Check regime_log in static DB
    # Check regime output file freshness (written by 4h_regime_scanner)
    regime_file = "/var/www/html/regime_4h.json"
    regime_age = file_age(regime_file)
    if regime_age > 8 * 3600:
        bug("WARNING", "regime", f"regime_4h.json is {regime_age/3600:.1f}h old (expected <4h)")

    # Also check regime_log table (if being populated)
    # Check both INTEGER unix timestamp and any ISO timestamp columns
    import time
    cutoff = int(time.time()) - 48 * 3600
    recent_regime = sqlite(STATIC_DB, f"""
        SELECT COUNT(*) as cnt FROM regime_log
        WHERE timestamp > {cutoff}
    """)
    if recent_regime and recent_regime[0]["cnt"] == 0:
        bug("INFO", "regime", "regime_log table has no entries (scanner may not be writing to it)")

    # Check momentum_cache freshness
    mom = sqlite(RUNTIME_DB,
        "SELECT COUNT(*) as cnt, MAX(updated_at) as last_update FROM momentum_cache")
    if mom and mom[0]["cnt"] > 0:
        try:
            age_h = (time.time() - datetime.fromisoformat(mom[0]["last_update"]).timestamp()) / 3600
        except:
            age_h = 999
        if age_h > 2:
            bug("WARNING", "momentum", f"Momentum cache stale: {mom[0]['cnt']} entries, last update {age_h:.1f}h ago")

# ═══════════════════════════════════════════════════════════════════════════
# 9. PIPELINE / CRON HEALTH
# ═══════════════════════════════════════════════════════════════════════════
def check_pipeline():
    if not os.path.exists(PIPELINE_LOG):
        bug("ERROR", "pipeline", "Pipeline log missing!")
        return

    # Check last pipeline run time
    age = file_age(PIPELINE_LOG)
    if age > 180:
        bug("CRITICAL", "pipeline", f"Pipeline log is {age:.0f}s old — pipeline may be dead")

    # Check last 50 lines for ERROR keywords
    try:
        with open(PIPELINE_LOG) as f:
            lines = f.readlines()
        recent = lines[-100:] if len(lines) > 100 else lines
        errors = [l.strip() for l in recent if "ERROR" in l or "CRITICAL" in l or "Exception" in l]
        if errors:
            bug("ERROR", "pipeline-log", f"{len(errors)} ERROR lines in last 100 log lines",
                errors[-1][:120])
    except Exception as e:
        bug("ERROR", "pipeline", f"Cannot read pipeline log: {e}")

    # Check errors log
    if os.path.exists(ERRORS_LOG):
        err_age = file_age(ERRORS_LOG)
        if err_age > 3600:
            bug("INFO", "errors-log", f"Errors log unchanged in {err_age/3600:.1f}h (good)")
        else:
            # Count recent errors
            try:
                with open(ERRORS_LOG) as f:
                    err_lines = [l for l in f.readlines()
                                 if l.strip() and "html>" not in l  # filter nginx 404 noise
                                 and time.mktime(time.strptime(l[:19], "%Y-%m-%d %H:%M:%S,%f")) > time.time() - 3600]
                if len(err_lines) > 10:
                    bug("WARNING", "errors-log", f"{len(err_lines)} errors in last hour")
            except: pass

    # Check cron health
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.splitlines()
        wasp_crons = [l for l in lines if "wasp" in l.lower()]
        if not wasp_crons:
            bug("WARNING", "cron", "WASP cron job not installed")
    except: pass

    # Check disk space
    try:
        result = subprocess.run(["df", "-h", "/root"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            if "/" in line and "Use%" in line:
                pct = int(line.split("Use%")[1].split()[0].rstrip("%"))
                if pct > 90:
                    bug("CRITICAL", "system", f"Disk usage at {pct}%")
                elif pct > 80:
                    bug("WARNING", "system", f"Disk usage at {pct}%")
    except: pass

# ═══════════════════════════════════════════════════════════════════════════
# 10. TRADES API / WEB
# ═══════════════════════════════════════════════════════════════════════════
def check_web_api():
    # Check trades.json freshness
    age = file_age(TRADES_API)
    if age > 120:
        bug("WARNING", "trades-api", f"trades.json is {age:.0f}s old")
    else:
        data = read_json(TRADES_API, {})
        if "error" in data:
            bug("ERROR", "trades-api", "trades.json contains error key", str(data.get("error")))

    # Check for brain entries with no corresponding trades.json entry
    open_tokens = {r[0] for r in psql(
        "SELECT token FROM trades WHERE status='open' AND server='Hermes'")}
    if open_tokens:
        api_tokens = set()
        try:
            api = read_json(TRADES_API, {})
            api_tokens = {t["token"] for t in api.get("open", [])}
        except: pass
        missing = open_tokens - api_tokens
        if missing:
            bug("WARNING", "trades-api", "Open positions missing from API",
                ", ".join(sorted(missing)))

# ═══════════════════════════════════════════════════════════════════════════
# 11. COOLDOWN / ANOMALY DETECTION
# ═══════════════════════════════════════════════════════════════════════════
def check_cooldowns():
    # Check cooldown_tracker in runtime DB
    cooldowns = sqlite(RUNTIME_DB, """
        SELECT token, direction, expires_at
        FROM cooldown_tracker
        WHERE expires_at > datetime('now')
        LIMIT 20
    """)
    if cooldowns:
        # Check for cooldown > 48h (suspiciously long)
        now_ts = time.time()
        long_cooldown = [c for c in cooldowns if
            (datetime.fromisoformat(c["expires_at"]).timestamp() - now_ts) / 60 > 2880]
        if long_cooldown:
            bug("WARNING", "cooldowns", f"{len(long_cooldown)} cooldowns > 48h",
                ", ".join(f"{c['token']}({c['direction']})" for c in long_cooldown[:3]))

    # Check for duplicate cooldowns (same token+direction)
    dups = sqlite(RUNTIME_DB, """
        SELECT token, direction, COUNT(*) as cnt
        FROM cooldown_tracker
        WHERE expires_at > datetime('now')
        GROUP BY token, direction
        HAVING cnt > 1
    """)
    if dups:
        bug("WARNING", "cooldowns", "Duplicate active cooldowns",
            ", ".join(f"{r['token']}({r['direction']}) x{r['cnt']}" for r in dups))

# ═══════════════════════════════════════════════════════════════════════════
# 12. SIGNAL SCHEMA / DB INTEGRITY
# ═══════════════════════════════════════════════════════════════════════════
def check_db_integrity():
    # Check runtime DB size (shouldn't balloon)
    try:
        size_mb = os.path.getsize(RUNTIME_DB) / 1024 / 1024
        if size_mb > 50:
            bug("WARNING", "db-integrity", f"Runtime DB is {size_mb:.0f}MB (should be < 50MB)")
    except: pass

    # Check for signals with future timestamps (clock skew)
    future_sig = sqlite(RUNTIME_DB,
        "SELECT COUNT(*) as cnt FROM signals WHERE created_at > datetime('now', '+5 minutes')")
    if future_sig and future_sig[0]["cnt"] > 0:
        bug("CRITICAL", "db-integrity", f"{future_sig[0]['cnt']} signals with future timestamps",
            "System clock may be wrong or DB is corrupted")

    # Check token_intel freshness
    intel = sqlite(RUNTIME_DB,
        "SELECT COUNT(*) as cnt, MAX(updated_at) as last FROM token_intel")
    if intel and intel[0]["cnt"] > 0:
        try:
            age_h = (time.time() - datetime.fromisoformat(intel[0]["last"]).timestamp()) / 3600
        except:
            age_h = 999
        if age_h > 24:
            bug("WARNING", "token-intel", f"token_intel stale: {intel[0]['cnt']} entries, {age_h:.1f}h old")

    # Check for duplicate momentum_cache entries
    dup_mom = sqlite(RUNTIME_DB,
        "SELECT token, COUNT(*) as cnt FROM momentum_cache GROUP BY token HAVING cnt > 1")
    if dup_mom:
        bug("WARNING", "momentum", "Duplicate momentum_cache entries",
            ", ".join(f"{r['token']}({r['cnt']})" for r in dup_mom))

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    print(f"🐝 WASP starting at {ts()}")
    print("─" * 60)

    check_prices()
    check_signals()
    check_ai_decider()
    check_positions()
    check_mirror()
    check_trailing_stops()
    check_ab_testing()
    check_regime()
    check_cooldowns()
    check_db_integrity()
    check_pipeline()
    check_web_api()

    # Sort by severity
    Bugs.sort(key=lambda x: x[0])
    criticals = [b for b in Bugs if "CRITICAL" in b[1]]
    errors = [b for b in Bugs if "ERROR" in b[1]]
    warnings = [b for b in Bugs if "WARNING" in b[1]]

    print(f"\n🐝 WASP REPORT — {ts()}")
    print(f"   🚨 CRITICAL: {len(criticals)}  |  ❌ ERROR: {len(errors)}  |  ⚠️ WARNING: {len(warnings)}")
    print("─" * 60)

    if not Bugs:
        print("   ✅ System clean — no issues found")
    else:
        for _, msg in Bugs:
            print(msg)

    # Write to wasp log
    log_path = "/root/.hermes/logs/wasp.log"
    with open(log_path, "a") as f:
        f.write(f"\n{'='*60}\n🐝 WASP {ts()}\n")
        f.write(f"   🚨 CRITICAL: {len(criticals)}  |  ❌ ERROR: {len(errors)}  |  ⚠️ WARNING: {len(warnings)}\n")
        for _, msg in Bugs:
            f.write(msg + "\n")

    print(f"\n   Full log: {log_path}")
    return len(criticals) > 0  # exit 1 if CRITICAL bugs found

if __name__ == "__main__":
    sys.exit(main())
