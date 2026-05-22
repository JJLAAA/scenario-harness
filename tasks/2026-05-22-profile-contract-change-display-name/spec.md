# Task Spec

## Scenario

`profile-contract-change`

Update the Profile API contract and synchronize profile consumers.

## User Request

在 profile-api 的 Profile contract 中新增可选字段 displayName；getProfile() 返回该字段；profile-web 和 notification-worker 优先使用 displayName，缺失时回退 email；补正常和 fallback 测试；运行场景 checks；更新 task 记录；不提交 commit。

## Scope

- `profile-api`: Owns the Profile API contract and example implementation.
- `profile-web`: Renders profile data returned by the Profile API.
- `notification-worker`: Builds notification copy from profile payloads.

## Non-Goals

- Do not commit unless explicitly requested.
- Do not edit repositories outside the scenario order.
- Do not overwrite unrelated local changes.

## Assumptions

- The scenario configuration is authoritative for repository order and branch gates.
- Repository-local instructions remain authoritative inside each business repository.

## Scenario Order

1. `profile-api`
2. `profile-web`
3. `notification-worker`

## Repository Context

### `profile-api`

- Path: `/Users/leo/Projects/scenario-harness-test/profile-api`
- Expected branch: `scenario/profile-display-name`
- Instruction sources:
- `AGENTS.md`
- `README.md`
- Key files:
- `openapi.yaml`
- `src/profile.js`
- Checks:
- `npm run typecheck`
- `npm test`
### `profile-web`

- Path: `/Users/leo/Projects/scenario-harness-test/profile-web`
- Expected branch: `scenario/profile-display-name`
- Instruction sources:
- `AGENTS.md`
- `README.md`
- Key files:
- `src/render-profile.js`
- Checks:
- `npm run typecheck`
- `npm test`
### `notification-worker`

- Path: `/Users/leo/Projects/scenario-harness-test/notification-worker`
- Expected branch: `scenario/profile-display-name`
- Instruction sources:
- `AGENTS.md`
- `README.md`
- Key files:
- `src/email-template.js`
- Checks:
- `npm run typecheck`
- `npm test`

## Steps

| Step | Repo | Action | Status |
| --- | --- | --- | --- |
| 1 | profile-api | Inspect status, verify branch, read instructions, and inspect key files | pending |
| 2 | profile-api | Implement repo-local change | pending |
| 3 | profile-api | Run repo-local checks | pending |
| 4 | profile-web | Inspect status, verify branch, read instructions, and inspect key files | pending |
| 5 | profile-web | Implement repo-local change | pending |
| 6 | profile-web | Run repo-local checks | pending |
| 7 | notification-worker | Inspect status, verify branch, read instructions, and inspect key files | pending |
| 8 | notification-worker | Implement repo-local change | pending |
| 9 | notification-worker | Run repo-local checks | pending |
| 10 | all | Update validation and final task status | pending |

## Open Questions

None.
