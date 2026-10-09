#!/usr/bin/env python3
"""Independent adversarial verification of gate_counterfactual_audit_2026-10-08.

Pass 1: my own log parser (per-gate explicit patterns, covers gates the audit
missed: CONFLUENCE-GATE-BLOCK, CONTINUUM-BLOCK, CONTINUUM-BULL-denied,
VOL-GATE-BYPASS, PENALTY-BLOCK, SLOPE-FILTER, CHASE-BLOCK, VOL-FLOOR,
CONF-FILTER-PRESERVE, PUMP-CHAIN-GAP-BLOCK, single-char token W ...).
Dumps events -> /tmp/gaudit/events.json
"""
import re, json
from datetime import datetime, timezone

LOG = '/root/.hermes/logs/pipeline.log'
WIN_START = datetime(2026, 10, 2, 20, 0, tzinfo=timezone.utc).timestamp()
WIN_END = datetime(2026, 10, 8, 23, 2, tzinfo=timezone.utc).timestamp()

TS_RE = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
TOK = r'([A-Za-z0-9]{1,14})'
DIR = r'(LONG|SHORT)'

# Every pattern has exactly 2 capture groups: (token, direction).
GATES = {
    # --- gates the original audit counted ---
    'SHORT-CONTINUUM':       re.compile(r'\[SHORT-CONTINUUM\] ' + TOK + r' (SHORT) blocked'),
    'LONG-NEUTRAL':          re.compile(r'\[LONG-NEUTRAL\] ' + TOK + r' (LONG) blocked'),
    'SHORT-NEUTRAL':         re.compile(r'\[SHORT-NEUTRAL\] ' + TOK + r' (SHORT) blocked'),
    'LONG-RSI-BLOCK':        re.compile(r'\[LONG-RSI-BLOCK\] ' + TOK + r': (LONG) blocked'),
    'PUMP-CHAIN-SHORT-RSI-MIN': re.compile(r'\[PUMP-CHAIN-SHORT-RSI-MIN\] ' + TOK + r' (SHORT) blocked'),
    'HALL-SHAME':            re.compile(r'\[HALL-SHAME\] ' + TOK + r' (LONG|SHORT) BLOCKED'),
    'LONG-RSI-CEILING':      re.compile(r'\[LONG-RSI-CEILING\] ' + TOK + r': (LONG) blocked'),
    'BTC-CHOP-GATE':         re.compile(r'\[BTC-CHOP-GATE\] ' + TOK + r' (LONG|SHORT) \S+: BLOCKED'),
    'SHORT-RSI-FLOOR':       re.compile(r'\[SHORT-RSI-FLOOR\] ' + TOK + r': (SHORT) blocked'),
    'PUMP-CHAIN-RSI-MAX':    re.compile(r'\[PUMP-CHAIN-RSI-MAX\] ' + TOK + r' (LONG) blocked'),
    'OVERSOLD-SHORT':        re.compile(r'\[OVERSOLD-SHORT\] ' + TOK + r': (SHORT) blocked'),
    'CTX-GATE':              re.compile(r'\[CTX-GATE\] ' + TOK + r' (LONG|SHORT) blocked'),
    'BTC-CRASH':             re.compile(r'\[BTC-CRASH\] ' + TOK + r' (LONG|SHORT) BLOCKED'),
    'PUMP-CHAIN-SHORT-HIGH': re.compile(r'\[PUMP-CHAIN-SHORT-HIGH\] ' + TOK + r' (SHORT) blocked'),
    'SPIKE-FILTER':          re.compile(r'\[SPIKE-FILTER\] ' + TOK + r': (LONG|SHORT) blocked'),
    'PUMP-CHAIN-VEL-SHORT':  re.compile(r'\[PUMP-CHAIN-VEL-SHORT\] ' + TOK + r': (SHORT) blocked'),
    'SHORT-BB-DEAD-ZONE2':   re.compile(r'\[SHORT-BB-DEAD-ZONE2\] ' + TOK + r': (SHORT) blocked'),
    'PUMP-CHAIN-RSI-MIN':    re.compile(r'\[PUMP-CHAIN-RSI-MIN\] ' + TOK + r' (LONG) blocked'),
    'SHORT-REGIME-GATE':     re.compile(r'\[SHORT-REGIME-GATE\] ' + TOK + r' (SHORT) blocked'),
    'CHOP':                  re.compile(r'\[CHOP\] ' + TOK + r' (LONG|SHORT) \S+: BLOCKED'),
    'EXEC-RSI-HARD-FLOOR':   re.compile(r'\[EXEC-RSI-HARD-FLOOR\] ' + TOK + r' (LONG|SHORT) BLOCKED'),
    'PUMP-CHAIN-VEL':        re.compile(r'\[PUMP-CHAIN-VEL\] ' + TOK + r': (LONG|SHORT) blocked'),
    'EXEC-RSI-CEILING':      re.compile(r'\[EXEC-RSI-CEILING\] ' + TOK + r' (LONG|SHORT) BLOCKED'),
    'PHANTOM-WRITE':         re.compile(r'\[PHANTOM-WRITE\] ' + TOK + r' (LONG|SHORT): BLOCKED'),
    'LONG-RSI-FLOOR':        re.compile(r'\[LONG-RSI-FLOOR\] ' + TOK + r': (LONG) blocked'),
    'SHORT-RSI-CEILING':     re.compile(r'\[SHORT-RSI-CEILING\] ' + TOK + r': (SHORT) blocked'),
    'EXEC-BLOCK':            re.compile(r'\[EXEC-BLOCK\] ' + TOK + r' (LONG|SHORT) (?:NOT in hot-set|blocked)'),
    'SHORT-BB-DEAD-ZONE':    re.compile(r'\[SHORT-BB-DEAD-ZONE\] ' + TOK + r': (SHORT) blocked'),
    'HOT-SET':               re.compile(r'\[HOT-SET\] ' + TOK + r': (LONG|SHORT) blocked'),
    'PRESERVE-SPIKE-BLOCK':  re.compile(r'\[PRESERVE-SPIKE-BLOCK\] ' + TOK + r' (LONG|SHORT) preserved entry blocked'),
    'VEL-FILTER':            re.compile(r'\[VEL-FILTER\] ' + TOK + r': (LONG|SHORT) blocked'),
    'HARD-BLOCK':            re.compile(r'\[HARD-BLOCK\] ' + TOK + r' (LONG|SHORT): .+BLOCKED'),
    'EXEC-RSI-FLOOR':        re.compile(r'\[EXEC-RSI-FLOOR\] ' + TOK + r' (LONG|SHORT) BLOCKED'),
    'V3-LONG-EXTREME':       re.compile(r'\[V3-LONG-EXTREME\] ' + TOK + r' (LONG) blocked'),
    'BTC-ACCEL':             re.compile(r'\[BTC-ACCEL\] ' + TOK + r' (LONG|SHORT) BLOCKED'),
    'V2-RECHECK':            re.compile(r'\[V2-RECHECK\] ' + TOK + r' (LONG|SHORT) BLOCKED'),
    'BB-SQUEEZE-EXTREME':    re.compile(r'\[BB-SQUEEZE-EXTREME\] ' + TOK + r' (LONG) blocked'),
    # --- gates the original audit MISSED ---
    'CONFLUENCE-GATE-BLOCK': re.compile(r'\[CONFLUENCE-GATE-BLOCK\] ' + TOK + r' (LONG|SHORT):'),
    'CONTINUUM-BLOCK':       re.compile(r'\[CONTINUUM-BLOCK\] ' + TOK + r' (LONG) .+ blocking'),
    'CONTINUUM-BULL':        re.compile(r'\[CONTINUUM-BULL\] ' + TOK + r' (SHORT) .+ bypass denied'),
    'VOL-GATE-BYPASS':       re.compile(r'\[VOL-GATE-BYPASS\] ' + TOK + r' (LONG|SHORT): bypass denied'),
    'PENALTY-BLOCK':         re.compile(r'\[PENALTY-BLOCK\] ' + TOK + r' (LONG|SHORT) exec_conf'),
    'SLOPE-FILTER':          re.compile(r'\[SLOPE-FILTER\] ' + TOK + r' (LONG|SHORT):'),
    'CHASE-BLOCK':           re.compile(r'\[CHASE-BLOCK\] ' + TOK + r' (LONG|SHORT):'),
    'CONF-FILTER-PRESERVE':  re.compile(r'\[CONF-FILTER-PRESERVE\] ' + TOK + r':' + DIR + r' blocked'),
    'PUMP-CHAIN-GAP-BLOCK':  re.compile(r'\[PUMP-CHAIN-GAP-BLOCK\] ' + TOK + r' (LONG|SHORT):'),
    'RR-ENGINE-HARD-BLOCK':  re.compile(r'\[RR-ENGINE\] ' + TOK + r' (LONG|SHORT): RR HARD BLOCK'),
    'HOT-SET-COOLDOWN':      re.compile(r'\[HOT-SET\] ' + TOK + r' (LONG|SHORT) BLOCKED'),
    'HOTSET-FILTER-WR':      re.compile(r'\[HOTSET-FILTER\] ' + TOK + r': (LONG|SHORT) blocked'),
    'CONFLICT-RESCUE-BLOCK': re.compile(r'\[CONFLICT-RESCUE-BLOCK\] ' + TOK + r':' + DIR + r' '),
    'LOSERS-BLOCK':          re.compile(r'\[LOSERS-BLOCK\] ' + TOK + r' (LONG|SHORT):'),
    'PRESERVE-MERGE-BLOCK':  re.compile(r'\[PRESERVE-MERGE-BLOCK\] ' + TOK + r':' + DIR + r' '),
    'PRESERVE-LOCK-BLOCK':   re.compile(r'\[PRESERVE-LOCK-BLOCK\] ' + TOK + r':' + DIR + r' '),
    'PRESERVE-CHOP-BLOCK':   re.compile(r'\[PRESERVE-CHOP-BLOCK\] ' + TOK + r':' + DIR + r' '),
    'PRESERVE-PUMP-CHAIN-BLOCK': re.compile(r'\[PRESERVE-PUMP-CHAIN-BLOCK\] ' + TOK + r' (LONG|SHORT) '),
    'DISABLED-COMPONENT':    re.compile(r'\[DISABLED-COMPONENT\] ' + TOK + r' (LONG|SHORT) '),
}
DIRECTIONLESS = {
    'VOL-FLOOR':         re.compile(r'\[VOL-FLOOR\] ' + TOK + r': blocked'),
    'HOTSET-FILTER':     re.compile(r'\[HOTSET-FILTER\] ' + TOK + r': blocked'),
    'VOL-GATE-V2-SKIP':  re.compile(r'\[VOL-GATE-v2\] ' + TOK + r': SKIP'),
}
GATE_BRACKET = re.compile(r'\[([A-Za-z][A-Za-z0-9-]{1,30})\]')

def main():
    counts = {g: 0 for g in GATES}
    dcounts = {g: 0 for g in DIRECTIONLESS}
    events = []
    dirless = []
    residual = {}
    residual_samples = {}
    n_lines = 0
    with open(LOG, 'r', errors='replace') as f:
        for line in f:
            n_lines += 1
            if not line[:4].isdigit():
                continue
            m = TS_RE.match(line)
            if not m:
                continue
            ts_s = m.group(1)
            if not ('block' in line.lower() or 'denied' in line or 'skip' in line.lower()):
                continue
            gb = GATE_BRACKET.search(line)
            if not gb:
                continue
            ts = int(datetime.strptime(ts_s, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp())
            if not (WIN_START <= ts <= WIN_END):
                continue
            hit = False
            for g, rx in GATES.items():
                mm = rx.search(line)
                if mm:
                    counts[g] += 1
                    events.append((ts, g, mm.group(1).rstrip('.,;:'), mm.group(2)))
                    hit = True
                    break
            if hit:
                continue
            for g, rx in DIRECTIONLESS.items():
                mm = rx.search(line)
                if mm:
                    dcounts[g] += 1
                    dirless.append((ts, g, mm.group(1).rstrip('.,;:')))
                    hit = True
                    break
            if hit:
                continue
            gname = gb.group(1)
            residual[gname] = residual.get(gname, 0) + 1
            if gname not in residual_samples:
                residual_samples[gname] = line.rstrip()[:180]
    print(f"lines scanned: {n_lines:,}")
    print(f"directional block events: {len(events):,}  across {sum(1 for g in counts if counts[g])} gates")
    print(f"direction-less block events: {len(dirless):,}")
    print("\n-- per-gate raw counts (my parser) --")
    for g in sorted(counts, key=lambda x: -counts[x]):
        if counts[g]:
            print(f"  {g:26} {counts[g]:6}")
    print("\n-- direction-less --")
    for g in dcounts:
        print(f"  {g:26} {dcounts[g]:6}")
    print("\n-- residual unmatched top 30 --")
    for g in sorted(residual, key=lambda x: -residual[x])[:30]:
        print(f"  {g:30} {residual[g]:6}  e.g. {residual_samples[g]}")
    json.dump({'events': events, 'dirless': dirless}, open('/tmp/gaudit/events.json', 'w'))

if __name__ == '__main__':
    main()
