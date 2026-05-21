# Tasks

Create one directory per cross-repo task. The task directory is the recovery point for interrupted or resumed scenario work.

Recommended naming:

```text
YYYY-MM-DD-scenario-name
```

Use a suffix when multiple tasks share the same scenario and date:

```text
YYYY-MM-DD-scenario-name-short-topic
```

Recommended files:

```text
spec.md
status.md
decisions.md
validation.md
```

Prefer creating task files with the helper CLI:

```bash
bin/scenario-harness init-task <scenario> [task-id] --request "..."
```

The helper fills repo order, branch gates, repo-local checks, instruction sources, and key files
from the scenario configuration. It is idempotent for agent retries: existing task files are reported
and are not overwritten.

If the helper cannot be used, start from the templates in `templates/`:

| Template | Task File |
| --- | --- |
| `spec.md` | `spec.md` |
| `task-status.md` | `status.md` |
| `decisions.md` | `decisions.md` |
| `validation-report.md` | `validation.md` |

When continuing a task, read the task files before editing repositories:

1. `spec.md`
2. `status.md`
3. `decisions.md`
4. `validation.md`

Use `spec.md` to understand the task definition and execution steps. Use `status.md` to find the current step. Use `validation.md` to avoid rerunning checks unless the related repo changed or prior output is stale. Use `decisions.md` to preserve compatibility and delivery choices.

Before entering business repositories, refresh mechanical repo state with:

```bash
bin/scenario-harness preflight <scenario> --task <task-id>
```

This updates marked preflight sections in `status.md` and `validation.md`. Re-running it is safe;
the previous marked sections are replaced.

For resume selection, list matching tasks with:

```bash
bin/scenario-harness list-tasks <scenario> --incomplete-only
```

For validation, list or run declared checks with:

```bash
bin/scenario-harness checks <scenario>
bin/scenario-harness checks <scenario> --run --task <task-id>
```

## Write Rules

- `spec.md`: write at task creation or selection; update when request scope, assumptions, repository order, or steps change.
- `status.md`: update before and after meaningful work, including resume, repo entry, repo completion, blockers, and final state.
- `validation.md`: update after checks run, are skipped, fail, or cannot run.
- `decisions.md`: update when an implementation, compatibility, migration, delivery-order, or risk judgment is made.
