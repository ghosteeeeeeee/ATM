#!/usr/bin/env python3
"""
ceo_index.py — deterministic section index over the CEO's own prior work.

Why this exists: the CEO's highest-value retrieval corpus is its OWN prior rulings —
`ceo_report.md` (append-only, dated `## CEO ... — <ts>` headers) and
`checkpoints/<ts>-{decision,result}-N.md`. Today a CEO run rediscovers that history by
`tail`-ing the report and `ls`-ing the checkpoints dir (21 + 21 calls on record), then
reading whole files to find one ruling. This builds a compact, deterministic index so a
run can see the whole decision history in one read and jump straight to the one file it
needs.

Deliberately NOT a vector index. The corpus is small, append-only, and already has
machine-parseable date/topic headers; exact index beats embedding here, costs nothing to
build, and cannot silently go stale. If the report ever grows past what grep handles
comfortably, revisit — that threshold is a long way off.

Usage:
    ceo_index.py                 # full index (report sections + checkpoints + topics)
    ceo_index.py --topic gate    # only sections mentioning 'gate'
    ceo_index.py --since 20261013
    ceo_index.py --max-chars 2500

Exit codes: 0 ok, 5 missing inputs.
"""
import argparse
import glob
import os
import re
import sys

CEO_DIR = "/root/.hermes/automation/ceo"
REPORT = os.path.join(CEO_DIR, "ceo_report.md")
CHECKPOINTS = os.path.join(CEO_DIR, "checkpoints")

# Section headers the CEO actually writes. Matched at line start.
SECTION_RE = re.compile(r"^(#{1,3})\s+(CEO[^-\n]*|RSI[^-\n]*|.*)\s+—\s+(\d{8}T\d{4,6}Z|\d{4}-\d{2}-\d{2})")
# Checkpoint files: <ts>-decision.md / <ts>-result-N.md
CKPT_RE = re.compile(r"^(\d{8}T\d{6}Z)-(decision|result(?:-\d+)?)\.md$")

DEFAULT_MAX_CHARS = 3000


def index_report(path=REPORT):
    """Yield (line_no, level, title, stamp, first_line_of_body)."""
    if not os.path.exists(path):
        return []
    out, cur = [], None
    with open(path, errors="replace") as f:
        for i, line in enumerate(f, 1):
            m = SECTION_RE.match(line)
            if m:
                if cur:
                    out.append(cur)
                cur = [i, len(m.group(1)), m.group(2).strip(), m.group(3), ""]
            elif cur and not cur[4] and line.strip() and not line.startswith("#"):
                # First substantive line under the header — enough to identify the
                # section without the CEO having to open the file.
                cur[4] = line.strip()[:160]
    if cur:
        out.append(cur)
    return out


def index_checkpoints(directory=CHECKPOINTS):
    """Yield (filename, stamp, kind, size_bytes)."""
    out = []
    for p in glob.glob(os.path.join(directory, "*.md")):
        b = os.path.basename(p)
        m = CKPT_RE.match(b)
        if not m:
            continue
        out.append((b, m.group(1), m.group(2), os.path.getsize(p)))
    out.sort(key=lambda r: r[1])
    return out


BRIEF_RE = re.compile(r"^(?:brief-|ceo_task_)(.+?)(?:-(\d{8}))?\.md$")


def index_briefs(directory=CEO_DIR):
    """Briefs are named free-form (brief-<topic>[-<date>].md, ceo_task_<topic>_<date>.md),
    so index by filename + mtime rather than a strict stamp. Sorted newest first."""
    out = []
    for p in glob.glob(os.path.join(directory, "brief-*.md")) + \
             glob.glob(os.path.join(directory, "ceo_task_*.md")):
        b = os.path.basename(p)
        m = BRIEF_RE.match(b)
        if not m:
            continue
        mtime = os.path.getmtime(p)
        import datetime as _dt
        stamp = _dt.datetime.fromtimestamp(mtime, _dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out.append((b, stamp, os.path.getsize(p)))
    out.sort(key=lambda r: r[1], reverse=True)
    return out


def main():
    ap = argparse.ArgumentParser(description="Index the CEO's prior rulings.")
    ap.add_argument("--topic", help="case-insensitive substring filter on section text")
    ap.add_argument("--since", help="only sections/checkpoints at or after this stamp (YYYYMMDD...)")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    ap.add_argument("--no-checkpoints", action="store_true")
    ap.add_argument("--no-briefs", action="store_true",
                    help="skip briefs (per-task scratch, low reuse)")
    args = ap.parse_args()

    sections = index_report()
    ckpts = [] if args.no_checkpoints else index_checkpoints()
    if not sections and not ckpts:
        print(f"[CEO-INDEX] nothing to index (no {REPORT}, no checkpoints)", file=sys.stderr)
        return 5

    if args.since:
        sections = [s for s in sections if s[3] >= args.since]
        ckpts = [c for c in ckpts if c[1] >= args.since]
    if args.topic:
        t = args.topic.lower()
        sections = [s for s in sections
                    if t in f"{s[2]} {s[4]}".lower()]
        # Checkpoints have no body index; filter on filename topic token.
        ckpts = [c for c in ckpts if t in c[0].lower()]

    lines = ["# CEO prior-work index", ""]
    lines.append(f"Report sections: {len(sections)}   Checkpoints: {len(ckpts)}")
    lines.append("Read a single checkpoint file for full rationale — do not read them all.")
    lines.append("")

    if sections:
        lines.append("## Report sections (newest first)")
        for ln, lvl, title, stamp, body in reversed(sections):
            pad = "  " * max(0, lvl - 2)
            lines.append(f"{pad}- {stamp}  {title}  (line {ln})")
            if body:
                lines.append(f"{pad}    {body}")
        lines.append("")

    if ckpts:
        lines.append("## Checkpoints (oldest first)")
        for fn, stamp, kind, size in ckpts:
            lines.append(f"  - {stamp}  {kind:<9} {size:>6}B  {fn}")
        lines.append("")

    # Briefs: scratch inputs, listed last and only if asked. They are per-task and
    # rarely reused, but knowing one exists beats re-writing it (several briefs were
    # re-created by later runs because nobody could find the original).
    if not args.no_briefs:
        briefs = index_briefs()
        if briefs:
            lines.append("## Briefs (per-task scratch — read only if directly relevant)")
            for fn, stamp, size in briefs:
                lines.append(f"  - {stamp}  {size:>6}B  {fn}")
            lines.append("")

    # Topic rollup: which topics recur, so the CEO can see its own repeated concerns.
    if not args.topic:
        counts = {}
        for _, _, title, _, _ in sections:
            for w in re.findall(r"[a-z]{5,}", title.lower()):
                counts[w] = counts.get(w, 0) + 1
        top = sorted(counts.items(), key=lambda kv: -kv[1])[:12]
        if top:
            lines.append("## Recurring topics in section titles")
            lines.append("  " + "  ".join(f"{w}({n})" for w, n in top))

    text = "\n".join(lines)
    if len(text) > args.max_chars:
        text = text[:args.max_chars] + f"\n...[truncated, {len(text)} chars total]"
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
