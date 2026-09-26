# Issue tracker: local `issues/` folder

PRDs and work items live as markdown under [`issues/`](../../issues/) at the repo root. GitHub Issues are **not** used (disabled on the remote).

## Layout

```
issues/
├── README.md
└── <NNN>-<feature-slug>/
    ├── meta.md       ← id, title, status, labels
    ├── PRD.md        ← full spec (when feature-sized)
    └── tasks/        ← numbered implementation slices
```

See [`issues/README.md`](../../issues/README.md) for conventions and the index.

## Conventions

- **Create an issue / publish a PRD** — add `issues/<NNN>-<slug>/` with `meta.md` (+ `PRD.md` if needed). Pick the next three-digit id from the index table.
- **Read an issue** — read `meta.md`; follow links to `PRD.md` or `tasks/*.md`.
- **List open work** — scan `issues/README.md` index, or `rg '^status:' issues/`.
- **Comment** — append under `## Comments` in `meta.md` or the task file.
- **Triage** — edit `status:` in `meta.md` frontmatter. Vocabulary: [`triage-labels.md`](./triage-labels.md).
- **Close** — set `status: closed` with a closing comment.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## When a skill says "publish to the issue tracker"

Create or update a directory under `issues/`.

## When a skill says "fetch the relevant ticket"

Read the path the user gives (e.g. `issues/001-complete-toobur-gadgetbridge-driver/meta.md`), or resolve by id from the index.
