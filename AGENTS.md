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
- Business code lives in external repositories declared by the active scenario.
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
5. Create or locate a task directory under `tasks/`.
6. Inspect git status for all affected repositories. Prefer `bin/scenario-harness preflight <scenario> --task <task-id>`.
7. Modify repositories in scenario-defined order.
8. For each repository:
   - enter the repo path
   - verify the current branch exactly matches the task-defined branch
   - read scenario-defined local instructions in the configured order
   - inspect scenario-defined key files
   - implement the repo-local change
   - run repo-local checks
   - record the result
9. Update task status.

## Agent Helper CLI

Use `bin/scenario-harness` for mechanical checks before doing manual reasoning.

- `bin/scenario-harness validate-scenario <scenario>` validates the selected scenario, resolved repository paths, checks, and basic field shapes.
- `bin/scenario-harness validate-scenario <scenario> --json` emits stable JSON for agents that want to parse findings.
- `bin/scenario-harness init-task <scenario> [task-id] --request "..."` creates `spec.md`, `status.md`, `validation.md`, and `decisions.md` from the selected scenario without overwriting existing task files.
- `bin/scenario-harness preflight <scenario> --task <task-id>` inspects affected repository git status, task branch gates, missing instruction sources, and missing key files, then updates `status.md` and `validation.md`.
- `bin/scenario-harness plan-scenario <scenario>` prints the compact execution plan: repo order, paths, instruction sources, key files, and checks.
- `bin/scenario-harness list-tasks <scenario>` lists matching task directories newest first for resume decisions.
- `bin/scenario-harness checks <scenario>` lists repo-local checks; add `--run --task <task-id>` to execute checks and update `validation.md`.

Exit codes:

- `0`: validation passed.
- `2`: scenario or repository configuration is invalid.
- `64`: command usage or runtime prerequisites are invalid.

The helper CLI never edits business repositories.

## Repo Entry Protocol

For each repository:

1. Resolve the repo path from `scenarios/<scenario>/scenario.yaml`.
2. Run `git status` in that repo.
3. Check the current branch against the expected branch recorded in `tasks/<task>/status.md`.
   - The branch check is an exact string match.
   - If the current branch does not match, stop before reading further repo-local context or editing files.
   - Record the expected branch, actual branch, and blocked repo in `tasks/<task>/status.md` when a task directory exists.
   - Report the mismatch to the user and wait for direction.
   - Do not automatically checkout, create, or rename branches unless the user explicitly requests it.
4. Read each scenario-defined `repos.<repo>.instruction_sources` entry in order.
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
6. Inspect scenario-defined `repos.<repo>.key_files`.
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
- Record the expected branch for each affected repository in `status.md`.
- Scenarios do not define working branches; tasks define them.
- If the user request or selected task files do not specify the expected branch for every affected repository, ask the user to clarify before entering or editing any business repository.
- Do not infer expected branches from the repository's current branch, default branch, scenario name, or task id.
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

`scenarios/<scenario>/scenario.yaml`:

- `scenario.yaml` is the authoritative execution template for the scenario.
- `description` is a one-sentence scenario summary.
- `repos` is a mapping of every repository involved in the scenario.
- `order` is authoritative for execution sequence and must use keys from `repos`.
- Repo keys are stable scenario-local identifiers. Use them for task tables, status records, validation records, and cross-repo references; do not replace them with directory names unless they are identical.
- `repos.<repo-key>.path` is the local filesystem path for the repository.
- `repos.<repo-key>.role` is a short machine-readable responsibility label for the repository in this scenario. It helps agents summarize context; it does not override scenario order or dependency declarations.
- `repos.<repo-key>.description` is one-sentence context for agents and humans.
- `repos.<repo-key>.outputs` lists stable artifacts, APIs, packages, schemas, or other cross-repo deliverables produced by the repository.
- `repos.<repo-key>.outputs[].id` is the scenario-local output identifier used by `depends_on`.
- `repos.<repo-key>.outputs[].type` classifies the output, such as package, schema, API, event, or generated artifact. It is descriptive metadata, not a release instruction.
- `repos.<repo-key>.outputs[].name` is the human-facing artifact name, package name, API name, or schema name.
- `repos.<repo-key>.outputs[].description` explains the output when the name is not enough.
- `repos.<repo-key>.depends_on` lists cross-repo dependencies that matter for this scenario.
- `repos.<repo-key>.depends_on[].repo` references the upstream repo key.
- `repos.<repo-key>.depends_on[].output` references an `outputs[].id` declared by the upstream repo.
- `repos.<repo-key>.depends_on[].reason` explains why the dependency matters for agent planning and validation.
- `repos.<repo-key>.instruction_sources` are read in order after entering that repo.
- `repos.<repo-key>.key_files` lists scenario-relevant files or directories to inspect first.
- `repos.<repo-key>.checks` are commands to run after repo-local changes unless the task says otherwise.
- `scenario.yaml` must not define working branches; expected branches are task-specific and recorded in `tasks/<task>/status.md`.
- `scenario.yaml` must not define task-specific dependency values such as branch, commit, ref, sha, tag, version, dist-tag, tarball, file, link, or workspace. Ask a human to confirm those values for the active task, then record them in task files.
- Fields not defined in this section are extension metadata. Agents may preserve and report them, but must not treat them as instructions to edit code, switch branches, publish releases, or change execution order unless `AGENTS.md`, the scenario README, or the helper CLI explicitly defines that behavior.

`scenarios/<scenario>/README.md`:

- The scenario README is the human-readable SOP, rationale, invariants, compatibility guidance, and completion criteria for the scenario.
- It should explain why the repositories are coordinated, what cross-repo behavior must remain true, and how to make judgment calls that do not fit cleanly in YAML.
- It should not duplicate or override structural execution fields from `scenario.yaml`, such as `repos` or `order`.
- If `scenario.yaml` and the scenario README conflict on structural execution, follow `scenario.yaml` unless doing so would be destructive or unsafe.
- If they conflict on business intent, compatibility requirements, or completion criteria, stop and report the conflict before editing repositories.

## Delivery Defaults

- Start in conservative mode: modify code and run checks, but do not commit automatically.
- Use one branch per repository when branch preparation is requested.
- Branch names should match across repositories where practical, for example `scenario/<task-id>`.
- If unrelated local changes exist, do not overwrite them. Record the state and ask for direction only if they block the task.
