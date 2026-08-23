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

## Knowledge Model

The harness splits the knowledge a cross-repo delivery needs into four layers, each with a distinct owner and lifecycle:

1. **Workspace registry — static, owned by this harness.** `repos.yaml` at the harness root. It records each registered repository's intrinsic facts — path, description, instruction sources, key files, checks — plus the baseline dependency graph (`edges`: directed existence assertions with evidence). The registry and its graph are accelerators, not authority: they seed candidate scoping and planning for free tasks, and never determine execution order or gate anything. Repositories few enough to traverse in one context do not strictly need the graph; it constrains discovery cost as the workspace grows.
2. **Scenario definition — static, owned by this harness.** `scenarios/<scenario>/scenario.yaml` plus the scenario `README.md`. This is the coordination knowledge for one recurring class of task: which repositories participate, what order they change in, how they depend on each other, which repo-local instruction sources must be read, which key files matter, and which checks prove completion. It is authored once per scenario class and reused across every task.
3. **Repo-local knowledge — static, owned by each business repo.** The files that `instruction_sources` points to (`AGENTS.md`, `CLAUDE.md`, `.trellis/workflow.md`, `CONTRIBUTING.md`, and similar), plus the contracts and code under `key_files`. This is the "how to work inside this repo" knowledge. It exists before any scenario run; the scenario only references it.
4. **Task records — dynamic, generated per execution.** `tasks/<task>/spec.md`, `status.md`, `decisions.md`, and `validation.md`. `init-task` scaffolds them from templates and the scenario or registry configuration; the executing agent enriches and updates them during planning, implementation, and validation. They are also the recovery point when a session is interrupted.

`repos.yaml` and `scenario.yaml` are the glues between the static layers: `repos.yaml` binds the workspace to its registered repositories; `scenario.yaml` binds harness-owned coordination knowledge to repo-owned local knowledge by pointing at instruction sources and key files inside each business repository.

Only the task layer is generated at runtime, and the flow is one-directional: repo-local instructions are read as inputs, and what the agent learns from them is condensed into the cross-repo task spec. The harness never writes back repo standing knowledge (the workflow documents and norms `instruction_sources` points to). Task-time repo artifacts — spec entries inside a repo's own spec framework — are authored document-level by the planning session per repo rules, runtime-reconciled by the repo-local implementation session, and referenced by workspace task files, never restated.

The knowledge placement is coupled with an execution protocol: planning and spec review gates, a fixed status vocabulary, check failure handling, interruption safety, and the helper CLI. The scenario concept answers *where the knowledge lives*; the protocol answers *how execution stays safe and resumable*. Together they turn "how should this class of cross-repo delivery be coordinated" from something an agent rediscovers on every run into explicit, pre-authored, protocol-driven knowledge.

## Declarative Coordination

The harness is declarative by choice: it favors pre-authored protocols over agent exploration. `instruction_sources` and `key_files` are not an exhaustive map of repo knowledge. They are a guaranteed minimum reading list — a floor, not a ceiling:

- The lists name pointers, not content. Style guides, workflow rules, and domain knowledge stay inside each business repo, maintained by its owners.
- The agent remains free to explore beyond the list; nothing in the protocol forbids reading additional files, and implementation naturally requires it.
- Declared files that do not exist are skipped and recorded. Repos without scenario-declared sources fall back to common project files such as `README.md`, `CONTRIBUTING.md`, `package.json`, and `Makefile`.

The restriction buys what free exploration cannot:

1. **Determinism.** The same guaranteed context on every run is a prerequisite for repeatable cross-repo delivery.
2. **Context economy.** Cross-repo tasks already carry coordination overhead; declared entry points keep per-repo discovery cost constant instead of unbounded.
3. **Verifiability.** Only declared files can be preflighted for existence and audited for skips.
4. **Protection of load-bearing files.** Missing a contract or schema file is catastrophic downstream; missing a style nuance is usually caught by checks. Scenario authors spend their judgment on the files that must never be missed.

Code style shows the split clearly: stylistic correctness is not trusted to the agent having read the guide — it is enforced by the repo's own `checks` (lint, typecheck, tests). Whatever must be deterministic is declared; whatever tolerates fuzziness is left to exploration.

In short: everything declared is machine-verifiable — `validate-scenario` validates structure, `preflight` validates branches and file existence, `checks` validates conventions, task files validate recoverability — and everything undeclared depends on agent capability. Agent freedom is not removed but reallocated: exploration stays where it is cheapest and errors are most likely to be caught by checks (in-repo implementation), while the layer where exploration is most expensive and errors most damaging (cross-repo order, dependency direction, contract entry points) is fully declared.

The cost is curation. Instruction and key-file lists are human-maintained and can go stale when a repo adopts conventions the scenario does not yet reference. Fallback discovery softens this but does not remove it; the maintenance burden falls on scenario authors, and what it purchases is determinism on every execution.

## Single-Session Limits And Per-Repo Sessions

The default execution model — one agent session running the scenario serially — has two honest limits:

1. **Cross-repo context contamination is mitigated, not eliminated.** The protocol firewalls (branch check before reading repo context, re-reading instruction sources on every repo entry, never applying one repo's instructions to another) are behavioral discipline, not runtime isolation. Conversation history still carries traces of earlier repos, and compaction summaries blur repo boundaries further. The per-repo summaries required by the execution model bound what carries forward, but a single session cannot guarantee isolation.
2. **Repo-local runtime mechanisms do not activate.** As noted in "Relationship To Repo-Local Spec Frameworks", hooks, skills, slash commands, and MCP injection bind to project configuration discovered at session start. An agent started in the harness directory that later enters a business repo does not re-trigger that discovery, so single-repo runtime support is absent and compliance runs at the document level.

The structural fix for both limits is the same: run each repository in a fresh agent session started inside that repository, where its runtime mechanisms activate normally. (Verified activation details for headless CLIs — including which mechanisms do not activate, such as Claude Code subagent-frontmatter hooks and approval-gated MCP tools — are recorded in `docs/subprocess-agent-run.md`.) Task files make this possible without orchestration, because they are session-external memory. A per-repo session reads `spec.md`, `status.md`, `decisions.md`, and `validation.md` first, does the repo-local work, and writes results back. The protocol is compatible with this pattern; it simply does not schedule it, and multi-agent orchestration is deferred beyond the MVP. When repos run under `bin/scenario-harness run`, each per-repo session must also end by writing a structured verdict file (`tasks/<task>/verdicts/<repo>.md`); a missing, malformed, or self-reported-blocked verdict blocks the run.

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

When a cross-repo request does not match any declared scenario — a one-off need, or a shape that has not repeated yet — use the free-task entry instead of forcing a scenario: `init-task --free` scaffolds the same gated task files, planning scopes candidates from the workspace registry, and the identical execution layer (gates, per-repo subprocess agents, verdicts, checks) runs the task-declared topology. A free task is a first-class entry with the same fail-closed behavior; when the same shape keeps recurring, promote it into a scenario.

Do not use this harness to replace a repository's own workflow. Each business repo still owns its code style, tests, generated files, commits, PRs, and CI.

## Agent-First Docs

This project treats agent readability as a primary design requirement. Agents should follow documented semantics instead of inferring behavior from YAML field names.

Required reading order:

1. `AGENTS.md`
2. `repos.yaml`
3. `scenarios/<scenario>/scenario.yaml` (scenario tasks)
4. `scenarios/<scenario>/README.md` (scenario tasks)

`AGENTS.md` defines the execution protocol and YAML semantics, including the `repos.yaml` registry semantics. `repos.yaml` registers the workspace repositories and the baseline dependency graph. Each scenario directory contains its own machine-readable execution template and human-readable SOP. Repository paths, roles, instruction sources, key files, and checks live inside the scenario (scenario tasks) or the registry (free tasks) so agents do not need a separate lookup. Task-specific data, such as expected branches and the concrete user request, lives under `tasks/`.

Within a scenario directory, the files have different jobs:

- `scenario.yaml` is the authoritative scenario template: selected repos, execution order, repository paths, repo-local instruction sources, key files, and checks.
- Task files declare the concrete request and expected task branches; agents stop and report if a repo is on a different branch during preflight.
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

### 2. Define Scenarios

Create a scenario directory with `scenario.yaml` and `README.md`.

```yaml
order:
  - api
  - web
  - worker

repos:
  api:
    path: ../api
    role: contract-source
    description: Owns API schema and domain contracts.
    instruction_sources:
      - AGENTS.md
      - CONTRIBUTING.md
      - README.md
    key_files:
      - openapi.yaml
      - src/contracts/
    checks:
      - npm run lint
      - npm test
  web:
    path: ../web
    role: downstream-consumer
    description: Consumes API contracts from api.
    instruction_sources:
      - AGENTS.md
      - README.md
    key_files:
      - src/api/
    checks:
      - pnpm typecheck
      - pnpm test
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

The command checks that the scenario files exist, `repos` and `order` agree,
checks have valid shapes, and repository paths resolve. It is read-only
and exits non-zero when the scenario is not safe to execute.

For a compact execution summary, use:

```bash
bin/scenario-harness plan-scenario billing-contract-change
```

This prints the scenario order, resolved repo paths, instruction sources, key
files, and repo-local checks. Use `--json` when the agent needs to carry the plan forward in a
structured form.

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

Expected branches are task-specific. By default, `init-task` records `scenario/<task-id>` as the
expected branch for every repo. Use `--branch <branch>` for a shared branch name, or repeat
`--repo-branch <repo>=<branch>` when repositories need different task branches.

When resuming, the agent should read the existing task files before editing repositories:

1. `spec.md`
2. `status.md`
3. `decisions.md`
4. `validation.md`

If the user asks to continue without naming a task directory, the agent should inspect `tasks/` for the matching scenario and continue the most recent incomplete task. If multiple plausible tasks exist, it should ask which one to use.

The helper can list matching task directories:

```bash
bin/scenario-harness list-tasks billing-contract-change --incomplete-only
```

Task-file structure can be linted at any time, read-only:

```bash
bin/scenario-harness check-task 2026-05-20-billing-contract-change
```

`templates/` doubles as the declarative schema for the four task files: the
required-section baseline is extracted from the template skeletons at runtime,
so adding or removing a template section changes what `check-task` requires on
its next run with zero code change. Mode-specific requirements (free-task
topology sections, mode-line and repo-resolution semantics) and error/warning
grading stay in the command. Stage-level incompleteness — gates not yet
recorded, an empty repo table, a legacy task without a Mode line — is
warning-only and never changes the exit code; shape violations exit non-zero.

### 2. Run Preflight

Before entering repo-local instructions or editing business code, run:

```bash
bin/scenario-harness preflight billing-contract-change \
  --task 2026-05-20-billing-contract-change
```

Preflight checks each affected repository's current branch against the task's expected branch, dirty state, missing instruction sources,
and missing key files. It updates marked sections in `status.md` and `validation.md`, so repeated
runs replace the previous preflight block instead of duplicating notes. Use `--no-write --json`
when the agent needs a read-only structured preview.

### 3. Run Checks

List the repo-local checks declared for the scenario:

```bash
bin/scenario-harness checks billing-contract-change
```

Run them after repo-local changes:

```bash
bin/scenario-harness checks billing-contract-change \
  --run \
  --task 2026-05-20-billing-contract-change
```

When `--task` is provided, check results are written to a marked section in `validation.md`.

### 4. Ask An Agent To Execute The Scenario

Start the agent in this harness directory and give it the scenario plus task directory when available.

Example prompt:

```text
Execute scenario billing-contract-change.
Task directory: tasks/2026-05-20-billing-contract-change.

Read AGENTS.md, scenarios/billing-contract-change/scenario.yaml,
and scenarios/billing-contract-change/README.md.

Then resolve repo paths, inspect git status for affected repos, enter repos in scenario order,
verify each repo is on the branch specified by the task, read scenario-defined repo-local instruction sources,
inspect key files, enrich the task spec, implement the requested change according to the enriched spec,
run checks, and update the task status, validation report, and decisions.
Do not commit unless I explicitly ask.
```

To continue existing work:

```text
Continue scenario billing-contract-change.
Task directory: tasks/2026-05-20-billing-contract-change.

Read the task files first, then resume from the next incomplete step.
Do not commit unless I explicitly ask.
```

### 5. Execute With Per-Repo Subprocess Agents

Once the Planning Gate and Spec Review Gate are recorded in `status.md`, the
helper CLI can drive the implementation pass itself:

```bash
bin/scenario-harness run billing-contract-change \
  --task 2026-05-20-billing-contract-change \
  --agent claude-code
```

`run` is a deterministic runner, not an orchestrating model: it refuses to
start unless both gates are recorded, walks repositories in scenario order,
checks the branch gate, renders the repo prompt from scenario data, spawns the
agent backend (`claude-code`, `codex`, or experimental `gemini`) in the
repository directory as its own process group, parses each repo's delivery
verdict file (`tasks/<task>/verdicts/<repo>.md`; missing, malformed, or
self-reported-blocked verdicts block the run), runs the repo checks itself
after the agent exits, and stops at the first failure with a stage × category
classification written to the task files. Raw agent output lands in
`tasks/<task>/logs/<repo>.log`; a `.run.lock` keeps runs single-writer; a
termination ladder (SIGTERM → grace → SIGKILL to the process group) enforces
`--timeout` (default 1800s per repo). `--dry-run` renders prompts only.

Design rationale, the borrowed-from-deepseek-harness mechanisms, and the
transport choice (public headless CLIs instead of SDK/app-server) are in
[`docs/subprocess-agent-run.md`](docs/subprocess-agent-run.md); the mock
self-test is `tests/run_mock_e2e.py`.

### 6. Free Tasks: Requests That Match No Scenario

When the request does not match a declared scenario (or is deliberately
one-off), the same machinery runs with a task-declared topology instead of a
pre-declared one:

```bash
bin/scenario-harness validate-registry
bin/scenario-harness init-task --free 2026-05-20-rename-profile-field \
  --request "Rename the profile field across api, web, and worker."
```

`init-task --free` validates the workspace registry instead of a scenario and
writes `mode: free` into `status.md`. The planning pass then scopes candidates
from `repos.yaml` (user-named repos plus baseline-graph in-edge neighbors),
verifies repo reality, fills the status.md per-repo table — row order is the
declared execution order — and initializes the dependency readiness section
from task-level dependency edges. Declaring a repo single-repo additionally
requires the workspace-level reverse lookup over all registered repos (see
AGENTS.md Free Task Protocol). Both gates apply without exemption; Spec Review
is the human control point that approves the generated topology.

The remaining commands drop the scenario argument and read the task
declaration plus the registry instead:

```bash
bin/scenario-harness preflight --task 2026-05-20-rename-profile-field
bin/scenario-harness checks --task 2026-05-20-rename-profile-field --run
bin/scenario-harness run --task 2026-05-20-rename-profile-field --agent claude-code
```

`run` refuses a free task without recorded gates exactly as it refuses a
scenario task (exit 2, `planning_gate_missing` / `spec_review_gate_missing`),
walks the task-declared order, and applies the same verdict and check gates.
Discovering a new affected repo mid-run goes through the Replanning Protocol
and a fresh Spec Review, never a silent expansion.

### 3. Execution Model

The default execution model is a single agent running the scenario serially. Do not introduce multi-agent scheduling in the MVP workflow. For the honest limits of this model and a compatible per-repo session pattern, see "Single-Session Limits And Per-Repo Sessions".

The scenario should be narrow enough that the agent can follow configured repos, checks, and scenario invariants without broad discovery across every repository. Put the required knowledge in `scenario.yaml`, the scenario README, and task files instead of relying on the agent to infer cross-repo behavior.

To control context pressure, the agent should summarize after each repository:

- files changed
- contract, API, event, or generated artifact implications
- checks run and results
- blockers, assumptions, or downstream notes

That summary becomes the required context for the next repository unless debugging requires returning to an earlier repo.

### 4. Expected Agent Behavior

The agent should:

1. Select the task mode with the Task Mode Selection Protocol in `AGENTS.md` (scenario task or free task) and record the mode plus reason in the task spec.
2. Read the required harness docs in order. For a scenario task, read `scenarios/<scenario>/scenario.yaml` to identify affected repository keys; for a free task, read `repos.yaml` and scope candidates before planning.
3. Read `scenarios/<scenario>/README.md` (scenario task).
4. Run `bin/scenario-harness validate-scenario <scenario>` (scenario task) or `bin/scenario-harness validate-registry` (free task).
5. Use `bin/scenario-harness plan-scenario <scenario>` to carry a compact execution summary (scenario accelerator; free tasks plan from the registry).
6. Create or select task files with `bin/scenario-harness init-task` (or `init-task --free`) or `bin/scenario-harness list-tasks`.
7. Run preflight before entering business repos: `bin/scenario-harness preflight <scenario> --task <task-id>`, or `preflight --task <task-id>` for a free task.
8. Follow the authoritative order: scenario `order` (scenario task) or the task-declared topology (free task).
9. For each repo, read the declared `repos.<repo>.instruction_sources` (registry entries fall back to common project files when absent).
10. Inspect the declared `repos.<repo>.key_files`.
11. Enrich `tasks/<task-id>/spec.md` with implementation notes, impact areas, risks, and validation focus learned from those key files before editing code. Author per-repo spec entries in the repo's own framework per the Spec Ownership Layering in AGENTS.md.
12. Implement repo-local changes according to the enriched task spec, following the repo-local spec entries it references (runtime reconciliation first).
13. Record user clarifications that affect goals, scope, implementation, validation, risks, or delivery order in `spec.md` before continuing.
14. Record any material deviation from the enriched spec in `decisions.md` and reflect it back into `spec.md` before continuing.
15. Run each affected repository's repo-local `checks`, preferably through `bin/scenario-harness checks <scenario> --run --task <task-id>` (or `checks --task <task-id> --run` for a free task).
16. Update task files under `tasks/<task-id>/`.
17. Report diff scope, validation results, risks, and delivery order.

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
| `spec.md` | User request, user clarifications, scope, non-goals, assumptions, repo order, execution steps, and key-file-derived implementation notes. |
| `status.md` | Current progress, branches, blockers, skipped files. |
| `decisions.md` | Compatibility choices, migration decisions, rejected options. |
| `validation.md` | Repo-local build and check results, known failures, and residual risk. |

These files are the recovery point if the session is interrupted.

## Delivery Checklist

Before considering a task complete, verify:

- every affected repo's git status was inspected
- every affected repo's current branch matched the task-defined branch
- repo-local instructions were read or missing files were recorded
- source-of-truth repos were changed before downstream repos
- generated artifacts were updated according to repo-local rules
- repo-local checks passed or failures were documented
- task status and validation files are current
- delivery order and dependencies are clear
- remaining risk is documented

## Helper CLI Checklist

For the first real use, run a small task through the helper CLI without committing:

1. Replace `example-contract-change` with one real scenario.
2. Declare the real scenario's repositories directly under `scenarios/<scenario>/scenario.yaml`.
3. Run `bin/scenario-harness validate-scenario <scenario>`.
4. Run `bin/scenario-harness plan-scenario <scenario> --json` and confirm the selected repos and order.
5. Run `bin/scenario-harness init-task <scenario> <task-id> --request "..."`.
6. Run `bin/scenario-harness preflight <scenario> --task <task-id>`.
7. Ask the agent to execute the scenario without committing.
8. Run `bin/scenario-harness checks <scenario> --run --task <task-id>` after repo-local changes.
9. Confirm `status.md`, `validation.md`, and `decisions.md` contain the recovery information needed for resume.

The helper CLI is responsible for repeated mechanical operations: validation, task initialization,
preflight state capture, task discovery, compact planning, and check execution. Keep business
judgment in scenario documents and task records.

## Future Delivery Layer

The current helper CLI covers the local execution layer:

```text
validate scenario -> plan scenario -> init/select task -> preflight -> implement repos -> run checks
```

The next maturity step is a delivery orchestration layer around that local workflow. It should not
replace repo-local development rules or CI/CD systems. It should give agents explicit insertion
points for existing issue, CI, Git hosting, and deployment CLIs or MCP tools.

Recommended lifecycle:

```text
1. Intake / create delivery item
2. Validate scenario
3. Initialize or resume task
4. Prepare branches
5. Preflight
6. Enrich task spec from key files
7. Implement repo-local changes according to the enriched spec
8. Run local checks
9. Commit and push branches
10. Create or update PRs
11. Collect CI status
12. Deploy or release
13. Close out task and external tracking
```

Future delivery commands should be layered separately from local execution commands:

| Stage | Insertion Point | Future Command Shape | Records To Update |
| --- | --- | --- | --- |
| Intake | Before or immediately after `validate-scenario` | `intake <scenario> --task <task-id>` | `spec.md`, `status.md` |
| Branch preparation | After `init-task`, before `preflight` | `branches <scenario> --task <task-id> --create` | `status.md`, `validation.md` |
| Commit | After local checks pass | `commits <scenario> --task <task-id>` | `status.md`, `decisions.md` |
| Push | After commits are reviewed locally | `push <scenario> --task <task-id>` | `status.md` |
| PRs | After push | `prs <scenario> --task <task-id> --create` | `status.md` |
| CI | After PR creation or push-triggered CI | `ci <scenario> --task <task-id>` | `validation.md` |
| Deploy | After CI passes and approvals are satisfied | `deploy <scenario> --task <task-id> --env staging` | `validation.md`, `status.md`, `decisions.md` |
| Closeout | After deployment or explicit stop | `closeout <scenario> --task <task-id>` | all task files, external ticket |

Safety rules for the future delivery layer:

- Default to read-only inspection unless the command name and flags clearly imply a side effect.
- Require explicit flags for external-state changes, such as `--create`, `--push`, `--deploy`, or `--close`.
- Never create, switch, rebase, reset, commit, push, merge, deploy, or close external tickets implicitly.
- Treat each repository independently; never mix commits across repositories.
- Stop on dirty worktrees unless the task record explicitly says the changes are expected.
- Record external IDs and links in task files: issue, branch, commit SHA, PR, CI run, deployment, release, and rollback notes.
- Keep business judgment in scenario README files and task records. The delivery layer should orchestrate mechanical platform operations, not decide compatibility, migration, release order, or risk acceptance by itself.

Suggested future scenario fields, once real delivery runs prove the shape:

```yaml
delivery:
  external_tracking:
    system: jira
    project: BILLING
  branch:
    create_from: default_branch
  pull_requests:
    base: main
    labels:
      - scenario
  deploy_order:
    - contract-repo
    - consumer-repo
    - worker-repo
  environments:
    - staging
    - production
  gates:
    staging_required: true
    production_requires_approval: true
```

Repo-specific deployment commands should live under `repos.<repo>` only when they are truly
scenario-specific. Stable repo-owned deployment rules should remain in the repo or its CI/CD
platform.

## Current State

The current implementation is ready for local cross-repo execution with helper CLI support. The next
maturity step is to use it on one real cross-repo scenario, then add delivery-layer adapters only for
the platform operations that repeat without requiring business judgment.
