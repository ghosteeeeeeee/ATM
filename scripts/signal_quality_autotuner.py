#!/usr/bin/env python3
"""
Auto-tuner: calls opencode LLM to evaluate signal quality and suggest param changes.

Usage:
  python3 signal_quality_autotuner.py          # Full cycle: eval → report → LLM → apply
  python3 signal_quality_autotuner.py --dry    # Dry run: show what LLM would change
"""

import sys, os, json, subprocess, re, datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TRACKER_DIR = Path(os.environ.get('HERMES_DATA_DIR', '/root/.hermes/data')) / 'signal_quality'
RESULTS_FILE = TRACKER_DIR / 'results.json'
REPORT_FILE = TRACKER_DIR / 'signal_quality_report.md'
TUNE_LOG = TRACKER_DIR / 'tune_log.json'
CONSTANTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hermes_constants.py')
COMACTOR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'signal_compactor.py')
OPENCODE_BIN = '/root/.opencode/bin/opencode'

DRY_RUN = '--dry' in sys.argv


def _load_results():
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            return json.load(f)
    return None


def _get_current_params():
    """Extract current tunable params from hermes_constants.py."""
    params = {}
    try:
        with open(CONSTANTS_FILE) as f:
            content = f.read()
        # Extract specific params
        for name in ['RS_MIN_TOUCHES', 'RS_COOLDOWN_HOURS', 'RS_PROXIMITY_K',
                      'RS_BOUNCE_THRESH_ATR', 'RS_MIN_CONFIDENCE',
                      'ACCEL_300_MIN_GAP_PCT_LONG', 'ACCEL_300_MIN_GAP_PCT_SHORT',
                      'ACCEL_300_PERSISTENCE_BARS', 'ACCEL_300_STALE_BARS',
                      'ACCEL_300_STALE_BARS_SHORT']:
            match = re.search(rf'{name}\s*=\s*([^\s#]+)', content)
            if match:
                params[name] = match.group(1)
    except Exception as e:
        print(f"Error reading constants: {e}")
    return params


def _get_compactor_weights():
    """Extract current source weights from signal_compactor.py."""
    weights = {}
    try:
        with open(COMACTOR_FILE) as f:
            content = f.read()
        # Find SIGNAL_SOURCE_WEIGHTS dict
        match = re.search(r'SIGNAL_SOURCE_WEIGHTS\s*=\s*\{(.*?)\}', content, re.DOTALL)
        if match:
            block = match.group(1)
            for line in block.split('\n'):
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                m = re.match(r"\('([^']+)',\s*'([^']+)'\):\s*([0-9.]+)", line)
                if m:
                    weights[f"{m.group(1)}|{m.group(2)}"] = float(m.group(3))
    except Exception as e:
        print(f"Error reading compactor: {e}")
    return weights


def _build_prompt(results, params, weights):
    """Build the LLM prompt for analysis and tuning."""
    stats = results.get('stats', {})
    completed = results.get('completed', [])

    # Breakdown by signal type
    by_type = {}
    for c in completed:
        for st in c.get('signal_types', ['unknown']):
            if st not in by_type:
                by_type[st] = {'total': 0, 'wins': 0, 'pnls': []}
            by_type[st]['total'] += 1
            if c['won']:
                by_type[st]['wins'] += 1
            by_type[st]['pnls'].append(c.get('pnl_pct', 0))

    # Breakdown by direction
    by_dir = {'LONG': {'total': 0, 'wins': 0}, 'SHORT': {'total': 0, 'wins': 0}}
    for c in completed:
        d = c['direction']
        by_dir[d]['total'] += 1
        if c['won']:
            by_dir[d]['wins'] += 1

    # Breakdown by confidence
    by_conf = {'high(>=80)': {'total': 0, 'wins': 0}, 'mid(65-79)': {'total': 0, 'wins': 0}, 'low(<65)': {'total': 0, 'wins': 0}}
    for c in completed:
        conf = c.get('confidence', 0) or 0
        if conf >= 80: bucket = 'high(>=80)'
        elif conf >= 65: bucket = 'mid(65-79)'
        else: bucket = 'low(<65)'
        by_conf[bucket]['total'] += 1
        if c['won']:
            by_conf[bucket]['wins'] += 1

    # Worst tokens
    token_pnl = {}
    for c in completed:
        t = c['token']
        if t not in token_pnl:
            token_pnl[t] = {'total': 0, 'wins': 0, 'pnls': []}
        token_pnl[t]['total'] += 1
        if c['won']:
            token_pnl[t]['wins'] += 1
        token_pnl[t]['pnls'].append(c.get('pnl_pct', 0))

    worst_tokens = sorted(token_pnl.items(), key=lambda x: sum(x[1]['pnls']))[:10]
    best_tokens = sorted(token_pnl.items(), key=lambda x: sum(x[1]['pnls']), reverse=True)[:10]

    prompt = f"""You are the Hermes trading system's signal quality analyst.

## Your Task
Analyze the 2-hour signal quality data below and recommend EXACT parameter changes to improve win rate toward 90%+.

## Current Win Rate
- Total signals: {stats.get('total', 0)}
- Win rate: {stats.get('win_rate', 0)}%
- Avg PnL: {stats.get('avg_pnl_pct', 0):.4f}%

## By Signal Type
"""
    for st, data in sorted(by_type.items(), key=lambda x: x[1]['total'], reverse=True):
        wr = data['wins'] / data['total'] * 100 if data['total'] > 0 else 0
        avg_pnl = sum(data['pnls']) / len(data['pnls']) if data['pnls'] else 0
        prompt += f"- {st}: {wr:.0f}% WR ({data['wins']}/{data['total']}), avg PnL={avg_pnl:+.4f}%\n"

    prompt += "\n## By Direction\n"
    for d, data in by_dir.items():
        wr = data['wins'] / data['total'] * 100 if data['total'] > 0 else 0
        prompt += f"- {d}: {wr:.0f}% WR ({data['wins']}/{data['total']})\n"

    prompt += "\n## By Confidence\n"
    for b, data in by_conf.items():
        wr = data['wins'] / data['total'] * 100 if data['total'] > 0 else 0
        prompt += f"- {b}: {wr:.0f}% WR ({data['wins']}/{data['total']})\n"

    prompt += "\n## Worst Tokens (lowest cumulative PnL)\n"
    for t, data in worst_tokens:
        avg = sum(data['pnls']) / len(data['pnls'])
        prompt += f"- {t}: {data['wins']}/{data['total']} WR, avg PnL={avg:+.4f}%\n"

    prompt += "\n## Best Tokens (highest cumulative PnL)\n"
    for t, data in best_tokens:
        avg = sum(data['pnls']) / len(data['pnls'])
        prompt += f"- {t}: {data['wins']}/{data['total']} WR, avg PnL={avg:+.4f}%\n"

    prompt += f"""
## Current Parameters
"""
    for k, v in params.items():
        prompt += f"- {k} = {v}\n"

    prompt += f"""
## Current Compactor Weights
"""
    for k, v in sorted(weights.items()):
        prompt += f"- {k}: {v}\n"

    prompt += """
## Rules for Changes
1. Only change params related to underperforming signal types
2. Keep changes small (±10-20% max per tuning cycle)
3. Never set params below minimum or above maximum
4. Focus on the biggest levers first
5. RS and accel_300 are the only signals being evaluated

## Output Format
Return ONLY a JSON array of changes. Each change is an object:
{
  "file": "constants" or "compactor",
  "param": "PARAM_NAME",
  "old_value": "current value",
  "new_value": "suggested value",
  "reason": "brief reason"
}

If no changes are needed, return an empty array: []
"""
    return prompt


def _call_opencode(prompt):
    """Call opencode run with the prompt and return the response."""
    try:
        result = subprocess.run(
            [OPENCODE_BIN, 'run', '--pure', '--format', 'json', prompt],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            print(f"opencode run failed: {result.stderr[:500]}")
            return None
        # Parse JSON events to find the assistant message
        for line in result.stdout.strip().split('\n'):
            try:
                event = json.loads(line)
                if event.get('type') == 'message' and event.get('role') == 'assistant':
                    content = event.get('content', [])
                    for block in content:
                        if block.get('type') == 'text':
                            return block['text']
            except json.JSONDecodeError:
                continue
        # Fallback: try parsing as plain text
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print("opencode run timed out")
        return None
    except Exception as e:
        print(f"Error calling opencode: {e}")
        return None


def _parse_changes(response):
    """Parse JSON array of changes from LLM response."""
    # Try to find JSON array in the response
    # Look for ```json blocks first
    json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON array
    json_match = re.search(r'\[\s*\{.*?\}\s*\]', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Try line-by-line
    for line in response.split('\n'):
        line = line.strip()
        if line.startswith('[') and line.endswith(']'):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

    print(f"Could not parse changes from response. First 500 chars:\n{response[:500]}")
    return []


def _apply_changes(changes):
    """Apply parameter changes to files."""
    applied = []

    for change in changes:
        param = change.get('param', '')
        old_val = change.get('old_value', '')
        new_val = change.get('new_value', '')
        file_type = change.get('file', 'constants')
        reason = change.get('reason', '')

        if not param or not new_val:
            continue

        target_file = CONSTANTS_FILE if file_type == 'constants' else COMACTOR_FILE

        try:
            with open(target_file) as f:
                content = f.read()

            # For constants file: replace "PARAM = value" pattern
            if file_type == 'constants':
                pattern = rf'({re.escape(param)}\s*=\s*){re.escape(str(old_val))}'
                replacement = f'\\g<1>{new_val}'
                new_content = re.sub(pattern, replacement, content)
            else:
                # For compactor: find the specific weight line
                parts = param.split('|')
                if len(parts) == 2:
                    stype, prefix = parts
                    pattern = rf"('{re.escape(stype)}',\s*'{re.escape(prefix)}'):\s*{re.escape(str(old_val))}"
                    replacement = f"('{stype}', '{prefix}'): {new_val}"
                    new_content = re.sub(pattern, replacement, content)
                else:
                    continue

            if new_content != content:
                if not DRY_RUN:
                    with open(target_file, 'w') as f:
                        f.write(new_content)
                applied.append({
                    'param': param,
                    'old': old_val,
                    'new': new_val,
                    'file': file_type,
                    'reason': reason,
                })
                print(f"{'[DRY] ' if DRY_RUN else ''}Applied: {file_type}:{param} {old_val} → {new_val} ({reason})")
            else:
                print(f"No match found for {param}={old_val} in {target_file}")

        except Exception as e:
            print(f"Error applying {param}: {e}")

    return applied


def _log_tune(applied, prompt_preview):
    """Log the tuning session."""
    log_entry = {
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'changes_applied': applied,
        'prompt_preview': prompt_preview[:1000],
        'dry_run': DRY_RUN,
    }

    log_data = []
    if TUNE_LOG.exists():
        with open(TUNE_LOG) as f:
            log_data = json.load(f)

    log_data.append(log_entry)
    # Keep last 20 entries
    log_data = log_data[-20:]

    with open(TUNE_LOG, 'w') as f:
        json.dump(log_data, f, indent=2, default=str)


def main():
    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Signal Quality Auto-Tuner")
    print(f"Time: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Step 1: Load results
    results = _load_results()
    if not results or not results.get('completed'):
        print("No completed evaluations yet. Run --eval first.")
        return

    stats = results.get('stats', {})
    print(f"Results: {stats.get('total', 0)} signals, {stats.get('win_rate', 0)}% WR")

    # Step 2: Get current params
    params = _get_current_params()
    weights = _get_compactor_weights()

    # Step 3: Build prompt
    prompt = _build_prompt(results, params, weights)

    # Step 4: Call LLM
    print("Calling LLM for analysis...")
    response = _call_opencode(prompt)
    if not response:
        print("No response from LLM")
        return

    # Step 5: Parse changes
    changes = _parse_changes(response)
    print(f"LLM suggested {len(changes)} changes")

    # Step 6: Apply changes
    applied = _apply_changes(changes)

    # Step 7: Log
    _log_tune(applied, prompt)

    print(f"\nDone. {len(applied)} changes applied.")
    if applied:
        print("Restart signals_runner to pick up new params.")


if __name__ == '__main__':
    main()
