#!/usr/bin/env python3
"""Signal Toggle API — flip *_ENABLED flags in hermes_constants.py."""
import re, sys, os, shutil, tempfile, importlib
sys.path.insert(0, '/root/.hermes/scripts')

from flask import Flask, request, jsonify
from pathlib import Path

app = Flask(__name__)

CONSTANTS_FILE = Path('/root/.hermes/scripts/hermes_constants.py')

# Load protected flags at startup
import hermes_constants as _hc
NEVER_REENABLE = getattr(_hc, 'NEVER_REENABLE_FLAGS', set())
CEO_PROTECTED = set(getattr(_hc, 'CEO_PROTECTED_FLAGS', {}).keys())


def _read_constants():
    return CONSTANTS_FILE.read_text()


def _write_constants(content):
    """Backup → atomic write → reload module."""
    shutil.copy2(CONSTANTS_FILE, CONSTANTS_FILE.with_suffix('.py.bak'))
    fd, tmp = tempfile.mkstemp(dir=CONSTANTS_FILE.parent, suffix='.tmp')
    try:
        os.write(fd, content.encode())
        os.close(fd)
        os.replace(tmp, CONSTANTS_FILE)
    except Exception:
        os.unlink(tmp)
        raise
    # Reload so other imports see the new values
    import hermes_constants
    importlib.reload(hermes_constants)


def _find_real_assignment(content, flag):
    """Find the actual assignment line, skipping comments."""
    pattern = rf'^({re.escape(flag)})(\s*=\s*)(True|False)'
    for m in re.finditer(pattern, content, re.MULTILINE):
        line_start = content.rfind('\n', 0, m.start()) + 1
        line_prefix = content[line_start:m.start()]
        if not line_prefix.lstrip().startswith('#'):
            return m
    return None


def _get_value(content, flag):
    m = _find_real_assignment(content, flag)
    return m.group(3) == 'True' if m else None


def _toggle_flag(content, flag):
    m = _find_real_assignment(content, flag)
    if not m:
        return None, None
    old_val = m.group(3)
    new_val = 'False' if old_val == 'True' else 'True'
    new_content = content[:m.start(3)] + new_val + content[m.end(3):]
    return new_content, new_val == 'True'


def _regenerate_config():
    """Regenerate signal_config.json after toggle."""
    try:
        from signals import SIGNAL_REGISTRY, _resolve_enabled
        from paths import SIGNAL_CONFIG_JSON
        from datetime import datetime, timezone
        import json, fcntl
        _FLAG_OVERRIDES = {
            'ma300_candle_confirm': 'MA300_CANDLE_ENABLED',
            'ma_100_cross_long': 'MA_100_CROSS_PLUS_ENABLED',
            'ma_100_cross_short': 'MA_100_CROSS_MINUS_ENABLED',
        }
        import hermes_constants as hc
        config = []
        for s in SIGNAL_REGISTRY:
            name = s['name']
            flag_name = s['enabled'] if isinstance(s['enabled'], str) else None
            if not flag_name:
                flag_name = _FLAG_OVERRIDES.get(name, name.upper() + '_ENABLED')
                if not hasattr(hc, flag_name):
                    base = re.sub(r'_(PLUS|MINUS|LONG|SHORT|NEW)$', '', flag_name)
                    if hasattr(hc, base):
                        flag_name = base
            config.append({'name': name, 'enabled': _resolve_enabled(s), 'flag': flag_name})
        result = {'signals': config, 'updated': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}
        lock_path = SIGNAL_CONFIG_JSON + '.lock'
        with open(lock_path, 'w') as lf:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            with open(SIGNAL_CONFIG_JSON, 'w') as f:
                json.dump(result, f, indent=2)
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass


@app.route('/toggle', methods=['POST'])
def toggle():
    data = request.get_json(silent=True) or {}
    flag = data.get('flag', '').strip()
    if not flag:
        return jsonify({'error': 'missing flag'}), 400
    if not re.match(r'^[A-Z_0-9]+$', flag):
        return jsonify({'error': 'invalid flag name'}), 400
    if flag in NEVER_REENABLE:
        return jsonify({'error': f'{flag} is permanently disabled (NEVER_REENABLE)'}), 403
    if flag in CEO_PROTECTED:
        return jsonify({'error': f'{flag} is CEO-protected'}), 403

    content = _read_constants()
    old_val = _get_value(content, flag)
    if old_val is None:
        return jsonify({'error': f'flag {flag} not found'}), 404

    new_content, new_val = _toggle_flag(content, flag)
    if new_content is None:
        return jsonify({'error': f'failed to toggle {flag}'}), 500

    _write_constants(new_content)
    _regenerate_config()
    return jsonify({'flag': flag, 'old': old_val, 'new': new_val})


@app.route('/set', methods=['POST'])
def set_flag():
    data = request.get_json(silent=True) or {}
    flag = data.get('flag', '').strip()
    value = data.get('value')
    if not flag or value is None:
        return jsonify({'error': 'missing flag or value'}), 400
    if not re.match(r'^[A-Z_0-9]+$', flag):
        return jsonify({'error': 'invalid flag name'}), 400
    if flag in NEVER_REENABLE:
        return jsonify({'error': f'{flag} is permanently disabled (NEVER_REENABLE)'}), 403
    if flag in CEO_PROTECTED:
        return jsonify({'error': f'{flag} is CEO-protected'}), 403

    content = _read_constants()
    old_val = _get_value(content, flag)
    if old_val is None:
        return jsonify({'error': f'flag {flag} not found'}), 404

    new_val_str = 'True' if value else 'False'
    m = _find_real_assignment(content, flag)
    new_content = content[:m.start(3)] + new_val_str + content[m.end(3):]
    _write_constants(new_content)
    _regenerate_config()
    return jsonify({'flag': flag, 'old': old_val, 'new': bool(value)})


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'constants': str(CONSTANTS_FILE)})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=3462, debug=False)
