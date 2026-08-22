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
- 任务进度、验证结果、决策和交付顺序记录在哪里

## 为什么需要它

Coding agent 越来越依赖 spec、指令和执行协议来可靠地完成代码开发。对于单个 repo，或者拥有统一工具链和统一 review 上下文的 monorepo，已经有很多方式可以给 agent 提供这些指引：repo-local instructions、任务 spec、package scripts、测试和项目文档。

但很多企业系统并不是这种形态。一次真实交付可能同时涉及多个独立 ownership 的 repo：API service、frontend、SDK、worker、infra、fixtures 或文档。这些 repo 可能因为团队边界、权限控制、发布节奏、合规要求或既有运维实践，必须继续保持独立。

代码分散在多个 repo 中，并不代表业务变更本身是分散的。对 agent 来说，它仍然需要理解这次变更的整体形状：哪些 repo 参与、哪个 repo 应该先改、进入每个 repo 后适用哪些本地规则、应该运行哪些检查、做过哪些决策，以及如何记录整个场景的进度。

Scenario Harness 补的就是这一层 scenario-level 协议。它不强行合并 repo，而是在保持各仓库独立的前提下，为 coding agent 提供一个最小但明确的跨 repo 协同开发流程。

## 知识模型

harness 把一次跨仓交付所需的知识分成三层，各有明确的归属和生命周期：

1. **场景定义——静态，本 harness 拥有。** `scenarios/<scenario>/scenario.yaml` 和场景 `README.md`。这是某一类重复任务的协调知识：哪些仓库参与、按什么顺序修改、彼此依赖什么、必须读哪些仓库本地指令、看哪些关键文件、用什么检查证明完成。每类场景编写一次，之后所有任务复用。
2. **仓库本地知识——静态，各业务仓库拥有。** `instruction_sources` 指向的文件（`AGENTS.md`、`CLAUDE.md`、`.trellis/workflow.md`、`CONTRIBUTING.md` 等），以及 `key_files` 圈定的契约和代码。这是"在这个仓库里怎么干活"的知识，在任何场景执行之前就已存在，场景只是引用它们。
3. **任务记录——动态，每次执行时生成。** `tasks/<task>/` 下的 `spec.md`、`status.md`、`decisions.md`、`validation.md`。`init-task` 从模板和场景配置机械生成骨架，执行 Agent 在规划、实现、验证过程中充实和更新它们。它们同时也是会话中断时的恢复点。

`scenario.yaml` 是两个静态层之间的胶水：它通过指向各业务仓库内的 instruction sources 和 key files，把 harness 拥有的协调知识与仓库拥有的本地知识绑定在一起。

只有任务层是运行时生成的，且数据流是单向的：仓库本地指令作为输入被阅读，Agent 从中学到的内容被浓缩进跨仓任务 spec。harness 从不生成、改写或回写仓库本地的 spec。

知识摆放位置与执行协议是耦合的：规划与规格评审门禁、固定的状态词汇表、检查失败处理、中断安全协议，以及 helper CLI。scenario 概念回答的是*知识在哪里*；协议回答的是*执行如何保持安全、可恢复*。两者合起来，把"这一类跨仓交付应该怎么协调"从 Agent 每次现场重新摸索的东西，变成显式、预置、按协议执行的知识。

## 声明式协调

这个 harness 是有意选择声明式的：预制协议优先于 Agent 探索。`instruction_sources` 和 `key_files` 不是仓库知识的完整地图，而是"最低保证阅读清单"——是下限，不是上限：

- 清单声明的是指针，不是内容。风格指南、工作流规则和领域知识留在各业务仓库内部，由仓库 owner 维护。
- Agent 保留清单之外探索的自由；协议没有任何条款禁止读取额外文件，实现阶段天然需要这么做。
- 声明的文件不存在则跳过并记录。没有场景级声明的仓库回退到 `README.md`、`CONTRIBUTING.md`、`package.json`、`Makefile` 等通用项目文件。

这个限制换来的是自由探索给不了的东西：

1. **确定性。** 每次运行都看到同样的保证上下文，是跨仓交付可重复的前提。
2. **上下文经济。** 跨仓任务本身已背负协调开销；声明入口让每个仓库的发现成本是常数而不是无上界。
3. **可验证性。** 只有声明过的文件才能被 preflight 检查存在性、被审计跳过记录。
4. **保护承重文件。** 漏读契约或 schema 文件对下游是灾难性的；漏读风格细节通常会被检查兜住。场景作者把判断力花在绝不能漏的文件上。

代码风格最能说明这种分工：风格正确性不指望 Agent 读懂指南，而是由仓库自己的 `checks`（lint、typecheck、test）强制执行。必须确定的走声明，允许模糊的留给探索。

一句话概括：凡是被声明的都可被机器校验——`validate-scenario` 校验结构、`preflight` 校验分支与文件存在性、`checks` 校验约定、task files 校验可恢复性；凡是未声明的都依赖 Agent 能力。Agent 的自由没有被取消，而是被重新分配：探索留在最便宜、错误最容易被 checks 兜住的那一层（仓库内实现），而探索代价最高、出错最致命的那一层（跨仓顺序、依赖方向、契约入口）被完全声明化。

代价是策展。指令清单和关键文件清单由人工维护，仓库采纳了场景尚未引用的新规范时就会过期。兜底发现机制缓解但不消除这一点；维护负担落在场景作者身上，换来的是每次执行的确定性。

## 单会话局限与每仓新会话模式

默认执行模型——单个 Agent 会话串行执行场景——有两个需要直视的局限：

1. **跨仓上下文污染只能缓解，不能消除。** 协议防火墙（读仓库上下文前先做分支检查、每次进仓重读 instruction sources、不把一个仓库的指令套用到另一个仓库）是行为纪律，不是运行时隔离。会话历史仍会携带前面仓库的痕迹，压缩摘要会进一步模糊仓库边界。执行模型要求的每仓总结约束了向后传递的内容，但单一会话无法保证隔离。
2. **仓库本地运行时机制不会激活。** 如"与 Repo-Local Spec 框架的关系"一节所述，hooks、skills、slash commands 和 MCP 注入绑定在会话启动时发现的项目配置上。从 harness 目录启动、随后进入业务仓库的 Agent 不会重新触发发现流程，因此单仓设计的运行时支持是缺席的，合规只发生在文档层。

两个局限的结构性解法相同：让每个仓库在它自己的目录里新起一个 Agent 会话来执行，此时该仓的运行时机制正常激活。task files 让这件事不需要编排就能做到，因为它们是会话外记忆。每仓会话先读 `spec.md`、`status.md`、`decisions.md`、`validation.md`，完成仓库内工作，再把结果写回。协议完全兼容这种模式，只是不为它做调度；多 Agent 编排推迟到 MVP 之后。

## 与 Repo-Local Spec 框架的关系

Scenario Harness 不与 Spec Kit、OpenSpec、Trellis 或 repo 自定义 agent workflow 这类单 repo / monorepo spec 框架竞争。它位于这些框架之上。

它当前能够保证的是显式发现和委托：每个 scenario 可以声明 Agent 进入某个 repo 后必须读取哪些 repo-local 指令入口、spec 目录和关键文件，然后再进行修改。

它不保证特定 spec 框架的运行时机制，例如 hooks、slash commands、MCP servers 或上下文注入，会在 Agent 进入 repo 后自动生效。这些机制是否可用，取决于具体 Agent runtime 和框架实现，需要针对每个框架通过实践验证。

对于依赖 hooks 的框架，业务 repo 应该通过 `AGENTS.md`、`CLAUDE.md`、`README.md` 或 scenario-defined `instruction_sources` 暴露静态 fallback 入口。这样即使运行时注入不可用，Agent 仍然可以显式读取并遵守 repo-local spec 规则。

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
2. `scenarios/<scenario>/scenario.yaml`
3. `scenarios/<scenario>/README.md`

其中：

- `AGENTS.md` 定义执行协议、YAML 字段语义、路径解析、执行顺序和冲突处理
- `scenarios/<scenario>/scenario.yaml` 定义该场景的机器可读执行模板，包括 repo 路径、角色、instruction sources、key files 和 checks
- `scenarios/<scenario>/README.md` 定义具体业务场景的 SOP
- `tasks/<task>/` 记录本次具体请求、期望分支、执行进度、决策和验证结果

在一个 scenario 目录内，两个文件职责不同：

- `scenario.yaml` 是权威场景模板：选择哪些 repo、执行顺序、repo 路径、repo-local instruction sources、key files 和 checks。
- task 文件声明本次具体请求和每个 repo 的期望任务分支；preflight 发现当前分支不匹配时，agent 必须停止并反馈。
- `README.md` 是场景 SOP：业务意图、设计理由、跨 repo invariants、兼容性要求、完成标准、风险，以及不适合写进 YAML 的判断规则。

README 不应该重复或覆盖 `scenario.yaml` 中的结构化执行字段。如果二者在执行结构上冲突，除非会造成破坏性或不安全行为，否则以 `scenario.yaml` 为准。如果二者在业务意图、兼容性要求或完成标准上冲突，先停止并报告冲突，不要直接编辑业务 repo。

## 目录结构

```text
scenario-harness/
  AGENTS.md
  README.md
  README.zh.md
  scenarios/
    example-contract-change/
      scenario.yaml
      README.md
  tasks/
  templates/
    decisions.md
    spec.md
    task-status.md
    validation-report.md
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

### 2. 定义业务场景

为每个场景创建目录，并在其中维护 `scenario.yaml` 和 `README.md`。

示例：

```yaml
order:
  - api
  - web
  - worker

repos:
  api:
    path: ../api
    role: contract-source
    description: Owns API schema and domain contracts.
    instruction_sources:
      - AGENTS.md
      - CONTRIBUTING.md
      - README.md
    key_files:
      - openapi.yaml
      - src/contracts/
    checks:
      - npm run lint
      - npm test
  web:
    path: ../web
    role: downstream-consumer
    description: Consumes API contracts from api.
    instruction_sources:
      - AGENTS.md
      - README.md
    key_files:
      - src/api/
    checks:
      - pnpm typecheck
      - pnpm test
```

放置位置：

```text
scenarios/billing-contract-change/scenario.yaml
```

然后创建 `scenarios/billing-contract-change/README.md`，写场景目的、repo 角色、跨 repo invariant 和完成标准。可以从 `scenarios/example-contract-change/` 复制一份。

## 执行一次任务

### 0. 校验 Scenario

创建 task 文件或进入业务仓库之前，先运行 agent helper CLI：

```bash
bin/scenario-harness validate-scenario billing-contract-change
```

如果 Agent 需要结构化输出，使用 JSON：

```bash
bin/scenario-harness validate-scenario billing-contract-change --json
```

这个命令会只读检查 scenario 文件是否存在、`repos` 和 `order` 是否一致、checks 形状是否合法、仓库路径是否可解析。它不会修改业务仓库；
当 scenario 不适合执行时会以非零状态码退出。

需要压缩执行上下文时，使用：

```bash
bin/scenario-harness plan-scenario billing-contract-change
```

它会打印 scenario 顺序、解析后的 repo 路径、instruction sources、key files 和 repo-local checks。
如果 Agent 需要结构化携带这份计划，使用 `--json`。

### 1. 创建或选择任务目录

任务目录用于记录进度，并让 agent 可以安全恢复。如果已有任务目录，直接提供给 agent。否则用 helper CLI 创建：

```bash
bin/scenario-harness init-task billing-contract-change \
  2026-05-20-billing-contract-change \
  --request "Update billing API contract and downstream consumers."
```

如果省略 task id，helper 会使用 `YYYY-MM-DD-<scenario>`。它会根据 scenario 配置生成
`spec.md`、`status.md`、`decisions.md` 和 `validation.md`，并且不会覆盖已有 task 文件。
需要结构化输出时使用 `--json`。

期望分支是 task-specific 的。默认情况下，`init-task` 会为每个 repo 记录
`scenario/<task-id>` 作为期望分支。使用 `--branch <branch>` 可以指定共享分支名；
如果各 repo 分支不同，可以重复传入 `--repo-branch <repo>=<branch>`。

继续已有任务时，agent 应先读取这些 task 文件，再编辑业务 repo：

1. `spec.md`
2. `status.md`
3. `decisions.md`
4. `validation.md`

如果用户只说继续某个 scenario，但没有提供 task 目录，agent 应检查 `tasks/` 中匹配该 scenario 的任务，并继续最近一个未完成任务。如果存在多个合理候选，应先询问使用哪个 task。

helper 可以列出匹配的 task 目录：

```bash
bin/scenario-harness list-tasks billing-contract-change --incomplete-only
```

### 2. 运行 Preflight

进入 repo-local instructions 或编辑业务代码之前，运行：

```bash
bin/scenario-harness preflight billing-contract-change \
  --task 2026-05-20-billing-contract-change
```

Preflight 会检查每个 affected repo 的当前分支、dirty state、缺失 instruction source 和缺失 key file。
它会更新 `status.md` 和 `validation.md` 中带标记的区块；重复运行会替换旧区块，不会反复追加重复记录。
如果 Agent 只需要结构化预览，使用 `--no-write --json`。

### 3. 运行 Checks

列出 scenario 声明的 repo-local checks：

```bash
bin/scenario-harness checks billing-contract-change
```

完成 repo-local 修改后运行：

```bash
bin/scenario-harness checks billing-contract-change \
  --run \
  --task 2026-05-20-billing-contract-change
```

提供 `--task` 时，check 结果会写入 `validation.md` 的带标记区块。

### 4. 让 agent 执行场景

在 harness 目录启动 agent，并尽量提供场景名和任务目录。

可直接使用这个 prompt：

```text
执行 scenario billing-contract-change。
任务目录是 tasks/2026-05-20-billing-contract-change。

先阅读 AGENTS.md、scenarios/billing-contract-change/scenario.yaml
和 scenarios/billing-contract-change/README.md。

然后解析 repo 路径，检查 affected repos 的 git status，按 scenario order 进入各 repo，
检查每个 repo 当前分支是否等于 task 指定分支，读取 scenario 定义的 repo-local instruction sources，
检查 key files，实施修改，运行 checks，并更新 task status、validation report 和 decisions。
除非我明确要求，不要 commit。
```

继续已有任务可以使用：

```text
继续 scenario billing-contract-change。
任务目录是 tasks/2026-05-20-billing-contract-change。

先读取 task 文件，然后从下一个未完成步骤继续。
除非我明确要求，不要 commit。
```

### 5. 用每仓子进程 Agent 执行

当 `status.md` 里记录了 Planning Gate 和 Spec Review Gate 之后，helper CLI
可以自己驱动实现阶段：

```bash
bin/scenario-harness run billing-contract-change \
  --task 2026-05-20-billing-contract-change \
  --agent claude-code
```

`run` 是确定性的 runner，不是编排模型：两个门禁未记录就拒绝启动；按场景顺序逐仓
推进——核对分支门禁、由场景数据渲染 prompt、在仓库目录内以独立进程组拉起 agent
后端（`claude-code`、`codex`，或实验性的 `gemini`）、agent 退出后由 runner 亲自跑
仓库 checks、首个失败即停止并把 stage × category 失败分类写进 task files。原始
agent 输出落在 `tasks/<task>/logs/<repo>.log`；`.run.lock` 保证单写者；终止阶梯
（SIGTERM → 宽限 → 对进程组 SIGKILL）执行 `--timeout`（默认每仓 1800 秒）；
`--dry-run` 只渲染 prompt。

设计理由、借鉴自 deepseek-harness 的机制清单、以及传输层选择（公开 headless CLI
而非 SDK/app-server）见 [`docs/subprocess-agent-run.md`](docs/subprocess-agent-run.md)；
mock 自测脚本为 `tests/run_mock_e2e.py`。

### 3. 执行模型

默认执行模型是单个 agent 串行执行 scenario。MVP 工作流中不引入多 agent 调度。关于这个模型需要直视的局限，以及与之兼容的每仓新会话模式，见"单会话局限与每仓新会话模式"一节。

scenario 应该足够收敛，让 agent 可以依靠已配置的 repos、checks 和 scenario invariants 推进，而不需要在每个 repo 中做大范围探索。必要知识应写进 `scenario.yaml`、scenario README 和 task files，而不是依赖 agent 自行推断跨 repo 行为。

为了控制上下文压力，agent 在完成每个 repo 后应总结：

- 修改了哪些文件
- 对 contract、API、event 或 generated artifact 的影响
- 运行了哪些 checks 以及结果
- blockers、assumptions 或下游注意事项

除非调试需要回到更早的 repo，这份总结就是进入下一个 repo 所需携带的上下文。

### 4. agent 应该做什么

agent 应该：

1. 按顺序阅读 harness 文档
2. 阅读 `scenarios/<scenario>/scenario.yaml`，确定 affected repo key
3. 阅读 `scenarios/<scenario>/README.md`
4. 运行 `bin/scenario-harness validate-scenario <scenario>`
5. 用 `bin/scenario-harness plan-scenario <scenario>` 携带压缩后的执行摘要
6. 用 `bin/scenario-harness init-task` 或 `bin/scenario-harness list-tasks` 创建或选择 task 文件
7. 进入业务 repo 前运行 `bin/scenario-harness preflight <scenario> --task <task-id>`
8. 按 `scenarios.<name>.order` 执行
9. 进入每个 repo 后读取 scenario 定义的 `repos.<repo>.instruction_sources`
10. 检查 scenario 定义的 `repos.<repo>.key_files`
11. 在编辑代码前，用 key files 中读到的信息补全 `tasks/<task-id>/spec.md`，记录 implementation notes、影响面、风险和验证重点
12. 按补全后的 task spec 实施 repo-local 修改
13. 如果用户澄清会影响目标、范围、实现、验证、风险或交付顺序，继续前先同步到 `spec.md`
14. 如果实现需要明显偏离补全后的 spec，先在 `decisions.md` 记录原因，并把变化同步回 `spec.md`
15. 运行每个 affected repo 的 repo-local `checks`，优先使用 `bin/scenario-harness checks <scenario> --run --task <task-id>`
16. 更新 `tasks/<task-id>/` 下的任务文件
17. 汇报 diff 范围、验证结果、风险和交付顺序

agent 不应该：

- 把 harness 目录当成业务 repo
- 把一个 repo 的规则套用到另一个 repo
- 覆盖无关本地改动
- 混合多个 repo 的 commit
- scenario 分支检查失败时自动 checkout 或创建分支
- 在没有明确要求时 commit 或创建 PR
- 在 `AGENTS.md` 已定义语义时自行猜测 YAML 行为

## 任务文件说明

每个任务目录建议包含：

| 文件 | 作用 |
| --- | --- |
| `spec.md` | 用户需求、用户澄清、范围、非目标、假设、repo 顺序、执行步骤和 key-file-derived implementation notes |
| `status.md` | 当前进度、分支、阻塞点、跳过的文件 |
| `decisions.md` | 兼容性选择、迁移决策、被拒绝的方案 |
| `validation.md` | repo-local 编译和检查结果、已知失败、剩余风险 |

这些文件是 session 中断后的恢复点。

## 完成检查清单

任务完成前确认：

- 已检查每个 affected repo 的 git status
- 已确认每个 affected repo 当前分支匹配 task 指定分支
- 已读取 repo-local instructions，或记录缺失文件
- source-of-truth repo 先于 downstream repo 修改
- 生成文件按 repo-local 规则更新
- repo-local checks 通过，或失败已记录原因和下一步
- task status 和 validation 文件已更新
- 交付顺序和依赖关系清楚
- 剩余风险已记录

## Helper CLI 检查清单

首次真实使用时，用 helper CLI 跑一个小任务，但不要 commit：

1. 用一个真实场景替换 `example-contract-change`
2. 在 `scenarios/<scenario>/scenario.yaml` 中直接声明该场景的真实 repo
3. 运行 `bin/scenario-harness validate-scenario <scenario>`
4. 运行 `bin/scenario-harness plan-scenario <scenario> --json`，确认 selected repos 和 order
5. 运行 `bin/scenario-harness init-task <scenario> <task-id> --request "..."`
6. 运行 `bin/scenario-harness preflight <scenario> --task <task-id>`
7. 要求 agent 执行场景，但不要 commit
8. repo-local 修改后运行 `bin/scenario-harness checks <scenario> --run --task <task-id>`
9. 确认 `status.md`、`validation.md` 和 `decisions.md` 包含恢复任务所需的信息

helper CLI 负责重复机械步骤：校验、初始化 task、捕获 preflight 状态、发现 task、压缩计划和执行 checks。
业务判断应该留在 scenario 文档和 task 记录里。

## 未来交付层

当前 helper CLI 覆盖的是本地执行层：

```text
validate scenario -> plan scenario -> init/select task -> preflight -> implement repos -> run checks
```

下一步成熟化方向是在本地 workflow 外围增加交付编排层。它不替代 repo-local 开发规则，也不替代
CI/CD 平台，而是为 agent 明确标出 issue、CI、Git hosting、部署平台 CLI 或 MCP 工具应该插入的位置。

推荐生命周期：

```text
1. Intake / 创建交付需求
2. Validate scenario
3. 初始化或恢复 task
4. 准备分支
5. Preflight
6. 基于 key files 补全 task spec
7. 按补全后的 spec 实施 repo-local 修改
8. 运行本地 checks
9. Commit 并 push 分支
10. 创建或更新 PR
11. 收集 CI 状态
12. 部署或发布
13. 收口 task 并回填外部需求
```

未来 delivery commands 应和本地执行 commands 分层：

| 阶段 | 插入位置 | 未来命令形态 | 更新记录 |
| --- | --- | --- | --- |
| Intake | `validate-scenario` 之前或之后 | `intake <scenario> --task <task-id>` | `spec.md`, `status.md` |
| 分支准备 | `init-task` 之后，`preflight` 之前 | `branches <scenario> --task <task-id> --create` | `status.md`, `validation.md` |
| Commit | 本地 checks 通过之后 | `commits <scenario> --task <task-id>` | `status.md`, `decisions.md` |
| Push | 本地确认 commits 之后 | `push <scenario> --task <task-id>` | `status.md` |
| PR | push 之后 | `prs <scenario> --task <task-id> --create` | `status.md` |
| CI | PR 创建后或 push 触发 CI 后 | `ci <scenario> --task <task-id>` | `validation.md` |
| Deploy | CI 通过并满足审批后 | `deploy <scenario> --task <task-id> --env staging` | `validation.md`, `status.md`, `decisions.md` |
| Closeout | 部署完成或明确停止后 | `closeout <scenario> --task <task-id>` | 所有 task 文件、外部 ticket |

未来交付层的安全规则：

- 默认只做只读检查，除非命令名和 flag 明确表示会产生副作用。
- 对外部状态变更必须要求显式 flag，例如 `--create`、`--push`、`--deploy`、`--close`。
- 不隐式创建、切换、rebase、reset、commit、push、merge、deploy 或关闭外部 ticket。
- 每个 repo 独立处理；永远不要跨 repo 混合 commit。
- dirty worktree 时停止，除非 task 记录明确说明这些改动是预期状态。
- 在 task 文件中记录外部 ID 和链接：issue、branch、commit SHA、PR、CI run、deployment、release、rollback notes。
- 业务判断留在 scenario README 和 task records 中。交付层只编排机械的平台操作，不自行决定兼容性、迁移、发布顺序或风险接受。

当真实交付运行证明字段形态稳定后，可以考虑增加这样的 scenario 字段：

```yaml
delivery:
  external_tracking:
    system: jira
    project: BILLING
  branch:
    create_from: default_branch
  pull_requests:
    base: main
    labels:
      - scenario
  deploy_order:
    - contract-repo
    - consumer-repo
    - worker-repo
  environments:
    - staging
    - production
  gates:
    staging_required: true
    production_requires_approval: true
```

只有当部署命令确实是 scenario-specific 时，才把 repo-specific deployment commands 写进 `repos.<repo>`。
稳定的 repo-owned 部署规则应继续留在业务 repo 或 CI/CD 平台中。

## 当前状态

当前实现已经可以支持带 helper CLI 的本地跨 repo 执行。下一步成熟化方向是：用它跑一次真实跨 repo
场景，然后只为那些重复且不需要业务判断的平台操作增加 delivery-layer adapters。
