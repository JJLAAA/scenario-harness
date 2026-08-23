# Goal Contract v2

状态：GOAL CONTRACT 已确认（2026-08-23）

## Goal

新增只读子命令 `bin/scenario-harness check-task <task-id>`：以 `templates/` 章节骨架为公共核心基准，对任务四文件做结构 lint（两模式同构生效、三处模式感知），使 templates/ 从无人消费的文档升级为任务文件 schema 的声明式来源。

## 背景（自包含）

- 现状：`init-task` 不读 `templates/`（生成走代码内嵌的 `render_task_files` / `render_free_task_files`），templates/ 仅剩"helper 不可用时人工复制"（AGENTS.md Task Directory Protocol）与"章节样板"两个轻作用，且与 CLI 内嵌渲染构成需人工同步的双源。
- 已否决的替代方案：删除 templates/（丢灾备路径且需改协议文档）；单一来源渲染（给人复制的模板与给程序填充的模板受众冲突，动态段落本就无法进模板）。
- 方案 A 的定位：与 `validate-scenario`（校验 scenario.yaml）、`validate-registry`（校验 repos.yaml）同构成闭环——声明在哪，校验就在哪；`check-task` 补任务层。
- 两种任务模式文件格式同构（设计定稿），故 lint 核心检查模式无关；自由任务的 per-repo 表**行序即执行顺序**（`read_task_repo_rows` 消费），是其独有的承重点。
- 模板即 schema 的传播语义：**公共核心章节集合运行时从 templates/ 提取**——模板增删章节即变更 schema，check-task 下次运行自动生效，零代码改动；模式归属映射与 error/warning 分级归置留在命令代码里，不随模板自动传播；lint 只查章节存在性，不查内容。

## 交付物

1. **`check-task <task-id>` 子命令**（纯只读，不写任何文件）：
   - 公共核心检查：四文件存在；必备章节存在（基准 = 运行时从 templates/ 骨架提取的章节集合）；`current step` 取值在 Status Step Vocabulary 内；per-repo 表形状合法（列数、分支单元格）；gates 章节存在
   - 三处模式感知（代码内映射）：
     | 检查点 | scenario 任务 | 自由任务 |
     | --- | --- | --- |
     | `Mode:` 行 | `scenario:<name>` 且该 scenario 存在 | `free` |
     | 表行 repo 来源 | 必须解析到对应 scenario.yaml | 必须解析到 repos.yaml |
     | 模式专属章节 | `Scenario Order` | `Task-Declared Topology` + `Candidate Scoping` |
   - finding 分级原则：**error = 形状非法**（文件缺失、章节缺失、step 不在词汇表、表列错位、mode 值非法、repo 解析失败）；**warning = 阶段性不完整**（gates 未记录、表无行、mode 行缺失——旧任务兼容、free 任务 Candidate Scoping 仍为 TBD）。warning 不改变退出码。
   - 报告沿用 validate-* 风格（finding 列表 + `--json`）；退出码 0/2/64
2. **`templates/` 骨架对齐**：`templates/spec.md` 补 `Task Mode` 段（当前缺失，而 CLI 生成器已有），使其成为合格的公共核心基准；不为两模式拆分模板变体——模式专属要求留在命令代码里
3. **测试**：`tests/run_mock_e2e.py` 扩展——
   - 合法 scenario 任务与自由任务各一（gate-ready 形态）exit 0
   - 破坏变体（删章节 / 非法 step / 表行 repo 未登记 / 非法 mode 值）exit 2 且 finding code 命中
   - 旧式任务（无 Mode 行）与 gates 未记录仅 warning、exit 0
   - **自洽性锁定**：两模式 `init-task` 刚生成的任务对 `check-task` 零 error（允许且仅允许阶段性 warning）——模板基准与生成器的同步由测试强制
4. **文档登记**：AGENTS.md Agent Helper CLI 登记 `check-task`（+ CLAUDE.md 镜像）；README.md / README.zh.md 各一处恰当提及（双语镜像），说明模板即 schema、增删章节自动传播的边界

## 范围

In scope：
- 上述四项交付物

Out of scope：
- 单一来源渲染（方向 B）、删除 templates/
- 内容质量检查（内容归 Spec Review 人工，lint 只查形状）
- 改动 run / preflight / checks / init-task 的既有行为
- 新增 Status Step 词汇或改变任务文件语义
- CI / git hook（测试触发维持手动跑套件；CI 另立任务）
- git commit（由用户另行指示）

## 验收标准

- [ ] `check-task` 对结构完整的两模式任务均 exit 0、零 error
- [ ] 形状非法各变体 exit 2 且 finding code 可判定（含模式感知三处：坏 mode 指向、表行不在对应声明层、模式专属章节缺失）
- [ ] 旧式任务（无 Mode 行）与阶段性不完整（gates 未记录）仅产生 warning，exit 0
- [ ] `--json` 输出结构与 validate-* 报告风格一致；退出码 0/2/64
- [ ] templates/spec.md 含 Task Mode 段；`check-task` 的章节基准实际从 templates/ 运行时提取（而非代码内再抄一份）
- [ ] **自洽性**：两模式 init-task 新生成任务对 check-task 零 error（阶段性 warning 之外）
- [ ] mock e2e：既有 20 用例零回归 + 新增用例全绿
- [ ] AGENTS.md 与 CLAUDE.md 登记一致；README 双语提及镜像对齐

## 上下文与依赖

- 实现参照：`validate_registry` / `validate_scenario` 的 finding 组织、`read_task_mode` / `read_task_repo_rows` / `STATUS_STEP_RANK`（既有解析与词汇表直接复用）
- 测试沿用 `tests/run_mock_e2e.py` 的临时仓库、零外部副作用模式（`make_task` / `make_free_task` 现成构造器）
- 纯标准库优先；本机无 PyYAML，天然走子集解析器

## 决策权限

Agent 可自主决定：
- finding code 命名、错误消息措辞、报告 JSON/文本结构（沿用 validate-* 报告风格）
- 代码组织与函数放置；章节提取的实现方式（如何从 templates 解析骨架）
- warning/error 的具体条目归置（在分级原则内调整）
- README 双语提及的具体位置与措辞（镜像一致约束下）

必须询问使用者：
- 实现中发现需要改变既有任务文件语义、新增 Status Step 词汇，或需要触碰 run / preflight / checks 行为
- 任何使既有 20 用例回归的必要性
- 范围变更（如把单一来源渲染或 CI 拉入本期）

## 验证方式

- `python3 tests/run_mock_e2e.py`（扩展后全绿）
- CLI 冒烟：对真 harness 临时任务目录跑 `check-task --json`（两模式各一）
- 回归：既有各命令输出比对
- 文档镜像一致性核对（AGENTS/CLAUDE diff、README zh/en 对齐）

## 停止与升级条件

- 完成：验收标准全勾、测试全绿
- 止损：实现中发现 templates 骨架无法用"公共核心 + 模式差异"表达（两模式章节集合存在不可调和冲突），方案 A 前提不成立时停下报告
- 升级：出现需要协议语义变更（词汇表、文件语义）才能继续的设计决定
- 不自动提交：交付为工作区变更，commit 由用户指示

## 已记录假设

- check-task 纯只读，不写任何文件（与 helper CLI"从不编辑业务仓库"一致）
- warning 不改变退出码（沿用 validate-scenario 既有惯例）
- 旧任务文件无 Mode 行合法、按 scenario 解释（既有兼容规则），故 mode 缺失为 warning 而非 error
- templates/spec.md 补 Task Mode 段属本期交付（否则基准自缺核心章节）
- 模板章节增删 = schema 变更：公共核心部分自动传播到 check-task；模式归属与分级归置需改代码；模板与 init-task 渲染器的同步由自洽性测试锁定（新增章节必须同步生成器，否则测试红；锁定单向——模板 ⊆ 生成产物，生成器多产出无害）
- 测试触发维持手动跑套件（无 CI/hook）；CI 为已识别的后续候选任务，触发条件是希望报警自动化
- 代码导出模板（权威翻转）为已记录演进选项，触发条件：任务文件格式变更频繁到同步动作成为真实负担
- 本次仅结构 lint，不涉真实后端
