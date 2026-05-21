# Scenario Harness

Scenario Harness is a lightweight control layer for delivering business scenarios that span multiple independent repositories.

More precisely, it is an agent-first memory and execution protocol for recurring cross-repo development scenarios outside monorepos. Its niche is not generic multi-repo management. It is for preserving the development knowledge behind a specific repeated scenario: which repositories participate, how they depend on each other, what order changes should follow, what local instructions must be read, and how completion is validated.

It does not replace Git, CI, PR review, or repo-local instructions. Its job is to make cross-repo delivery explicit and repeatable:

- which scenario is being executed
- which repositories are affected
- what role each repository plays
- what order the repositories should be changed in
- which repo-local instructions must be read
- which checks prove the work is complete
- where task progress, validation, decisions, and PR ordering are recorded

## When To Use This

Use this harness when a specific class of task repeatedly crosses repository boundaries, for example:

- a contract or schema repo must be changed before downstream consumers
- an API change must update backend, frontend, SDK, fixtures, and workers
- a product flow change spans web, mobile, backend, and infra repos
- multiple repositories do not share a monorepo or meta repo

This harness is primarily for non-monorepo environments. If the affected projects can naturally live in one monorepo or workspace with shared tooling, unified local instructions, and a single review/build context, prefer that structure. In a monorepo, cross-package development is usually much closer to single-repo development than to independent cross-repo delivery.

The strongest fit is when the repositories belong to different business domains and should remain independently owned, versioned, and reviewed, but a specific recurring scenario still requires coordinated development across them. In that case, the scenario deserves shared context without forcing the repositories into the same monorepo.

Do not use this harness to replace a repository's own workflow. Each business repo still owns its code style, tests, generated files, commits, PRs, and CI.

## Agent-First Docs

This project treats agent readability as a primary design requirement. Agents should follow documented semantics instead of inferring behavior from YAML field names.

Required reading order:

1. `AGENTS.md`
2. `repos.yaml`
3. `scenarios/<scenario>/scenario.yaml`
4. `scenarios/<scenario>/README.md`

`AGENTS.md` defines the execution protocol and YAML semantics. `repos.yaml` defines stable repository metadata. Each scenario directory contains its own machine-readable execution config and human-readable SOP.

## Repository Structure

```text
scenario-harness/
  AGENTS.md
  README.md
  repos.yaml
  scenarios/
    example-contract-change/
      scenario.yaml
      README.md
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

### 1. Place The Harness

Keep this harness separate from all business repos:

```text
~/work/
  scenario-harness/
  api/
  web/
  worker/
```

The harness is assumed to be standalone; no placement field is required.

### 2. Configure Repositories

Edit `repos.yaml` and replace the placeholder repos with real repositories.

Example configuration:

```yaml
repos:
  api:
    path: ../api
    role: contract-source
    description: Owns API schema and domain contracts.
    default_branch: main
    branch_prefix: scenario
    checks:
      - npm run lint
      - npm test

  web:
    path: ../web
    role: downstream-consumer
    description: Consumes API contracts from api.
    default_branch: main
    branch_prefix: scenario
    checks:
      - pnpm typecheck
      - pnpm test
```

Read `AGENTS.md` for the complete field semantics.

### 3. Define Scenarios

Create a scenario directory with `scenario.yaml` and `README.md`.

```yaml
description: Update billing API contract and downstream consumers.

repos:
  - api
  - web
  - worker

order:
  - api
  - web
  - worker

repo_context:
  api:
    instruction_sources:
      - AGENTS.md
      - CONTRIBUTING.md
      - README.md
    key_files:
      - openapi.yaml
      - src/contracts/
  web:
    instruction_sources:
      - AGENTS.md
      - README.md
    key_files:
      - src/api/

integration_checks:
  - scripts/run-integration-checks billing-contract-change
```

Place it at:

```text
scenarios/billing-contract-change/scenario.yaml
```

Then create `scenarios/billing-contract-change/README.md` for the scenario purpose, repository roles, invariants, and completion criteria. Start by copying `scenarios/example-contract-change/`.

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

Read AGENTS.md, repos.yaml, scenarios/billing-contract-change/scenario.yaml,
and scenarios/billing-contract-change/README.md first.

Then resolve repo paths, inspect git status for affected repos, enter repos in scenario order,
read scenario-defined repo-local instruction sources, inspect key files, implement the requested change, run checks, and update
the task status, validation report, decisions, and PR plan.
Do not commit unless I explicitly ask.
```

### 3. Execution Model

The default execution model is a single agent running the scenario serially. Do not introduce multi-agent scheduling in the MVP workflow.

The scenario should be narrow enough that the agent can follow configured repos, `repo_context`, checks, and scenario invariants without broad discovery across every repository. Put the required knowledge in `repos.yaml`, scenario directories, and task files instead of relying on the agent to infer cross-repo behavior.

To control context pressure, the agent should summarize after each repository:

- files changed
- contract, API, event, or generated artifact implications
- checks run and results
- blockers, assumptions, or downstream notes

That summary becomes the required context for the next repository unless debugging requires returning to an earlier repo.

### 4. Expected Agent Behavior

The agent should:

1. Read the required harness docs in order.
2. Resolve affected repo paths from `repos.yaml`.
3. Read `scenarios/<scenario>/scenario.yaml`.
4. Read `scenarios/<scenario>/README.md`.
5. Inspect `git status` in each affected repo.
6. Follow `scenarios.<name>.order`.
7. For each repo, read scenario-defined `repo_context.<repo>.instruction_sources`.
8. Inspect scenario-defined `repo_context.<repo>.key_files`.
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
- guess YAML semantics when `AGENTS.md` defines them

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

1. Replace placeholder repos in `repos.yaml`.
2. Replace `example-contract-change` with one real scenario.
3. Create a task directory from templates.
4. Ask the agent to run the scenario without committing.
5. Check whether the YAML fields were enough for path resolution, repo entry, checks, and task records.
6. Add only the missing fields or scripts that the dry run proves are necessary.

## Scripts

The MVP intentionally starts with documents before scripts.

Add scripts only for repeated mechanical operations, such as:

- reporting repo status
- preparing branches
- running YAML-defined checks
- running integration smoke tests
- collecting diff summaries
- creating PR plans

Keep business judgment in scenario documents and task records.

## Practice Roadmap

Implement the remaining ideas in this order, after the first real scenario dry run:

1. Strengthen quality gates in task templates.
   - Add repo-local, cross-repo, and delivery gate sections to `templates/validation-report.md` or `templates/task-status.md`.
   - Keep the gates checklist-oriented so agents can update them during execution.

2. Add a read-only `scripts/repo-status`.
   - Report branch, dirty state, untracked files, and recent commits for each affected repo.
   - Keep it non-destructive and useful before any branch or code changes.

3. Add YAML validation after the configuration shape stabilizes.
   - Check required fields, unresolved paths, missing scenario documents, and scenario repos that are not declared in `repos.yaml`.
   - Prefer validation reports over automatic fixes.

4. Add task template generation only if task creation becomes frequent.
   - Generate `brief.md`, `plan.md`, `status.md`, `decisions.md`, `validation.md`, and `prs.md` from the existing templates.
   - Do not hide the task files; they remain the recovery point for interrupted sessions.

## Future Design

These ideas are intentionally deferred until several manual runs prove they are needed:

- Keep the harness as a standalone coordination repository.
- Keep the Trellis and meta-repo rationale as design guidance: this harness should stay independent of any single repo-local workflow system and should encode delivery semantics directly.
- Treat CLI support as a helper for mechanical, low-risk steps, not as the core execution model. Good candidates are YAML validation, repo status reports, task skeleton generation, and task summaries.
- Do not build a full CLI orchestrator until the manual workflow has repeated enough to prove the command boundaries are stable. Candidate helper commands include `scenario prepare`, `scenario status`, `scenario check`, and `scenario summary`.
- Do not treat multi-agent orchestration as a goal. Re-evaluate it only if real scenarios show that single-agent serial execution cannot manage context, repo count, or verification complexity.
- Avoid automatic commits and PR creation by default. If added later, they should be explicit delivery modes and should still record one commit or PR plan per repository.
- Avoid complex branch management until repeated tasks prove it saves time. Branch preparation should always inspect dirty state and unrelated local changes first.

## Current State

This is an MVP skeleton. It is ready for a manual dry run against real repositories. The next maturity step is to use it on one real cross-repo scenario, then add scripts for the steps that repeat without requiring judgment.
