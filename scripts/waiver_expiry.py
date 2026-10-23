"""waiver_expiry.py — CEO unclog flip#1 expiry gate (single source of truth).

WHY THIS EXISTS (brain_auditor run #102, 2026-10-23):
data/vacation_mode.json records `rules.unclog_waiver.expires` = 2026-10-24T00:00:00Z
but NOTHING read it. Every audit run since #93 planned "the waiver lapses Oct 24"
and no code path was ever going to do it — the [35, floor) SHORT band would have
kept firing after T's stated expiry, silently.

Flip#1 = decider ctx/exec + compactor approval hard-floor + brain final-gate
BTC-bear exemption for SHORT RSI in [OVERSOLD_SHORT_RSI_MAX, floor).

Flip#2 (volatility_gate_v2 REGIME_SIGNALS volume-buildup- HIGH/EXTREME) is
DELIBERATELY NOT covered here — CEO rules item-3 separately (#99 decoupling).

FAIL-CLOSED on purpose: unreadable / missing / malformed expiry → False → the
band blocks, mirroring the bear-exemption's own fail-closed convention. Use
flip1_state() when you need to tell a REAL expiry from an unreadable file —
they used to log identically (see flip1_state docstring).

Self-check: python3 scripts/waiver_expiry.py --selfcheck
"""
import datetime
import json
import os


def flip1_state(now=None):
    """(active, reason) — reason in {'active', 'expired', 'unreadable:<ExcName>'}.

    Same read-per-call contract as flip1_active (no cache: the lapse takes effect
    on the first gate after the timestamp). The reason exists because run #103 hit
    a 20-minute false-lapse (2026-10-23 17:36-17:56, 10 log lines) where the gate
    fail-closed on a missing `rules.unclog_waiver` key and logged the SAME
    "waiver expired" text a real expiry would print — diagnosing it cost an audit.
    'expired' = T's timestamp passed; 'unreadable:*' = file/key/parse problem
    (fail-closed, but NOT an expiry — fix the file, don't wait for midnight).
    """
    try:
        from paths import HERMES_DATA
        with open(os.path.join(HERMES_DATA, 'vacation_mode.json')) as f:
            exp = json.load(f)['rules']['unclog_waiver']['expires']
        exp_dt = datetime.datetime.fromisoformat(str(exp).replace('Z', '+00:00'))
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=datetime.timezone.utc)
    except Exception as e:
        return False, f'unreadable:{type(e).__name__}'  # fail-closed, but say WHY
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    if now < exp_dt:
        return True, 'active'
    return False, 'expired'


def flip1_active(now=None):
    """True only while the recorded waiver expiry is still in the future.

    Reads the file each call (no cache) so the expiry takes effect on the first
    gate after the timestamp, not on the first process start after it.
    """
    return flip1_state(now=now)[0]


def _selfcheck():
    import paths
    real_data = paths.HERMES_DATA
    before = datetime.datetime(2026, 10, 23, 23, 59, 59, tzinfo=datetime.timezone.utc)
    after = datetime.datetime(2026, 10, 24, 0, 0, 1, tzinfo=datetime.timezone.utc)
    at = datetime.datetime(2026, 10, 24, 0, 0, 0, tzinfo=datetime.timezone.utc)

    assert flip1_active(now=before) is True, 'must be active before expiry'
    assert flip1_active(now=after) is False, 'must lapse at expiry'
    assert flip1_active(now=at) is False, 'expiry is exclusive (>= expires = off)'
    assert flip1_state(now=before) == (True, 'active'), flip1_state(now=before)
    assert flip1_state(now=at) == (False, 'expired'), flip1_state(now=at)

    # reason must NOT claim 'expired' for file problems (the #103 false-lapse class)
    paths.HERMES_DATA = '/nonexistent-waiver-selfcheck'
    try:
        active, why = flip1_state()
        assert active is False and why.startswith('unreadable:'), (active, why)
        assert why != 'expired', 'missing file must not be reported as an expiry'
    finally:
        paths.HERMES_DATA = real_data

    import tempfile
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, 'vacation_mode.json'), 'w') as f:
        json.dump({'rules': {}}, f)  # readable file, no unclog_waiver key = 17:36 window
    paths.HERMES_DATA = tmp
    try:
        active, why = flip1_state()
        assert active is False and why == 'unreadable:KeyError', (active, why)
        assert flip1_active() is False, 'missing key must still fail closed'
    finally:
        paths.HERMES_DATA = real_data

    assert flip1_active() in (True, False), 'restored path must return a bool'
    print('waiver_expiry --selfcheck PASS (active/expired/unreadable-key/missing-file all '
          'distinguished, fail-closed on both file failure modes)')


if __name__ == '__main__':
    import sys
    if '--selfcheck' in sys.argv:
        _selfcheck()
    else:
        print(f'flip1_active={flip1_active()}')
