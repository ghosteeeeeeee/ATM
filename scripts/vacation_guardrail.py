#!/usr/bin/env python3
"""
vacation_guardrail.py — Hard safety net for T-on-vacation mode.

Checks 24h PnL and 48h WR. Auto-pauses live trading if thresholds breached.
Runs via systemd timer every 30 minutes.

CEO mandate (2026-10-14): "Do not leave without it. It is the only hard
safety net — the day-14 kill criteria don't exist as code until #10 ships."
"""
import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psycopg2
from paths import HERMES_DATA
from hermes_log import log

# ── Thresholds (CEO 2026-10-14 + own-conclusions gap fix) ───────────────────
PNL_24H_PAUSE = -3.00      # Auto-pause if 24h PnL < this
WR_48H_ESCALATE = 40.0     # Escalate if 48h WR < this (after 48h soak)
WR_7D_PAUSE = 35.0         # Auto-pause if 7d WR < this (plan kill criterion — was NOT coded)
WR_7D_MIN_TRADES = 50      # Need 50+ trades before 7d WR is meaningful
# 2026-10-15 captain fix: WR-alone is a false-positive machine during fix-aging
# windows (Oct 12-13 bad day sits in the 7d window while Oct 13-14 fixes need
# live cohort data). Pair WR pause with a PnL confirmation so we only freeze
# on sustained bleed, not a window artifact.
WR_7D_PNL_CONFIRM = -2.00  # 7d WR pause ALSO requires pnl_7d < this
# Auto-resume hysteresis: only clear pause when metrics recover past the
# pause threshold, so we don't thrash pause/resume on a single borderline check.
WR_7D_RESUME = 37.0
KILL_SWITCH_PATH = os.path.join(WWW_DATA := '/var/www/hermes/data', 'hype_live_trading.json')
ALERT_PATH = os.path.join(HERMES_DATA, '..', 'automation', 'ceo', 'vacation_alerts.json')
# BUG-HUNTER 2026-10-15: marker that pipeline_watchdog checks before auto-restarting
# the pipeline timer. Without it the watchdog re-armed the timer ~6min after pause
# (heartbeat goes stale >300s → CRITICAL → restart) and LIVE trading resumed.
PAUSE_MARKER = os.path.join(HERMES_DATA, 'vacation_pause.json')
# T directive 2026-10-17: WR-based pause is counter-productive — pausing prevents
# WR from improving (no new trades = no new wins to push WR up). Instead of pausing,
# write a SIZE REDUCE flag that the pipeline reads to cut position sizes to minimum.
# New trades still come in (WR can recover), losses are minimized.
SIZE_REDUCE_MARKER = os.path.join(HERMES_DATA, 'vacation_size_reduce.json')


def check_guardrails():
    """Check PnL and WR thresholds. Returns (should_pause, should_escalate, data)."""
    conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
    try:
        # 24h PnL
        cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(SUM(pnl_usdt), 0), COUNT(*),
                   ROUND(100.0*SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1)
            FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '24 hours'
        """)
        pnl_24h, n_24h, wr_24h = cur.fetchone()

        # 48h WR
        cur.execute("""
            SELECT COALESCE(SUM(pnl_usdt), 0), COUNT(*),
                   ROUND(100.0*SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1)
            FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '48 hours'
        """)
        pnl_48h, n_48h, wr_48h = cur.fetchone()

        # 7d WR (plan kill criterion — own-conclusions gap fix)
        cur.execute("""
            SELECT COALESCE(SUM(pnl_usdt), 0), COUNT(*),
                   ROUND(100.0*SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1)
            FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '7 days'
        """)
        pnl_7d, n_7d, wr_7d = cur.fetchone()

        data = {
            'pnl_24h': float(pnl_24h), 'n_24h': n_24h, 'wr_24h': float(wr_24h or 0),
            'pnl_48h': float(pnl_48h), 'n_48h': n_48h, 'wr_48h': float(wr_48h or 0),
            'pnl_7d': float(pnl_7d), 'n_7d': n_7d, 'wr_7d': float(wr_7d or 0),
            'checked_at': datetime.now(timezone.utc).isoformat(),
        }

        should_pause = (data['pnl_24h'] < PNL_24H_PAUSE or
                       (data['wr_7d'] < WR_7D_PAUSE and data['pnl_7d'] < WR_7D_PNL_CONFIRM
                        and data['n_7d'] >= WR_7D_MIN_TRADES))
        should_escalate = data['wr_48h'] < WR_48H_ESCALATE and data['n_48h'] >= 30
        # Auto-resume: pause marker present + metrics recovered → clear and restart.
        # Hysteresis (WR_7D_RESUME > WR_7D_PAUSE) prevents thrash on borderline checks.
        should_resume = (os.path.exists(PAUSE_MARKER) and
                         data['pnl_24h'] >= PNL_24H_PAUSE and
                         (data['wr_7d'] >= WR_7D_RESUME or data['pnl_7d'] >= 0))

        return should_pause, should_escalate, should_resume, data
    finally:
        conn.close()


def pause_trading(reason):
    """Disable live trading: close positions + stop pipeline timers.

    BUG-HUNTER BLOCKER FIX (2026-10-14): the JSON write alone was a no-op —
    is_live_trading_enabled() reads only the static constant (commit 28215e7e
    removed JSON consultation due to ghost trades). This fix uses
    disable_live_trading() (closes HL positions + saves flags) AND stops
    the pipeline/decider systemd timers so no new trades can open.

    BUG-HUNTER BLOCKER FIX v2 (2026-10-15): pipeline_watchdog.py (2-min timer)
    treats the stale heartbeat as CRITICAL and restarts hermes-pipeline.timer
    ~6 min after we stop it — silently resuming LIVE trading (decider reads
    the LIVE_TRADING_ENABLED constant, which stays True). Now we:
      a) write PAUSE_MARKER (watchdog checks it before any restart), and
      b) stop hermes-watchdog.timer itself, and
      c) stop the running hermes-pipeline.service (stopping the timer alone
         does NOT stop an in-flight or already-scheduled service run).
    Note: 'hermes-decider.timer' does not exist (decider_run is a pipeline
    step) — kept out of the list; stopping the pipeline covers it.
    """
    import subprocess
    try:
        # 0. Write pause marker FIRST so the watchdog never restarts the pipeline
        try:
            with open(PAUSE_MARKER, 'w') as f:
                json.dump({'paused_at': datetime.now(timezone.utc).isoformat(),
                           'reason': reason}, f, indent=2)
        except Exception as e:
            log(f"⚠️ [VACATION-GUARDRAIL] Could not write pause marker: {e}", 'WARN')

        # 1. Stop the watchdog BEFORE the pipeline (it would re-arm the timer)
        r = subprocess.run(['systemctl', 'stop', 'hermes-watchdog.timer'],
                         capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            log("🛑 [VACATION-GUARDRAIL] Stopped hermes-watchdog.timer")
        else:
            log(f"⚠️ [VACATION-GUARDRAIL] Could not stop hermes-watchdog.timer: {r.stderr.strip()}", 'WARN')

        # 2. Stop the pipeline service (kill any in-flight run) then its timer
        for unit in ['hermes-pipeline.service', 'hermes-pipeline.timer']:
            r = subprocess.run(['systemctl', 'stop', unit],
                             capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                log(f"🛑 [VACATION-GUARDRAIL] Stopped {unit}")
            else:
                log(f"⚠️ [VACATION-GUARDRAIL] Could not stop {unit}: {r.stderr.strip()}", 'WARN')

        # 3. Close automated HL positions + save flags.
        # FIX (2026-10-17): manual CEO trades (signal='ai-trader-manual') are
        # EXEMPT from guardrail closes — trade #16257 BTC SHORT was force-closed
        # at +0.76% by this pause without CEO intent. Pause gates automated
        # trading; manual positions stay open until CEO closes them.
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from hyperliquid_exchange import disable_live_trading
        manual_coins = []
        try:
            import psycopg2
            from _secrets import BRAIN_PASSWORD, BRAIN_HOST
            _conn = psycopg2.connect(host=BRAIN_HOST, dbname='brain', user='postgres',
                                     password=BRAIN_PASSWORD, connect_timeout=5)
            _cur = _conn.cursor()
            _cur.execute("""SELECT DISTINCT token FROM trades
                            WHERE status='open' AND paper=false
                            AND signal LIKE 'ai-trader-manual%'""")
            manual_coins = [r[0] for r in _cur.fetchall()]
            _cur.close()
            _conn.close()
        except Exception as mq:
            log(f"⚠️ [VACATION-GUARDRAIL] manual trade query failed: {mq}", 'WARN')
        result = disable_live_trading(exclude_coins=manual_coins)
        closed = result.get('closed_positions', [])
        kept = result.get('kept_open', [])
        log(f"🛑 [VACATION-GUARDRAIL] Closed {len(closed)} HL positions: {closed}")
        if kept:
            log(f"🛑 [VACATION-GUARDRAIL] Kept {len(kept)} manual CEO trades open: {kept}")

        # 4. Keep the guardrail timer RUNNING so auto-resume can fire when
        #    metrics recover. (Pre-fix: stopped itself → permanent freeze
        #    with no resume path except manual intervention.)
        log(f"🛑 [VACATION-GUARDRAIL] TRADING PAUSED (positions closed + timers stopped): {reason}")
        log("🛑 [VACATION-GUARDRAIL] Guardrail timer stays armed for auto-resume (WR>=37% or pnl_7d>=0)")
        return True
    except Exception as e:
        log(f"❌ [VACATION-GUARDRAIL] Failed to pause: {e}", 'ERROR')
        return False


def resume_trading(reason):
    """Clear pause marker + restart pipeline/watchdog timers + re-enable kill JSON.

    Does NOT touch LIVE_TRADING_ENABLED (CEO-protected constant). Resume only
    clears the runtime pause; the constant stays authoritative.
    """
    import subprocess
    try:
        if os.path.exists(PAUSE_MARKER):
            os.remove(PAUSE_MARKER)
            log(f"▶️ [VACATION-GUARDRAIL] Removed pause marker: {reason}")
        # Also clear size-reduce flag on resume
        try:
            if os.path.exists(SIZE_REDUCE_MARKER):
                os.remove(SIZE_REDUCE_MARKER)
                log(f"▶️ [VACATION-GUARDRAIL] Removed size-reduce marker")
        except Exception:
            pass
        # Restore kill JSON to true (cosmetic for is_live_trading_enabled, but
        # dashboards/watchdogs read it — keep state coherent).
        try:
            with open(KILL_SWITCH_PATH, 'w') as f:
                json.dump({'live_trading': True, 'reason': f'RESUME: {reason}',
                           'ts': datetime.now(timezone.utc).timestamp()}, f, indent=2)
        except Exception as e:
            log(f"⚠️ [VACATION-GUARDRAIL] Could not write kill JSON: {e}", 'WARN')
        for unit in ['hermes-pipeline.timer', 'hermes-watchdog.timer']:
            r = subprocess.run(['systemctl', 'start', unit],
                             capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                log(f"▶️ [VACATION-GUARDRAIL] Started {unit}")
            else:
                log(f"⚠️ [VACATION-GUARDRAIL] Could not start {unit}: {r.stderr.strip()}", 'WARN')
        log(f"▶️ [VACATION-GUARDRAIL] TRADING RESUMED: {reason}")
        return True
    except Exception as e:
        log(f"❌ [VACATION-GUARDRAIL] Failed to resume: {e}", 'ERROR')
        return False


def write_alert(level, message, data):
    """Write alert to vacation_alerts.json for CEO/T to read."""
    try:
        os.makedirs(os.path.dirname(ALERT_PATH), exist_ok=True)
        alerts = []
        if os.path.exists(ALERT_PATH):
            with open(ALERT_PATH) as f:
                alerts = json.load(f)
        alerts.append({
            'level': level, 'message': message, 'data': data,
            'ts': datetime.now(timezone.utc).isoformat(),
        })
        # Keep last 50 alerts
        alerts = alerts[-50:]
        with open(ALERT_PATH, 'w') as f:
            json.dump(alerts, f, indent=2)
    except Exception:
        pass


def write_size_reduce(reason):
    """Write size-reduce flag. Pipeline reads this to cut position sizes.

    T directive 2026-10-17: instead of pausing (which prevents WR recovery),
    reduce position sizes to minimum. New trades still come in, losses are
    minimized, WR can improve.
    """
    try:
        config = {
            'size_reduce': True,
            'reason': reason,
            'written_at': datetime.now(timezone.utc).isoformat(),
            'size_multiplier': 0.5,
        }
        with open(SIZE_REDUCE_MARKER, 'w') as f:
            json.dump(config, f, indent=2)
        log(f"📉 [VACATION-GUARDRAIL] SIZE REDUCED to 50% (not paused): {reason}")
    except Exception as e:
        log(f"❌ [VACATION-GUARDRAIL] Failed to write size-reduce: {e}", 'ERROR')


def check_ichimoku_bypass_kill():
    """Check if ichimoku LONG bypass should be auto-reverted (CEO 2026-10-20).

    Pre-registered kill criteria: if loosened LONG cohort 24h WR < 40% with
    5+ trades, auto-revert ICHIMOKU_LONG_BYPASS_ENABLED to False.

    bug_hunter 2026-10-20 fixes:
    - float() casts for psycopg2 Decimal (json.dump TypeError)
    - try/finally on PG connection (house convention)
    - atomic write (temp file + os.replace) to avoid racing compactor import
    - query counts single-source ichimoku LONG only (not confluence trades)
    """
    try:
        from hermes_constants import (
            ICHIMOKU_LONG_BYPASS_ENABLED,
            ICHIMOKU_LONG_BYPASS_MIN_WR,
            ICHIMOKU_LONG_BYPASS_MIN_TRADES,
        )
        if not ICHIMOKU_LONG_BYPASS_ENABLED:
            return  # already disabled

        import psycopg2
        conn = None
        cur = None
        try:
            conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
            cur = conn.cursor()
            # Count ONLY single-source ichimoku LONG trades (the loosened cohort).
            # signal='ichimoku+' means single-source; 'ichimoku+,rs_s' means confluence.
            cur.execute("""
                SELECT COUNT(*), SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END),
                       ROUND(SUM(pnl_usdt), 2),
                       ROUND(100.0 * SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) / COUNT(*), 1)
                FROM trades
                WHERE status = 'closed'
                  AND signal = 'ichimoku+'
                  AND direction = 'LONG'
                  AND close_time > NOW() - INTERVAL '24 hours'
            """)
            row = cur.fetchone()
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

        n_trades = int(row[0] or 0)
        n_wins = int(row[1] or 0)
        pnl = float(row[2] or 0)
        wr = float(row[3] or 0)

        if n_trades >= ICHIMOKU_LONG_BYPASS_MIN_TRADES:
            if wr < ICHIMOKU_LONG_BYPASS_MIN_WR:
                # Auto-revert: disable the bypass (atomic write)
                const_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hermes_constants.py')
                with open(const_path, 'r') as f:
                    content = f.read()
                content = content.replace(
                    'ICHIMOKU_LONG_BYPASS_ENABLED = True',
                    f'ICHIMOKU_LONG_BYPASS_ENABLED = False  # AUTO-REVERTED {datetime.now(timezone.utc).isoformat()}: WR {wr}% < {ICHIMOKU_LONG_BYPASS_MIN_WR}% ({n_trades}T)'
                )
                # Atomic write: temp file + os.replace to avoid racing compactor import
                tmp_path = const_path + '.tmp'
                with open(tmp_path, 'w') as f:
                    f.write(content)
                os.replace(tmp_path, const_path)
                log(f"🔴 [ICHIMOKU-BYPASS-KILL] Auto-reverted: WR {wr}% < {ICHIMOKU_LONG_BYPASS_MIN_WR}% ({n_trades}T, PnL ${pnl:+.2f})")
                write_alert('WARNING', f'ichimoku LONG bypass auto-reverted: WR {wr}% < {ICHIMOKU_LONG_BYPASS_MIN_WR}%', {
                    'n_trades': n_trades, 'wr': wr, 'pnl': pnl
                })
            else:
                log(f"✅ [ICHIMOKU-BYPASS-KILL] OK: WR {wr}% >= {ICHIMOKU_LONG_BYPASS_MIN_WR}% ({n_trades}T, PnL ${pnl:+.2f})")
        else:
            log(f"⏳ [ICHIMOKU-BYPASS-KILL] Collecting data: {n_trades}/{ICHIMOKU_LONG_BYPASS_MIN_TRADES} trades (WR {wr}%)")

    except Exception as e:
        log(f"❌ [ICHIMOKU-BYPASS-KILL] Check failed: {e}", 'ERROR')


def main():
    # Check ichimoku LONG bypass kill criteria first (CEO 2026-10-20)
    check_ichimoku_bypass_kill()

    should_pause, should_escalate, should_resume, data = check_guardrails()

    log(f"📊 [VACATION-GUARDRAIL] 24h: {data['n_24h']}T {data['wr_24h']}% ${data['pnl_24h']:+.2f} | "
        f"48h: {data['n_48h']}T {data['wr_48h']}% ${data['pnl_48h']:+.2f} | "
        f"7d: {data['n_7d']}T {data['wr_7d']}% ${data['pnl_7d']:+.2f}")

    if should_resume:
        reason = (f"auto-resume: 7d WR {data['wr_7d']}% / pnl_7d ${data['pnl_7d']:+.2f} recovered "
                  f"(hysteresis WR>={WR_7D_RESUME}% or pnl>=0)")
        resume_trading(reason)
        write_alert('INFO', f'TRADING RESUMED: {reason}', data)
    elif (not should_pause and os.path.exists(SIZE_REDUCE_MARKER) and
          ((data['wr_7d'] >= WR_7D_RESUME and data['pnl_7d'] >= WR_7D_PNL_CONFIRM) or data['pnl_7d'] >= 0)):
        # BH-SR-1 fix: auto-clear size-reduce when metrics recover.
        # Without this, the flag persists indefinitely after WR recovers.
        # brain_auditor 2026-10-19: parenthesized the OR — without parens,
        # `A and B and C or D` evaluated as `(A and B and C) or D`, so
        # pnl_7d>=0 alone cleared size-reduce AND swallowed the hard-pause
        # elif below (7d-profitable week + catastrophic 24h day = no pause).
        # brain_auditor 2026-10-19 (run #25): aging-artifact guard — WR path
        # now ALSO requires pnl_7d >= WR_7D_PNL_CONFIRM (-2.00). Bad-day aging
        # out of the rolling window inflates WR by denominator change, not
        # actual recovery (Oct 13 cohort 56T -$1.53 ages out Oct 20: WR
        # 33.8->37.2% while pnl still -$2.60 — old OR would full-size a
        # still-bleeding book). Clear paths: (WR>=37 AND pnl>=-2) OR pnl>=0.
        try:
            os.remove(SIZE_REDUCE_MARKER)
            log(f"▶️ [VACATION-GUARDRAIL] Size-reduce auto-cleared: WR {data['wr_7d']}% recovered")
            write_alert('INFO', f'Size-reduce cleared: WR {data["wr_7d"]}%', data)
        except Exception:
            pass
    elif should_pause:
        reasons = []
        size_reduce = False
        if data['pnl_24h'] < PNL_24H_PAUSE:
            reasons.append(f"24h PnL ${data['pnl_24h']:.2f} < ${PNL_24H_PAUSE:.2f}")
        if data['wr_7d'] < WR_7D_PAUSE and data['pnl_7d'] < WR_7D_PNL_CONFIRM and data['n_7d'] >= WR_7D_MIN_TRADES:
            # T directive 2026-10-17: WR-based triggers get SIZE REDUCE, not pause.
            # Pausing prevents WR from improving (no new trades = no new wins).
            size_reduce = True
            reasons.append(f"7d WR {data['wr_7d']}% < {WR_7D_PAUSE}% AND pnl_7d ${data['pnl_7d']:+.2f} < ${WR_7D_PNL_CONFIRM:.2f} ({data['n_7d']}T) → SIZE REDUCE (not pause — WR can't recover without trades)")
        reason = "; ".join(reasons)
        if size_reduce and data['pnl_24h'] >= PNL_24H_PAUSE:
            # Only size-reduce (don't pause) when 24h PnL is OK
            write_size_reduce(reason)
            write_alert('WARNING', f'SIZE REDUCED (not paused): {reason}', data)
        else:
            # 24h PnL is also bad → hard pause
            pause_trading(reason)
            write_alert('CRITICAL', f'TRADING PAUSED: {reason}', data)
    elif should_escalate:
        reason = f"48h WR {data['wr_48h']}% < {WR_48H_ESCALATE}% with {data['n_48h']} trades"
        log(f"⚠️ [VACATION-GUARDRAIL] ESCALATE: {reason}")
        write_alert('WARNING', f'Early escalation: {reason}', data)
    else:
        write_alert('INFO', 'Guardrails OK', data)


if __name__ == '__main__':
    main()
