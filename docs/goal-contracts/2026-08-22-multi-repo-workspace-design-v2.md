# Goal Contract v2

状态：GOAL CONTRACT 已确认（2026-08-22）

## Goal
为 scenario-harness 产出以"多仓共存工作区"为核心价值的设计文档：跨仓需求（自由需求与 scenario 需求）由 Agent 在全局视角下编排分析；scenario 模式与自由模式是同一工作区能力下的两种任务入口，共享同一套 gates 与执行层。

## 交付物
- `docs/freeform-task-design.md`（中文设计文档），必含章节：
  - **核心价值与工作区模型**：多仓共存于 Agent 工作区 → 全局视角编排分析；规划单上下文 / 实现每仓子进程的既有分工（`run` 层已实现）如何承载该价值，并显式保留
  - 双模式任务模型：scenario 任务（拓扑预声明，可复用加速器）vs 自由任务（全局分析现场生成拓扑），两种入口汇入同一 Planning Gate / Spec Review Gate / verdict / per-repo run
  - repo registry + 基线依赖图：**定位为全局视角的索引与加速器**（圈定候选邻域、定位关键文件），非机制本体；语义边界成文——存在性边 + 证据字段，无排序权威，不 gate 任何行为
  - 自由任务协议流程：初始化 → 图/registry 圈定候选仓库 → Planning Pass 全局影响分析 → task 自声明 repo 集与顺序 → gates → per-repo 执行
  - 与现有 AGENTS.md 协议及 CLI 7 个子命令的映射与修改点清单
  - 5 个待决设计问题的选项、取舍与推荐
  - 迁移与兼容策略（example 场景处置）、验证策略
- 分层/流程图一张，落盘 `docs/diagrams/`（形式 mermaid 或 drawio 由 Agent 定，遵循现有目录惯例）

## 范围
In scope：
- 设计文档与图
- 5 个待决问题的选项分析（边方向性、registry 与图文件合一/分离、scenario.yaml 迁移、校验职责、自由任务中途扩 repo 集）
- 对 AGENTS.md / CLI 的修改点清单（仅文档层面）

Out of scope：
- `bin/scenario-harness` 代码实现与 AGENTS.md 正式修订（后续 Goal）
- `repos.yaml`/依赖图的实际内容编写（真实仓库登记）
- 现有 example-contract-change 场景的实际改造

## 验收标准
- [ ] `docs/freeform-task-design.md` 存在且覆盖上述全部必含章节
- [ ] **工作区核心价值成文且贯穿全文**：两种模式均以"全局视角编排分析"为一等能力；registry/图被明确定位为其加速器与索引，而非前提或裁决者
- [ ] 规划阶段单上下文全局分析与实现阶段每仓子进程隔离的分工被显式保留，全局视野不扩张为全局写权限
- [ ] 双模型边界明确：scenario 降级为可选加速器，两种模式共享同一套 gates 与执行机制
- [ ] 图的语义边界成文：仅存在性声明 + 证据字段，不决定执行顺序，不 gate 任何行为；任务级依赖/影响由 Planning Pass 全局分析单独产出
- [ ] 5 个待决问题每项含：互斥选项、影响取舍、明确推荐
- [ ] 修改点清单精确到 AGENTS.md 章节 / CLI 子命令粒度
- [ ] 设计不破坏 fail-closed 性质：自由任务同样强制过全部 gates
- [ ] 文档风格与 `docs/` 现有文档一致

## 上下文与依赖
- 本对话已收敛的结论：图"权威性"反对意见的化解（图仅为加速器）、repo 事实下沉的重构机会、gate 保留原则
- **用户核心价值声明**：多仓共存工作区使跨仓需求（自由/scenario）可被全局视角编排分析，此为项目最核心价值
- `scenarios/example-contract-change/scenario.yaml`（现状参考：仓库固有属性与场景目的属性混写）
- `AGENTS.md` 协议语义、`bin/scenario-harness` 现有 7 个子命令（均强制 scenario 参数）、`run` 层已实现的单上下文规划/每仓子进程分工
- `docs/goal-contracts/` 既有契约惯例、`docs/diagrams/` 图示惯例
- 用户偏好：权衡分析先行、契约可按文件引用恢复、README 双语（README 层面，不强制适用于 docs/）

## 决策权限
Agent 可自主决定：
- 文档章节组织、图示形式与工具（mermaid / drawio）
- 5 个待决问题的推荐取向（对话已有倾向：有向边 + 证据字段、文件合一、gates 原样适用、扩集走 replanning gate）
- 文档语言（中文单份；README 双语惯例不适用于 docs/）

必须询问使用者：
- 设计方向性变更（放弃 registry 分层、改变 gate 适用性、动摇单上下文规划/每仓实现分工等）
- 5 个待决问题的最终拍板（文档 review 时确认，实现前定案）

## 验证方式
- 验收标准逐条自检
- 与 AGENTS.md 语义逐节核对，确保设计不引入未定义行为或与现行协议冲突的表述
- 使用者 review 设计文档

## 停止与升级条件
- 完成：文档 + 图落盘，验收标准全部勾选
- 止损：设计推演中发现与现有 fail-closed 协议或单上下文/每仓分工存在无法调和的根本冲突
- 升级：任何需要不可逆决策或大范围协议语义重解释的事项

## 已记录假设
- 自由任务复用 `tasks/` 目录与既有 task 文件结构（spec / status / validation / decisions / verdicts）
- 全局视角主要服务于规划/编排阶段；实现阶段保持每仓子进程与 fail-closed gates（与已实现 `run` 层分工一致）
- 图采用有向粗粒度边 + 证据字段（待决问题 1 的推荐项，最终以确认为准）
- 契约落盘遵循仓库惯例 `docs/goal-contracts/`（而非 skill 默认的 `./goal-contracts/`，因仓库已有既存契约目录）
