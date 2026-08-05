---
name: transcript-analysis
description: "Analyze local video transcripts. Extract lessons, patterns, and actionable insights for Hermes trading system. Triggers on: 'analyze transcript', 'read transcript', 'what can we learn', 'lessons from'."
platforms: [linux, macos, windows]
---

# Transcript Analysis

## When to use

When the user drops a transcript (`*.md` file with `[timestamp]` formatted lines) in `~/.hermes/vids/` and wants:
- Key takeaways relevant to the Hermes trading system
- Patterns or techniques worth stealing
- Concepts to spec or implement

## Workflow

1. **Find the transcript**: Check `~/.hermes/vids/` for `.md` files. If the user says "read the most recent", use `ls -t ~/.hermes/vids/*.md | head -1`.

2. **Read it**: Use the Read tool. Transcripts are timestamped like `[123.4s] text`. They can be long — read in chunks if needed.

3. **Extract relevance to Hermes**: For each point the speaker makes, ask:
   - Does Hermes already do this? (check AGENTS.md, brain/, scripts/)
   - Is this a known concept we've discussed? (check brain.db via `hebbian_engine.py recall`)
   - Can we steal this technique?
   - Is it irrelevant to algorithmic trading?

4. **Structure the output**:

```
Key takeaways from "<transcript title>":

**Worth stealing:**
1. <technique> — <2-line description> — <which Hermes module it applies to>

**Already have:**
- <concept> — <how we already do it>

**Not applicable:**
- <concept> — <why it doesn't fit>
```

5. **If actionable items emerge**: Offer to write specs to `plans/`. Don't auto-write unless the user says to.

6. **Learn**: Store key concepts in brain via `hebbian_engine.py` if they're novel and relevant.

## YouTube transcripts

If the user shares a YouTube URL instead of a local file, fetch it first:

```bash
uv run python3 ~/.hermes/skills/media/youtube-content/scripts/fetch_transcript.py "URL" --text-only --timestamps > ~/.hermes/vids/<descriptive-name>.md
```

Then proceed with step 2 above.

## Transcript format

Transcripts in `~/.hermes/vids/` use this format:
```
[0.0s] First line of speech
[1.6s] Second line
[3.3s] Third line
```

Each line has a timestamp in seconds and the spoken text. Multi-speaker transcripts may have `>>` prefixes for dialogue turns.