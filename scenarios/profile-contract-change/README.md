# Profile Contract Change Scenario

## Purpose

Use this scenario when the Profile API response shape changes and downstream profile consumers must stay synchronized.

## Repository Roles

- `profile-api` is the source of truth for the profile contract and example response.
- `profile-web` renders profile fields in the UI layer.
- `notification-worker` uses profile fields in async notification templates.

## Required Order

1. Update `profile-api` contract, implementation, and tests.
2. Run `profile-api` checks.
3. Update `profile-web` rendering and tests.
4. Run `profile-web` checks.
5. Update `notification-worker` templates and tests.
6. Run `notification-worker` checks.

## Cross-Repo Invariants

- Required profile fields in `openapi.yaml` must match fields assumed by consumers.
- Downstream consumers should handle any newly added optional field with a fallback unless the contract marks it required.
- Tests should show the intended behavior for both normal and fallback payloads when applicable.

## Completion Criteria

- All affected repo git states are inspected and recorded.
- Each repo is on `scenario/profile-display-name` before editing.
- Repo-local instruction sources are read or missing files are documented.
- Repo-defined checks pass or failures are documented with next steps.
