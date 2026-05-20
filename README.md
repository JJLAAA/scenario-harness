# Scenario Harness

Scenario Harness is a lightweight control layer for delivering business scenarios that span multiple independent repositories.

It does not replace Git, CI, PR review, or repo-local instructions. Its job is to make cross-repo delivery explicit and repeatable:

- which scenario is being executed
- which repositories are affected
- what role each repository plays
- what order the repositories should be changed in
- which repo-local instructions must be read
- which checks prove the work is complete
- where task progress, validation, decisions, and PR ordering are recorded

## When To Use This

Use this harness when a task repeatedly crosses repository boundaries, for example:

- a contract or schema repo must be changed before downstream consumers
- an API change must update backend, frontend, SDK, fixtures, and workers
- a product flow change spans web, mobile, backend, and infra repos
- multiple repositories do not share a monorepo or meta repo

Do not use this harness to replace a repository's own workflow. Each business repo still owns its code style, tests, generated files, commits, PRs, and CI.

## Agent-First Docs

This project treats agent readability as a primary design requirement. Agents should follow documented semantics instead of inferring behavior from YAML field names.

Required reading order:

1. `AGENTS.md`
2. `manifests/README.md`
3. `manifests/repos.yaml`
4. `manifests/scenarios.yaml`
5. `scenarios/<scenario>.md`

`AGENTS.md` defines the execution protocol. `manifests/README.md` defines how to interpret YAML fields, path variables, placement modes, execution order, and conflict handling.

## Repository Structure

```text
scenario-harness/
  AGENTS.md
  README.md
  docs/
    scenario-harness-design.md
  manifests/
    README.md
    repos.yaml
    scenarios.yaml
  scenarios/
    example-contract-change.md
  tasks/
    README.md
  templates/
    decisions.md
    pr-plan.md
    task-brief.md
    task-plan.md
    task-status.md
    validation-report.md
  scripts/
    README.md
```

## Setup

### 1. Choose Placement

Use `standalone` when this harness is separate from all business repos:

```text
~/work/
  scenario-harness/
  api/
  web/
  worker/
```

Use `hosted` when this harness lives inside a primary source-of-truth repo:

```text
api/
  scenario-harness/
  src/
web/
worker/
```

Set the placement in `manifests/repos.yaml`.

### 2. Configure Repositories

Edit `manifests/repos.yaml` and replace the placeholder repos with real repositories.

Example standalone configuration:

```yaml
harness:
  placement: standalone
  root: $HARNESS_ROOT
  workspace_root: /Users/leo/work/repos

repos:
  api:
    path: $WORKSPACE_ROOT/api
    role: contract-source
    description: Owns API schema and domain contracts.
    default_branch: main
    branch_prefix: scenario
    instruction_sources:
      - AGENTS.md
      - CONTRIBUTING.md
      - README.md
    checks:
      - npm run lint
      - npm test
    key_files:
      - openapi.yaml
      - src/contracts/

  web:
    path: $WORKSPACE_ROOT/web
    role: downstream-consumer
    description: Consumes API contracts from api.
    default_branch: main
    branch_prefix: scenario
    instruction_sources:
      - AGENTS.md
      - README.md
    checks:
      - pnpm typecheck
      - pnpm test
    key_files:
      - src/api/
```

Read `manifests/README.md` for the complete field semantics.

### 3. Define Scenarios

Edit `manifests/scenarios.yaml` to map scenario names to affected repos and execution order.

```yaml
scenarios:
  billing-contract-change:
    description: Update billing API contract and downstream consumers.
    repos:
      - api
      - web
      - worker
    order:
      - api
      - web
      - worker
    integration_checks:
      - scripts/run-integration-checks billing-contract-change
    requires_pr_order: true
```

Then create a matching scenario document:

```text
scenarios/billing-contract-change.md
```

Start by copying `scenarios/example-contract-change.md`, then replace the repo names, required order, invariants, and completion criteria with the real workflow.

## Running A Task

### 1. Create A Task Directory

Use a stable task id. Date plus scenario name works well:

```bash
mkdir -p tasks/2026-05-20-billing-contract-change
cp templates/task-brief.md tasks/2026-05-20-billing-contract-change/brief.md
cp templates/task-plan.md tasks/2026-05-20-billing-contract-change/plan.md
cp templates/task-status.md tasks/2026-05-20-billing-contract-change/status.md
cp templates/decisions.md tasks/2026-05-20-billing-contract-change/decisions.md
cp templates/validation-report.md tasks/2026-05-20-billing-contract-change/validation.md
cp templates/pr-plan.md tasks/2026-05-20-billing-contract-change/prs.md
```

Fill in `brief.md` with the user's request, scope, non-goals, and assumptions.

### 2. Ask An Agent To Execute The Scenario

Start the agent in this harness directory and give it the scenario plus task directory.

Example prompt:

```text
Execute scenario billing-contract-change.
Task directory: tasks/2026-05-20-billing-contract-change.

Read AGENTS.md, manifests/README.md, manifests/repos.yaml, manifests/scenarios.yaml,
and scenarios/billing-contract-change.md first.

Then resolve repo paths, inspect git status for affected repos, enter repos in scenario order,
read repo-local instruction sources, implement the requested change, run checks, and update
the task status, validation report, decisions, and PR plan.
Do not commit unless I explicitly ask.
```

### 3. Expected Agent Behavior

The agent should:

1. Read the required harness docs in order.
2. Resolve affected repo paths from `manifests/repos.yaml`.
3. Validate that the scenario exists in `manifests/scenarios.yaml`.
4. Read `scenarios/<scenario>.md`.
5. Inspect `git status` in each affected repo.
6. Follow `scenarios.<name>.order`.
7. For each repo, read configured `instruction_sources`.
8. Inspect relevant `key_files`.
9. Implement repo-local changes.
10. Run repo-local `checks`.
11. Run `integration_checks`.
12. Update task files under `tasks/<task-id>/`.
13. Report diff scope, validation results, risks, and PR order.

The agent should not:

- assume this harness is a business repo
- apply one repo's instructions to another repo
- overwrite unrelated local changes
- mix commits across repos
- commit or create PRs unless explicitly requested
- guess YAML semantics when `manifests/README.md` defines them

## Task Files

Each task directory should contain:

| File | Purpose |
| --- | --- |
| `brief.md` | User request, scope, non-goals, assumptions. |
| `plan.md` | Repo order and step-by-step execution plan. |
| `status.md` | Current progress, branches, blockers, skipped files. |
| `decisions.md` | Compatibility choices, migration decisions, rejected options. |
| `validation.md` | Repo-local checks and cross-repo validation results. |
| `prs.md` | PR order, dependencies, suggested commit messages, migration notes. |

These files are the recovery point if the session is interrupted.

## Delivery Checklist

Before considering a task complete, verify:

- every affected repo's git status was inspected
- repo-local instructions were read or missing files were recorded
- source-of-truth repos were changed before downstream repos
- generated artifacts were updated according to repo-local rules
- repo-local checks passed or failures were documented
- integration checks passed or failures were documented
- task status and validation files are current
- PR order and dependencies are clear
- remaining risk is documented

## Dry Run Checklist

For the first real use, run a small task manually before adding automation:

1. Replace placeholder repos in `manifests/repos.yaml`.
2. Replace `example-contract-change` with one real scenario.
3. Create a task directory from templates.
4. Ask the agent to run the scenario without committing.
5. Check whether the manifest fields were enough for path resolution, repo entry, checks, and task records.
6. Add only the missing fields or scripts that the dry run proves are necessary.

## Scripts

The MVP intentionally starts with documents before scripts.

Add scripts only for repeated mechanical operations, such as:

- reporting repo status
- preparing branches
- running manifest-defined checks
- running integration smoke tests
- collecting diff summaries
- creating PR plans

Keep business judgment in scenario documents and task records.

## Current State

This is an MVP skeleton. It is ready for a manual dry run against real repositories. The next maturity step is to use it on one real cross-repo scenario, then add scripts for the steps that repeat without requiring judgment.
