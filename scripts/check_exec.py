import sys
sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import get_approved_signals

approved = get_approved_signals(hours=24)
MIN_EXEC_CONFIDENCE = 50
MIN_COMPACT_ROUNDS = 1

approved = [s for s in approved if s.get('final_confidence', 0) >= MIN_EXEC_CONFIDENCE]
print(f'Signals with conf >= {MIN_EXEC_CONFIDENCE}: {len(approved)}')

# These are tokens with open positions (from compactor open-pos-filter)
BLOCKED_TOKENS = {'APEX', 'AXS', 'ETHFI', 'PEOPLE', 'PROMPT', 'PURR', 'STABLE'}

for s in approved:
    token = s.get('token', '')
    direction = s.get('direction', '')
    cr = s.get('hot_rounds', 0)
    conf = s.get('final_confidence', 0)

    if token.upper() in BLOCKED_TOKENS:
        status = 'SKIP POS'
    elif cr < MIN_COMPACT_ROUNDS:
        status = 'SKIP SURF'
    else:
        status = '>>> EXECUTE'

    print(f'  {token:10} {direction:5} conf={conf:.1f} cr={cr} {status}')
