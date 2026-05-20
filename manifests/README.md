# Manifest Semantics

This document defines how agents must interpret files in `manifests/`.

Read this file before reading `repos.yaml` or `scenarios.yaml`.

## Files

- `repos.yaml` describes physical repositories and repo-local execution contracts.
- `scenarios.yaml` maps scenario names to affected repositories, execution order, and cross-repo checks.

## Variables

Agents must resolve paths using these variables:

| Variable | Meaning |
| --- | --- |
| `$HARNESS_ROOT` | Absolute path of this scenario harness directory. |
| `$WORKSPACE_ROOT` | Optional shared parent directory for business repositories. Defined by `harness.workspace_root`. |
| `$HOST_REPO_ROOT` | Absolute path of the host repository. Valid only when `harness.placement` is `hosted`. |

Path resolution rules:

1. Absolute paths are used as-is.
2. Paths beginning with `$HARNESS_ROOT` are resolved relative to the harness root.
3. Paths beginning with `$WORKSPACE_ROOT` require `harness.workspace_root`.
4. Paths beginning with `$HOST_REPO_ROOT` require `harness.placement: hosted`.
5. Plain relative paths are resolved relative to `$HARNESS_ROOT`, but production manifests should prefer explicit variables.

If a path cannot be resolved, record the failure in the active task status and do not edit that repository.

## `repos.yaml`

### `harness`

Required fields:

| Field | Meaning |
| --- | --- |
| `placement` | Either `standalone` or `hosted`. Controls path resolution and ownership assumptions. |
| `root` | Harness root. Usually `$HARNESS_ROOT`. |

Optional fields:

| Field | Meaning |
| --- | --- |
| `workspace_root` | Shared workspace root used by `$WORKSPACE_ROOT`. |
| `host_repo` | Repository key for the host repo. Required when `placement` is `hosted`. |

`standalone` means this harness is separate from all business repositories.

`hosted` means this harness lives inside a business repository. Hosted mode does not allow host repo rules to be applied to downstream repositories. Each repo still requires its own repo-entry protocol.

### `repos.<repo-key>`

Required fields:

| Field | Meaning |
| --- | --- |
| `path` | Local filesystem path for the repository. |
| `role` | Repository responsibility in cross-repo delivery. Informational unless a scenario uses it explicitly. |
| `description` | One-sentence context for agents and humans. |
| `instruction_sources` | Ordered list of repo-local instruction files to read after entering the repo. |
| `checks` | Commands to run after repo-local changes unless the task says otherwise. |

Optional fields:

| Field | Meaning |
| --- | --- |
| `default_branch` | Base branch used for branch and PR planning. |
| `branch_prefix` | Prefix used when preparing scenario branches. |
| `key_files` | Scenario-relevant files or directories to inspect first. |

Rules:

- `instruction_sources` are read in order.
- Missing instruction files are skipped and recorded in task status; they are not automatically fatal.
- If none of the configured instruction files exist, inspect common files such as `README.md`, `CONTRIBUTING.md`, `package.json`, `Makefile`, `pyproject.toml`, `Cargo.toml`, or `go.mod`.
- `checks` run after changes by default. Baseline checks before changes are optional and should be requested by the user or scenario.
- Check failures block clean delivery unless they are documented with cause, impact, and next steps.
- `role` explains intent but does not override `scenarios.<name>.order`.

## `scenarios.yaml`

Each scenario key must correspond to a document in `scenarios/<scenario-key>.md`.

Required fields:

| Field | Meaning |
| --- | --- |
| `description` | One-sentence scenario summary. |
| `repos` | Repository keys involved in the scenario. Must exist in `repos.yaml`. |
| `order` | Repository keys in the required execution order. Must be drawn from `repos`. |

Optional fields:

| Field | Meaning |
| --- | --- |
| `integration_checks` | Commands for cross-repo validation after repo-local work. |
| `requires_pr_order` | Whether PR order and dependencies must be recorded. |

Rules:

- `order` is authoritative for execution sequence.
- A repo listed in `repos` but omitted from `order` is in scope but has no required edit order. Inspect it only if the scenario or task requires it.
- A repo listed in `order` but missing from `repos` is a configuration error.
- A repo referenced by a scenario but missing from `repos.yaml` is a configuration error.
- `integration_checks` run after all repo-local checks unless the scenario document says otherwise.
- Failed integration checks must be recorded in `tasks/<task>/validation.md` with next steps.

## Conflict Handling

When configuration files conflict:

1. Prefer the safer non-destructive behavior.
2. Record the conflict in the active task status.
3. Ask for direction if the conflict blocks path resolution, repo selection, execution order, or delivery.

When repo-local instructions conflict with this harness:

- Repo-local instructions control code style, tests, generated files, and local workflows inside that repo.
- Harness instructions control cross-repo order, task records, PR dependency planning, and whether the agent may edit a repo at all.
