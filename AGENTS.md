# AGENTS.md (for weaker models)

- Be explicit and deterministic: follow instructions exactly, avoid assumptions, and do not invent files, modules, or behavior not shown in the codebase.
- Keep changes minimal: modify only what is necessary to fix the issue; never refactor, rename, or restructure unless explicitly requested.
- Debug in order: identify the exact error → explain the cause briefly → provide the smallest possible fix with concrete code changes.
- Avoid creativity: do not suggest alternative architectures, dependency changes, or “best practices” unless the user asks for them.
- When uncertain: do not guess; say “not enough information” and ask one clear, specific question.
