# Scenario Harness Instructions

This workspace coordinates scenario-oriented delivery across multiple independent repositories.

## Agent-First Documentation

This project treats agent readability as a primary design requirement.

- Prefer explicit protocols over implied conventions.
- Read documentation in the order defined here before interpreting YAML or editing repositories.
- When YAML fields are ambiguous, follow `manifests/README.md` instead of inferring behavior from field names.
- If a required document is missing, record the missing document in the active task status before continuing.
- If configuration and prose conflict, stop and report the conflict unless the safer behavior is obvious and non-destructive.

## Core Rules

- Do not assume the current directory is a business repository.
- Business code lives in external repositories listed in `manifests/repos.yaml`.
- Respect the manifest semantics defined in `manifests/README.md`.
- Respect the placement model declared in `manifests/repos.yaml`.
- If this is a hosted harness, do not apply host repository rules to downstream repositories.
- Before editing any business repository, read its repo-local instructions.
- Repo-local instructions may come from Trellis, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `README.md`, `Makefile`, package scripts, or manifest-defined files.
- Treat each repository's git state independently.
- Never mix commits across repositories.
- Never run destructive commands unless the user explicitly requested them.
- Record cross-repo progress in the active task directory under `tasks/`.

## Execution Protocol

1. Identify the scenario.
2. Read `manifests/README.md`.
3. Read `manifests/repos.yaml` and `manifests/scenarios.yaml`.
4. Read the scenario document from `scenarios/`.
5. Create or locate a task directory under `tasks/`.
6. Inspect git status for all affected repositories.
7. Modify repositories in scenario-defined order.
8. For each repository:
   - enter the repo path
   - read local instructions in the configured order
   - inspect affected files
   - implement the repo-local change
   - run repo-local checks
   - record the result
9. Run cross-repo checks.
10. Produce a PR plan.
11. Update task status.

## Repo Entry Protocol

For each repository:

1. Resolve the repo path from `manifests/repos.yaml` using `manifests/README.md`.
2. Run `git status` in that repo.
3. Read each configured `instruction_sources` entry in order.
   - If the file exists, read it.
   - If the file does not exist, skip it and record the skip.
4. If no instruction source exists, inspect common project files:
   - `README.md`
   - `CONTRIBUTING.md`
   - `package.json`
   - `Makefile`
   - `pyproject.toml`
   - `Cargo.toml`
   - `go.mod`
5. Inspect scenario-defined `key_files`.
6. Implement the repo-local change.
7. Run manifest-defined checks.
8. Record check output summary in `tasks/<task>/validation.md`.
9. Do not commit unless the user or scenario explicitly requests commits.

## Delivery Defaults

- Start in conservative mode: modify code and run checks, but do not commit automatically.
- Use one branch per repository when branch preparation is requested.
- Branch names should match across repositories where practical, for example `scenario/<task-id>`.
- If unrelated local changes exist, do not overwrite them. Record the state and ask for direction only if they block the task.
