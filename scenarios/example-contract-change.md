# Example Contract Change Scenario

## Purpose

Use this scenario when a shared contract, schema, generated client, or source-of-truth domain model changes and downstream repositories must be synchronized.

## Repository Roles

- `contract-repo` is the source of truth for the shared contract.
- `consumer-repo` consumes the contract through API calls, generated clients, or shared types.
- `worker-repo` consumes related events, jobs, or background workflow payloads.

## Required Order

1. Update `contract-repo` contract and domain model.
2. Run `contract-repo` checks.
3. Generate or export downstream artifacts if the repo-local instructions require it.
4. Update `consumer-repo` usage.
5. Update `worker-repo` event or job handling.
6. Run cross-repo integration checks.

## Cross-Repo Invariants

- Contract version and generated artifacts must match.
- Shared identifiers, event names, endpoint names, and payload fields must stay consistent across repositories.
- Breaking changes require explicit migration notes in the task decisions or PR plan.
- Generated files must not be edited manually unless repo-local instructions allow it.

## Completion Criteria

- All affected repo git states are inspected and recorded.
- Repo-local instruction sources were read or missing files were documented.
- Manifest-defined checks passed or failures are documented with next steps.
- Cross-repo integration checks passed or failures are documented with next steps.
- PR order and dependencies are recorded.
