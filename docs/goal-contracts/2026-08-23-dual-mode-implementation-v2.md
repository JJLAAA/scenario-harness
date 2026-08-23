# Goal Contract v2

> 历史迁移说明：本文件保留项目更名为 RepoMesh 前的名称与命令，以维持当时决策的可追溯性；当前 CLI 为 `bin/repomesh`。

状态：GOAL CONTRACT 已确认（2026-08-23）

## Goal
实现已定稿的双模式设计（`docs/freeform-task-design.md`，Q1–Q5 已全部拍板，含第三轮摄取/综合/实现三分）：落地自由任务入口（repos.yaml registry + 基线图、Free Task Protocol 的 CLI 与协议文档），scenario 链路行为保持零改动，两种模式在 gates / verdict / checks 上不可区分。

## 交付物
1. **CLI（`bin/scenario-harness`）**
   - 新增 `validate-registry`：结构校验、边端点存在、`(from,to)` 唯一、evidence 非空、无任务级取值、path 为 git 仓库；Q4-a 一致性核对（scenario repo key ⊆ registry）为 warning
   - `validate-scenario`：增 warning 级 registry 不一致提示（Q3-B），既有 error 语义与退出码不变
   - `init-task --free`：跳过 scenario 校验（改跑 validate-registry），task 文件记录 `mode: free`，分支规则不变
   - `preflight`：新增 `--task` 驱动模式（repo 集来自 task 声明 + registry 解析）
   - `list-tasks`：scenario 参数变可选，mode 过滤
   - `checks`：接受 registry / task 声明的 checks 来源
   - `run`：`cmd_run:2304` context 缝改造——自由任务 context 从 task 声明 + registry 构造；gates 判定、verdict、checks 逻辑零触碰；prompt 增运行时对账与仓内 spec 引用要求
2. **`repos.yaml`**：格式落地（Q1-A/Q2-A 字段级规格 + 已定完整字段语义：path 解析规则、instruction_sources 公共文件回落、checks 缺省记 validation gap、五字段与 scenario 允许复制带 warning 哨兵）+ example 三仓登记为首个内容
3. **协议文档**：AGENTS.md + CLAUDE.md 镜像修订（设计文档映射表全部行：Task Mode Selection Protocol、Spec 分层所有权与三边界、规划期只读 subAgent 摄取规则（四边界；综合与 spec 撰写不可委托）、Replanning 增补、Agent Helper CLI 登记、YAML Semantics 的 repos.yaml 节）；README.md + README.zh.md 双语同步（Knowledge Model 四层与 write-back 精确化、自由任务入口与流程、必读顺序、Repository Structure）
4. **模板**：`task-status.md` 增 `mode` 字段（旧任务文件无 mode 按 scenario 解释）
5. **测试**：`tests/run_mock_e2e.py` 扩展——自由任务 5 断言（init mode 字段与分支缺省 / 无 gates 被 run 拒绝且同类别 / task 声明 order 被尊重 / verdict 四路径语义不变 / checks 来源为 registry）+ validate-registry 用例；沿用临时仓库、零外部副作用模式

## 范围
In scope：
- 上述五项交付物
- Q4-b 协议义务形态：工作区反查义务写进 AGENTS.md 协议文本与 run prompt 措辞（非代码）

Out of scope：
- `graph` 派生 union 视图命令（触发条件未到：第二个 scenario）
- Q4-b 的 CLI 固化（manifest 扫描器）
- 真实后端验收（沿用既有模式，另立契约）；真实业务仓库运行（用户驱动）
- scenario 合成；git commit（由用户另行指示）

## 验收标准
- [ ] `validate-registry` 必做项全部实现且子集解析器兼容（无 PyYAML 环境可跑）；退出码沿用 0/2/64
- [ ] `validate-scenario` 既有行为回归不变（含 JSON 输出结构），仅新增 warning 项
- [ ] `init-task --free` 产出含 `mode: free` 的四文件、分支缺省 `scenario/<task-id>`；scenario 用法输出不变
- [ ] `preflight` / `checks` / `list-tasks` 自由任务变体按设计工作，scenario 用法不变
- [ ] `run`：自由任务按 task 声明顺序执行；无 gates 记录的自由任务被拒（exit 2，`planning_gate_missing` / `spec_review_gate_missing` 同类别同路径）
- [ ] mock e2e：既有 15 用例全绿不回归 + 新增自由任务断言全绿
- [ ] AGENTS.md 与 CLAUDE.md 修订镜像一致；README.md 与 README.zh.md 结构对齐；设计文档映射表每行都有对应落地（含摄取规则行）
- [ ] `repos.yaml` 存在、格式符合字段级规格、通过结构校验（example 三仓本机未克隆，path error 允许——与 validate-scenario 对 example-contract-change 的现状行为一致）

## 上下文与依赖
- 实现规范唯一来源：`docs/freeform-task-design.md`（含三轮评审补丁与 Q1–Q5 定稿）
- 既有 run 层架构与 `tests/run_mock_e2e.py`（15 用例、零外部副作用）模式
- CLI 约束：纯标准库优先，PyYAML 可选、缺席回落自写子集解析器（`bin/scenario-harness:152-162`）——新增解析路径必须兼容子集
- 文档惯例：AGENTS.md/CLAUDE.md 镜像；README zh/en 镜像；`docs/goal-contracts/` 契约落盘
- 本次仅 mock，不涉真实后端

## 决策权限
Agent 可自主决定：
- finding code 命名、错误消息措辞、代码组织与函数放置
- `validate-registry` 的 JSON/文本报告结构（沿用 validate-scenario 报告风格）
- `repos.yaml` 初始内容以 example 三仓登记
- 自由任务 prompt 复用现有渲染骨架 + mode/task 声明数据的拼装细节
- 模板与文档措辞（在镜像一致约束下）

必须询问使用者：
- 实现中发现与设计文档冲突、需要触碰 gates / verdict / checks 逻辑或修改已定稿协议语义
- 任何破坏"scenario 用法零改动"回归的必要性
- 范围变更（如把 `graph` 命令或 Q4-b CLI 拉入本期）

## 验证方式
- `python3 tests/run_mock_e2e.py`（扩展后全绿）
- CLI 冒烟：`validate-registry --json`、`init-task --free --dry-run`、`run --dry-run`（自由任务与 scenario 各一）
- 回归：既有 scenario 流程各命令输出比对
- 文档镜像一致性人工核对（AGENTS/CLAUDE 对齐、README zh/en 对齐）

## 停止与升级条件
- 完成：验收标准全勾、测试全绿
- 止损：context 缝改造证伪设计假设——无法在不触碰 gates/verdict/checks 逻辑前提下支持自由任务
- 升级：出现 Q1–Q5 与三轮评审之外的新设计决定需求
- 不自动提交：交付为工作区变更，commit 由用户指示

## 已记录假设
- `repos.yaml` 首版登记 example 三仓，本机未克隆故 validate-registry 报 path error（与现状 validate-scenario 行为一致，非缺陷）
- Q4-b 协议义务落点是协议文本与 prompt 措辞，无代码
- 规划期允许只读 subAgent 摄取（四边界）属协议文本，本期无对应代码——综合与 spec 撰写仍单上下文，`run`/执行层不涉 subAgent
- 自由任务对 `run` 的全部改动收敛于 context 构造（设计文档"关键缝"结论）
- Status Step Vocabulary 零新增（设计已确认词汇表模式无关）
