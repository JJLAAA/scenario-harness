# Scenario Harness Instructions

This workspace coordinates scenario-oriented delivery across multiple independent repositories.

## Agent-First Documentation

This project treats agent readability as a primary design requirement.

- Prefer explicit protocols over implied conventions.
- Read documentation in the order defined here before editing repositories.
- When YAML fields are ambiguous, follow this file instead of inferring behavior from field names.
- If a required document is missing, record the missing document in the active task status before continuing.
- If configuration and prose conflict, stop and report the conflict unless the safer behavior is obvious and non-destructive.

## Core Rules

- Do not assume the current directory is a business repository.
- Business code lives in external repositories listed in `repos.yaml`.
- Treat this harness as a standalone coordination repository, not as a business repository.
- Before editing any business repository, read its repo-local instructions.
- Repo-local instructions may come from Trellis, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `README.md`, `Makefile`, package scripts, or scenario-defined files.
- Treat each repository's git state independently.
- Never mix commits across repositories.
- Never run destructive commands unless the user explicitly requested them.
- Record cross-repo progress in the active task directory under `tasks/`.

## Execution Protocol

1. Identify the scenario.
2. Read `scenarios/<scenario>/scenario.yaml`.
3. Read `scenarios/<scenario>/README.md`.
4. Run `bin/scenario-harness validate-scenario <scenario>` from the harness root.
   - If it reports errors, stop before editing business repositories.
   - Use `--json` when machine-readable output is useful.
5. Read only the `repos.yaml` entries referenced by the scenario's `repos` and `order` fields.
6. Create or locate a task directory under `tasks/`.
7. Inspect git status for all affected repositories.
8. Modify repositories in scenario-defined order.
9. For each repository:
   - enter the repo path
   - verify the current branch exactly matches the scenario-defined branch
   - read scenario-defined local instructions in the configured order
   - inspect scenario-defined key files
   - implement the repo-local change
   - run repo-local checks
   - record the result
10. Update task status.

## Agent Helper CLI

Use `bin/scenario-harness` for mechanical checks before doing manual reasoning.

- `bin/scenario-harness validate-scenario <scenario>` validates the selected scenario, `repos.yaml` references, resolved repository paths, branch gate declarations, and basic field shapes.
- `bin/scenario-harness validate-scenario <scenario> --json` emits stable JSON for agents that want to parse findings.
- `bin/scenario-harness init-task <scenario> [task-id] --request "..."` creates `spec.md`, `status.md`, `validation.md`, and `decisions.md` from the selected scenario without overwriting existing task files.

Exit codes:

- `0`: validation passed.
- `2`: scenario or repository configuration is invalid.
- `64`: command usage or runtime prerequisites are invalid.

The helper CLI never edits business repositories.

## Repo Entry Protocol

For each repository:

1. Resolve the repo path from `repos.yaml`.
2. Run `git status` in that repo.
3. Check the current branch against `repo_context.<repo>.branch`.
   - The branch check is an exact string match.
   - If the current branch does not match, stop before reading further repo-local context or editing files.
   - Record the expected branch, actual branch, and blocked repo in `tasks/<task>/status.md` when a task directory exists.
   - Report the mismatch to the user and wait for direction.
   - Do not automatically checkout, create, or rename branches unless the user explicitly requests it.
4. Read each scenario-defined `repo_context.<repo>.instruction_sources` entry in order.
   - If the file exists, read it.
   - If the file does not exist, skip it and record the skip.
5. If no scenario-specific instruction source exists, inspect common project files:
   - `README.md`
   - `CONTRIBUTING.md`
   - `package.json`
   - `Makefile`
   - `pyproject.toml`
   - `Cargo.toml`
   - `go.mod`
6. Inspect scenario-defined `repo_context.<repo>.key_files`.
7. Implement the repo-local change.
8. Run repo-defined checks.
9. Record check output summary in `tasks/<task>/validation.md`.
10. Do not commit unless the user or scenario explicitly requests commits.

## Task Directory Protocol

The active task directory is the recovery point for a scenario run.

1. If the user provides a task directory, use it.
2. If the user asks to continue, resume, or finish existing work without naming a task directory, inspect `tasks/` for the matching scenario and choose the most recent task directory whose `status.md` is not complete.
3. If exactly one plausible task directory exists for the scenario, use it.
4. If multiple plausible task directories exist and the user did not identify one, ask which task to continue before editing repositories.
5. If no plausible task directory exists, create a new one under `tasks/` using `YYYY-MM-DD-<scenario>` or `YYYY-MM-DD-<scenario>-<short-topic>` when the task needs distinction.

When creating a new task directory:

- Prefer `bin/scenario-harness init-task <scenario> [task-id] --request "..."`.
- If the helper cannot be used, copy the files from `templates/` into the task directory with these names:
  - `spec.md` to `spec.md`
  - `task-status.md` to `status.md`
  - `decisions.md` to `decisions.md`
  - `validation-report.md` to `validation.md`
- Fill `spec.md` with the scenario, user request, scope, non-goals, assumptions, repository order, and execution steps.
- Fill `status.md` with the task id, scenario, initial repo states, skipped instruction files, and current step.
- Adjust `spec.md` and `validation.md` to match the scenario's actual repository keys and order.

When resuming an existing task directory, read these files before editing repositories:

1. `spec.md`
2. `status.md`
3. `decisions.md`
4. `validation.md`

Use those files to determine completed work, current blockers, checked repo states, validation already run, and the next repository in scenario order. Update `status.md` before and after meaningful work, and update `spec.md`, `validation.md`, and `decisions.md` as facts change.

## Task File Write Rules

Write task files at the time their information becomes true. Do not wait until the end of the scenario to reconstruct progress from memory.

- `spec.md` is written when the task directory is created or selected. It records the scenario, user request, scope, non-goals, assumptions, repository order, and execution steps. Update it when the user changes the request, a scope assumption becomes false, or steps are completed, skipped, blocked, added, or reordered.
- `status.md` is the live task state. Update it before and after meaningful work, including task creation, task resume, repo entry, repo completion, blockers, skipped instruction files, and the final task state.
- `validation.md` is written after checks are run, skipped, or fail to run. Record the repo, command, result, important output summary, known failures, and residual risk.
- `decisions.md` is written when the agent makes or discovers a judgment that affects implementation, compatibility, migration, delivery order, or risk. Record why the decision was made, not just what changed.

Do not duplicate routine progress in `decisions.md`; put progress in `status.md`. Do not put check output in `status.md`; summarize checks in `validation.md`. Do not treat `spec.md` as a scratchpad for transient notes after execution starts.

## YAML Semantics

Path resolution:

- Absolute paths are used as-is.
- Relative paths are resolved relative to the scenario harness root.
- Paths containing shell-style variables are invalid.

`repos.yaml`:

- `repos.yaml` is a repository registry, not an execution plan.
- Agents must not treat every repository listed in `repos.yaml` as affected by a scenario.
- A scenario selects repositories through `scenarios/<scenario>/scenario.yaml`; use `repos.yaml` only to look up metadata for those selected repository keys.
- `repos.<repo-key>.path` is the local filesystem path for the repository.
- `repos.<repo-key>.role` describes the repository responsibility in cross-repo delivery. It does not override scenario order.
- `repos.<repo-key>.description` is one-sentence context for agents and humans.
- `repos.<repo-key>.checks` are commands to run after repo-local changes unless the task says otherwise.
- `default_branch` and `branch_prefix` are optional and used for branch planning.

`scenarios/<scenario>/scenario.yaml`:

- `scenario.yaml` is the authoritative execution configuration for the scenario.
- `description` is a one-sentence scenario summary.
- `repos` lists repository keys involved in the scenario. Each key must exist in `repos.yaml`.
- `order` is authoritative for execution sequence and must use keys from `repos`.
- `repo_context.<repo-key>.branch` is the exact branch name the agent must find after entering that repository.
- Every repo listed in `repos` and `order` must have a `repo_context.<repo-key>.branch` value before business repository edits begin.
- `repo_context.<repo-key>.instruction_sources` are read in order after entering that repo.
- `repo_context.<repo-key>.key_files` lists scenario-relevant files or directories to inspect first.

`scenarios/<scenario>/README.md`:

- The scenario README is the human-readable SOP, rationale, invariants, compatibility guidance, and completion criteria for the scenario.
- It should explain why the repositories are coordinated, what cross-repo behavior must remain true, and how to make judgment calls that do not fit cleanly in YAML.
- It should not duplicate or override structural execution fields from `scenario.yaml`, such as `repos`, `order`, or `repo_context`.
- If `scenario.yaml` and the scenario README conflict on structural execution, follow `scenario.yaml` unless doing so would be destructive or unsafe.
- If they conflict on business intent, compatibility requirements, or completion criteria, stop and report the conflict before editing repositories.

## Delivery Defaults

- Start in conservative mode: modify code and run checks, but do not commit automatically.
- Use one branch per repository when branch preparation is requested.
- Branch names should match across repositories where practical, for example `scenario/<task-id>`.
- If unrelated local changes exist, do not overwrite them. Record the state and ask for direction only if they block the task.
