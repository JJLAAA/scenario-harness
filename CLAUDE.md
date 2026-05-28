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

1. Identify the scenario using the Scenario Identification Protocol.
2. Read `scenarios/<scenario>/scenario.yaml`.
3. Read `scenarios/<scenario>/README.md`.
4. Run `bin/scenario-harness validate-scenario <scenario>` from the harness root before creating a new task directory.
   - If it reports errors, stop before editing business repositories.
   - If resuming an existing task, record `current step: scenario_invalid` and the validation errors in `tasks/<task>/status.md`.
   - If creating a new task, do not create the task directory until the scenario validates.
   - Use `--json` when machine-readable output is useful.
5. Create or locate a task directory under `tasks/`, then set `current step` to `scenario_validated`.
6. Inspect git status for all affected repositories. Prefer `bin/scenario-harness preflight <scenario> --task <task-id>`, then set `current step` to `preflight_complete` if it succeeds.
7. Complete the Planning Pass Protocol for all affected repositories.
8. Confirm the Planning Gate is recorded as complete in `tasks/<task>/status.md`.
   - Do not edit business repository code before this gate is complete.
9. Complete the Spec Review Gate Protocol.
   - Do not edit business repository code before this gate is approved or explicitly skipped by the user.
10. Modify repositories in scenario-defined order using the Implementation Repo Entry Protocol.
11. Run repo-local checks and follow the Check Failure Protocol for any failure.
12. Mark the task complete only when the Completion State Protocol is satisfied.

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

## Scenario Identification Protocol

1. If the user explicitly names a scenario, use that scenario.
2. If the user asks to resume, continue, or finish existing work without naming a scenario, inspect `tasks/` and scenario names to find matching incomplete tasks.
3. If the user does not name a scenario, inspect `scenarios/*/scenario.yaml` and `scenarios/*/README.md` only enough to find plausible matches.
4. If exactly one scenario clearly matches the request, select it and record the selection reason in `tasks/<task>/spec.md` when the task directory exists.
5. If no scenario or multiple scenarios plausibly match, ask the user to choose before creating a task directory, entering business repositories, or editing files.

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

Before editing code in any business repository, complete a lightweight cross-repo planning pass for all affected repositories in scenario-defined order.

1. Set `current step` to `planning_in_progress` in `tasks/<task>/status.md`.
2. For each affected repository:
   - resolve the repo path from `scenarios/<scenario>/scenario.yaml`
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
5. Update `tasks/<task>/decisions.md` for planning decisions that affect compatibility, migration, delivery order, or risk.
6. If the planning pass reveals missing task-specific dependency values, branch mismatches, conflicting repo-local instructions, or unresolved design choices that would make implementation risky, set `current step` to `planning_blocked`, record the blocker, and ask for direction.
7. When the planning pass is complete and unblocked, record a Planning Gate in `tasks/<task>/status.md`:
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

## Planning Resume Protocol

Use this protocol when the user responds to a `planning_blocked` state.

1. Record the user clarification in `tasks/<task>/spec.md`.
2. If the clarification affects compatibility, migration, delivery order, validation, or risk, also record the decision in `tasks/<task>/decisions.md`.
3. Set `current step` to `planning_in_progress` and append the transition from `planning_blocked` to Status History.
4. Re-run the Planning Pass Protocol only for the blocked repositories, dependency edges, and task-file sections unless the clarification invalidates the full plan.
5. Update the per-repo status table, dependency readiness section, and Planning Gate fields that were affected by the blocker.
6. If the blocker is resolved and no new planning blocker exists, record `current step: planning_complete`.
7. Run the Spec Review Gate Protocol before editing business repository code.

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
3. Wait for user approval before implementation unless review is explicitly skipped by the user.
   - The skip must come from the current conversation or from task files that existed before the current agent run.
   - Agent-written task updates in the current run cannot authorize skipping review.
   - If the authorization source is ambiguous, wait for user approval.
4. Record the approval, requested changes, or explicit user-authorized skip in `tasks/<task>/status.md`.
5. If the user changes scope or design during review, update `tasks/<task>/spec.md` and `tasks/<task>/decisions.md` before implementation.
6. Set `current step` to `spec_review_approved` only after approval is recorded or the explicit skip is recorded.

## Implementation Repo Entry Protocol

Run this protocol for each repository during the implementation pass, even if the same repo was already inspected during planning.

1. Set `current step` to `implementing:<repo-key>` in `tasks/<task>/status.md`.
2. Resolve the repo path from `scenarios/<scenario>/scenario.yaml`.
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
8. Reread or deepen scenario-defined `repos.<repo>.key_files` as needed for implementation.
9. Add any new repo-local implementation notes, impact areas, risks, and validation focus to `tasks/<task>/spec.md`.
10. Implement the repo-local change according to the enriched task spec.
11. If implementation requires a material deviation from the enriched spec, record the reason in `tasks/<task>/decisions.md` and update `tasks/<task>/spec.md` before continuing.
12. Set `current step` to `validating:<repo-key>` before running checks.
13. Run repo-defined checks.
14. Record check output summary in `tasks/<task>/validation.md`.
15. If checks pass, update the per-repo status table and record scenario-declared outputs for this repository as ready, unchanged, skipped, or blocked in the dependency readiness section.
16. If checks pass, set `current step` to `repo_complete:<repo-key>`.
17. Do not commit unless the user or scenario explicitly requests commits.

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

Use this protocol when scenario files, task scope, dependency assumptions, or user clarifications invalidate part of an existing task plan.

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

## Delivery Defaults

- Start in conservative mode: modify code and run checks, but do not commit automatically.
- Use one branch per repository when branch preparation is requested.
- Branch names should match across repositories where practical, for example `scenario/<task-id>`.
- If unrelated local changes exist, do not overwrite them. Record the state and ask for direction only if they block the task.
- Unrelated local changes block the task when they touch files that must be edited, prevent branch preparation or checks, make expected diffs ambiguous, or create a realistic risk that implementation would overwrite or depend on user work.
