# Scenario README

This file records scenario-specific guidance that helps agents execute existing tasks safely.

`scenario.yaml` is authoritative for repository paths, execution order, instruction sources, key files, checks, outputs, and dependency links. This README should explain the scenario intent, cross-repo semantics, required clarifications, and completion expectations that do not fit cleanly in YAML.

## Scope

Describe when agents should use this scenario and what kind of task it covers.

Include:

- covered change types
- explicitly out-of-scope work
- assumptions that must hold before the scenario can be used

## Cross-Repo Relationship

Explain why these repositories are coordinated.

Include:

- which repository owns the source of truth, if any
- how downstream repositories consume upstream outputs
- what must remain consistent across repositories
- what conflicts should cause the agent to stop and ask for direction

## Scenario-Specific Rules

Record invariants and execution constraints that apply to this scenario.

Include:

- compatibility requirements
- migration or rollout constraints
- generated-artifact rules
- validation expectations beyond repo-local checks
- actions agents must not take automatically

## Required Clarifications

List decisions that must be answered before implementation when the user request does not already answer them.

Include only scenario-level questions here. Repo-local implementation questions should live in repo-local instructions or key files.

For each clarification, describe:

- what must be clarified
- why it matters
- where the confirmed answer should be recorded in the active task directory

## Risk Areas

Describe the parts of this scenario where agents should pay extra attention.

Include:

- common regression risks
- data, API, schema, auth, migration, or generated-code hazards
- user-visible behavior that is easy to miss
- validation gaps that checks may not cover

## Completion Criteria

Describe how agents know a task using this scenario is complete.

Include:

- expected task-file evidence in `spec.md`, `status.md`, `decisions.md`, and `validation.md`
- required repo-local checks or documented skip reasons
- cross-repo behavior that must be verified
- residual risks that must be reported before handoff
