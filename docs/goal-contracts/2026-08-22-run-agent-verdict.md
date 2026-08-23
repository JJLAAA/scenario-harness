# Goal Contract v1

> 历史迁移说明：本文件保留项目更名为 RepoMesh 前的名称与命令，以维持当时决策的可追溯性；当前 CLI 为 `bin/repomesh`。

状态：GOAL CONTRACT 已确认（2026-08-22）

> 本文件是定稿契约，可作为后续执行会话的自包含输入。执行范围仅限本 harness 仓库直改（harness 自研不属于任何 scenario，不进 scenario 协议）；不主动 commit。

## Goal

为 `bin/scenario-harness run` 增加"子 Agent 结构化交付判决（verdict）"机制：仓库标记为 complete 的必要条件从"exit 0 + checks 通过"收紧为"exit 0 + 有效 ok verdict + checks 通过"，失败自报或判决缺失/非法时 fail-closed 地阻断 run。

## 交付物

- `bin/scenario-harness`：verdict 解析与门禁集成、prompt 契约更新、失败分类扩展、telemetry 呈现
- `tests/run_mock_e2e.py`：mock 后端新增 verdict 相关模式 + 4 个新用例
- `docs/subprocess-agent-run.md`：新增"Agent Verdict 契约"一节，更新失败分类表与安全属性
- `AGENTS.md`：helper CLI `run` 描述句补充 verdict 门禁（一句话）
- `README.md` / `README.zh.md`：每仓会话小节各补一句 verdict 契约（中英同步）

## 范围

In scope：

- `render_agent_prompt`（`bin/scenario-harness:2034-2077`）：新增一步——按固定格式写 verdict 文件，给出精确路径与格式
- verdict 解析器 + 门禁插入点：在严格成功映射（`agent_success_is_strict`，`bin/scenario-harness:2011-2031`）通过之后、`run_checks` 之前
- 失败分类新增三个 category（stage `agent`）：`verdict_missing`、`verdict_invalid`、`agent_report_blocked`
- 失败消息与 `run-status` / `run-validation` 标记块携带 blocker 文本
- `--dry-run` 随 prompt 模板自然反映，无独立逻辑

Out of scope：

- 真实后端（真实 claude/codex CLI）验收——保持用户驱动
- 路径 B（NL 关键词签名）与路径 C（runner 内嵌 LLM）
- verdict 内容的语义校验（只验格式与枚举值，不判断"ok 是否属实"——那是 checks 的职责）
- commit / push（用户未要求，不主动提交）

## 验收标准

- [ ] `python3 tests/run_mock_e2e.py` 退出码 0，覆盖：ok verdict → complete；exit 0 无 verdict → blocked（`verdict_missing`）；verdict=blocked → blocked（`agent_report_blocked`）且失败消息含 blocker 文本；格式非法 → blocked（`verdict_invalid`）
- [ ] 现有用例全部不回归（fail/hang/env-dump/多仓顺序/锁等）
- [ ] `run --dry-run` 渲染出的 prompt 包含 verdict 文件路径与格式说明
- [ ] 三处文档与实现一致（失败分类表、安全属性、README 中英同步）

## 上下文与依赖

- 改动对象全部在本 harness 仓库内；harness 自研不属于任何 scenario（仅 `example-contract-change`），按既定惯例走仓库直改，不进 scenario 协议
- 关键锚点：prompt 渲染 `bin/scenario-harness:2034-2077`；严格成功 `2011-2031`；每仓循环与 checks `2285-2395`；fail() 分类落盘 `2220-2237`；mock 控制机制 `tests/run_mock_e2e.py:23-67,201-209`
- 纯 Python 标准库约束不变，零新增依赖

## 决策权限

Agent 可自主决定：

- 函数拆分、解析器实现细节、新 category 命名的微调、测试组织方式
- verdict 模板的具体措辞（不改变语义的前提下）

必须询问使用者（已定版为默认值，确认契约即视为采纳，修改请直接指出）：

- **D1 载体**：`tasks/<task>/verdicts/<repo>.md` 独立文件（非 status.md 标记块、非 stdout 解析）。固定三键格式：`verdict: ok|blocked`、`blocker: <一行>`、`residual_risk: <一行>`
- **D2 判定语义（信任不对称）**：非零退出/超时/invalid_success 仍按既有类目优先；exit 0 + 判决缺失或非法 → blocked（fail-closed）；exit 0 + verdict=blocked → blocked 且跳过 checks；exit 0 + verdict=ok → 才进入 checks
- **D3 生效方式**：无条件启用，不加开关旗标（内部工具、单一代码路径、mock 测试同批更新）

## 验证方式

- 唯一机器验证：`python3 tests/run_mock_e2e.py`（零外部副作用，临时目录内自建 harness root 与假 git 仓库）
- 辅助：`bin/scenario-harness run <mock-scenario> --dry-run` 人工核对 prompt 片段

## 停止与升级条件

- 完成：验收标准全部满足
- 止损：verdict 门禁与现有 mock e2e 机制出现无法在既有 case() 框架内表达的冲突，或改动需要触碰 provider 传输层架构 → 停止并报告
- 升级：任一 D1-D3 默认值与你的意图不符；或实现中发现需要引入 provider 特判（超出"纯 prompt + 文件契约"范围）

## 已记录假设

- verdict 信任不对称原则成立：负向自报可信（阻断），正向自报不可信（仍需 checks 复核）
- mock e2e 的 regex 提取 task 路径机制（`tests/run_mock_e2e.py:27-29`）足以让 mock agent 定位 verdict 文件写入位置；若不足，允许在 prompt 中加一行显式 `verdicts/` 路径供解析
