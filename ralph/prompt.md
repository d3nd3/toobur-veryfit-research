# ISSUES

Open issues labelled `ready-for-agent` are provided at the start of context (local `issues/` folder or GitHub, per **Issue source**). Parse them to understand the open work.

Work on AFK issues (`ready-for-agent`) only — not `ready-for-human` (HITL).

You've also been passed the last few commits. Review these to understand what work has been done.

If all AFK tasks are complete, output **NO MORE TASKS**.

Issue tracker conventions: `docs/agents/issue-tracker.md`. Triage labels: `docs/agents/triage-labels.md`.

# TASK SELECTION

Pick the next task. Prioritize in this order:

1. Critical bugfixes
2. Development infrastructure (tests, dev scripts)
3. Tracer bullets for new features — a thin end-to-end slice through all layers before expanding
4. Polish and quick wins
5. Refactors

Respect **Blocked by** links in issue bodies — don't start work blocked by an open issue unless you can unblock it in the same iteration.

# EXPLORATION

Explore the repo. Read `CONTEXT.md` and relevant `docs/adr/` before changing code. Use domain vocabulary from the glossary.

# IMPLEMENTATION

Follow the TDD skill at `.agents/skills/tdd/SKILL.md` when adding or changing executable code (red → green → refactor, one vertical slice at a time).

# FEEDBACK LOOPS

Before committing, run any validation relevant to what you changed (e.g. `python3 -m py_compile` on edited Python, sanity-check parsers against sample dumps in `packetdumps/`).

# COMMIT

Make a git commit. The commit message must:

1. Include key decisions made
2. Include files changed
3. Note blockers or context for the next iteration

# THE ISSUE

Use the **Path** field on each issue. If **Issue source** is `local`:

- **Complete** — set `status: closed` in frontmatter, remove `ready-for-agent` from `labels`, append a summary under `## Comments`
- **Incomplete** — append progress under `## Comments` (what was done, what's left)

If **Issue source** is `github`:

- **Complete** — `gh issue close <number> --comment "..."`; remove `ready-for-agent` if still present
- **Incomplete** — `gh issue comment <number> --body "..."`

# FINAL RULES

ONLY WORK ON A SINGLE TASK.
