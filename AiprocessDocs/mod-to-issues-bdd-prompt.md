Add BDD to my installed `/to-issues` skill, append-only.

1. Find the SKILL.md whose frontmatter name is `to-issues`. If multiple, ask me which.
2. Copy it to SKILL.md.bak first.
3. Append (do not edit/delete ANY existing line, especially the issue template) this section at the very end of the file:

## Addendum — BDD scenarios (additive)
Everything above still applies unchanged, including the Acceptance criteria section.
Each published issue also gets a `## BDD scenarios` section right after `## Acceptance criteria`: executable Gherkin with a Feature line, one happy-path Scenario, and at least one failure/edge Scenario (Scenario Outline + Examples for data variations). Every scenario must trace to an acceptance criterion and a user story — if not, stop and flag it, don't invent requirements. Describe observable end-to-end behaviour in domain language; no file paths or function names.
Add to the quiz step: "Are the BDD scenarios correct, and do they cover the happy path plus key failure/edge cases?" — keep all existing quiz questions.

4. Show me a unified diff. It must contain additions only. If anything was removed or changed, restore from SKILL.md.bak and stop.