#!/usr/bin/env python3
"""shadow_zero_fire_diag.py — Why is a shadow-bypass key firing zero signals?

Read-only diagnosis for registry keys with 0 shadow fires. For each key:
  1. module import OK?
  2. ENABLED flag name resolves?
  3. detector run() executes without exception?
  4. how many signals captured pre-filter vs post SOURCE_FILTERS?

record_to_shadow is stubbed — NOTHING is written to shadow_trades.db.
Detector side effects are identical to a normal shadow_signals_runner run.

Usage:
  python3 scripts/shadow_zero_fire_diag.py                # all Stage A+C keys
  python3 scripts/shadow_zero_fire_diag.py --key hmacd_mtf-+
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shadow_signals_runner as ssr


def diagnose(key, registry):
    info = registry.get(key)
    if info is None:
        return key, 'NOT_IN_REGISTRY', ''
    module_path = ssr.SIGNAL_MODULE_MAP.get(key)
    flag_name = ssr.ENABLED_FLAG_MAP.get(key)
    if not module_path or not flag_name:
        return key, 'NO_MAPPING', f'module={module_path} flag={flag_name}'

    # Stub recorder: count instead of write
    calls = []
    def stub_record(sig, stage, reason):
        calls.append(sig)
        return True
    ssr.record_to_shadow = stub_record

    # Wrap the source/dir filter so rejected samples are visible
    orig_match = ssr._sig_matches_registry
    filter_log = []
    def wrapped_match(sig, reg_key, direction):
        ok = orig_match(sig, reg_key, direction)
        filter_log.append((ok, sig))
        return ok
    ssr._sig_matches_registry = wrapped_match

    try:
        status, n = ssr.run_shadow_signal(
            key, module_path, flag_name, info.get('stage', '?'),
            info.get('reason', ''), info.get('direction', ''))
    finally:
        ssr._sig_matches_registry = orig_match

    n_pre = len(filter_log)
    n_pass = sum(1 for ok, _ in filter_log if ok)
    n_rej = n_pre - n_pass
    detail = (f'status={status} pre_filter={n_pre} post_filter={n_pass} '
              f'rejected={n_rej} filters={ssr.SOURCE_FILTERS.get(key)}')
    # status: empty=QUIET, filtered=FILTER MISMATCH, recorded=WAS QUIET BEFORE,
    #         import_error/run_error=BROKEN
    if n_rej:
        rej = next(s for ok, s in filter_log if not ok)
        detail += (f" rej_sample_src={rej.get('source')!r} "
                   f"dir={rej.get('direction')!r}")
    return key, status, detail


def main():
    ap = argparse.ArgumentParser(description='Zero-fire shadow key diagnostic')
    ap.add_argument('--key', action='append', help='registry key (repeatable)')
    args = ap.parse_args()

    registry = ssr.get_shadow_registry()
    if not registry:
        return 1

    keys = args.key or [k for k, v in registry.items()
                        if v.get('stage') in ('A', 'C')
                        and ssr.SIGNAL_MODULE_MAP.get(k)]
    print(f'{"KEY":28} {"STATUS":16} DETAIL')
    bad = 0
    for k in keys:
        key, status, detail = diagnose(k, registry)
        if status not in ('empty', 'recorded', 'filtered'):
            bad += 1
        print(f'{key:28} {status:16} {detail}')
    print(f'\n{len(keys)} keys checked, {bad} broken (import/mapping errors)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
