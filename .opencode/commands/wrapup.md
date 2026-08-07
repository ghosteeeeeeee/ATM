---
description: Run the full post-change workflow (bug_hunter, memory, CEO, commit+push)
---

Load and execute the `post-change` skill. Run all 4 steps in order:

1. `bug_hunter` — audit changed files, implement fixes if found
2. OpenMemory — store what was done
3. CEO — inform via ceo-comm skill
4. git commit + push

Do not skip any steps. Do not ask for confirmation — just run them.
