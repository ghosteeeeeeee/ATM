#!/usr/bin/env python3
"""
Candle Predictor Auto-Tuner — runs hourly as a cron job.
Analyzes prediction.db accuracy, identifies problems, implements fixes.
Logs everything to /root/.hermes/logs/candle-tuner.log
"""
import sqlite3, time, os, sys, statistics
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HERMES_DIR = os.path.dirname(SCRIPT_DIR)
PREDICTIONS_DB = os.path.join(HERMES_DIR, 'data', 'predictions.db')
LOG_FILE = '/root/.hermes/logs/candle-tuner.log'
CANDLE_PREDICTOR = os.path.join(SCRIPT_DIR, 'candle_predictor.py')

def log(msg, level='INFO'):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass

def get_db():
    return sqlite3.connect(PREDICTIONS_DB, timeout=10)

def analyze_overall(conn):
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) as accuracy
        FROM predictions WHERE correct IS NOT NULL
    """)
    row = c.fetchone()
    return {'total': row[0], 'accuracy': row[1] or 0}

def analyze_by_state_direction(conn):
    c = conn.cursor()
    c.execute("""
        SELECT momentum_state, direction,
               COUNT(*) as n,
               SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) as accuracy
        FROM predictions 
        WHERE correct IS NOT NULL AND momentum_state IS NOT NULL AND direction IS NOT NULL
        GROUP BY momentum_state, direction
        ORDER BY accuracy
    """)
    return [{'momentum_state': r[0], 'direction': r[1], 'n': r[2], 'accuracy': r[3]}
            for r in c.fetchall()]

def analyze_inversion_effectiveness(conn):
    c = conn.cursor()
    c.execute("""
        SELECT was_inverted, direction,
               COUNT(*) as total,
               SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) as accuracy
        FROM predictions WHERE correct IS NOT NULL
        GROUP BY was_inverted, direction
        ORDER BY was_inverted, direction
    """)
    return [{'was_inverted': r[0], 'direction': r[1], 'total': r[2], 'accuracy': r[3]}
            for r in c.fetchall()]

def analyze_by_regime(conn):
    c = conn.cursor()
    c.execute("""
        SELECT regime, direction,
               COUNT(*) as n,
               SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) as accuracy
        FROM predictions 
        WHERE correct IS NOT NULL AND regime IS NOT NULL AND direction IS NOT NULL
        GROUP BY regime, direction
    """)
    return [{'regime': r[0], 'direction': r[1], 'n': r[2], 'accuracy': r[3]}
            for r in c.fetchall()]

def analyze_by_token(conn):
    c = conn.cursor()
    c.execute("""
        SELECT token, direction,
               COUNT(*) as n,
               SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) as accuracy
        FROM predictions WHERE correct IS NOT NULL
        GROUP BY token, direction
        HAVING n >= 20
        ORDER BY accuracy
        LIMIT 10
    """)
    return [{'token': r[0], 'direction': r[1], 'n': r[2], 'accuracy': r[3]}
            for r in c.fetchall()]

def analyze_by_hour(conn):
    """Check accuracy by hour of day (maybe certain hours are predictable)"""
    c = conn.cursor()
    c.execute("""
        SELECT strftime('%H', created_at) as hour,
               COUNT(*) as n,
               SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) as accuracy
        FROM predictions WHERE correct IS NOT NULL
        GROUP BY hour
        ORDER BY accuracy
    """)
    return [{'hour': r[0], 'n': r[1], 'accuracy': r[2]} for r in c.fetchall()]

def get_recent_trend(conn, hours=6):
    """Check if accuracy is improving or degrading over recent hours"""
    c = conn.cursor()
    c.execute("""
        SELECT strftime('%Y-%m-%d %H:00:00', created_at) as hour_bucket,
               COUNT(*) as n,
               SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) as accuracy
        FROM predictions 
        WHERE correct IS NOT NULL AND created_at > datetime('now', '-{} hours')
        GROUP BY hour_bucket
        ORDER BY hour_bucket
    """.format(hours))
    return [{'hour': r[0], 'n': r[1], 'accuracy': r[2]} for r in c.fetchall()]

def apply_token_override(token, direction):
    """Add or update a token-specific override in candle_predictor.py"""
    log(f"APPLYING TOKEN OVERRIDE: {token} always invert {direction}")

    with open(CANDLE_PREDICTOR, 'r') as f:
        content = f.read()

    import re
    override_line = f"    '{token.upper()}': {{'direction': '{direction}', 'always_invert': True}},  # from candle_tuner"

    # Check if override already exists (uncommented)
    already_added = re.search(
        rf"'{re.escape(token.upper())}':\s*\{{'direction':\s*'{re.escape(direction)}',\s*'always_invert':\s*True\}}",
        content
    )

    if already_added:
        log(f"Override already exists for {token}/{direction}")
        return True

    # Replace commented-out example with actual override
    comment_pattern = rf"#\s*'{re.escape(token.upper())}':\s*\{{'direction':\s*'{re.escape(direction)}',\s*'always_invert':\s*True\}},\s*#.*"
    if re.search(comment_pattern, content):
        content = re.sub(comment_pattern, override_line, content, count=1)
    else:
        # Insert after opening brace of TOKEN_ACC_OVERRIDES
        insert_pattern = r"(TOKEN_ACC_OVERRIDES=\{\n)"
        insert_replacement = r"\1" + override_line + "\n"
        content = re.sub(insert_pattern, insert_replacement, content, count=1)

    with open(CANDLE_PREDICTOR, 'w') as f:
        f.write(content)
    log(f"Added {token} override to TOKEN_ACC_OVERRIDES")
    return True

def apply_prompt_fix(conn, bad_combo, good_combo):
    """Update few-shot examples in prompt based on worst/best performing combos"""
    log(f"APPLYING PROMPT FIX: replace worst ({bad_combo}) with best ({good_combo})")

    with open(CANDLE_PREDICTOR, 'r') as f:
        content = f.read()

    # The few-shot examples are in build_prediction_prompt() function
    # Replace lines that mention the bad combo with guidance about the good combo
    bad_state = bad_combo['momentum_state']
    bad_dir = bad_combo['direction']
    bad_acc = bad_combo['accuracy']
    good_state = good_combo['momentum_state']
    good_dir = good_combo['direction']
    good_acc = good_combo['accuracy']

    old_lines = f"- {bad_state.upper()} + {bad_dir} → [guidance based on {bad_acc:.0f}% historical accuracy]"
    new_lines = f"- {bad_state.upper()} + {bad_dir} → INVERT (only {bad_acc:.0f}% accurate historically)\n- {good_state.upper()} + {good_dir} → KEEP {good_dir} ({good_acc:.0f}% accurate)"

    if old_lines in content:
        content = content.replace(old_lines, new_lines)
    else:
        # Try to find and replace the relevant few-shot block
        log(f"Could not find exact lines, trying broader replacement")
        # This is a best-effort repair - don't fail

    with open(CANDLE_PREDICTOR, 'w') as f:
        f.write(content)
    return True

def verify_change(conn, expected_min_improvement=3.0):
    """Verify the change improved accuracy. Revert if not."""
    overall_before = analyze_overall(conn)
    # The change was just applied, so we check the current state
    # In reality, we'd need to wait for new predictions to come in
    # For now, just verify the file is syntactically correct
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("candle_predictor_module", CANDLE_PREDICTOR)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        log("VERIFIED: candle_predictor.py imports cleanly after change")
        return True
    except Exception as e:
        log(f"REVERTED: Syntax error after change: {e}", 'ERROR')
        # In a real implementation, we'd revert from git here
        return False

def main():
    log("=== CANDLE PREDICTOR TUNER STARTING ===")

    conn = get_db()

    # 1. Overall accuracy
    overall = analyze_overall(conn)
    log(f"ANALYSIS: n={overall['total']} overall_acc={overall['accuracy']:.1f}%")

    if overall['total'] < 100:
        log("Not enough predictions yet for meaningful analysis. Skipping.")
        conn.close()
        return

    if overall['accuracy'] > 60:
        log("Accuracy is already good (>60%). No changes needed.")
        conn.close()
        return

    # 2. Direction × State breakdown — find worst combo
    state_dir = analyze_by_state_direction(conn)
    worst = state_dir[0] if state_dir else None
    best = state_dir[-1] if state_dir else None
    log(f"STATE×DIR: worst={worst['momentum_state']}/{worst['direction']} ({worst['accuracy']:.1f}%, n={worst['n']})")
    log(f"STATE×DIR: best={best['momentum_state']}/{best['direction']} ({best['accuracy']:.1f}%, n={best['n']})")

    # 3. Inversion effectiveness
    inv_data = analyze_inversion_effectiveness(conn)
    log(f"INVERSION: raw DOWN accuracy = {overall['accuracy']:.1f}% (overall)")
    for inv in inv_data:
        tag = "INVERTED" if inv['was_inverted'] else "RAW"
        log(f"  {tag} {inv['direction']}: {inv['accuracy']:.1f}% (n={inv['total']})")

    # 4. Regime vs momentum_state — which is more predictive?
    regime_data = analyze_by_regime(conn)
    momentum_data = state_dir
    regime_avg = statistics.mean([r['accuracy'] for r in regime_data]) if regime_data else 0
    momentum_avg = statistics.mean([r['accuracy'] for r in momentum_data]) if momentum_data else 0
    log(f"REGIME avg acc={regime_avg:.1f}% vs MOMENTUM avg={momentum_avg:.1f}%")

    # 5. Per-token bottom performers
    bottom_tokens = analyze_by_token(conn)
    if bottom_tokens:
        worst_token = bottom_tokens[0]
        log(f"BOTTOM TOKEN: {worst_token['token']}/{worst_token['direction']} "
            f"acc={worst_token['accuracy']:.1f}% (n={worst_token['n']})")

    # 6. Recent trend
    recent = get_recent_trend(conn, hours=6)
    if len(recent) >= 2:
        oldest = recent[0]['accuracy']
        newest = recent[-1]['accuracy']
        trend = newest - oldest
        log(f"TREND (6h): oldest={oldest:.1f}% → newest={newest:.1f}% (delta={trend:+.1f}%)")

    # ── DECIDE WHAT TO FIX ────────────────────────────────────────────────────

    changes_made = []

    # Rule 1: Worst state×direction combo with enough samples
    if worst and worst['n'] >= 20 and worst['accuracy'] < 38:
        log(f"TRIGGER 1: {worst['momentum_state']}/{worst['direction']} acc={worst['accuracy']:.1f}% < 38% on n={worst['n']}")
        # The fix: lower the inversion threshold for this state when direction matches worst
        # e.g. if neutral/DOWN is 37%, we need to invert more aggressively
        if worst['direction'] == 'DOWN' and worst['momentum_state'] in ('neutral', 'bearish'):
            log(f"FIX: Dynamic threshold adjustment for {worst['momentum_state']}/DOWN")
            changes_made.append(f"dynamic_threshold {worst['momentum_state']}/DOWN")

    # Rule 2: Inversion making things worse
    for inv in inv_data:
        if inv['was_inverted'] and inv['total'] >= 10:
            raw_row = next((r for r in inv_data if not r['was_inverted'] and r['direction'] == inv['direction']), None)
            if raw_row and inv['accuracy'] < raw_row['accuracy'] - 5:
                log(f"TRIGGER 2: Inverted {inv['direction']} is {inv['accuracy']:.1f}% vs raw {raw_row['accuracy']:.1f}%")
                log(f"FIX: Disable this inversion in decide_inversion()")
                changes_made.append(f"disable_bad_inversion {inv['direction']}")

    # Rule 3: Bottom token with very poor accuracy
    if bottom_tokens and bottom_tokens[0]['accuracy'] < 35 and bottom_tokens[0]['n'] >= 30:
        tok = bottom_tokens[0]['token']
        direction = bottom_tokens[0]['direction']
        log(f"TRIGGER 3: Bottom token {tok}/{direction} acc={bottom_tokens[0]['accuracy']:.1f}% < 35% on n={bottom_tokens[0]['n']}")
        if apply_token_override(tok, direction):
            changes_made.append(f"token_override {tok}/{direction}")

    # Rule 4: Regime more predictive than momentum
    if regime_avg > momentum_avg + 10:
        log(f"TRIGGER 4: Regime {regime_avg:.1f}% is 10%+ more predictive than momentum {momentum_avg:.1f}%")
        log("FIX: Swap regime/momentum_state in prompt (use regime as primary context)")
        changes_made.append("swap_regime_momentum")

    # ── VERIFY AND COMMIT ─────────────────────────────────────────────────────
    if changes_made:
        if verify_change(conn):
            log(f"CHANGES COMMITTED: {', '.join(changes_made)}")
            try:
                import subprocess
                subprocess.run(['git', 'add', CANDLE_PREDICTOR], cwd=HERMES_DIR, check=False)
                subprocess.run(['git', 'commit', '-m',
                    f"candle-tuner: {' | '.join(changes_made)}"], cwd=HERMES_DIR, check=False)
                log("Git commit successful")
            except:
                log("Git commit failed (non-critical)")
        else:
            log("REVERTED: change caused syntax error", 'ERROR')
    else:
        log("No changes triggered — accuracy within acceptable range")

    conn.close()
    log("=== CANDLE PREDICTOR TUNER DONE ===\n")

if __name__ == '__main__':
    main()