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
- This harness coordinates a multi-repo workspace: business repositories are registered in `repos.yaml` and may additionally be declared by a scenario. Repositories may only be entered and edited through the task protocols.
- Treat this harness as a standalone coordination repository, not as a business repository.
- Before editing any business repository, read its repo-local instructions.
- Repo-local instructions may come from Trellis, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `README.md`, `Makefile`, package scripts, or scenario-defined files.
- Treat each repository's git state independently.
- Never mix commits across repositories.
- Never run destructive commands unless the user explicitly requested them.
- Record cross-repo progress in the active task directory under `tasks/`.

## Execution Protocol

1. Select the task mode using the Task Mode Selection Protocol (scenario task or free task).
2. For a scenario task, read `scenarios/<scenario>/scenario.yaml`, then `scenarios/<scenario>/README.md`. For a free task, read `repos.yaml`.
3. Run validation from the harness root before creating a new task directory: scenario tasks run `bin/scenario-harness validate-scenario <scenario>`; free tasks run `bin/scenario-harness validate-registry`.
   - If it reports errors, stop before editing business repositories.
   - If resuming an existing task, record `current step: scenario_invalid` (scenario task) or `current step: blocked` with the validation errors (free task) in `tasks/<task>/status.md`.
   - If creating a new task, do not create the task directory until validation passes.
   - Use `--json` when machine-readable output is useful.
4. Create or locate a task directory under `tasks/`, then set `current step` to `scenario_validated` (scenario task) or `task_created` (free task, before planning).
5. Inspect git status for all affected repositories. Prefer `bin/scenario-harness preflight <scenario> --task <task-id>` (scenario task) or `bin/scenario-harness preflight --task <task-id>` (free task), then set `current step` to `preflight_complete` if it succeeds.
6. Complete the Planning Pass Protocol for all affected repositories.
7. Confirm the Planning Gate is recorded as complete in `tasks/<task>/status.md`.
   - Do not edit business repository code before this gate is complete.
8. Complete the Spec Review Gate Protocol.
   - Do not edit business repository code before this gate is approved or explicitly skipped by the user.
9. Modify repositories in the authoritative order using the Implementation Repo Entry Protocol: scenario `order` for scenario tasks, the task-declared topology for free tasks.
10. Run repo-local checks and follow the Check Failure Protocol for any failure.
11. Mark the task complete only when the Completion State Protocol is satisfied.

## Agent Helper CLI

Use `bin/scenario-harness` for mechanical checks before doing manual reasoning.

- `bin/scenario-harness validate-scenario <scenario>` validates the selected scenario, resolved repository paths, checks, and basic field shapes. When `repos.yaml` exists it also emits warning-level consistency findings (Q3-B); warnings never change the exit code.
- `bin/scenario-harness validate-scenario <scenario> --json` emits stable JSON for agents that want to parse findings.
- `bin/scenario-harness validate-registry` validates the workspace registry `repos.yaml`: structure, edge endpoints, `(from, to)` uniqueness, non-empty evidence, absence of task-specific values, and path resolution; it also cross-checks scenario repo keys and intrinsic fields against the registry (Q4-a) at warning level.
- `bin/scenario-harness init-task <scenario> [task-id] --request "..."` creates `spec.md`, `status.md`, `validation.md`, and `decisions.md` from the selected scenario without overwriting existing task files. `bin/scenario-harness init-task --free <task-id> --request "..."` scaffolds the same four files for a free task: it validates the registry instead of a scenario and records `mode: free`; branch rules (default `scenario/<task-id>`, `--branch`, `--repo-branch`) are unchanged.
- `bin/scenario-harness preflight <scenario> --task <task-id>` inspects affected repository git status, task branch gates, missing instruction sources, and missing key files, then updates `status.md` and `validation.md`. Without a scenario argument, `preflight --task <task-id>` drives the preflight from the task declaration: free tasks resolve their repo set from the status table plus the registry.
- `bin/scenario-harness plan-scenario <scenario>` prints the compact execution plan: repo order, paths, instruction sources, key files, and checks. Scenario accelerator only; free tasks plan from `repos.yaml` directly.
- `bin/scenario-harness list-tasks <scenario>` lists matching task directories newest first for resume decisions. The scenario argument is optional: without it, free tasks are listed (mode filter, replacing string haystack matching; `--all` lists every mode).
- `bin/scenario-harness checks <scenario>` lists repo-local checks; add `--run --task <task-id>` to execute checks and update `validation.md`. Without a scenario argument, `checks --task <task-id>` uses the task-declared repo set with checks from `repos.yaml`.
- `bin/scenario-harness check-task <task-id>` lints the structure of `tasks/<task-id>` with `templates/` as the declarative schema source: the common-core required-section baseline is extracted from the template skeletons at runtime, so adding or removing a template section changes the schema on the next run with zero code change (mode ownership of sections and error/warning grading stay in the command code; the lint checks section existence, never content). It applies to both modes with the same core: the four task files exist, required sections exist, `current step` is inside the Status Step Vocabulary, the per-repo status table has a legal shape (column count, branch cells, duplicate rows), and the gate sections exist. Three checks are mode-aware: the `Mode:` line value (and scenario existence), table rows resolving against scenario.yaml (scenario tasks) vs `repos.yaml` (free tasks), and mode-specific spec sections (`Scenario Order` vs `Task-Declared Topology` + `Candidate Scoping`). Shape violations are errors (exit 2); stage-level incompleteness — a legacy task without a Mode line, unrecorded gates, an empty repo table, an unset current step, free-task Candidate Scoping still TBD — is warning-only and never changes the exit code. Purely read-only and never writes files; supports `--json`.
- `bin/scenario-harness run <scenario> --task <task-id>` executes the gated per-repo subprocess agent layer: it refuses to start unless the Planning Gate and Spec Review Gate are recorded in `status.md`, then walks repositories in scenario order, spawns the selected agent backend (`--agent claude-code|codex|gemini`) inside each repository, requires each child agent to end with a structured verdict file (`tasks/<task>/verdicts/<repo>.md`) where a missing, malformed, or self-reported-blocked verdict blocks the run, runs repo checks itself, and records agent telemetry and stage × category failures in task files. The scenario argument is optional: `run --task <task-id>` reads the mode from the task's `status.md`; a free task builds its context from the task declaration plus `repos.yaml` and walks the task-declared order, with gates, verdicts, and checks behaving identically. See `docs/subprocess-agent-run.md`.

Exit codes:

- `0`: validation passed.
- `2`: scenario or repository configuration is invalid.
- `64`: command usage or runtime prerequisites are invalid.

The helper CLI itself never edits business repositories and never changes git state; `run` only delegates gated repo-local edits to child agent processes started inside each repository.

## Task Mode Selection Protocol

1. If the user explicitly names a scenario, use that scenario (scenario task).
2. If the user asks to resume, continue, or finish existing work without naming a scenario, inspect `tasks/` and scenario names to find matching incomplete tasks.
3. If the user does not name a scenario, inspect `scenarios/*/scenario.yaml` and `scenarios/*/README.md` only enough to find plausible matches.
4. If exactly one scenario clearly matches the request, select it and record the selection reason in `tasks/<task>/spec.md` when the task directory exists.
5. If no scenario or multiple scenarios plausibly match, ask the user to choose between the options instead of only asking for a scenario name: proceed as a free task (works for no-match and deliberate one-off requests), or pick one of the matching scenarios. A free task is a protocolized first-class entry, not a bypass around the protocols: it runs the same Planning Gate, Spec Review Gate, branch gates, verdicts, and checks.
6. Record the mode and the selection reason in `tasks/<task>/spec.md` for both modes (`mode: scenario:<name>` or `mode: free`).
7. Ask before creating a task directory, entering business repositories, or editing files whenever the choice is ambiguous.

## Free Task Protocol

Free tasks handle cross-repo requests whose topology is not pre-declared by any scenario. They share every gate, verdict, check, and completion semantic with scenario tasks; the only differences are where the topology comes from and how the dependency readiness section is initialized.

1. **Mode selection**: Task Mode Selection Protocol; record `mode: free` and the reason in `spec.md`.
2. **Initialization**: `bin/scenario-harness init-task --free <task-id> --request "..."` scaffolds the same four files and writes `mode: free` into `status.md`. Free tasks are named `YYYY-MM-DD-<short-topic>` (no scenario suffix). Expected-branch rules match scenario tasks: default `scenario/<task-id>`, or `--branch` / `--repo-branch` overrides recorded as defaults the Planning Pass materializes into per-repo rows.
3. **Candidate scoping**: read `repos.yaml`. Start from the user-named repos and collect candidates along baseline-graph in-edges (repos consuming a changed repo's outputs). Out-edge upstreams are included only when the request itself requires upstream changes; never traverse out-edges only. Record each candidate and its provenance (edge evidence or user naming) in `spec.md`. When the graph is empty or `repos.yaml` declares no edges, the candidate set is all registered repos or the user-named set.
4. **Planning Pass**: verify repo reality for each candidate (actual dependencies, not just graph edges), then determine the affected repo set, order, per-repo expected changes, contracts, downstream impact, and validation strategy; write them into `spec.md` and the `status.md` per-repo table — row order in that table is the task-declared execution order consumed by preflight, checks, and run. Initialize the dependency readiness section from the task-level dependency edges produced by planning. Record exclusion reasons for candidates not selected (auditable, recoverable). Then author per-repo spec entries per the Spec Ownership Layering.
5. **Single-repo adjudication duty**: a single-repo conclusion is derived, never assumed. Adjudge single-repo only when all three hold: (a) a workspace-level reverse lookup mechanically scanned all registered repos for references to X's outputs (imports, manifest dependencies, API paths, event names) with no hits — graph hits may narrow the scan, but an empty in-edge set alone is never sufficient; (b) every in-edge neighbor of X was verified against repo reality and its exclusion recorded; (c) out-edge upstreams genuinely need no change. Persist evidence and exclusions in `spec.md`.
6. **Gates**: Planning Gate and Spec Review Gate apply without exemption. For a free task, Spec Review is the human control point that approves the generated topology — it replaces scenario-mode's "topology pre-declared by a human", it is not extra bureaucracy. Review objects are the same in both modes: the workspace cross-repo spec, each repo's spec entries, and per-repo spec diffs (see Spec Ownership Layering).
7. **Implementation**: Implementation Repo Entry Protocol per repo, with repo paths resolved from `repos.yaml`; the child agent first performs runtime reconciliation, then implements from the repo-local spec entries. `run --task <task-id>` walks the task-declared order through the same per-repo subprocess → verdict → checks chain as scenario tasks.
8. **Mid-run expansion**: discovering a new affected repo applies the Replanning Protocol (`replanning_required` → replanning → spec review re-approval → continue); record the expansion and reason in `decisions.md`.

Fail-closed invariants are mode-independent: `run` rejects a free task without recorded gates exactly as it does a scenario task (exit 2, `planning_gate_missing` / `spec_review_gate_missing`); a repo counts as complete only with exit 0 plus a valid `ok` verdict plus passing checks.

## Status Step Vocabulary

Use these exact `current step` values in `tasks/<task>/status.md`:

- `task_created`
- `scenario_invalid`
- `scenario_validated`
- `preflight_complete`
- `branch_preparation_in_progress`
- `branch_preparation_complete`
- `planning_in_progress`
- `planning_blocked`
- `planning_complete`
- `spec_review_pending`
- `spec_review_approved`
- `replanning_required`
- `replanning_in_progress`
- `replanning_complete`
- `implementing:<repo-key>`
- `validating:<repo-key>`
- `repo_complete:<repo-key>`
- `blocked`
- `complete`

When blocked, include the blocked repo if applicable, the expected branch, the actual branch, the blocking condition, and the user decision needed. Do not invent synonymous step names.

`current step` is only the agent's current global position. It must not be the only recovery record. `tasks/<task>/status.md` must also include:

- a per-repo status table with repo key, expected branch, actual branch, planning status, implementation status, validation status, output readiness, and blocker
- a Planning Gate section
- a Spec Review Gate section
- a dependency readiness section for scenario-declared `depends_on` links
- an append-only Status History section with timestamped step changes

Append to Status History whenever `current step` changes. Do not replace the history when updating the current step.

## Planning Pass Protocol

Before editing code in any business repository, complete a lightweight cross-repo planning pass for all affected repositories in the authoritative order (scenario `order` for scenario tasks, the task-declared topology for free tasks).

1. Set `current step` to `planning_in_progress` in `tasks/<task>/status.md`.
2. For each affected repository:
   - resolve the repo path from `scenarios/<scenario>/scenario.yaml` (scenario task) or `repos.yaml` (free task)
   - run `git status` in that repo
   - verify the current branch exactly matches the task-defined branch before reading further repo-local context
   - read scenario-defined local instructions that exist, recording skipped instruction files in `tasks/<task>/status.md`
   - if no scenario-specific instruction source exists, inspect common project files listed in the Implementation Repo Entry Protocol
   - inspect scenario-defined key files enough to identify contracts, downstream consumption, expected changes, risks, and validation focus
3. Update `tasks/<task>/spec.md` with:
   - cross-repo implementation plan
   - compatibility constraints and contract decisions
   - per-repo expected changes
   - downstream impact notes
   - validation strategy
   - planning assumptions and unresolved questions
4. For each affected repository, record the minimum planning checklist in `tasks/<task>/spec.md` or `tasks/<task>/status.md`:
   - instruction sources read
   - instruction sources skipped
   - key files inspected
   - owned outputs that may be touched
   - upstream outputs consumed
   - expected changes
   - validation commands or documented validation gaps
   - known unknowns
   - downstream repos affected
5. Author repo-local spec entries per the Spec Ownership Layering: the single planning session writes each repo's spec entries directly into the repo framework's documented location (document-level compliance). The workspace task spec holds only the cross-repo layer plus references; it never restates per-repo design.
6. Update `tasks/<task>/decisions.md` for planning decisions that affect compatibility, migration, delivery order, or risk.
7. Initialize the dependency readiness section of `tasks/<task>/status.md`: scenario tasks initialize from scenario `depends_on`; free tasks initialize from the task-level dependency edges produced by this planning pass.
8. If the planning pass reveals missing task-specific dependency values, branch mismatches, conflicting repo-local instructions, or unresolved design choices that would make implementation risky, set `current step` to `planning_blocked`, record the blocker, and ask for direction.
9. When the planning pass is complete and unblocked, record a Planning Gate in `tasks/<task>/status.md`:
   - `current step: planning_complete`
   - repositories reviewed
   - instruction files read and skipped
   - key files inspected
   - spec updated: yes
   - minimum planning checklist complete for every affected repo: yes
   - dependency readiness section initialized: yes
   - blocking issues: none

Lightweight planning means reading enough to identify contracts, consumption points, expected changes, and validation strategy. It does not require tracing every call site, editing code, running repo-local checks, generating artifacts, or making implementation-level refactors.

Lightweight planning is sufficient only when all of these are true:

- the minimum planning checklist is complete for every affected repository
- every scenario-declared `depends_on` edge has a documented producer, consumer, output, and validation approach
- no unresolved question can change implementation shape, compatibility, migration behavior, delivery order, or validation strategy
- the validation strategy covers the expected changes or records a validation gap and risk
- downstream impact is known for each touched output, or the unknown is recorded as a blocker

### Delegation Rules For The Planning Pass (Ingestion / Synthesis)

The single-context constraint covers synthesis and adjudication, not ingestion. Both modes share these rules:

- **Ingestion may be delegated to read-only subagents**: reading large code spans, cross-repo grep, call-chain tracing, manifest/reference scanning, and single-repo workspace reverse lookups — heavy-ingestion, light-decision mechanical collection. Four boundaries:
  1. read-only — zero writes to business repositories;
  2. digests must carry file:line citations so the main session keeps spot-check ability;
  3. results are persisted to task notes under `tasks/<task>/` (recovery-point principle), never left only in conversation;
  4. allowed, not mandated — for small repos direct reading is better (one less lossy hop). Trigger heuristics: reads exceed a context budget, independent traces can run in parallel, or the pattern is purely mechanical.
- **Synthesis is not delegable**: topology adjudication, contract decisions, cross-repo spec writing, per-repo spec entries, and single-repo adjudication happen in the single planning session. Free-task topology is generated in exactly this phase.

## Planning Resume Protocol

Use this protocol when the user responds to a `planning_blocked` state.

1. Record the user clarification in `tasks/<task>/spec.md`.
2. If the clarification affects compatibility, migration, delivery order, validation, or risk, also record the decision in `tasks/<task>/decisions.md`.
3. Set `current step` to `planning_in_progress` and append the transition from `planning_blocked` to Status History.
4. Re-run the Planning Pass Protocol only for the blocked repositories, dependency edges, and task-file sections unless the clarification invalidates the full plan.
5. Update the per-repo status table, dependency readiness section, and Planning Gate fields that were affected by the blocker.
6. If the blocker is resolved and no new planning blocker exists, record `current step: planning_complete`.
7. Run the Spec Review Gate Protocol before editing business repository code.

## Spec Ownership Layering

Task design knowledge is owned in two layers, and the workspace never restates the per-repo layer:

| Content | Owner | Shape in the other layer |
| --- | --- | --- |
| Affected repo set, order, dependency edges | workspace task spec | n/a (home layer) |
| Cross-repo contracts, interface changes, compatibility decisions | workspace task spec | n/a (home layer) |
| Cross-repo validation strategy, single-repo adjudication evidence, candidate and exclusion records | workspace task spec | n/a (home layer) |
| Per-repo implementation design (repo has a local spec framework) | repo-local framework (Trellis / Spec Kit / OpenSpec …) | workspace holds a reference (repo, path, coverage) |
| Per-repo implementation design (no framework, or framework cannot create entries document-level) | workspace task spec | inline fallback, transcribed at implementation |

Repo-local spec entries are authored by the single planning session at planning time (see Planning Pass Protocol step 5), in document-level compliance: read the workflow documents declared in `instruction_sources` and hand-write entries in the framework's documented format. Implementation-phase child agents read the finished entries, reconcile, and implement — they do not design. Rationale: coherence errors cannot be auto-repaired, format errors can — format deviations are visible in Spec Review and correctable with framework tooling at implementation, while two specs describing the same contract differently have no machine backstop.

**Runtime reconciliation** (first step of implementation): the child agent starts in the repo (runtime active), runs the framework's own scaffold/registration flow as its instruction sources document, then merges the planning-authored content — planning content is authoritative and the reconciliation diff stays visible in the repo. If a framework fundamentally cannot accept document-level entries, that repo's design falls back to inline workspace content transcribed at implementation; the fallback must be recorded explicitly in `spec.md` ("this repo's framework does not support document-level creation"); silent downgrade is not allowed.

Three boundaries, shared by both modes, so spec entries cannot become a backdoor around the implementation gates:

1. **Location whitelist**: entries may only be written into the repo framework's declared spec directories (derived from `instruction_sources` / `key_files`). Writes outside the whitelist remain covered by the "no business-repo edits before Spec Review approval" prohibition; business repo code is never edited before approval — whitelisted spec entries are the review medium itself.
2. **Branch precondition**: spec entries are written on the preflight-verified task branch, on the same branch and in the same delivery batch as the implementation.
3. **Diff review**: the Spec Review checklist includes per-repo review of spec-entry diffs; out-of-scope writes become visible in review.

Write-back rule: the harness never writes back repo standing knowledge (the workflow documents and norms `instruction_sources` point to). Task-time repo artifacts (spec entries) are document-level created by the planning session per repo rules and runtime-reconciled by the repo-local session; workspace task files reference them and never restate them.

## Spec Review Gate Protocol

After the Planning Gate is complete and before editing business repository code:

1. Set `current step` to `spec_review_pending`.
2. Present the user with a concise summary of `tasks/<task>/spec.md`, including:
   - cross-repo implementation plan
   - expected changes by repo
   - contract or compatibility decisions
   - downstream impact
   - validation strategy
   - known risks and unresolved questions
   - repo-local spec entry references per repo and their diffs (see Spec Ownership Layering; walk each repo's spec-entry diff — out-of-scope writes must be visible here)
3. Business repo code remains off-limits before approval. The only permitted pre-approval writes inside a business repo are spec entries inside the location whitelist (Spec Ownership Layering boundary 1): they are the review medium itself, not an exemption from the gate.
4. Wait for user approval before implementation unless review is explicitly skipped by the user.
   - The skip must come from the current conversation or from task files that existed before the current agent run.
   - Agent-written task updates in the current run cannot authorize skipping review.
   - If the authorization source is ambiguous, wait for user approval.
5. Record the approval, requested changes, or explicit user-authorized skip in `tasks/<task>/status.md`.
6. If the user changes scope or design during review, update `tasks/<task>/spec.md` and `tasks/<task>/decisions.md` before implementation.
7. Set `current step` to `spec_review_approved` only after approval is recorded or the explicit skip is recorded.

## Implementation Repo Entry Protocol

Run this protocol for each repository during the implementation pass, even if the same repo was already inspected during planning.

1. Set `current step` to `implementing:<repo-key>` in `tasks/<task>/status.md`.
2. Resolve the repo path from `scenarios/<scenario>/scenario.yaml` (scenario task) or `repos.yaml` (free task).
3. Run `git status` in that repo.
4. Check the current branch against the expected branch recorded in `tasks/<task>/status.md`.
   - The branch check is an exact string match.
   - If the current branch does not match, stop before reading further repo-local context or editing files.
   - Record the expected branch, actual branch, and blocked repo in `tasks/<task>/status.md`.
   - Report the mismatch to the user and wait for direction.
   - Do not automatically checkout, create, or rename branches unless the user explicitly requested branch preparation.
5. Before implementing a repository with `depends_on` entries, verify each upstream dependency in the dependency readiness section of `tasks/<task>/status.md`.
   - The upstream repo must be recorded as complete or intentionally skipped.
   - The referenced upstream output must be recorded as ready, unchanged, or intentionally not produced with a documented reason.
   - If dependency readiness is missing or failed, set `current step` to `blocked`, record the dependency blocker, and ask for direction before editing the downstream repository.
6. Read or reread each scenario-defined `repos.<repo>.instruction_sources` entry in order.
   - If the file exists, read it.
   - If the file does not exist, skip it and record the skip.
7. If no scenario-specific instruction source exists, inspect common project files:
   - `README.md`
   - `CONTRIBUTING.md`
   - `package.json`
   - `Makefile`
   - `pyproject.toml`
   - `Cargo.toml`
   - `go.mod`
8. Reread or deepen scenario-declared (scenario task) or registry-declared (free task) `repos.<repo>.key_files` as needed for implementation.
9. Add any new repo-local implementation notes, impact areas, risks, and validation focus to `tasks/<task>/spec.md`.
10. Perform runtime reconciliation (Spec Ownership Layering): if planning-authored spec entries exist for this repo, run the repo framework's scaffold/registration flow as its instruction sources document, then merge the planning-authored content (planning content authoritative; reconciliation diff visible in the repo). If a document-level-creation fallback was recorded, transcribe the inline design instead.
11. Implement the repo-local change according to the enriched task spec, following the repo-local spec entries it references instead of re-designing them.
12. If implementation requires a material deviation from the enriched spec, record the reason in `tasks/<task>/decisions.md` and update `tasks/<task>/spec.md` before continuing.
13. Set `current step` to `validating:<repo-key>` before running checks.
14. Run repo-defined checks.
15. Record check output summary in `tasks/<task>/validation.md`.
16. If checks pass, update the per-repo status table and record scenario-declared outputs for this repository as ready, unchanged, skipped, or blocked in the dependency readiness section.
17. If checks pass, set `current step` to `repo_complete:<repo-key>`.
18. Do not commit unless the user or scenario explicitly requests commits.

## Check Failure Protocol

When a repo-local check fails:

1. Record the repo, command, exit status, important output summary, known failures, and residual risk in `tasks/<task>/validation.md`.
2. Default to `current step: blocked`, stop, and report the failure to the user.
3. Continue only after the user explicitly approves continuing with the recorded failure, or after the failure is fixed and checks are rerun.
4. If the user approves continuing, record the approval and rationale in both `validation.md` and `decisions.md` before moving to the next repository.
5. Do not mark a repository complete while its required checks are failing unless the user-approved skip or failure acceptance is recorded in both `validation.md` and `decisions.md`.

## Branch Preparation Protocol

Use this protocol only when the user explicitly requests branch preparation.

1. Set `current step` to `branch_preparation_in_progress`.
2. Prepare branches before the planning pass, so branch gates validate the branch that will receive the work.
3. Use one branch per affected repository unless the user says otherwise.
4. Prefer matching branch names across repositories, such as `scenario/<task-id>`.
5. Prepare branches in scenario-defined order.
6. If branch preparation fails in any repository, stop, record the prepared and failed repositories in `tasks/<task>/status.md`, and ask for direction. Do not roll back branches automatically.
7. When all requested branches are prepared, set `current step` to `branch_preparation_complete` and record the expected branch for each affected repository in `tasks/<task>/status.md`.

## Task Directory Protocol

The active task directory is the recovery point for a scenario run.

1. If the user provides a task directory, use it.
2. If the user asks to continue, resume, or finish existing work without naming a task directory, inspect `tasks/` for the matching scenario and choose the most recent task directory whose `current step` is not `complete`.
3. If exactly one plausible task directory exists for the scenario, use it.
4. If multiple plausible task directories exist and the user did not identify one, ask which task to continue before editing repositories.
5. If no plausible task directory exists, create a new one under `tasks/` using `YYYY-MM-DD-<scenario>` or `YYYY-MM-DD-<scenario>-<short-topic>` when the task needs distinction. Free tasks are named `YYYY-MM-DD-<short-topic>` (no scenario suffix).

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
- Fill `spec.md` with the task mode (`scenario:<name>` or `free`) and selection reason, the scenario (scenario tasks), user request, scope, non-goals, assumptions, repository order, and execution steps.
- Record user clarifications that affect task goals, scope, implementation, validation, risks, or delivery order in `spec.md` before continuing implementation.
- Before implementing code in any repository, enrich `spec.md` through a lightweight cross-repo planning pass over all affected repositories after branch verification and repo-local instruction review.
- The planning pass should identify contracts, downstream consumption, expected per-repo changes, compatibility constraints, risks, and validation strategy without requiring implementation-level deep reading of every file.
- Fill `status.md` with the task id, scenario, selected scenario reason, expected branches, initial repo states, skipped instruction files, current step, per-repo status table, Planning Gate state, Spec Review Gate state, dependency readiness section, and Status History.
- Adjust `spec.md` and `validation.md` to match the scenario's actual repository keys and order.

When resuming an existing task directory, read these files before editing repositories:

1. `spec.md`
2. `status.md`
3. `decisions.md`
4. `validation.md`

After reading the task files, rerun scenario validation before editing repositories:

1. Read the current `scenarios/<scenario>/scenario.yaml` and `scenarios/<scenario>/README.md`.
2. Run `bin/scenario-harness validate-scenario <scenario>`.
3. Compare the current repo order, repo keys, repo paths, instruction sources, key files, and checks against the selected task files.
4. If scenario structure changed in a way that could invalidate the task spec or validation plan, set `current step` to `replanning_required`, record the mismatch in `status.md`, and run the Replanning Protocol before editing repositories.

Use the task files to determine completed work, current blockers, checked repo states, validation already run, the Planning Gate state, and the next repository in scenario order. Update `status.md` before and after meaningful work, and update `spec.md`, `validation.md`, and `decisions.md` as facts change.

## Replanning Protocol

Use this protocol when scenario files, task scope, dependency assumptions, or user clarifications invalidate part of an existing task plan. It applies equally when a free task discovers a new affected repository mid-implementation: the expanded repo set and the reason are recorded in `decisions.md`, and the Spec Review Gate must re-approve before the new repos are entered.

1. Set `current step` to `replanning_in_progress`.
2. Identify the affected repositories, dependency edges, key files, checks, and task-file sections.
3. Preserve completed repo records that remain valid.
4. Re-run the Planning Pass Protocol only for affected repositories and affected dependency edges unless the change invalidates the full scenario.
5. Update `tasks/<task>/spec.md` with revised expected changes, compatibility notes, downstream impact, and validation strategy.
6. Update `tasks/<task>/decisions.md` with why partial or full replanning was chosen.
7. Update the per-repo status table and dependency readiness section for any repo whose previous planning, implementation, validation, or output readiness is no longer valid.
8. Set `current step` to `replanning_complete` when the revised plan is ready.
9. Re-run the Spec Review Gate Protocol before editing additional business repository code.

## Interruption Safety Protocol

Task files are the recovery point when context is compacted, the session is interrupted, or the agent must pause.

1. After every planning gate change, spec review decision, repo implementation step, validation result, dependency readiness change, blocker, or user clarification, update the relevant task files immediately.
2. If context may run out, work must stop, or the agent is about to hand off, update `tasks/<task>/status.md` before doing anything else.
3. The interruption update must include:
   - current step
   - per-repo status table
   - dependency readiness state
   - latest gate states
   - active blocker, if any
   - next recommended action
   - Status History entry for the interruption or handoff point
4. Do not rely on conversation history for recovery-critical facts. Record them in `spec.md`, `status.md`, `validation.md`, or `decisions.md` when they become true.

## Completion State Protocol

Set `current step` to `complete` only when all of these are true:

1. The Planning Gate is recorded as complete.
2. The Spec Review Gate is approved or explicitly skipped by the user.
3. Every affected repository is recorded in the per-repo status table as complete or has a documented skip reason.
4. Required checks are recorded in `validation.md` as passed, skipped with reasons, or accepted failures with decisions.
5. Scenario-declared outputs and `depends_on` paths are recorded in the dependency readiness section as ready, unchanged, skipped with reasons, or blocked.
6. Cross-repo contracts, downstream consumption, and completion criteria from the scenario README are addressed in `spec.md`, `validation.md`, or `decisions.md`.
7. Residual risks are recorded in `validation.md`.
8. When setting `current step` to `complete`, append the final transition to Status History.

## Task File Write Rules

Write task files at the time their information becomes true. Do not wait until the end of the scenario to reconstruct progress from memory.

- `spec.md` is written when the task directory is created or selected. It records the scenario, user request, user clarifications, scope, non-goals, assumptions, repository order, execution steps, the cross-repo implementation plan, and key-file-derived implementation notes. Update it after the pre-implementation cross-repo planning pass, after deeper repo-local reading changes the plan, when the user clarifies anything that affects implementation or validation, and when the user changes the request, a scope assumption becomes false, or steps are completed, skipped, blocked, added, or reordered.
- `status.md` is the live task state. Update it before and after meaningful work, including task creation, task resume, branch preparation, preflight, planning gate changes, spec review, replanning, repo entry, repo completion, dependency readiness changes, blockers, skipped instruction files, interruption safety updates, and the final task state. Use only the values from Status Step Vocabulary for `current step`.
- `status.md` must keep `current step`, the per-repo status table, dependency readiness, gate states, and append-only Status History in sync. Do not rely on `current step` to reconstruct completed repositories.
- `validation.md` is written after checks are run, skipped, or fail to run. Record the repo, command, result, important output summary, known failures, and residual risk.
- `decisions.md` is written when the agent makes or discovers a judgment that affects implementation, compatibility, migration, delivery order, or risk. Record why the decision was made, not just what changed.

User clarifications that only describe transient progress belong in `status.md`. User clarifications that affect implementation choices should also be captured in `decisions.md` when they explain why the task changed.

Do not duplicate routine progress in `decisions.md`; put progress in `status.md`. Do not put check output in `status.md`; summarize checks in `validation.md`. Do not treat `spec.md` as a scratchpad for transient notes after execution starts.

## YAML Semantics

Path resolution:

- Absolute paths are used as-is.
- Relative paths are resolved relative to the scenario harness root.
- Paths containing shell-style variables are invalid.

`scenarios/<scenario>/scenario.yaml`:

- `scenario.yaml` is the authoritative execution template for the scenario.
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
- Use the current scenario README structure as follows:
  - `Scope` describes when agents should use the scenario, covered change types, out-of-scope work, and assumptions that must hold before the scenario applies.
  - `Cross-Repo Relationship` explains why the repositories are coordinated, which repo owns the source of truth, how downstream repos consume upstream outputs, what must remain consistent, and which conflicts require user direction.
  - `Scenario-Specific Rules` records invariants and execution constraints such as compatibility requirements, migration or rollout rules, generated-artifact handling, extra validation expectations, and actions agents must not take automatically.
  - `Required Clarifications` lists scenario-level decisions that must be answered before implementation when the user request does not already answer them, why each answer matters, and where to record the confirmed answer in the active task directory.
  - `Risk Areas` highlights common regression risks, data/API/schema/auth/migration/generated-code hazards, user-visible behavior that is easy to miss, and validation gaps that repo checks may not cover.
  - `Completion Criteria` defines how agents know the scenario task is complete, including expected task-file evidence, required checks or documented skip reasons, cross-repo behavior to verify, and residual risks to report.
- If `scenario.yaml` and the scenario README conflict on structural execution, follow `scenario.yaml` unless doing so would be destructive or unsafe.
- If they conflict on business intent, compatibility requirements, or completion criteria, stop and report the conflict before editing repositories.

`repos.yaml` (workspace registry):

- `repos.yaml` lives at the harness root. It is optional for scenario tasks (scenario self-containment is unchanged) and required for free tasks.
- `repos` is a mapping of every repository registered in the workspace. Repo keys are stable workspace-local identifiers; when a repo also appears in a scenario, the same key must be used in both files so cross-checks can compare them.
- `repos.<repo-key>.path` is the local filesystem path for the repository. Resolution follows the same rules as scenario paths: absolute paths are used as-is, relative paths resolve against the harness root, shell-style variables are invalid.
- `repos.<repo-key>.description` is one-sentence context for agents and humans.
- `repos.<repo-key>.instruction_sources` are read in order when entering the repo for a free task. When the list is absent or empty, fall back to the common project files: `README.md`, `CONTRIBUTING.md`, `package.json`, `Makefile`, `pyproject.toml`, `Cargo.toml`, `go.mod`.
- `repos.<repo-key>.key_files` lists workspace-relevant files or directories to inspect first.
- `repos.<repo-key>.checks` are commands to run after repo-local changes in free tasks. When the list is absent or empty, no checks are declared for that repo and the task must record a validation gap in `validation.md`.
- The five intrinsic fields (`path`, `description`, `instruction_sources`, `key_files`, `checks`) may duplicate scenario.yaml entries. `validate-registry` and `validate-scenario` emit warning-level divergence findings (`registry_field_divergence`, `repo_not_in_registry`) when a duplicated repo drifts or a scenario repo is missing from the registry; duplication itself is allowed and never gates execution.
- `repos.<repo-key>` and edge mappings must not declare task-specific dependency values (the same ban list as `scenario.yaml`). Ask a human to confirm those values for the active task and record them in task files.
- `edges` is the baseline dependency graph: a list of mappings with `from`, `to`, and `evidence`.
  - `from` depends on / consumes `to`. An edge asserts only that this dependency relation exists; direction encodes consumption, never an ordering obligation ("from must change after to" is not a thing).
  - `(from, to)` is the natural key: duplicate pairs are validation errors, edges carry no id. `evidence` is a non-empty free-form string citing how the dependency is observable (manifest line, import, generated-code source); its text is never parsed for semantics.
  - Edge endpoints must reference keys declared under `repos`.
  - The graph has no ordering authority and gates nothing. Execution order and dependency direction come solely from scenario.yaml `order` + `depends_on` (scenario tasks) or the task's own declared topology (free tasks). No command may refuse to run or reorder work because of edge content; the graph's only use is seeding Planning Pass candidate neighborhoods.
  - Purpose-specific dependencies (the `reason`-bearing `depends_on` of a scenario) stay in scenario.yaml. The baseline graph holds only purpose-independent relations that recur across scenarios.
  - The graph tolerates drift: an out-of-date graph at worst mis-seeds the candidate set, which the Planning Pass corrects by verifying repo reality. Missing edges are the dangerous direction, so curation prefers extra edges over missing ones, and the protocol duties (workspace-level reverse lookup in the Free Task Protocol) all aim at the missing-edge side.

## Delivery Defaults

- Start in conservative mode: modify code and run checks, but do not commit automatically.
- Use one branch per repository when branch preparation is requested.
- Branch names should match across repositories where practical, for example `scenario/<task-id>`.
- If unrelated local changes exist, do not overwrite them. Record the state and ask for direction only if they block the task.
- Unrelated local changes block the task when they touch files that must be edited, prevent branch preparation or checks, make expected diffs ambiguous, or create a realistic risk that implementation would overwrite or depend on user work.
