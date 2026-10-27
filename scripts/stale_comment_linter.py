#!/usr/bin/env python3
"""
stale_comment_linter.py — SHADOW-RECKONING Q2 mechanism (CEO consult 20261027T024741Z):
"same mistakes still being made" class #1 = comment-vs-code drift (BUG-065: constants
comment promises behavior the code can no longer produce; the 10-24 'expired 2026-10-24'
strings; the 'MUST match X' pairs drifting apart).

Rules (mechanical only — no semantic claims):
  R1  'MUST match <CONST>' / 'matched to <CONST>' pairs in hermes_constants.py comments
      must be EQUAL to the referenced constant.
  R2  constants whose comment says UNUSED (and 'left in constants') must not be
      referenced anywhere else in scripts/*.py.
  R3  hardcoded calendar dates in scripts/*.py STRING literals that claim expiry/lapse
      ('expired YYYY-MM-DD' / 'until YYYY-MM-DD') must not be in the past.

Usage:
  python3 scripts/stale_comment_linter.py            # print warnings, exit 0
  python3 scripts/stale_comment_linter.py --strict   # exit 1 on any warning (CI/hook opt-in)

Hook: .git/hooks/pre-commit runs the non-strict form (warn-only) — created 2026-10-27.
"""
import glob
import os
import re
import sys
from datetime import date

REPO = '/root/.hermes'
CONSTANTS = os.path.join(REPO, 'scripts', 'hermes_constants.py')


def parse_constants(text):
    """name -> numeric value (first plain assignment only)."""
    vals = {}
    for m in re.finditer(r'^([A-Z][A-Z0-9_]+)\s*=\s*(-?\d+(?:\.\d+)?)\s*(?:#.*)?$',
                         text, re.M):
        vals.setdefault(m.group(1), float(m.group(2)))
    return vals


def rule_r1(const_text, vals):
    out = []
    pat = re.compile(r'(MUST match|matched to|must match)\s+([A-Z][A-Z0-9_]+)')
    for lineno, line in enumerate(const_text.splitlines(), 1):
        if line.lstrip().startswith('#'):
            continue
        for m in pat.finditer(line):
            lhs = re.match(r'\s*([A-Z][A-Z0-9_]+)\s*=', line)
            if not lhs:
                continue
            a, b = lhs.group(1), m.group(2)
            if a in vals and b in vals and vals[a] != vals[b]:
                out.append(f'R1 hermes_constants.py:{lineno}: {a}={vals[a]:g} but comment '
                           f'requires match with {b}={vals[b]:g}')
    return out


def rule_r2(const_text, vals):
    out = []
    pat = re.compile(r'^([A-Z][A-Z0-9_]+)\s*=.*#\s*.*'
                     r'(?:UNUSED|left in constants.*unused).*$',   # whole line: trailing
                     re.I | re.M)                                  # "while X=0" clauses
    cond_pat = re.compile(r'while\s+([A-Z][A-Z0-9_]+)\s*=\s*0')  # conditional-unused claim
    hits = [(m.group(1), m.group(0)) for m in pat.finditer(const_text)]
    if not hits:
        return out
    others = []
    for p in glob.glob(os.path.join(REPO, 'scripts', '*.py')):
        if os.path.abspath(p) in (os.path.abspath(CONSTANTS), os.path.abspath(__file__)):
            continue  # constants parsed separately; skip self (docstring examples)
        try:
            with open(p, errors='replace') as f:
                # strip code comments — prose mentioning the name is not a reference
                others.append((p, '\n'.join(
                    ln.split('#', 1)[0] for ln in f)))
        except Exception:
            pass
    for name, comment in hits:
        cond = cond_pat.search(comment)
        if cond:
            # comment may abbreviate the companion constant ("unused while BOOST=0"
            # where the real name is LONG_RSI_SWEET_SPOT_BOOST)
            full = cond.group(1)
            cand = full if full in vals else next(
                (v for v in vals if v.endswith('_' + full) or v.endswith(full)), None)
            if cand and vals[cand] == 0:
                continue  # claim is conditionally true today ("unused while X=0", X IS 0)
        for p, txt in others:
            if re.search(rf'\b{name}\b', txt):
                out.append(f'R2 hermes_constants.py: {name} marked UNUSED but referenced '
                           f'in {os.path.basename(p)}')
                break
    return out


def rule_r3():
    out = []
    today = date.today()
    pat = re.compile(r'(expired|expires|until|lapse[ds]?)\s*["\']?(\d{4}-\d{2}-\d{2})',
                     re.I)
    for p in glob.glob(os.path.join(REPO, 'scripts', '*.py')):
        if os.path.abspath(p) == os.path.abspath(__file__):
            continue  # skip self (docstring examples)
        try:
            with open(p, errors='replace') as f:
                for lineno, line in enumerate(f, 1):
                    # only STRING literals (quotes present), not comments' prose
                    if '"' not in line and "'" not in line:
                        continue
                    for m in pat.finditer(line):
                        try:
                            d = date.fromisoformat(m.group(2))
                        except ValueError:
                            continue
                        if d < today:
                            out.append(f'R3 {os.path.basename(p)}:{lineno}: hardcoded '
                                       f'past date {m.group(2)} in string ({m.group(1)})')
        except Exception:
            pass
    return out


def main():
    strict = '--strict' in sys.argv
    try:
        with open(CONSTANTS, errors='replace') as f:
            const_text = f.read()
    except Exception as e:
        print(f'stale_comment_linter: cannot read constants: {e}')
        return 0 if not strict else 1
    vals = parse_constants(const_text)
    warnings = rule_r1(const_text, vals) + rule_r2(const_text, vals) + rule_r3()
    if not warnings:
        print('stale_comment_linter: clean')
        return 0
    print(f'stale_comment_linter: {len(warnings)} warning(s)')
    for w in warnings:
        print(f'  ⚠️  {w}')
    return 1 if strict else 0


if __name__ == '__main__':
    sys.exit(main())
