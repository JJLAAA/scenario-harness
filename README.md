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
- where task progress, validation, decisions, and delivery ordering are recorded

## Why This Exists

Coding agents increasingly need specs, instructions, and execution protocols to make code changes reliably. For a single repository, or a monorepo with shared tooling and unified review context, there are already many ways to give an agent that guidance: repo-local instructions, task specs, package scripts, tests, and project documentation.

Many enterprise systems do not fit that shape. A real delivery scenario may span several independently owned repositories: an API service, a frontend, an SDK, a worker, infrastructure code, fixtures, or documentation. Those repositories may need to stay separate because of team ownership, access control, release cadence, compliance boundaries, or existing operational practice.

The business change still has one logical shape even when the code lives in separate repos. The agent needs to know which repositories participate, which one must change first, which local instructions apply inside each repo, what checks to run, what decisions were made, and how to record progress across the whole scenario.

Scenario Harness provides that missing scenario layer. It keeps the repositories independent while giving coding agents a minimal, explicit protocol for coordinated cross-repo development.

## Relationship To Repo-Local Spec Frameworks

Scenario Harness deliberately does not compete with single-repo or monorepo spec frameworks such as Spec Kit, OpenSpec, Trellis, or repo-specific agent workflows. It operates above them.

Its current guarantee is explicit discovery and delegation: for each repository, a scenario can declare which repo-local instruction sources, spec directories, and key files an agent must read before making changes.

It does not guarantee that framework-specific runtime mechanisms, such as hooks, slash commands, MCP servers, or injected context, will automatically activate after the agent enters a repository. Whether those mechanisms work depends on the agent runtime and framework implementation, and should be validated in practice for each framework.

For hook-based frameworks, repositories should expose a static fallback entrypoint through `AGENTS.md`, `CLAUDE.md`, `README.md`, or scenario-defined `instruction_sources`, so the agent can still follow repo-local spec rules when runtime injection is unavailable.

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
2. `scenarios/<scenario>/scenario.yaml`
3. `scenarios/<scenario>/README.md`
4. `repos.yaml`, as a registry for only the repository keys selected by the scenario

`AGENTS.md` defines the execution protocol and YAML semantics. Each scenario directory contains its own machine-readable execution config and human-readable SOP. `repos.yaml` defines stable repository metadata and should be treated as a lookup table, not as the list of affected repositories for every scenario.

Within a scenario directory, the files have different jobs:

- `scenario.yaml` is the authoritative execution config: selected repos, execution order, repo-local instruction sources, and key files.
- It also declares the exact branch expected for each repo through `repo_context.<repo>.branch`; agents stop and report if a repo is on any other branch.
- `README.md` is the scenario SOP: business intent, rationale, invariants, compatibility guidance, completion criteria, risks, and judgment calls that do not fit cleanly in YAML.

The README should not duplicate or override structural fields from `scenario.yaml`. If the two conflict on execution structure, follow `scenario.yaml` unless doing so would be destructive or unsafe. If they conflict on business intent, compatibility, or completion criteria, stop and report the conflict before editing repositories.

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
    spec.md
    task-status.md
    validation-report.md
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
    branch: scenario/billing-contract-change
    instruction_sources:
      - AGENTS.md
      - CONTRIBUTING.md
      - README.md
    key_files:
      - openapi.yaml
      - src/contracts/
  web:
    branch: scenario/billing-contract-change
    instruction_sources:
      - AGENTS.md
      - README.md
    key_files:
      - src/api/
```

Place it at:

```text
scenarios/billing-contract-change/scenario.yaml
```

Then create `scenarios/billing-contract-change/README.md` for the scenario purpose, repository roles, invariants, and completion criteria. Start by copying `scenarios/example-contract-change/`.

## Running A Task

### 0. Validate The Scenario

Before creating task files or entering business repositories, run the agent helper CLI:

```bash
bin/scenario-harness validate-scenario billing-contract-change
```

Use JSON when the agent needs a structured contract:

```bash
bin/scenario-harness validate-scenario billing-contract-change --json
```

The command checks that the scenario files exist, selected repo keys are present in `repos.yaml`,
`repos` and `order` agree, branch gates are declared, and repository paths resolve. It is read-only
and exits non-zero when the scenario is not safe to execute.

### 1. Create Or Select A Task Directory

A task directory records progress and lets an agent resume safely. If you already have one, pass it to the agent. If not, create one with the helper CLI:

```bash
bin/scenario-harness init-task billing-contract-change \
  2026-05-20-billing-contract-change \
  --request "Update billing API contract and downstream consumers."
```

If the task id is omitted, the helper uses `YYYY-MM-DD-<scenario>`. It creates `spec.md`,
`status.md`, `decisions.md`, and `validation.md` from the scenario configuration and does not
overwrite existing task files. Pass `--json` for structured output.

When resuming, the agent should read the existing task files before editing repositories:

1. `spec.md`
2. `status.md`
3. `decisions.md`
4. `validation.md`

If the user asks to continue without naming a task directory, the agent should inspect `tasks/` for the matching scenario and continue the most recent incomplete task. If multiple plausible tasks exist, it should ask which one to use.

### 2. Run Preflight

Before entering repo-local instructions or editing business code, run:

```bash
bin/scenario-harness preflight billing-contract-change \
  --task 2026-05-20-billing-contract-change
```

Preflight checks each affected repository's current branch, dirty state, missing instruction sources,
and missing key files. It updates marked sections in `status.md` and `validation.md`, so repeated
runs replace the previous preflight block instead of duplicating notes. Use `--no-write --json`
when the agent needs a read-only structured preview.

### 3. Ask An Agent To Execute The Scenario

Start the agent in this harness directory and give it the scenario plus task directory when available.

Example prompt:

```text
Execute scenario billing-contract-change.
Task directory: tasks/2026-05-20-billing-contract-change.

Read AGENTS.md, scenarios/billing-contract-change/scenario.yaml,
scenarios/billing-contract-change/README.md, then the selected repo entries in repos.yaml.

Then resolve repo paths, inspect git status for affected repos, enter repos in scenario order,
verify each repo is on the branch specified by scenario.yaml, read scenario-defined repo-local instruction sources,
inspect key files, implement the requested change, run checks, and update the task status, validation report, and decisions.
Do not commit unless I explicitly ask.
```

To continue existing work:

```text
Continue scenario billing-contract-change.
Task directory: tasks/2026-05-20-billing-contract-change.

Read the task files first, then resume from the next incomplete step.
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
2. Read `scenarios/<scenario>/scenario.yaml` to identify affected repository keys.
3. Read `scenarios/<scenario>/README.md`.
4. Resolve only those affected repo paths from `repos.yaml`.
5. Inspect `git status` in each affected repo.
6. Verify each affected repo's current branch exactly matches `repo_context.<repo>.branch`; stop and report before editing if it does not.
7. Follow `scenarios.<name>.order`.
8. For each repo, read scenario-defined `repo_context.<repo>.instruction_sources`.
9. Inspect scenario-defined `repo_context.<repo>.key_files`.
10. Implement repo-local changes.
11. Run each affected repository's repo-local `checks`.
12. Update task files under `tasks/<task-id>/`.
13. Report diff scope, validation results, risks, and delivery order.

The agent should not:

- assume this harness is a business repo
- apply one repo's instructions to another repo
- overwrite unrelated local changes
- mix commits across repos
- automatically checkout or create branches when the scenario branch check fails
- commit or create PRs unless explicitly requested
- guess YAML semantics when `AGENTS.md` defines them

## Task Files

Each task directory should contain:

| File | Purpose |
| --- | --- |
| `spec.md` | User request, scope, non-goals, assumptions, repo order, and execution steps. |
| `status.md` | Current progress, branches, blockers, skipped files. |
| `decisions.md` | Compatibility choices, migration decisions, rejected options. |
| `validation.md` | Repo-local build and check results, known failures, and residual risk. |

These files are the recovery point if the session is interrupted.

## Delivery Checklist

Before considering a task complete, verify:

- every affected repo's git status was inspected
- every affected repo's current branch matched the scenario-defined branch
- repo-local instructions were read or missing files were recorded
- source-of-truth repos were changed before downstream repos
- generated artifacts were updated according to repo-local rules
- repo-local checks passed or failures were documented
- task status and validation files are current
- delivery order and dependencies are clear
- remaining risk is documented

## Dry Run Checklist

For the first real use, run a small task manually before adding automation:

1. Replace placeholder repos in `repos.yaml`.
2. Replace `example-contract-change` with one real scenario.
3. Create a task directory from templates.
4. Ask the agent to run the scenario without committing.
5. Check whether the YAML fields were enough for path resolution, repo entry, checks, and task records.
6. Add only the missing fields or automation that the dry run proves is necessary.

## Future Automation

The MVP intentionally starts with documents before automation. No helper script is required to execute a scenario: the agent should enter each affected repository in scenario order and run the repo-local checks listed in `repos.yaml`.

Add automation later only for repeated mechanical operations, such as:

- reporting repo status
- preparing branches
- collecting diff summaries
- collecting delivery notes

Keep business judgment in scenario documents and task records.

## Practice Roadmap

Implement the remaining ideas in this order, after the first real scenario dry run:

1. Strengthen quality gates in task templates.
   - Add repo-local and delivery gate sections to `templates/validation-report.md` or `templates/task-status.md`.
   - Keep the gates checklist-oriented so agents can update them during execution.

2. Add a read-only repo status helper.
   - Report branch, dirty state, untracked files, and recent commits for each affected repo.
   - Keep it non-destructive and useful before any branch or code changes.

3. Add YAML validation after the configuration shape stabilizes.
   - Check required fields, unresolved paths, missing scenario documents, and scenario repos that are not declared in `repos.yaml`.
   - Prefer validation reports over automatic fixes.

4. Add task template generation only if task creation becomes frequent.
   - Generate `spec.md`, `status.md`, `decisions.md`, and `validation.md` from the existing templates.
   - Do not hide the task files; they remain the recovery point for interrupted sessions.

## Future Design

These ideas are intentionally deferred until several manual runs prove they are needed:

- Keep the harness as a standalone coordination repository.
- Keep the Trellis and meta-repo rationale as design guidance: this harness should stay independent of any single repo-local workflow system and should encode delivery semantics directly.
- Treat CLI support as a helper for mechanical, low-risk steps, not as the core execution model. Good candidates are YAML validation, repo status reports, task skeleton generation, and task summaries.
- Do not build a full CLI orchestrator until the manual workflow has repeated enough to prove the command boundaries are stable. Candidate helper commands include `scenario prepare`, `scenario status`, `scenario check`, and `scenario summary`.
- Do not treat multi-agent orchestration as a goal. Re-evaluate it only if real scenarios show that single-agent serial execution cannot manage context, repo count, or verification complexity.
- Avoid automatic commits and PR creation by default. If added later, they should be explicit delivery modes.
- Avoid complex branch management until repeated tasks prove it saves time. Branch preparation should always inspect dirty state and unrelated local changes first.

## Current State

This is an MVP skeleton. It is ready for a manual dry run against real repositories. The next maturity step is to use it on one real cross-repo scenario, then add automation for the steps that repeat without requiring judgment.
