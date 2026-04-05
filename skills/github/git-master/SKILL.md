---
name: git-master
description: Run the Git Workflow Master subagent to audit the Hermes trading system repo for inconsistencies, symlinks, broken imports, and structural issues.
---

# git-master — Hermes Repo Audit & Git Workflow Analysis

## When to Use
Run this when you need a comprehensive audit of the Hermes codebase for:
- Symlinks that break on other machines (standalone zip download)
- Broken imports (files that reference non-existent modules)
- Duplicate/redundant files
- Inconsistent naming conventions
- Missing dependencies or broken references
- Git history issues (large files, binary blobs, merged but untracked)
- Any structural problems that would prevent the zip from working standalone

## Subagent
Uses the **Git Workflow Master** subagent persona from `/hermes/subagents/git-workflow-master.md`.
This agent has deep Git expertise and applies it to audit the Hermes system.

## Steps

### 1. Read the subagent persona
Load: `/hermes/subagents/git-workflow-master.md`

### 2. Audit the Hermes repo
Run comprehensive checks on `/root/.hermes`:

**A. Symlinks check**
```bash
find /root/.hermes -type l -exec ls -la {} \; 2>/dev/null
```
Report any symlinks — all must be resolved to real files before zip export.

**B. Import consistency check**
```bash
# Find all Python import statements
grep -rh "^import \|^from " /root/.hermes/scripts/*.py 2>/dev/null | sort -u

# Check for imports of files that don't exist
for f in /root/.hermes/scripts/*.py; do
    grep -h "^from \|^import " "$f" 2>/dev/null
done | sort -u
```

**C. Duplicate files check**
```bash
# Find files with same content (potential duplicates)
find /root/.hermes/scripts -name "*.py" -exec md5sum {} \; 2>/dev/null | sort | uniq -D -w32
```

**D. Git history check**
```bash
cd /root/.hermes
git log --oneline -20
git fsck --full 2>&1 | grep -v "Checking object directories"
git count-objects -vH
git lfs ls-files 2>/dev/null
```

**E. File structure check**
```bash
find /root/.hermes -maxdepth 3 -type f -name "*.py" | sort
ls -la /root/.hermes/
ls -la /root/.hermes/scripts/ | head -30
ls -la /root/.hermes/config/
ls -la /root/.hermes/data/ 2>/dev/null | head -10
```

**F. Zip self-test (if one exists)**
```bash
# If there's a zip in /hermes/, verify its contents
ls -la /hermes/*.zip 2>/dev/null
unzip -l /hermes/hermes-trading-system-v3.zip 2>/dev/null | grep "ai_decider\|symlink\|->" | head -10
```

**G. Cross-reference check**
```bash
# Check for .py files referenced in scripts but missing
grep -rho "exec\|import\|open\|read_file\|write_file" /root/.hermes/scripts/*.py 2>/dev/null | \
  grep -E "\.(py|json|yaml|sql|sh|csv|md)$" | sort -u
```

**H. Skills check**
```bash
ls -la /root/.hermes/skills/*/SKILL.md 2>/dev/null
# Verify referenced files in skills actually exist
```

### 3. Apply Git Workflow Master analysis
After collecting the data above, apply the subagent's expertise to:
- Identify which issues are critical (zip won't work standalone)
- Prioritize fixes
- Provide a remediation plan with exact commands

## Deliverables
1. **Critical issues** — things that MUST be fixed before the zip works standalone
2. **Warnings** — things that could break but aren't fatal
3. **Recommendations** — structural improvements for the repo
4. **Fix commands** — exact commands to apply each fix

## Pitfalls
- `git archive` resolves symlinks automatically — but the working tree check won't
- Absolute symlinks (e.g. `/root/.hermes/...`) break on other machines
- Relative symlinks (e.g. `../scripts/foo.py`) are safe if the directory structure is preserved
- Python's `sys.path.insert(0, ...)` at runtime can mask import issues
- `.pyc` files in the repo can cause stale bytecode issues

## Verification
After applying fixes, re-run the symlinks check and import check to confirm.
