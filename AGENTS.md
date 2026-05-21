# Scenario Harness Instructions

This workspace coordinates scenario-oriented delivery across multiple independent repositories.

## Agent-First Documentation

This project treats agent readability as a primary design requirement.

- Prefer explicit protocols over implied conventions.
- Read documentation in the order defined here before interpreting YAML or editing repositories.
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
2. Read `repos.yaml`.
3. Read `scenarios/<scenario>/scenario.yaml`.
4. Read `scenarios/<scenario>/README.md`.
5. Create or locate a task directory under `tasks/`.
6. Inspect git status for all affected repositories.
7. Modify repositories in scenario-defined order.
8. For each repository:
   - enter the repo path
   - read scenario-defined local instructions in the configured order
   - inspect scenario-defined key files
   - implement the repo-local change
   - run repo-local checks
   - record the result
9. Run cross-repo checks.
10. Produce a PR plan.
11. Update task status.

## Repo Entry Protocol

For each repository:

1. Resolve the repo path from `repos.yaml`.
2. Run `git status` in that repo.
3. Read each scenario-defined `repo_context.<repo>.instruction_sources` entry in order.
   - If the file exists, read it.
   - If the file does not exist, skip it and record the skip.
4. If no scenario-specific instruction source exists, inspect common project files:
   - `README.md`
   - `CONTRIBUTING.md`
   - `package.json`
   - `Makefile`
   - `pyproject.toml`
   - `Cargo.toml`
   - `go.mod`
5. Inspect scenario-defined `repo_context.<repo>.key_files`.
6. Implement the repo-local change.
7. Run repo-defined checks.
8. Record check output summary in `tasks/<task>/validation.md`.
9. Do not commit unless the user or scenario explicitly requests commits.

## YAML Semantics

Path resolution:

- Absolute paths are used as-is.
- Relative paths are resolved relative to the scenario harness root.
- Paths containing shell-style variables are invalid.

`repos.yaml`:

- `repos.<repo-key>.path` is the local filesystem path for the repository.
- `repos.<repo-key>.role` describes the repository responsibility in cross-repo delivery. It does not override scenario order.
- `repos.<repo-key>.description` is one-sentence context for agents and humans.
- `repos.<repo-key>.checks` are commands to run after repo-local changes unless the task says otherwise.
- `default_branch` and `branch_prefix` are optional and used for branch and PR planning.

`scenarios/<scenario>/scenario.yaml`:

- `description` is a one-sentence scenario summary.
- `repos` lists repository keys involved in the scenario. Each key must exist in `repos.yaml`.
- `order` is authoritative for execution sequence and must use keys from `repos`.
- `repo_context.<repo-key>.instruction_sources` are read in order after entering that repo.
- `repo_context.<repo-key>.key_files` lists scenario-relevant files or directories to inspect first.
- `integration_checks` are commands for cross-repo validation after repo-local work.

## Delivery Defaults

- Start in conservative mode: modify code and run checks, but do not commit automatically.
- Use one branch per repository when branch preparation is requested.
- Branch names should match across repositories where practical, for example `scenario/<task-id>`.
- If unrelated local changes exist, do not overwrite them. Record the state and ask for direction only if they block the task.
