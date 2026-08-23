# 自由任务与多仓工作区设计（Free-Form Task Design）

本文件是"双模式任务支持"的设计文档：在现有 scenario 预声明拓扑模式之外，支持自由定义的
开发任务。它不改动已实现机制的行为承诺，只新增一个入口层与一个工作区级索引层。执行层
（`bin/scenario-harness run`、verdict、checks、gates）原样复用，见
[`docs/subprocess-agent-run.md`](subprocess-agent-run.md)。

对应 Goal Contract：`docs/goal-contracts/2026-08-22-multi-repo-workspace-design-v2.md`。
配图：[`docs/diagrams/freeform-workspace.png`](diagrams/freeform-workspace.png)。

## 背景与动机

现状：harness 只协调已声明的 scenario。七个 CLI 子命令全部要求 scenario 参数并从
`scenarios/<scenario>/scenario.yaml` 加载（`bin/scenario-harness:186-192`、`:2588-2755`）；
`depends_on` 校验在单份 scenario.yaml 内闭合（`:328-385`）。scenario 的准确语义是
**协调域声明**：它固化拓扑（repo 集、顺序、依赖边、指令来源、关键文件、检查），禁止
模板化任务内容（branch/commit/version 等任务级取值）；任务方案本身一直是由 Planning
Pass 逐任务动态生成的（写入 `tasks/<task>/spec.md`）。光谱位置：

- 一般 coding harness：自由目标 → 自由拓扑 + 自由计划
- 现状本 harness：自由目标 → 声明式拓扑 + 自由计划

这个落差的真实代价有四：新拓扑形状的冷启动成本（先手写 scenario.yaml + README）、
仓库全集封闭（scenario 之外的仓库不可触达）、检查命令冻结在 scenario 层、以及模板价值
依赖拓扑形状复现。用户目标：跨仓需求无论形状是否复现，都应能在本工作区内被处理——
即补充"自由拓扑"这一档，同时不放弃声明式模式在可复现形状上的收益。

## 核心价值与工作区模型

**本 workspace 最核心的价值：不同 repo 同时出现在 Agent 的工作区内，使跨仓需求
（无论自由需求还是 scenario 需求）可以被全局视角的编排分析处理。**

工作区 = harness 根目录 + 兄弟路径上的业务仓库。这个共存是机制本体：全局视角靠 Agent
对全部仓库的直接可及实现，不依赖任何中间数据结构。由此推出本设计最重要的一条定位：

**registry 与依赖图是加速器，不是机制。** 仓库数量小到单上下文可以遍历时，图是可选的；
当仓库规模超出一个上下文合理的遍历预算时，图与 key_files 一起约束发现成本（与 README
"Declarative Coordination" 一节 "floor, not ceiling" 的语境经济逻辑同构）。图永远不需要
权威性——这正是它区别于"全局权威关系图"方案的地方：权威图会被当作事实复制第三份并
参与裁决，而加速器图错了只影响候选圈定的起点，会在 Planning Pass 核对仓库现实时被抓住。

### 既有分工显式保留（摄取/综合/实现三分）

规划/实现分工沿用已实现的架构，不做任何削弱；规划期内部再按"摄取/综合"两分精确化——
**单上下文约束的是综合与裁决，不是摄取**：

- **摄取（规划期，可委托只读 subAgent）**：读大段代码、跨仓 grep、追调用链、manifest/
  引用扫描、单仓判定的工作区反查——重摄取、轻决策的机械汇集。四条边界：只读（对业务
  仓零写入）；蒸馏物必须附 file:line 引文（主会话保留抽查能力）；结果落盘
  `tasks/<task>/` notes（恢复点原则，不留在对话里）；允许而非强制（小仓直接读更好，
  少一跳有损压缩；触发启发式：读取量超预算、独立追查可并行、纯机械模式扫描）。
- **综合（规划主会话，单上下文，不可委托）**：拓扑判定、契约决策、跨仓 spec 与各仓
  spec 条目撰写、单仓结论裁决——跨仓关联推理需要一个上下文（README "Single-Session
  Limits And Per-Repo Sessions" 记录的结论）。自由任务的拓扑正是在这一阶段生成。
- **实现（每仓子进程隔离）**：`run` 层把实现下放给以仓库为 cwd 的子 Agent 进程，
  runner 亲自执行 checks。全局视野**不扩张为全局写权限**：无论哪种模式，写路径都经过
  分支门禁、verdict、checks 的 fail-closed 链。

## 双模式任务模型

两种任务入口，同一个机制底座。scenario 从"必选容器"降级为"可选加速器"：

| | scenario 任务 | 自由任务 |
| --- | --- | --- |
| 拓扑来源 | scenario.yaml 预声明（order / repos / depends_on） | Planning Pass 全局分析现场生成，由 task 文件自声明 |
| 候选仓库集 | scenario.yaml 直接给定 | registry + 基线图圈定候选 → Planning Pass 核实 |
| 适用形状 | 复现的协调形状（如契约变更波及下游） | 一次性 / 尚未定形的跨仓需求 |
| 任务文件 | spec / status / validation / decisions / verdicts | 相同 |
| Gates | Planning Gate → Spec Review Gate | 相同，无任何豁免 |
| 执行层 | `run`：每仓子进程 + verdict + checks | 相同，仅 order 来源不同 |
| 完成语义 | Completion State Protocol | 相同 |

两处仅有的实质差异，都在"拓扑从哪来"：一是 task 文件记录 `mode` 字段
（`scenario:<name>` 或 `free`，供 `list-tasks` 过滤与协议分支判断），二是依赖就绪段
（dependency readiness）的初始化来源——scenario 任务从 scenario `depends_on` 初始化，
自由任务从 planning 产出的任务级依赖边初始化。

模式选择规则：请求能匹配已声明 scenario → scenario 任务（保留既有识别协议）；不匹配或
明确为一次性需求 → 自由任务。自由任务是**协议化的一等入口**，不是绕过协议的逃生门——
此前"无匹配则必须问用户"的规则改为"问用户：选 scenario，还是走自由任务"，且自由任务
同样要在 spec.md 记录模式选择理由。同一自由形状反复出现时，再固化为 scenario（该
"scenario 合成"方向见验证策略一节的已知缺口，实现不在本设计范围）。

## Repo Registry 与基线依赖图

### 事实分层

scenario.yaml 的 `repos` 条目目前混装两类事实（见
`scenarios/example-contract-change/scenario.yaml`）：

- **仓库固有属性**：path、description、instruction_sources、key_files、checks——不随场景
  变化的"怎么在这个仓库里工作"。
- **场景目的属性**：role、outputs、depends_on、在 order 中的位置——只在特定协调目的下
  成立的关系。

新增强 harness 层 `repos.yaml`，承接固有属性并内联基线图（Q2 已定：单文件合一）：

```yaml
repos:
  profile-api:
    path: ../profile-api
    description: Owns the source-of-truth profile contract.
    instruction_sources:
      - AGENTS.md
      - CONTRIBUTING.md
      - README.md
    key_files:
      - openapi.yaml
      - src/contracts/
    checks:
      - npm run typecheck
      - npm test

edges:
  - from: profile-web
    to: profile-api
    evidence: "package.json depends on @company/profile-client"
  - from: notification-worker
    to: profile-api
    evidence: "consumes contract payload types for notification events"
```

scenario.yaml 是否瘦身为引用式写法，是待决问题 Q3；本设计不强制迁移。

### 语义边界（成文约束）

对 `edges` 的约束是本设计的承重墙，逐条成文：

1. **只声明存在性**：一条边断言"from 与 to 存在依赖往来"，附 `evidence` 证据字段。它
   不是"from 必须在 to 之后改"，不编码方向性义务。
2. **无排序权威**：执行顺序与依赖方向的唯一权威，scenario 任务是 scenario.yaml 的
   `order` + `depends_on`，自由任务是 task 文件里 planning 产出的自声明拓扑。基线图
   两边都不参与。
3. **不 gate 任何行为**：任何命令不得因图的内容拒绝执行或改变执行顺序。图的全部用途
   是给 Planning Pass 提供候选邻域起点。
4. **目的性边仍归 scenario**：`depends_on` 的 `reason` 字段是目的性语义的一部分
   （同一对仓库在契约变更场景有边、在 CI 配置场景可以无边），这类声明不进基线图。
   基线图是剥离目的后的残余：跨场景稳定存在的关系。
5. **漂移容忍**：图过时的后果上限是候选集起点错误，由 Planning Pass 对仓库现实的核实
   （读 import、package.json、生成代码来源）纠正。因此图可以也应该保持粗粒度，不追求
   完备。图的角色是**已知关系的缓存**：命中省分析预算，漏掉由分层机制兜底——工作区级
   反查（自由任务协议流程第 5 步）、Spec Review 人工审批、声明式通道的机器推导（Q4-b）。
   错误不对称：多边只产生便宜排除的多余候选，漏边才是危险方向，因此策展宁多勿漏，协议
   义务全部瞄准漏边一侧。

与"跨场景派生 union 视图"（此前讨论的 `graph` 只读聚合命令）的关系：两者可以共存且
输入不同——union 视图聚合各 scenario 的目的性边（带出处），基线图是手写的目的无关边。
派生视图的搭建触发条件（第二个 scenario 出现且共享仓库）不变。

## Spec 分层所有权（Spec Ownership Layering）

任务的设计描述分两层拥有，workspace 永不复述单仓层：

| 内容 | 拥有者 | 在另一层的形态 |
| --- | --- | --- |
| 受影响仓库集、顺序、依赖边 | workspace task spec | 本体 |
| 仓间契约、接口变更、兼容性决策 | workspace task spec | 本体 |
| 跨仓验证策略、单仓判定证据、候选集与排除记录 | workspace task spec | 本体 |
| 单仓实现设计（该仓有本地 spec 框架） | 仓内框架（Trellis / Spec Kit / OpenSpec…） | workspace 持引用（仓、路径、覆盖范围） |
| 单仓实现设计（无框架，或框架不支持文档级创建） | workspace task spec | 内联回退，实现期转录 |

动机与依赖图的"第三份副本"论证同源：复述即第二份权威副本，必然漂移且漂移无审计面。
引用而非复述消灭漂移面；评审者沿引用跳仓的成本由多仓共存兜底（一次 Read）。

### 仓内 spec 的生成时序（方案一）

**由规划主会话（单一上下文）在规划期直接写入仓内框架位置**，实现期子 Agent 读现成
spec 实现，不再自行设计。曾被考虑并否决的时序：

- **运行期物化（原方案 A，否决）**：Spec Review 批准的只有跨仓 spec + 一堆尚不存在的
  引用——单仓详细设计从产出到落地不经过任何人（verdict 管交付语义、checks 管代码
  健康，都不管设计质量）；且每仓 spec 由隔离子会话各自撰写，契约消费方式各说各话。
  设计评审空洞 + 连贯性碎裂，两洞都致命。
- **分段 run（原方案二，否决）**：先 spec-only 跑一遍、逐仓评审、再实现。保持规划期
  零写入，但 runner 新增模式、评审轮次 × N、串行等待，仪式成本高。
- **内联后升格（原方案三，否决）**：详细设计内联 workspace（可评审），实现期转录进
  框架。零协议改动，但转录保真无人核对，"引用不复述"迟至实现期才达成。

方案一的依据：**连贯性错误不可自动修复，格式错误可以**——格式偏差在 Spec Review 人审
时可见、实现期可用框架工具修正；两份 spec 对同一契约的矛盾描述没有任何机器层能兜住。

单 session 撰写的诚实代价：主会话以 harness 为 cwd，仓内运行时（hooks、框架 CLI、
skills）不激活，spec 撰写走**文档级合规**——读 instruction_sources 声明的工作流文档、
按其约定格式手写。这与 harness 全部既有路径同构（`docs/subprocess-agent-run.md`
"文档级合规路径"结论），不引入新依赖。两层补救：

- **实现期运行时对账**：子 Agent 以仓为 cwd 启动（运行时已激活）后，先执行框架自身的
  脚手架/注册流程（任务 ID、校验 hooks），再把规划期写好的 spec 内容并入——内容以
  规划版为准，对账 diff 在仓内可见。形式由运行时补齐，语义由单会话保证。
- **回退规则**：框架本质上无法文档级创建条目（必须先过运行时注册）时，该仓设计内容
  回退为 workspace task files 内联，实现期转录；回退须在 spec 中显式记录（"该仓框架
  不支持文档级创建"），不允许静默降级。

角色分工（与"既有分工"三分一致）：spec 生成属综合类，不派 subAgent——subAgent 的正式
类别是**规划期只读摄取**（原"key_files 策展失效时应急探索"槽位是其特例，被泛化收编）；
子进程 Agent 的职责起点从"设计并实现"改为"对账并实现"。

### 协议精确化（三边界，防"spec 条目"成为绕过实现门禁的后门）

1. **位置白名单**：仅允许写入各仓框架声明的 spec 目录（自 instruction_sources /
   key_files 推导）；白名单外的仓内写入仍被"Spec Review 批准前不得编辑业务仓"禁令
   覆盖。
2. **分支前提**：spec 写入发生在 preflight 已核验的任务分支上，与实现同分支、同批交付。
3. **diff 评审**：Spec Review 检查清单加入"逐仓查看 spec 条目 diff"，越界写入在评审中
   可见。

write-back 规则相应精确化（README Knowledge Model 修订）：harness 绝不写回仓内**常设
知识**（instruction_sources 指向的工作流与规范）；任务期的仓内工件（spec 条目）按仓规
由规划会话文档级创建、由仓内会话运行时对账，workspace task files 引用而绝不复述。

## 自由任务协议流程

新协议 **Free Task Protocol**，与既有协议并行，复用全部既有词汇与文件：

1. **模式选择**：用户请求无法匹配 scenario（或明确一次性）→ 提议自由任务；选择记录于
   spec.md（模式 + 理由）。
2. **初始化**：`init-task --free <task-id> --request "..."` 从 templates 脚手架同样四个
   文件，`mode: free` 写入 status.md；期望分支规则与 scenario 任务一致（缺省
   `scenario/<task-id>`，或 `--branch` / `--repo-branch` 覆写；用户未指定时按 Task
   Directory Protocol 询问）。
3. **候选圈定**：读取 `repos.yaml`；从用户点名的仓库出发沿 edges 收集候选集；候选及其
   出处（图边 evidence 或用户明示）记入 spec.md。**方向规则**：改仓库 X 时必查 X 的
   入边邻居（消费 X 产物的仓库——波及方向）；X 的出边邻居（X 消费的上游）默认不受
   影响，仅当需求本身要求上游变更时才纳入候选；禁止只做出边遍历。图为空或不存在时，
   候选集 = 全部注册仓库或用户指定集合。
4. **Planning Pass（单上下文、全局）**：对每个候选核实仓库现实（真实依赖关系，而非仅
   图边），确定受影响仓库集、顺序、每仓预期变更、契约与兼容约束、下游影响、验证策略，
   写入 spec.md 与 status.md 的 per-repo 状态表；依赖就绪段从任务级依赖边初始化。
   未入选的候选记录排除理由（可审计、可恢复）。随后按「Spec 分层所有权」一节撰写各仓
   spec 条目——规划主会话单上下文、文档级写入仓内框架位置；workspace task spec 只持
   跨仓层与引用。
5. **单仓结论的判定义务**：单仓是推导结论，不是前提。当且仅当三个条件同时成立才允许
   把任务定为单仓：（a）**工作区级反查**在全部注册仓库上机械扫描对 X 产物的引用
   （import、manifest 依赖、API 路径、事件名）无命中——图命中可缩减扫描范围，图为空
   或存疑时扫描全集；（b）X 的每个图入边仓库经仓库现实核实并记录排除理由；（c）出边
   上游确不需要变更。反查必须独立于图遍历——图不完备正是它要补偿的对象，不允许
   "遍历图入边为空"单独作为单仓依据。证据与排除记录落盘 spec.md。
6. **Gates**：Planning Gate 与 Spec Review Gate 照常。Spec Review 对自由任务是**人工
   批准生成拓扑的控制点**——它替代了 scenario 模式里"拓扑预先由人声明"的控制，而不是
   额外的官僚步骤。评审对象（两模式同构）：workspace 跨仓 spec + 各仓 spec 条目 +
   逐仓 spec diff（边界见「Spec 分层所有权」一节）。
7. **实现**：Implementation Repo Entry Protocol 逐仓执行，路径解析自 registry；子
   Agent 先**运行时对账**（执行框架脚手架/注册流程，并入规划版 spec，内容以规划版为
   准），再按仓内 spec 实现；`run` 按 task 声明的顺序走每仓子进程 → verdict →
   checks，与 scenario 任务完全同构。
8. **中途扩集**：实现中发现新的受影响仓库 → 等价适用 Replanning Protocol：
   `replanning_required` → 对受影响边重跑 planning → spec review 重新审批 → 继续。
   扩集与理由记入 decisions.md（详见待决问题 Q5）。

fail-closed 不变量：`run` 对无 gates 记录的自由任务与 scenario 任务一视同仁地拒绝
（exit 2）；仓库完成仍需 exit 0 + 有效 `ok` verdict + checks 通过三者齐备。Status Step
Vocabulary 一个词都不需要新增——词汇表本身与模式无关，这是"薄扩展"的直接证据。

## 与现有协议和 CLI 的映射

### AGENTS.md（CLAUDE.md 为其镜像，同步修改）

| 章节 | 修改 |
| --- | --- |
| Core Rules | 增一条：harness 协调一个多仓工作区；业务仓库登记于 `repos.yaml`（或由 scenario.yaml 声明）；仓库只能经任务协议进入编辑 |
| Execution Protocol | 步骤 1 改为"用 Task Mode Selection Protocol 选择模式"；步骤 2–4 按模式分流（scenario → 读 scenario.yaml + validate-scenario；free → 读 repos.yaml + validate-registry） |
| Scenario Identification Protocol | 更名/扩展为 Task Mode Selection Protocol：保留原判定；新增"无匹配或多重匹配时，向用户提供自由任务选项"，自由任务同样记录选择理由 |
| Planning Pass Protocol | "resolve the repo path from scenario.yaml" → "from scenario.yaml 或 repos.yaml"；依赖就绪段初始化来源两分；新增义务：按「Spec 分层所有权」以单上下文文档级撰写各仓 spec 条目（两模式同享）；增补只读 subAgent 摄取规则（四边界；综合与 spec 撰写不可委托） |
| Spec Review Gate Protocol | 「批准前不得编辑业务仓」精确化：业务仓**代码**仍禁改，仓内框架 spec 目录内的条目写入是评审介质本身（位置白名单约束）；评审对象加入各仓 spec 条目与逐仓 diff |
| Implementation Repo Entry Protocol | 同上，第 2 步路径解析两分；新增首步：运行时对账（框架脚手架/注册 + 并入规划版 spec） |
| Task Directory Protocol | 自由任务命名 `YYYY-MM-DD-<short-topic>`（无 scenario 后缀）；spec.md 记录 mode |
| Status Step Vocabulary | 无修改（词汇模式无关） |
| YAML Semantics | 新增 `repos.yaml` 一节：repos 映射语义 + edges 语义（上文五条边界约束的规范表述）+ 沿用任务级取值禁令 |
| Agent Helper CLI | 登记新子命令与既有子命令的自由任务变体 |
| Replanning Protocol | 增补：适用于自由任务中途扩 repo 集 |

### README.md / README.zh.md（双语同步）

- Knowledge Model：三层模型外新增工作区层（registry——静态、harness 持有、仓库固有
  事实与基线图）；`scenario.yaml is the glue` 表述改为"glue 之一"；知识流单向性精确化
  ——仓内常设知识绝不写回，任务期 spec 条目按仓规文档级创建、运行时对账，workspace
  引用而绝不复述。
- When To Use This、Running A Task、Expected Agent Behavior：加入自由任务入口与流程。
- Agent-First Docs 必读顺序加入 `repos.yaml`。
- Repository Structure 图加入 `repos.yaml`。

### CLI 子命令

| 命令 | 修改 |
| --- | --- |
| `validate-registry`（新增） | 校验 repos.yaml：结构、边端点存在、path 解析为 git 仓库、无任务级取值；按 Q3 阶段对 scenario repo key 集合做交叉核对 |
| `validate-scenario` | 主流程不变；Q3-B 阶段增加 warning 级"scenario 与 registry 不一致"提示（不 error） |
| `init-task` | 增加 `--free` 变体：跳过 scenario 校验（改跑 validate-registry），task 文件记录 `mode: free`，分支规则不变；scenario 用法原样 |
| `preflight` | 新增按 `--task` 驱动的模式：repo 集来自 task 声明 + registry 解析；scenario 用法原样 |
| `plan-scenario` | 不变（scenario 专用加速器） |
| `list-tasks` | scenario 参数变可选：缺省列出自由任务（mode 过滤，替代现在的字符串 haystack 匹配 `bin/scenario-harness:1006`） |
| `checks` | check_matrix（`:1041`）接受 registry/task 声明的 checks 来源；scenario 用法原样 |
| `run` | 见下 |
| `graph`（新增，后置） | 派生 union 视图：聚合各 scenario `depends_on` + registry edges，带出处，只读不裁决 |

**`run` 的关键缝（seam）只有一个**：`cmd_run:2304` 的 `context = scenario_context(...)`。
context 携带按序 repo 列表（含 instruction_sources / key_files / checks），其后一切
（prompt 渲染 `:2360`、分支门禁、verdict、checks）都消费这个 context，不关心它来自
scenario 还是 task 声明 + registry 解析。gates 预检读取的 status.md 章节与
`current step:` 秩（`STATUS_STEP_RANK`，`:1654`）本来就是模式无关的。即自由任务对
执行层的改动 = 换一个 context 构造函数。

## 待决设计问题

### Q1 基线图边的方向性

- **A（推荐）有向边 + evidence 字段**：`from → to` 表示 from 依赖/消费 to。信息密度高，
  匹配消费方向，候选圈定天然不对称（改 to 时收集 from 集）；代价是声明更强、需要 evidence
  纪律约束过时风险。
- **B 无向边**："有往来"。声明最弱、最不易过时；但丢失消费方向，候选圈定退化为对称遍历，
  对排序分析帮助小。
- **已定（2026-08-23）：A**。evidence 把声明成本转化为 Planning Pass 可核对性，方向性
  正是全局分析最需要的那一维；成文"方向 ≠ 排序义务"。字段级规格：`(from, to)` 为自然键
  （重复边属校验错误，不设 id）；`evidence` 为非空纯字符串，不结构化、不解析语义——兼容
  PyYAML 缺席时的子集解析器（`bin/scenario-harness:152-162`）。背景判断（用户，2026-08-23）：
  日常任务中仓库边界明显、依赖关系不是瓶颈——图层保持最小机制，价值投资集中在跨仓
  spec 层与 gates。

### Q2 registry 与图合一还是分文件

- **A（推荐）单文件 `repos.yaml`**（repos + edges 内联）：文件少、一次校验；边变更会
  混入仓库条目的变更历史。
- **B 分离 `repos.yaml` + `graph.yaml`**：边的演化历史干净、可供外部工具单独消费；两个
  文件要保持同步，小数据量下仪式感偏重。
- **已定（2026-08-23）：A**。B 的触发条件保留为演进信号：edges 高频独立演化，或外部
  工具需要单独消费图；在"边界明显、边集小而稳"的当前现实下不构成触发。

### Q3 scenario.yaml 是否迁移为 registry 引用式

- **A 全量迁移**：scenario.yaml 只留目的属性 + repo key 引用，固有属性归 registry。一步
  到位但 breaking：所有场景、文档、校验同时改。
- **B 渐进附加**：registry 先建为自由任务的种子；scenario.yaml 保持自包含
  （fail-closed 校验不依赖 registry 存在）；validate-scenario 增加 warning 级一致性
  提示收敛漂移；全量迁移推迟到自由任务真实运行后再评估。
- **C 不迁移**：registry 仅服务自由任务。零风险，但同一仓库的 instruction_sources /
  checks 在两处维护，漂移无信号。
- **已定（2026-08-23）：B**。scenario 的自包含性是既有 fail-closed 性质的一部分，
  不为新增入口冒险拆掉；warning 提示让 C 的漂移问题有观测面；A 作为后续演进保留
  （触发条件：自由任务真实运行后重估）。

### Q4 校验职责（validate-registry 范围）

- **必做（推荐先行）**：结构校验、边端点存在于 repos、path 解析且为 git 仓库、无任务级
  取值（沿用 scenario.yaml 的禁令）、evidence 非空（不解析语义）。
- **可选 a——静态一致性**：scenario repo key ⊆ registry keys、path 一致（warning 级，
  随 Q3-B）。
- **b——现实核对（指定完备性机制）**：扫各仓库 package.json / go.mod / import 与
  edges 对照。定位是**声明式依赖通道的完备性机制**而非可选糖：先以协议义务形态存在
  （协议流程第 5 步的工作区反查），后固化为 CLI 命令。推导链两头都可从仓库自身读出：
  各仓 manifest 自带包名 / module path → 包归属映射，无需人工登记 outputs；他仓依赖
  声明命中归属 → 产出边 `consumer → producer`，evidence 自动生成（如 `package.json:
  @company/profile-client@^2`），方向与 Q1 有向边同构。机器盲区（运行时 HTTP/gRPC
  耦合、事件/异步消费、跨仓重复定义、组织性意图）仍归人工标注——edges 演进为
  "机器推导 + 人工标注"两半。落地形态：**建议-确认**（扫描器输出 missing / stale /
  contradicted 差异报告，批准后落盘）或**读取时合成**（repos.yaml 只存人工边，有效图
  = 声明边 ∪ 派生边，消费时现算），两者可组合；排除静默自动写入——污染人工文件的变更
  历史，且违反机械层不擅自改声明的一贯立场。两个边界：依赖声明可能指向已发布旧版本而
  非工作区 HEAD，派生边仍是存在性声明、语义核实不省；包名归属冲突（一包多仓、一仓
  多包）需要仲裁，归入必做校验。
- **已定（2026-08-23）：按推荐执行**——必做项 + a 先行；b 的协议义务形态（工作区反查）
  随自由任务实现即刻生效，CLI 固化后置。

### Q5 自由任务中途扩 repo 集

- **A Replanning 等价适用**：发现新受影响仓库 → `replanning_required` → 对受
  影响边重跑 planning → spec review 重新审批 → 继续；扩集与理由记 decisions.md。与
  scenario 任务语义完全一致，协议无新词。
- **B 允许 planning agent 自主扩集免重审**：灵活，但拓扑生成正是自由任务最需要人类控制
  的点，免重审会把 Spec Review 的批准对象变成过时快照，破坏 fail-closed。
- **已定（2026-08-23）：A**。

## 迁移与兼容

- **example-contract-change 不动**（Q3-B）。registry 落地后可把三个仓库登记进 repos.yaml
  作为首个真实内容——这属于实现阶段的工作，不在本设计文档范围。
- **既有 scenario 任务链路行为基本不变**：所有现有子命令的 scenario 用法、scenario.yaml
  语义零改动；自由任务是纯增量入口。例外是协议层的 Spec 分层所有权（含 Spec Review
  评审对象扩充、运行时对账首步）——它对两种模式同享，属协议演进而非自由任务特性；
  gates 机制本身（存在性、词汇、fail-closed 判定）零改动。
- **task 文件兼容**：status.md 增 `mode` 字段；旧任务文件无该字段按 `scenario:*` 解释
  （`list-tasks` 的缺省行为不变）。
- **文档协议**：AGENTS.md 与 CLAUDE.md 镜像同步；README.md 与 README.zh.md 按既有双语
  镜像惯例同步修订。

## 验证策略

- **静态**：`validate-registry` 必做项（Q4）；`validate-scenario` 的 warning 交叉核对。
- **行为（mock e2e 扩展）**，沿用 `tests/run_mock_e2e.py` 的零外部副作用模式：
  1. 自由任务 init → task 文件含 `mode: free`、分支缺省正确；
  2. **fail-closed 断言**：无 gates 记录的自由任务被 `run` 拒绝（exit 2），与 scenario
     任务同路径同类别（`planning_gate_missing` / `spec_review_gate_missing`）；
  3. task 声明的 order 被尊重（非 scenario order）；
  4. verdict ok / missing / blocked / invalid 四路径在自由任务上语义不变；
  5. checks 来源为 registry 声明。
- **验收语义（可判定表述）**：自由任务与 scenario 任务在 gates、分支门禁、verdict、
  checks 上的拒绝路径与完成条件**不可区分**——这是"共享执行层"的机器可验证形式。
- **Spec 分层证据（协议层，人工核对）**：Spec Review 时各仓 spec 条目已在盘（或该仓
  回退已显式记录）；workspace spec 中引用路径可解析。runner 不校验条目内容——对账
  diff 归仓内与评审，属 Spec Review 的人工证据项。
- **已知缺口（residual risk）**：图的召回缺口（漏边）无法靠图自身消除。协议层补偿：
  第 5 步的工作区级反查义务（脱离图遍历、在全集上机械执行）；机器层补偿：Q4-b 的
  声明式通道推导。机器盲区通道（运行时耦合、事件消费、重复定义）仍属 planning 质量，
  由 Spec Review Gate 人工审批兜底。scenario 合成（自由形状固化为 scenario 的辅助
  流程）为后续演进方向，不在本设计范围。

## 状态

设计完成（本文件 + `docs/diagrams/freeform-workspace.*` 配图），对应 Goal Contract
`docs/goal-contracts/2026-08-22-multi-repo-workspace-design-v2.md`。实现未开始：
`bin/scenario-harness` 修改、AGENTS.md / CLAUDE.md / README 双语修订、repos.yaml 落地
均属后续执行 Goal。待决问题（2026-08-23）**全部拍板**：Q1=A（有向边 + evidence，
字段级规格见条目）、Q2=A（统一单文件 repos.yaml）、Q3=B（渐进附加 + warning 交叉
核对）、Q4=按推荐（必做项 + a 先行；b 协议义务即刻生效、CLI 固化后置）、Q5=A
（replanning 等价适用）。**设计定稿**；下一步为实现 Goal（另立 Goal Contract）。
评审补充（2026-08-23，第三轮）：规划期分工精确化为摄取/综合/实现三分——只读 subAgent
摄取被正式允许（四边界：只读、蒸馏物带 file:line 引文、结果落盘 task notes、允许而非
强制），综合与 spec 撰写仍单上下文不可委托；原"应急探索"槽位被泛化收编。
评审补充（同日）：候选圈定方向规则、单仓判定义务（工作区级反查）、Q4-b 升级为声明式
通道的指定完备性机制（edges = 机器推导 + 人工标注，建议-确认 / 读取时合成）。
评审补充（同日，第二轮）：Spec 分层所有权（跨仓层归 workspace；单仓层有框架则引用、
无框架或框架不支持文档级创建则内联回退）；仓内 spec 由规划主会话单 session 文档级撰写
（连贯不可修、格式可修），否决运行期物化（设计评审空洞 + 连贯性碎裂）、分段 run、内联
后升格；实现期运行时对账；位置白名单 / 分支前提 / diff 评审三边界；write-back 规则
精确化为"常设知识绝不写回、任务期工件按仓规创建"。协议层修订对两种模式同享。
