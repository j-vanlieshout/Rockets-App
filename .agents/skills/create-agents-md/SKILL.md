---
name: create-agents-md
description: Analyze a codebase and produce a well-structured AGENTS.md (linked from CLAUDE.md) with progressive disclosure into docs/ and .agents/skills/. Use when bootstrapping agent docs for a project or when AGENTS.md needs a full rewrite.
---

Be extremely concise. Sacrifice grammar for concision.
At the end of each plan, list unresolved questions.

## Output files

| File | Purpose |
|------|---------|
| `AGENTS.md` | Root doc — 100–150 lines, links out to everything else |
| `CLAUDE.md` | One line: `@AGENTS.md` — Claude Code's actual entry point |
| `docs/architectural_patterns.md` | Recurring code patterns with file:line refs |
| `.agents/skills/<name>/SKILL.md` | One skill per procedural workflow |
| `.claude/skills/<name>` | Symlink → `../../.agents/skills/<name>` (Claude Code's lookup path) |

## AGENTS.md rules

1. **Under 150 lines** — 100–150 is the target.
2. **Always include at the top:**
   - `Be extremely concise. Sacrifice grammar for concision.`
   - `At the end of each plan, list unresolved questions.`
3. **Cover WHAT / WHY / HOW** — tech stack, purpose, critical commands.
4. **File:line refs, not code snippets** — `config.py:9` not a fenced block.
5. **2–3 critical workflows as numbered steps** — only the ones every contributor runs.
6. **Progressive disclosure index** — one line per linked file describing when to read it.
7. **No formatting rules** — linters own style; omit from AGENTS.md.

## Codebase analysis steps

1. Read entry points: `app.py`, `main.py`, `index.html`, `package.json`, `Makefile`.
2. Read config: `config.py`, `.env.example`, `pyproject.toml`, `tsconfig.json`.
3. Read models/schema: ORM models, DB migrations, GraphQL/OpenAPI schema.
4. Read tests: one test file per layer to understand fixture patterns.
5. Note: **which data is live-fetched vs cached**, **upsert vs insert patterns**,
   **test DB isolation strategy** — these become `architectural_patterns.md` entries.
6. Identify the 2–3 commands every contributor must know (sync, serve, test).

## Extracting architectural patterns

Move to `docs/architectural_patterns.md` any pattern that:
- Repeats across 3+ files, OR
- Would surprise a reader unfamiliar with the codebase

Each entry: name → what it does → file:line refs → when/why it applies.

## Extracting skills

Move to `.agents/skills/<name>/SKILL.md` any workflow that:
- Has non-obvious steps or failure modes
- Requires troubleshooting knowledge
- Is run less often than the critical 2–3 (which stay in root)

YAML frontmatter: `name` + `description` (one line, used for skill discovery).

## CLAUDE.md setup

```
echo "@AGENTS.md" > CLAUDE.md
```

Claude Code reads `CLAUDE.md`; `@AGENTS.md` imports the real content.
Never write agent instructions directly into `CLAUDE.md`.

## .claude/skills symlinks

If `.claude/skills/` already exists as a directory with per-skill symlinks,
add new skills individually:

```
ln -s ../../.agents/skills/<name> .claude/skills/<name>
```

If `.claude/skills/` doesn't exist yet, a single directory symlink works:

```
mkdir -p .claude && ln -s ../.agents/skills .claude/skills
```

## Flags for deletion

Remove from any agent doc:
- Formatting / style rules (linter's job)
- Instructions derivable from reading the code
- Git history explanations (use `git log`)
- Redundant restatements of the same fact
- Vague instructions without actionable steps
