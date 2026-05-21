# Task Spec

## Scenario

<!-- Scenario directory name under scenarios/. -->

## User Request

<!-- Copy or summarize the user's request. -->

## Scope

<!-- Repositories, files, workflows, or behavior expected to change. -->

## Non-Goals

<!-- Explicitly excluded work. -->

## Assumptions

<!-- Facts assumed at task start. Update if they change. -->

## Scenario Order

1. `contract-repo`
2. `consumer-repo`
3. `worker-repo`

## Steps

| Step | Repo | Action | Status |
| --- | --- | --- | --- |
| 1 | contract-repo | Inspect status, verify branch, and read instructions | pending |
| 2 | contract-repo | Implement source-of-truth change | pending |
| 3 | contract-repo | Run repo-local checks | pending |
| 4 | consumer-repo | Inspect status, verify branch, and read instructions | pending |
| 5 | consumer-repo | Synchronize downstream usage | pending |
| 6 | consumer-repo | Run repo-local checks | pending |
| 7 | worker-repo | Inspect status, verify branch, and read instructions | pending |
| 8 | worker-repo | Synchronize event or job handling | pending |
| 9 | worker-repo | Run repo-local checks | pending |
| 10 | all | Update validation and task status | pending |

## Open Questions

None.
