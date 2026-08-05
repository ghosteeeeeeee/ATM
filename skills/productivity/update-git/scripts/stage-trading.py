#!/usr/bin/env python3
"""
stage-trading.py — Selective staging for Hermes update-git workflow.

Shows all changed files grouped by type, then stages only trading-related files.
Must show user the grouped list BEFORE staging — user picks what to include.
"""
import subprocess
import sys
from pathlib import Path

HERMES = Path("/root/.hermes")

# Categories for display — order matters (most important first)
CATEGORIES = [
    ("TRADING SIGNALS", [
        "scripts/accel_300_signals.py",
        "scripts/away_detector.py",
        "scripts/breakout_engine.py",
        "scripts/ema20_50_signals.py",
        "scripts/exhaustion_signals.py",
        "scripts/gap300_signals.py",
        "scripts/ma300_candle_confirm_signals.py",
        "scripts/macd_rules.py",
        "scripts/pattern_scanner.py",
        "scripts/rs_signals.py",
        "scripts/trend_purity_signals.py",
    ]),
    ("TRADING SCRIPTS", [
        "scripts/archive-signals.py",
        "scripts/candle_predictor.py",
        "scripts/cascade_flip.py",
        "scripts/decider_run.py",
        "scripts/hl-sync-guardian.py",
        "scripts/hyperliquid_exchange.py",
        "scripts/hyperliquid-trader.py",
        "scripts/live-decider.py",
        "scripts/position_manager.py",
        "scripts/price_collector.py",
        "scripts/signal_compactor.py",
        "scripts/top150.py",
        "scripts/trading-checklist.py",
    ]),
    ("TRADING BACKTEST/UTILS", [
        "scripts/atr_cache.py",
        "scripts/atr_dry_run.py",
        "scripts/backfill_72h.py",
        "scripts/backfill_hl_pnl.py",
        "scripts/backfill_orphan_hl_prices.py",
        "scripts/backfill_prices.py",
        "scripts/backtest_candle.py",
        "scripts/backtest_minimax.py",
        "scripts/backtest_patterns.py",
        "scripts/checkpoint_utils.py",
        "scripts/metrics_collector.py",
        "scripts/purge_and_compact.py",
        "scripts/rebuild_ab_results.py",
        "scripts/speed_tracker.py",
    ]),
    ("TRADING CORE", [
        "scripts/hermes_constants.py",
        "scripts/hermes_ab_utils.py",
        "scripts/brain.py",
    ]),
    ("TRADING SKILLS", [
        "skills/trading/",
    ]),
    ("UPDATE-GIT SCRIPT", [
        "scripts/update-git.py",
    ]),
]

# Files that should NEVER be staged
FORBIDDEN = ["brain/", "memories/", ".db$", "auth.json", "wandb-local/",
             "CONTEXT.md", "SOUL.md", "processes.json", ".update_check",
             "archive/signals/", "wandb/", "skills/creative/", "skills/mlops/",
             "skills/red-teaming/", "skills/apple/", "skills/gaming/",
             "skills/media/", "skills/research/", "skills/smart-home/",
             "skills/software-development/hermes-agent-skill-authoring",
             "skills/software-development/plan/", "skills/software-development/writing-plans/",
             "skills/software-development/test-driven-development/",
             "skills/software-development/subagent-driven-development/",
             "skills/software-development/requesting-code-review/",
             "skills/software-development/multi-file-symbol-removal/",
             "skills/data-science/", "skills/devops/", "skills/dogfood/",
             "skills/email/", "skills/github/", "skills/leisure/",
             "skills/mcp/", "skills/note-taking/", "skills/productivity/google-workspace/",
             "skills/productivity/linear/", "skills/productivity/nano-pdf/",
             "skills/productivity/notion/", "skills/productivity/ocr-and-documents/",
             "skills/productivity/powerpoint/", "skills/reality-checker/"]


def get_changed():
    status = subprocess.run(["git", "status", "--porcelain"],
                           cwd=HERMES, capture_output=True, text=True).stdout
    changed = {}
    for line in status.splitlines():
        if len(line) < 4:
            continue
        code = line[:2]
        fname = line[3:].strip()
        # Only tracked files (M or D in first char), not untracked (??)
        if code.strip() and not line.startswith("??") and line[0] in ("M", "D", " "):
            # Handle " M filename" vs "M  filename"
            if line[0] == " " and line[1] == "M":
                fname = line[3:].strip()
            elif line[0] == "M" and line[1] == " ":
                fname = line[3:].strip()
            changed[fname] = code.strip()
    return changed


def show_grouped(changed):
    print("\n" + "=" * 70)
    print("CHANGED FILES GROUPED BY TYPE")
    print("=" * 70)

    for cat_name, patterns in CATEGORIES:
        files = []
        for f in changed:
            if any(f.startswith(p) or f == p for p in patterns):
                files.append(f)
        if files:
            print(f"\n--- {cat_name} ({len(files)} files) ---")
            for f in sorted(files):
                print(f"  [{changed[f]}] {f}")

    # Non-trading (changed but not in any trading category)
    trading_files = set()
    for cat_name, patterns in CATEGORIES:
        for f in changed:
            if any(f.startswith(p) or f == p for p in patterns):
                trading_files.add(f)

    non_trading = {f: changed[f] for f in changed if f not in trading_files}
    if non_trading:
        print(f"\n--- NON-TRADING (excluded from auto-staging) ---")
        for f in sorted(non_trading):
            print(f"  [{non_trading[f]}] {f}")

    print("\n" + "=" * 70)
    print(f"Total: {len(changed)} changed files ({len(trading_files)} trading, {len(non_trading)} non-trading)")
    print("=" * 70)


def stage_trading_files(changed):
    """Stage only trading-related files, unstage any forbidden files."""
    to_stage = []
    for f in changed:
        # Check if file matches any trading category
        in_trading = any(
            f.startswith(p) or f == p
            for cat_name, patterns in CATEGORIES
            for p in patterns
        )
        if in_trading:
            to_stage.append(f)

    if not to_stage:
        print("No trading files to stage.")
        return

    print(f"\nStaging {len(to_stage)} trading files...")
    for f in to_stage:
        print(f"  + {f}")
        subprocess.run(["git", "add", "--", f], cwd=HERMES)

    # Check if any forbidden files got staged
    new_status = subprocess.run(["git", "status", "--short"],
                              cwd=HERMES, capture_output=True, text=True).stdout
    forbidden_staged = [
        l for l in new_status.splitlines()
        if any(pat in l for pat in FORBIDDEN) and l.startswith(("M ", "D "))
    ]
    if forbidden_staged:
        print(f"\n⚠️  FORBIDDEN FILES STAGED — unstaging:")
        for l in forbidden_staged:
            fname = l[3:].strip()
            print(f"  - {fname}")
            subprocess.run(["git", "reset", "HEAD", "--", fname], cwd=HERMES)
        print("\nRe-run to see updated state.")


def main():
    changed = get_changed()
    if not changed:
        print("No changed files.")
        return

    show_grouped(changed)

    # Auto-stage trading files
    stage_trading_files(changed)

    # Final status
    print("\n--- After staging ---")
    result = subprocess.run(["git", "status", "--short"], cwd=HERMES, capture_output=True, text=True)
    print(result.stdout or "(empty — nothing staged)")
    print("\nNext: git commit -m 'message', then python3 scripts/update-git.py")


if __name__ == "__main__":
    main()
