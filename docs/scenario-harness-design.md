# Scenario-Oriented Multi-Repo Harness 设计方案

> **文档摘要**
>
> 本文设计一个面向特定业务场景的 multi-repo delivery harness。顶层 harness 不依赖 Trellis，也不要求多个业务仓库位于同一个 monorepo 或 meta repo 下。它负责跨仓库任务编排、执行顺序、状态记录和交付门禁；各业务仓库只需要提供 repo-local instructions，可以来自 Trellis、AGENTS.md、CLAUDE.md、CONTRIBUTING.md、README、Makefile、package scripts 或其他本地约定。

## 目标

这个 harness 的目标是让 AI agent 能稳定交付一类总是横跨多个独立仓库的任务。

它解决的问题不是“如何管理多个 Git repo”，而是“如何把某个业务场景的跨仓库交付流程变成可重复、可检查、可恢复的执行协议”。

不改变现有 repo结构，用一个轻量的控制层把跨 repo的业务语义（顺序、角色、验证）显式编码出来，让 agent有协议可以遵循

典型场景：

- 先修改 contract/source-of-truth repo，再修改 downstream consumer repo。
- 某个 API schema 变更必须同步 worker、frontend、SDK、test fixtures。
- 某个产品流程变更总是横跨 backend、web、mobile、infra。
- 多个 repo 没有共同父 meta repo，也不适合强行改造成 monorepo。

## 非目标

这个 harness 不承担以下职责：

- 不替代 Git repo 边界。
- 不替代各 repo 的 CI/CD。
- 不要求顶层使用 Trellis。
- 不要求每个业务 repo 使用 Trellis。
- 不强制自动 commit 或自动创建 PR。
- 不把多个 repo 复制、挂载或改造成 meta repo。

## 架构定位

推荐的三层模型：

```text
Scenario Harness
  负责跨 repo 编排：
  - 场景识别
  - repo 清单
  - repo 角色
  - 修改顺序
  - 跨 repo contract
  - 任务状态
  - 验证与交付门禁

Repo-Local Instructions
  负责单 repo 约束：
  - 代码风格
  - 架构约定
  - 生成代码规则
  - 测试命令
  - 提交和 PR 规则

Git / CI / PR
  负责 repo-local 版本管理和远端验证：
  - branch
  - commit
  - pull request
  - CI checks
  - review
```

Trellis 在这个模型里是可选的 repo-local instruction provider。某个 repo 可以使用 Trellis；另一个 repo 可以只使用 AGENTS.md；第三个 repo 可以只依赖 README、CONTRIBUTING 和 Makefile。

顶层 harness 只关心三个问题：

1. 当前场景涉及哪些 repo？
2. 这些 repo 应该按什么顺序修改和验证？
3. 进入每个 repo 后，agent 应该读取哪些本地规则并运行哪些检查？

## 推荐目录结构

```text
scenario-harness/
  AGENTS.md
  README.md

  scenarios/
    billing-migration.md
    onboarding-flow.md
    entitlement-change.md

  manifests/
    repos.yaml
    scenarios.yaml

  tasks/
    2026-05-20-billing-migration/
      brief.md
      plan.md
      status.md
      decisions.md
      validation.md
      prs.md

  scripts/
    repo-status
    prepare-branches
    run-repo-checks
    run-integration-checks
    collect-diff-summary
    create-prs

  templates/
    task-brief.md
    task-status.md
    validation-report.md
    pr-plan.md
```

这个目录可以是一个独立 git repo，也可以只是本地目录。推荐使用 git repo，因为 scenario 文档、manifest、任务记录和交付规范都值得版本化。

## Placement model

Harness 可以放在两类位置：

```text
Standalone harness

~/work/
  scenario-harness/
  repo-a/
  repo-b/
  repo-c/
```

```text
Hosted harness

repo-a/
  scenario-harness/
  src/

repo-b/
repo-c/
```

这两种位置不会改变核心模型。核心模型仍然是：

```text
scenario -> affected repos -> execution order -> repo-local instructions -> checks -> delivery record
```

它们改变的是路径解析、ownership、默认上下文和风险边界。

### Standalone harness

Standalone harness 是独立控制层，不属于任何业务 repo。

适合：

- 多个 repo 没有明确主从关系。
- 一个 harness 要支持多个业务场景。
- 跨 repo 任务由平台、交付或架构团队维护。
- 不希望任一业务 repo 的规则天然高于其他 repo。

特点：

- `repos.yaml` 中的相对路径默认相对 `HARNESS_ROOT`。
- 所有 repo 都必须在 manifest 中显式声明。
- 没有默认 source-of-truth repo；每个 scenario 必须显式声明执行顺序和 repo 角色。
- task 记录、scenario 文档、manifest 都归 harness 自己管理。

### Hosted harness

Hosted harness 放在一个主要驱动 repo 内。这个 repo 通常是 contract、schema、domain model 或业务流程的 source of truth。

适合：

- 所有跨 repo 任务都从一个主 repo 的 contract 或 domain model 开始。
- 下游 repo 明确依赖主 repo 的输出。
- harness 主要由主 repo 团队维护。
- 用户通常从主 repo 启动 agent。

特点：

- manifest 应显式声明 `host_repo`。
- host repo 可以通过 `$HOST_REPO_ROOT` 引用。
- 外部 repo 仍然通过 manifest 显式声明，不能隐式继承 host repo 的规则。
- task 记录会跟随 host repo 版本化。

Hosted harness 的主要风险是 agent 把 host repo 的规则误套到其他 repo。顶层 AGENTS.md 必须明确：进入每个 repo 后都要重新读取该 repo 的 repo-local instructions。

### Path resolution

不要让 agent 靠猜测解析路径。manifest 应声明 placement，并使用显式变量。

推荐变量：

| Variable | Meaning |
| --- | --- |
| `$HARNESS_ROOT` | harness 目录根路径。 |
| `$HOST_REPO_ROOT` | hosted 模式下的宿主 repo 根路径。 |
| `$WORKSPACE_ROOT` | 可选的共同工作区根路径，例如 `~/work`。 |

路径解析规则：

1. 绝对路径直接使用。
2. 以 `$HARNESS_ROOT` 开头的路径相对 harness 根解析。
3. 以 `$HOST_REPO_ROOT` 开头的路径仅在 hosted 模式下有效。
4. 以 `$WORKSPACE_ROOT` 开头的路径需要 manifest 显式配置 workspace root。
5. 普通相对路径默认相对 `$HARNESS_ROOT`，但生产用 manifest 推荐使用变量前缀。

## 顶层 AGENTS.md

顶层 AGENTS.md 是 harness 的最高优先级执行协议。它应该约束 agent 不要把当前目录误认为业务 repo，也不要在未读取 repo-local instructions 的情况下修改业务代码。

示例：

```md
# Scenario Harness Instructions

This workspace coordinates multi-repo delivery tasks.

## Core Rules

- Do not assume the current directory is a business repo.
- Business code lives in external repositories listed in `manifests/repos.yaml`.
- Respect the placement model declared in `manifests/repos.yaml`.
- If this is a hosted harness, do not apply host repo rules to downstream repos.
- Before editing any business repo, read its repo-local instructions.
- Repo-local instructions may come from Trellis, AGENTS.md, CLAUDE.md, README, CONTRIBUTING, Makefile, package scripts, or manifest-defined files.
- Treat each repo's git state independently.
- Never mix commits across repos.
- Never run destructive commands unless the user explicitly requested them.
- Record cross-repo progress in the active task directory under `tasks/`.

## Execution Protocol

1. Identify the scenario.
2. Read the scenario document from `scenarios/`.
3. Read `manifests/repos.yaml` and `manifests/scenarios.yaml`.
4. Create or locate a task directory under `tasks/`.
5. Inspect git status for all affected repos.
6. Modify repos in scenario-defined order.
7. For each repo:
   - enter the repo path
   - read local instructions in the configured order
   - inspect affected files
   - implement the repo-local change
   - run repo-local checks
   - record the result
8. Run cross-repo checks.
9. Produce a PR plan.
10. Update task status.
```

## Repo manifest

`manifests/repos.yaml` describes the physical repositories and their local execution contracts.

Use explicit path variables or absolute paths by default. Plain relative paths can work, but they become fragile when repos do not share a parent directory.

Standalone example:

```yaml
harness:
  placement: standalone
  root: $HARNESS_ROOT
  workspace_root: /Users/leo/work/repos

repos:
  repo-a:
    path: $WORKSPACE_ROOT/repo-a
    role: contract-source
    description: Owns API schema and domain model.
    default_branch: main
    branch_prefix: scenario
    instruction_sources:
      - AGENTS.md
      - .trellis/workflow.md
      - .trellis/spec/backend/index.md
      - CONTRIBUTING.md
    checks:
      - npm run lint
      - npm run typecheck
      - npm test
    key_files:
      - src/contracts/
      - openapi.yaml

  repo-b:
    path: $WORKSPACE_ROOT/repo-b
    role: downstream-consumer
    description: Consumes generated client from repo-a.
    default_branch: main
    branch_prefix: scenario
    instruction_sources:
      - AGENTS.md
      - CLAUDE.md
      - CONTRIBUTING.md
      - README.md
    checks:
      - pnpm typecheck
      - pnpm test
    key_files:
      - src/api/
      - src/generated/

  repo-c:
    path: $WORKSPACE_ROOT/repo-c
    role: async-worker
    description: Processes events emitted by repo-a.
    default_branch: main
    instruction_sources:
      - README.md
      - Makefile
    checks:
      - make test
```

Hosted example:

```yaml
harness:
  placement: hosted
  root: $HARNESS_ROOT
  host_repo: repo-a

repos:
  repo-a:
    path: $HOST_REPO_ROOT
    role: contract-source
    description: Owns API schema and domain model.
    default_branch: main
    branch_prefix: scenario
    instruction_sources:
      - AGENTS.md
      - .trellis/workflow.md
      - .trellis/spec/backend/index.md
      - CONTRIBUTING.md
    checks:
      - npm run lint
      - npm run typecheck
      - npm test
    key_files:
      - src/contracts/
      - openapi.yaml

  repo-b:
    path: $HOST_REPO_ROOT/../repo-b
    role: downstream-consumer
    description: Consumes generated client from repo-a.
    default_branch: main
    branch_prefix: scenario
    instruction_sources:
      - AGENTS.md
      - CLAUDE.md
      - CONTRIBUTING.md
      - README.md
    checks:
      - pnpm typecheck
      - pnpm test
    key_files:
      - src/api/
      - src/generated/

  repo-c:
    path: $HOST_REPO_ROOT/../repo-c
    role: async-worker
    description: Processes events emitted by repo-a.
    default_branch: main
    instruction_sources:
      - README.md
      - Makefile
    checks:
      - make test
```

### Repo manifest 字段

| Field | Purpose |
| --- | --- |
| `harness.placement` | `standalone` 或 `hosted`。决定路径解析和 ownership 语义。 |
| `harness.root` | harness 根路径，通常是 `$HARNESS_ROOT`。 |
| `harness.host_repo` | hosted 模式下的主 repo 名称。 |
| `harness.workspace_root` | standalone 模式下可选的共同 workspace 根路径。 |
| `path` | 本地 repo 绝对路径。 |
| `role` | repo 在场景里的职责，例如 `contract-source`、`downstream-consumer`、`async-worker`。 |
| `description` | 给 agent 的一句话上下文。 |
| `default_branch` | 准备分支和 PR 时使用的默认 base branch。 |
| `branch_prefix` | 生成 task branch 时使用的前缀。 |
| `instruction_sources` | 进入 repo 后需要读取的本地规则文件，按顺序读取；不存在的文件跳过并记录。 |
| `checks` | repo-local 验证命令。 |
| `key_files` | 该 repo 中与场景高相关的入口文件或目录。 |

不要把 Trellis 写成必填字段。更稳的方式是显式列出 `instruction_sources`。如果某个 repo 使用 Trellis，就把 `.trellis/workflow.md` 和相关 `.trellis/spec/.../index.md` 放进清单；如果没有 Trellis，就列出其他规则来源。

同样，不要把 host repo 写成隐式 source-of-truth。即使在 hosted 模式下，也应该通过 repo `role` 和 scenario `order` 明确表达 source-of-truth 和 downstream 关系。

## Scenario manifest

`manifests/scenarios.yaml` 把场景映射到 repo、执行顺序和跨 repo 检查。

```yaml
scenarios:
  billing-migration:
    description: Change billing contract and update all consumers.
    repos:
      - repo-a
      - repo-b
      - repo-c
    order:
      - repo-a
      - repo-b
      - repo-c
    integration_checks:
      - scripts/run-integration-checks billing-migration
    requires_pr_order: true

  onboarding-flow:
    description: Update user onboarding across API, web, and worker.
    repos:
      - repo-a
      - repo-b
    order:
      - repo-a
      - repo-b
    integration_checks:
      - scripts/run-integration-checks onboarding-flow
```

这个文件的价值是防止 agent 每次重新猜：

- 哪些 repo 相关。
- 哪个 repo 是 source of truth。
- 哪些 downstream repo 必须跟着改。
- 跨 repo 检查应该在什么时候运行。

## Scenario 文档

每个 `scenarios/<name>.md` 是领域级 SOP。它解释为什么按这个顺序改、关键契约是什么、常见失败点是什么。

示例：

```md
# Billing Migration Scenario

## Purpose

Billing migration changes must preserve API contract compatibility while updating all downstream consumers.

## Repository Roles

- repo-a is the source of truth for billing contracts.
- repo-b consumes repo-a's generated client.
- repo-c consumes billing events emitted by repo-a.

## Required Order

1. Update repo-a contract and domain model.
2. Run repo-a checks.
3. Regenerate or export client artifacts.
4. Update repo-b consumer calls.
5. Update repo-c event handling.
6. Run cross-repo integration checks.

## Repo-A Instructions

Before editing:
- Read instruction sources from `manifests/repos.yaml`.
- Confirm contract changes are backward compatible unless the task explicitly says otherwise.

Required checks:
- npm run lint
- npm run typecheck
- npm test

## Repo-B Instructions

Before editing:
- Read instruction sources from `manifests/repos.yaml`.
- Do not manually edit generated client files unless repo-local instructions allow it.

## Cross-Repo Invariants

- API schema version must match generated client version.
- Event names must remain consistent across repo-a and repo-c.
- Breaking changes require explicit migration notes.

## Completion Criteria

- All affected repos have clean or intentionally documented git state.
- Repo-local checks passed or failures are documented.
- Integration checks passed.
- PR order is documented.
```

## Task directory

顶层不用 Trellis 也应该保留轻量任务记录。否则跨 repo 任务很容易在 session 中断后丢失上下文。

```text
tasks/2026-05-20-billing-migration/
  brief.md
  plan.md
  status.md
  decisions.md
  validation.md
  prs.md
```

文件职责：

| File | Purpose |
| --- | --- |
| `brief.md` | 用户需求、范围、非目标。 |
| `plan.md` | repo 修改顺序和具体步骤。 |
| `status.md` | 当前进度、分支、阻塞点。 |
| `decisions.md` | 重要技术决策和原因。 |
| `validation.md` | 每个 repo 的检查结果和跨 repo 验证结果。 |
| `prs.md` | commit、PR 链接、合并顺序、依赖关系。 |

`status.md` 示例：

```md
# Status

Scenario: billing-migration

## Repos

| Repo | Status | Branch | Checks |
| --- | --- | --- | --- |
| repo-a | implemented | scenario/billing-migration | passed |
| repo-b | in progress | scenario/billing-migration | pending |
| repo-c | not started | - | pending |

## Current Step

Update repo-b consumer calls after repo-a contract change.

## Blockers

None.
```

## Repo entry protocol

顶层 harness 必须规定固定的 repo-entry protocol。不要依赖 agent 自发“知道该读什么”。

```text
For each repo:
1. Resolve the repo path from `manifests/repos.yaml` using the declared placement rules.
2. Run git status in that repo.
3. Read each configured `instruction_sources` entry in order.
   - If the file exists, read it.
   - If the file does not exist, skip it and record the skip.
4. If no instruction source exists, inspect common project files:
   - README.md
   - CONTRIBUTING.md
   - package.json
   - Makefile
   - pyproject.toml
   - Cargo.toml
   - go.mod
5. Inspect scenario-defined `key_files`.
6. Implement the repo-local change.
7. Run manifest-defined checks.
8. Record check output summary in `tasks/<task>/validation.md`.
9. Do not commit unless the user or scenario explicitly requests commits.
```

This protocol makes Trellis optional. If a repo has `.trellis/`, the manifest can point to it. If it does not, the repo can still participate through other instruction sources and check commands.

In hosted mode, this protocol applies to the host repo too. The host repo is not exempt from repo-local instruction loading; it is just one of the repos listed in the scenario.

## Branch strategy

Use one branch per repo. The branch names can match across repos:

```text
repo-a: scenario/billing-migration
repo-b: scenario/billing-migration
repo-c: scenario/billing-migration
```

For better traceability, include the task date or task id:

```text
scenario/2026-05-20-billing-migration
```

Before creating or switching branches, the harness should check:

- Current branch.
- Dirty state.
- Untracked files.
- Whether target branch already exists.
- Whether the repo has local changes unrelated to the task.

If unrelated local changes exist, the agent should not overwrite them. It should record the state and ask for direction if the changes block the task.

## Commit and PR strategy

Start with a conservative mode:

```text
Agent modifies code and runs checks, but does not commit automatically.
At the end, agent reports each repo's diff summary and suggested commit message.
```

After the workflow is stable, enable explicit auto-delivery mode:

```text
Agent creates one commit per repo.
Top-level task records commit hashes.
PR creation script opens PRs in the scenario-defined order.
```

`prs.md` should record dependencies:

```md
# PR Plan

## Order

1. repo-a
   - Reason: source of truth for API contract
   - Must merge before repo-b and repo-c

2. repo-b
   - Depends on repo-a contract/client update

3. repo-c
   - Depends on repo-a event contract update

## PRs

| Repo | Branch | PR | Depends On |
| --- | --- | --- | --- |
| repo-a | scenario/billing-migration | TBD | none |
| repo-b | scenario/billing-migration | TBD | repo-a |
| repo-c | scenario/billing-migration | TBD | repo-a |
```

## Script boundaries

Scripts should handle mechanical, low-judgment operations. Business judgment belongs in scenario docs and agent reasoning.

Recommended first scripts:

```text
scripts/repo-status
  Output branch, dirty state, and recent commits for affected repos.

scripts/prepare-branches
  Create or switch branches for affected repos after checking dirty state.

scripts/run-repo-checks
  Run checks listed in `manifests/repos.yaml` for one repo or all affected repos.

scripts/run-integration-checks
  Run scenario-specific cross-repo smoke tests.

scripts/collect-diff-summary
  Summarize `git diff --stat` and changed files for each repo.
```

Avoid putting complex business decisions into scripts too early. Once the scenario stabilizes, migrate repeated mechanical steps into scripts.

## Quality gates

Use three levels of completion criteria.

### Repo-local gate

- Repo git status has been inspected.
- Repo-local instructions have been read or missing files have been documented.
- Scenario-relevant files have been inspected.
- Manifest-defined checks have been run.
- Failures are fixed or documented.

### Cross-repo gate

- Source-of-truth repo changed first.
- Downstream repos are synchronized with source changes.
- Generated artifacts are updated where required.
- Shared contract identifiers match across repos.
- Integration checks pass or failures are documented with next steps.

### Delivery gate

- Each repo's diff scope is clear.
- Branch names are recorded.
- Commit plan or commit hashes are recorded.
- PR order and dependencies are recorded.
- Remaining risks and follow-up tasks are documented.

## MVP rollout

Start with documents before scripts:

```text
scenario-harness/
  AGENTS.md
  manifests/repos.yaml
  manifests/scenarios.yaml
  scenarios/<scenario>.md
  tasks/<task-id>/
    brief.md
    status.md
    validation.md
    prs.md
```

Manual execution flow:

1. Start the agent in the harness directory. In standalone mode this is the harness repo; in hosted mode this is usually `<host-repo>/scenario-harness/`.
2. Tell it the scenario and task directory.
3. Agent reads `AGENTS.md`, manifests, placement settings, and scenario docs.
4. Agent resolves repo paths and enters repos in scenario order.
5. Agent reads repo-local instructions from `instruction_sources`.
6. Agent modifies and checks each repo.
7. Agent updates task status and validation files.

## Mature version

After several successful manual runs, add a small CLI or script suite:

```bash
scenario prepare billing-migration --task 2026-05-20-billing
scenario status 2026-05-20-billing
scenario check 2026-05-20-billing
scenario summary 2026-05-20-billing
scenario pr 2026-05-20-billing
```

At that point, consider adding:

- Manifest schema validation.
- Repo path existence checks.
- Instruction source existence reports.
- Branch preparation.
- Check execution with structured output.
- PR dependency graph generation.
- Task template generation.

## Design tradeoffs

### Why not top-level Trellis?

Top-level Trellis is useful when you want Trellis task lifecycle, spec injection, journals, and finish-work behavior at the orchestration layer.

For a narrow scenario harness, a custom AGENTS.md plus manifests can be simpler:

- Less machinery.
- Clearer separation between scenario orchestration and repo-local development.
- No need to model multi-repo tasks through a single `package` field.
- Easier to use with repos that do not have Trellis.

### Why keep repo-local instructions flexible?

Requiring Trellis in every repo raises adoption cost. The harness only needs a stable way to answer:

- What rules apply inside this repo?
- What files are relevant?
- What checks prove this repo is healthy?

Those answers can come from Trellis, AGENTS.md, CLAUDE.md, CONTRIBUTING.md, README, Makefile, package scripts, or explicit manifest fields.

### Why not a meta repo?

A meta repo solves filesystem grouping, not delivery semantics. It does not automatically teach the agent:

- Which repo is source of truth.
- Which repo depends on generated artifacts.
- Which PR must merge first.
- Which integration check proves the scenario works.

The harness should encode those semantics directly.

## Summary

The scenario harness should be a lightweight control layer:

```text
Top-level scenario harness:
  scenario SOP + repo manifest + task status + cross-repo validation

Business repos:
  code + repo-local instructions + repo-local checks

Git/CI/PR:
  branch + commit + pull request + remote verification
```

Trellis is optional at every layer. It can be used inside repos that benefit from Trellis specs and workflows, but the harness should work with any repo that exposes enough local instructions and check commands.
