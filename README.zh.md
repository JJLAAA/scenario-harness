# Scenario Harness 中文使用说明

Scenario Harness 是一个轻量的跨仓库交付控制层，用来帮助 agent 稳定执行“一个业务场景需要修改多个独立仓库”的任务。

它不替代 Git、CI、PR review，也不替代每个业务仓库自己的开发规范。它的职责是把跨 repo 交付中容易靠记忆和猜测完成的部分显式写下来：

- 当前执行的是哪个业务场景
- 涉及哪些仓库
- 每个仓库在场景中的角色是什么
- 仓库应该按什么顺序修改
- 进入每个仓库后应该先读哪些本地规则
- 应该运行哪些检查
- 任务进度、验证结果、决策和 PR 顺序记录在哪里

## 适用场景

当某类任务经常跨多个仓库时，适合使用这个 harness，例如：

- 先改 contract/schema/source-of-truth repo，再同步下游 consumer repo
- API 变更需要同步 backend、frontend、SDK、fixtures、worker
- 产品流程变更横跨 web、mobile、backend、infra
- 多个 repo 没有共同 monorepo 或 meta repo，也不适合强行合并

不适合用它来替代单个 repo 内部的工作流。每个业务 repo 仍然负责自己的代码风格、测试、生成文件、提交、PR 和 CI。

## Agent-First 文档原则

本项目把 agent 阅读理解作为一等公民。agent 不应该仅凭 YAML 字段名猜测行为，而应该按文档定义解释配置。

强制阅读顺序：

1. `AGENTS.md`
2. `manifests/README.md`
3. `manifests/repos.yaml`
4. `manifests/scenarios.yaml`
5. `scenarios/<scenario>.md`

其中：

- `AGENTS.md` 定义执行协议
- `manifests/README.md` 定义 YAML 字段语义、路径变量、placement 模式、执行顺序和冲突处理
- `repos.yaml` 定义仓库清单和 repo-local 执行约定
- `scenarios.yaml` 定义场景与仓库顺序
- `scenarios/<scenario>.md` 定义具体业务场景的 SOP

## 目录结构

```text
scenario-harness/
  AGENTS.md
  README.md
  README.zh.md
  docs/
    scenario-harness-design.md
  manifests/
    README.md
    repos.yaml
    scenarios.yaml
  scenarios/
    example-contract-change.md
  tasks/
    README.md
  templates/
    decisions.md
    pr-plan.md
    task-brief.md
    task-plan.md
    task-status.md
    validation-report.md
  scripts/
    README.md
```

## 初始化配置

### 1. 选择放置模式

如果 harness 是独立目录，和业务 repo 并列，使用 `standalone`：

```text
~/work/
  scenario-harness/
  api/
  web/
  worker/
```

如果 harness 放在某个主要业务 repo 内，使用 `hosted`：

```text
api/
  scenario-harness/
  src/
web/
worker/
```

在 `manifests/repos.yaml` 中设置：

```yaml
harness:
  placement: standalone
  root: $HARNESS_ROOT
  workspace_root: /Users/leo/work/repos
```

### 2. 配置真实仓库

编辑 `manifests/repos.yaml`，把占位仓库替换成你的真实 repo。

示例：

```yaml
harness:
  placement: standalone
  root: $HARNESS_ROOT
  workspace_root: /Users/leo/work/repos

repos:
  api:
    path: $WORKSPACE_ROOT/api
    role: contract-source
    description: Owns API schema and domain contracts.
    default_branch: main
    branch_prefix: scenario
    instruction_sources:
      - AGENTS.md
      - CONTRIBUTING.md
      - README.md
    checks:
      - npm run lint
      - npm test
    key_files:
      - openapi.yaml
      - src/contracts/

  web:
    path: $WORKSPACE_ROOT/web
    role: downstream-consumer
    description: Consumes API contracts from api.
    default_branch: main
    branch_prefix: scenario
    instruction_sources:
      - AGENTS.md
      - README.md
    checks:
      - pnpm typecheck
      - pnpm test
    key_files:
      - src/api/
```

字段解释以 `manifests/README.md` 为准。

### 3. 定义业务场景

编辑 `manifests/scenarios.yaml`，声明场景涉及哪些 repo，以及执行顺序。

示例：

```yaml
scenarios:
  billing-contract-change:
    description: Update billing API contract and downstream consumers.
    repos:
      - api
      - web
      - worker
    order:
      - api
      - web
      - worker
    integration_checks:
      - scripts/run-integration-checks billing-contract-change
    requires_pr_order: true
```

然后创建对应的场景文档：

```text
scenarios/billing-contract-change.md
```

可以从 `scenarios/example-contract-change.md` 复制一份，再替换为真实 repo 名称、修改顺序、跨 repo invariant 和完成标准。

## 执行一次任务

### 1. 创建任务目录

建议使用日期加场景名作为 task id：

```bash
mkdir -p tasks/2026-05-20-billing-contract-change
cp templates/task-brief.md tasks/2026-05-20-billing-contract-change/brief.md
cp templates/task-plan.md tasks/2026-05-20-billing-contract-change/plan.md
cp templates/task-status.md tasks/2026-05-20-billing-contract-change/status.md
cp templates/decisions.md tasks/2026-05-20-billing-contract-change/decisions.md
cp templates/validation-report.md tasks/2026-05-20-billing-contract-change/validation.md
cp templates/pr-plan.md tasks/2026-05-20-billing-contract-change/prs.md
```

先填写 `brief.md`，记录用户需求、范围、非目标和初始假设。

### 2. 让 agent 执行场景

在 harness 目录启动 agent，并提供场景名和任务目录。

可直接使用这个 prompt：

```text
执行 scenario billing-contract-change。
任务目录是 tasks/2026-05-20-billing-contract-change。

先阅读 AGENTS.md、manifests/README.md、manifests/repos.yaml、
manifests/scenarios.yaml 和 scenarios/billing-contract-change.md。

然后解析 repo 路径，检查 affected repos 的 git status，按 scenario order 进入各 repo，
读取 repo-local instruction sources，实施修改，运行 checks，并更新 task status、
validation report、decisions 和 PR plan。
除非我明确要求，不要 commit。
```

### 3. agent 应该做什么

agent 应该：

1. 按顺序阅读 harness 文档
2. 从 `manifests/repos.yaml` 解析 repo 路径
3. 确认 scenario 存在于 `manifests/scenarios.yaml`
4. 阅读 `scenarios/<scenario>.md`
5. 检查每个 affected repo 的 `git status`
6. 按 `scenarios.<name>.order` 执行
7. 进入每个 repo 后读取 `instruction_sources`
8. 检查相关 `key_files`
9. 实施 repo-local 修改
10. 运行 repo-local `checks`
11. 运行 `integration_checks`
12. 更新 `tasks/<task-id>/` 下的任务文件
13. 汇报 diff 范围、验证结果、风险和 PR 顺序

agent 不应该：

- 把 harness 目录当成业务 repo
- 把一个 repo 的规则套用到另一个 repo
- 覆盖无关本地改动
- 混合多个 repo 的 commit
- 在没有明确要求时 commit 或创建 PR
- 在 `manifests/README.md` 已定义语义时自行猜测 YAML 行为

## 任务文件说明

每个任务目录建议包含：

| 文件 | 作用 |
| --- | --- |
| `brief.md` | 用户需求、范围、非目标、假设 |
| `plan.md` | repo 顺序和执行步骤 |
| `status.md` | 当前进度、分支、阻塞点、跳过的文件 |
| `decisions.md` | 兼容性选择、迁移决策、被拒绝的方案 |
| `validation.md` | repo-local checks 和 cross-repo validation 结果 |
| `prs.md` | PR 顺序、依赖关系、建议 commit message、迁移说明 |

这些文件是 session 中断后的恢复点。

## 完成检查清单

任务完成前确认：

- 已检查每个 affected repo 的 git status
- 已读取 repo-local instructions，或记录缺失文件
- source-of-truth repo 先于 downstream repo 修改
- 生成文件按 repo-local 规则更新
- repo-local checks 通过，或失败已记录原因和下一步
- integration checks 通过，或失败已记录原因和下一步
- task status 和 validation 文件已更新
- PR 顺序和依赖关系清楚
- 剩余风险已记录

## 第一次 dry run

首次真实使用时，建议先手工跑一个小任务，不要急着加脚本：

1. 替换 `manifests/repos.yaml` 中的占位 repo
2. 用一个真实场景替换 `example-contract-change`
3. 从 templates 创建 task 目录
4. 要求 agent 执行场景，但不要 commit
5. 检查 manifest 字段是否足够支持路径解析、repo entry、checks 和任务记录
6. 只为 dry run 证明需要的重复机械步骤添加脚本

## 脚本边界

MVP 阶段优先使用文档，不急着写自动化脚本。

脚本适合处理机械操作，例如：

- 汇总 repo status
- 准备分支
- 运行 manifest 定义的 checks
- 运行 integration smoke tests
- 收集 diff summary
- 生成 PR plan

业务判断应该留在 scenario 文档和 task 记录里。

## 当前状态

当前版本是 MVP skeleton，已经可以用于真实 repo 的手工 dry run。下一步成熟化方向是：用它跑一次真实跨 repo 场景，然后把重复且不需要判断的步骤沉淀成脚本。
