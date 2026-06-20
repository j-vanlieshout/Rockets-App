---
name: refactor-agentsmd
description: Refactor an existing AGENTS.md to follow progressive disclosure — minimal root, linked docs, skills for procedural know-how.
---

Refactor my AGENTS.md to follow progressive disclosure.

1. Find contradictions. Ask which to keep.
2. Extract essentials for the root: one-line description, package manager, build /
   typecheck, anything truly relevant to every task.
3. Keep the 2–3 most critical workflows in the root as numbered steps —
   they earn their place.
4. Group the rest into categories. One markdown file per category in docs/.
   Move procedural know-how into `.agents/skills/<name>/SKILL.md`.
5. Output a minimal root AGENTS.md linking each file with a one-line description.
   Replace code snippets with file:line refs.
6. Flag for deletion: redundant, vague, or overly obvious instructions.
