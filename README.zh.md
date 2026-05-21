# Scenario Harness 中文使用说明

Scenario Harness 是一个轻量的跨仓库交付控制层，用来帮助 agent 稳定执行“一个业务场景需要修改多个独立仓库”的任务。

更准确地说，它是面向非 monorepo 环境中、反复出现的特定跨 repo 开发 Scenario 的 agent-first 记忆层和执行协议。它不是泛化的 multi-repo 管理工具，而是用来沉淀某类重复业务变更背后的开发知识：哪些仓库参与、仓库之间如何依赖、修改应按什么顺序推进、进入每个仓库前要读取哪些本地规则，以及如何验证交付完成。

它不替代 Git、CI、PR review，也不替代每个业务仓库自己的开发规范。它的职责是把跨 repo 交付中容易靠记忆和猜测完成的部分显式写下来：

- 当前执行的是哪个业务场景
- 涉及哪些仓库
- 每个仓库在场景中的角色是什么
- 仓库应该按什么顺序修改
- 进入每个仓库后应该先读哪些本地规则
- 应该运行哪些检查
- 任务进度、验证结果、决策和 PR 顺序记录在哪里

## 适用场景

当某类特定任务经常跨多个仓库时，适合使用这个 harness，例如：

- 先改 contract/schema/source-of-truth repo，再同步下游 consumer repo
- API 变更需要同步 backend、frontend、SDK、fixtures、worker
- 产品流程变更横跨 web、mobile、backend、infra
- 多个 repo 没有共同 monorepo 或 meta repo，也不适合强行合并

这个 harness 主要面向非 monorepo 环境。如果这些项目可以自然放进一个 monorepo 或 workspace，并共享工具链、本地开发规则、review/build 上下文，应优先使用 monorepo/workspace。进入 monorepo 后，跨 package 开发通常更接近单 repo 开发，而不是独立跨 repo 交付。

它最适合的情况是：这些 repo 本质上属于不同业务域，应该保持独立 ownership、版本管理和 review 流程，但某个反复出现的特定 Scenario 又要求它们协同开发。此时应该沉淀 scenario 级共享上下文，而不是为了这个场景强行把 repo 合并进同一个 monorepo。

不适合用它来替代单个 repo 内部的工作流。每个业务 repo 仍然负责自己的代码风格、测试、生成文件、提交、PR 和 CI。

## Agent-First 文档原则

本项目把 agent 阅读理解作为一等公民。agent 不应该仅凭 YAML 字段名猜测行为，而应该按文档定义解释配置。

强制阅读顺序：

1. `AGENTS.md`
2. `repos.yaml`
3. `scenarios/<scenario>/scenario.yaml`
4. `scenarios/<scenario>/README.md`

其中：

- `AGENTS.md` 定义执行协议、YAML 字段语义、路径解析、执行顺序和冲突处理
- `repos.yaml` 定义稳定的仓库清单和 repo-local 执行约定
- `scenarios/<scenario>/scenario.yaml` 定义该场景的机器可读执行配置
- `scenarios/<scenario>/README.md` 定义具体业务场景的 SOP

## 目录结构

```text
scenario-harness/
  AGENTS.md
  README.md
  README.zh.md
  repos.yaml
  scenarios/
    example-contract-change/
      scenario.yaml
      README.md
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

### 1. 放置 harness

保持 harness 为独立目录，和业务 repo 并列：

```text
~/work/
  scenario-harness/
  api/
  web/
  worker/
```

默认假设 harness 是 standalone；不需要再声明 placement 字段。

### 2. 配置真实仓库

编辑 `repos.yaml`，把占位仓库替换成你的真实 repo。

示例：

```yaml
repos:
  api:
    path: ../api
    role: contract-source
    description: Owns API schema and domain contracts.
    default_branch: main
    branch_prefix: scenario
    checks:
      - npm run lint
      - npm test

  web:
    path: ../web
    role: downstream-consumer
    description: Consumes API contracts from api.
    default_branch: main
    branch_prefix: scenario
    checks:
      - pnpm typecheck
      - pnpm test
```

字段解释以 `AGENTS.md` 为准。

### 3. 定义业务场景

为每个场景创建目录，并在其中维护 `scenario.yaml` 和 `README.md`。

示例：

```yaml
description: Update billing API contract and downstream consumers.

repos:
  - api
  - web
  - worker

order:
  - api
  - web
  - worker

repo_context:
  api:
    instruction_sources:
      - AGENTS.md
      - CONTRIBUTING.md
      - README.md
    key_files:
      - openapi.yaml
      - src/contracts/
  web:
    instruction_sources:
      - AGENTS.md
      - README.md
    key_files:
      - src/api/

integration_checks:
  - scripts/run-integration-checks billing-contract-change
```

放置位置：

```text
scenarios/billing-contract-change/scenario.yaml
```

然后创建 `scenarios/billing-contract-change/README.md`，写场景目的、repo 角色、跨 repo invariant 和完成标准。可以从 `scenarios/example-contract-change/` 复制一份。

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

先阅读 AGENTS.md、repos.yaml、scenarios/billing-contract-change/scenario.yaml
和 scenarios/billing-contract-change/README.md。

然后解析 repo 路径，检查 affected repos 的 git status，按 scenario order 进入各 repo，
读取 scenario 定义的 repo-local instruction sources，检查 key files，实施修改，运行 checks，并更新 task status、
validation report、decisions 和 PR plan。
除非我明确要求，不要 commit。
```

### 3. 执行模型

默认执行模型是单个 agent 串行执行 scenario。MVP 工作流中不引入多 agent 调度。

scenario 应该足够收敛，让 agent 可以依靠已配置的 repos、`repo_context`、checks 和 scenario invariants 推进，而不需要在每个 repo 中做大范围探索。必要知识应写进 `repos.yaml`、scenario 目录和 task files，而不是依赖 agent 自行推断跨 repo 行为。

为了控制上下文压力，agent 在完成每个 repo 后应总结：

- 修改了哪些文件
- 对 contract、API、event 或 generated artifact 的影响
- 运行了哪些 checks 以及结果
- blockers、assumptions 或下游注意事项

除非调试需要回到更早的 repo，这份总结就是进入下一个 repo 所需携带的上下文。

### 4. agent 应该做什么

agent 应该：

1. 按顺序阅读 harness 文档
2. 从 `repos.yaml` 解析 repo 路径
3. 阅读 `scenarios/<scenario>/scenario.yaml`
4. 阅读 `scenarios/<scenario>/README.md`
5. 检查每个 affected repo 的 `git status`
6. 按 `scenarios.<name>.order` 执行
7. 进入每个 repo 后读取 scenario 定义的 `repo_context.<repo>.instruction_sources`
8. 检查 scenario 定义的 `repo_context.<repo>.key_files`
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
- 在 `AGENTS.md` 已定义语义时自行猜测 YAML 行为

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

1. 替换 `repos.yaml` 中的占位 repo
2. 用一个真实场景替换 `example-contract-change`
3. 从 templates 创建 task 目录
4. 要求 agent 执行场景，但不要 commit
5. 检查 YAML 字段是否足够支持路径解析、repo entry、checks 和任务记录
6. 只为 dry run 证明需要的重复机械步骤添加脚本

## 脚本边界

MVP 阶段优先使用文档，不急着写自动化脚本。

脚本适合处理机械操作，例如：

- 汇总 repo status
- 准备分支
- 运行 YAML 定义的 checks
- 运行 integration smoke tests
- 收集 diff summary
- 生成 PR plan

业务判断应该留在 scenario 文档和 task 记录里。

## 实践路线

第一次真实 scenario dry run 之后，按以下优先级逐步实践剩余设计：

1. 强化 task templates 中的 quality gates。
   - 在 `templates/validation-report.md` 或 `templates/task-status.md` 中加入 repo-local、cross-repo、delivery 三层 gate。
   - 保持 checklist 形式，方便 agent 在执行过程中持续更新。

2. 增加只读的 `scripts/repo-status`。
   - 汇总每个 affected repo 的 branch、dirty state、untracked files 和 recent commits。
   - 保持非破坏性，用于任何 branch 或代码修改之前。

3. 在 YAML 结构稳定后增加配置校验。
   - 检查必填字段、无法解析的路径、缺失的 scenario 文档，以及 scenario 引用但未在 `repos.yaml` 声明的 repo。
   - 优先输出 validation report，不做自动修复。

4. 只有在频繁创建 task 时，才增加 task template generation。
   - 从现有 templates 生成 `brief.md`、`plan.md`、`status.md`、`decisions.md`、`validation.md` 和 `prs.md`。
   - 不隐藏 task 文件；它们仍然是 session 中断后的恢复点。

## 未来设计

以下设计应等多次手工执行证明必要后再实现：

- 保持 harness 作为 standalone coordination repository。
- 保留 Trellis 和 meta-repo 相关设计理由：harness 不应绑定某个 repo-local workflow 系统，也不应只解决文件系统聚合问题，而应直接编码交付语义。
- 将 CLI 支持定位为机械、低风险步骤的辅助工具，而不是核心执行模型。适合的方向包括 YAML validation、repo status report、task skeleton generation 和 task summary。
- 在手工 workflow 经过多次执行、命令边界足够稳定之前，不构建完整 CLI orchestrator。候选辅助命令可以是 `scenario prepare`、`scenario status`、`scenario check` 和 `scenario summary`。
- 不把多 agent 编排当作目标。只有当真实 scenario 证明单 agent 串行执行无法管理上下文、repo 数量或验证复杂度时，才重新评估。
- 默认不自动 commit 或创建 PR。未来如增加，也应作为显式 delivery mode，并继续保持每个 repo 独立记录 commit 或 PR plan。
- 暂缓复杂 branch management。任何 branch preparation 都应先检查 dirty state 和无关本地改动。

## 当前状态

当前版本是 MVP skeleton，已经可以用于真实 repo 的手工 dry run。下一步成熟化方向是：用它跑一次真实跨 repo 场景，然后把重复且不需要判断的步骤沉淀成脚本。
