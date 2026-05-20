# PR Plan

## Order

1. `contract-repo`
   - Reason: source of truth for the contract.
   - Must merge before downstream repositories when the change is not backward compatible.

2. `consumer-repo`
   - Depends on `contract-repo` contract and generated artifact update.

3. `worker-repo`
   - Depends on `contract-repo` event, job, or payload contract update.

## Pull Requests

| Repo | Branch | PR | Depends On |
| --- | --- | --- | --- |
| contract-repo | TBD | TBD | none |
| consumer-repo | TBD | TBD | contract-repo |
| worker-repo | TBD | TBD | contract-repo |

## Suggested Commit Messages

| Repo | Message |
| --- | --- |
| contract-repo | TBD |
| consumer-repo | TBD |
| worker-repo | TBD |

## Migration Notes

<!-- Required for breaking changes or rollout sequencing. -->
