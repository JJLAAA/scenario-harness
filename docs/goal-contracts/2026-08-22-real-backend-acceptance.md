# Goal Contract v1

> 历史迁移说明：本文件保留项目更名为 RepoMesh 前的名称与命令，以维持当时验收契约的可追溯性；当前 CLI 为 `bin/repomesh`。

状态：GOAL READY（待确认）

> 本文件是待执行契约。收到"确认 Goal Contract"后按此执行；验收对象为当前工作区的 `bin/scenario-harness`（verdict 门禁版）。

## Goal

在一次性沙箱（临时 harness root + 假 git 仓库）中，用真实 claude-code / codex 后端执行 `bin/scenario-harness run`，端到端验收 verdict 门禁的三条路径（ok / blocked / missing）与真实 agent 的契约遵守情况，产出验收报告。

## 交付物

- 验收报告 `docs/real-backend-acceptance.md`：每用例的命令、退出码、stage × category 分类、verdict 文件内容摘录、耗时、日志路径、agent 行为观察、残余风险
- 沙箱运行产物（临时目录内，验收后保留路径引用、目录本身随系统清理）

## 范围

In scope：

- **R0 冒烟**：`claude -p` 与 `codex exec` 各一次最小调用，确认登录态与 headless 可用（claude 登录态存疑，以冒烟结果为准）
- **R1 claude-code happy path**：spec 要求在仓库创建 `feature.txt` 写入指定内容，checks 为 `test -f feature.txt`；期望 run exit 0、verdict ok、repo complete、仓库无新 commit
- **R2 claude-code blocked 自报**：spec 指示"不实现，写 verdict: blocked 并给出 blocker 原因"；checks 故意 rigged 为 `exit 1`，若分类仍为 `agent_report_blocked` 即证明 checks 被跳过
- **R3 claude-code missing verdict**：spec 指示"实现任务但明确不写 verdict 文件"；期望 exit 2、`verdict_missing`（真实 agent 是否服从 spec 本身就是验收观察项）
- **R4 codex happy path**：同 R1，换 `--agent codex`
- 每用例独立临时 root + 独立 task（互不污染），`--permission full-access`、`--timeout 300`

Out of scope：

- gemini 后端（本机未安装）
- invalid-verdict 真实路径（mock 已覆盖，管道相同）
- 验收中发现 runner bug 的修复——只记录并升级，修复另立任务
- 在真实业务仓库上运行（沙箱仅用假 git 仓库）

## 验收标准

- [ ] R1：exit 0；`run-status` 块含 `| alpha | pass | success | ok | pass | complete |`；`verdicts/alpha.md` 为合法三键 ok；仓库 `git log` 无新 commit
- [ ] R2：exit 2；stderr 含 `agent_report_blocked` 且含 blocker 文本；`validation.md` 记录该分类（rigged check 未执行）
- [ ] R3：exit 2；stderr 含 `verdict_missing`
- [ ] R4：exit 0；codex 后端下 R1 同款断言成立
- [ ] 验收报告落盘且结论明确：每路径通过 / 失败 / 行为发现，含残余风险

## 上下文与依赖

- 后端：`/opt/homebrew/bin/claude` 2.1.238、`/opt/homebrew/bin/codex` 0.149.0；codex 已有凭据，claude 待 R0 判定
- 被验收对象：当前工作区的 `bin/scenario-harness`（verdict 门禁已实现，mock e2e 15/15）
- 沙箱构造方式沿用 `tests/run_mock_e2e.py` 的 temp root 模式，但 `--agent` 指向真实 CLI

## 决策权限

Agent 可自主决定：

- 沙箱目录布局、scenario/task 内容细节、验收执行脚本的临时组织方式
- prompt/spec 措辞（不改变语义）

必须询问使用者（已定版为默认值，确认契约即视为采纳，修改请直接指出）：

- **D1 权限预设 `full-access`**：task files 与 verdict 文件位于 repo cwd 之外，workspace/read-only 预设会因写权限被拒而误报失败；沙箱为一次性临时目录，bypass 风险受控
- **D2 成本预算**：≤5 次真实 API 调用（R0×2 + R1-R4 各 1），单仓超时 300s；claude 若未登录则 R1-R3 降级为 codex 覆盖
- **D3 行为发现不算失败**：R2/R3 中真实 agent 违背 spec（例如 refused-to-skip-verdict）记录为发现并报告，不重试冲刷结果；单用例最多重试 1 次且仅限环境性失败（超时/网络）

## 验证方式

- 每用例的退出码 + stderr 分类断言 + task files 标记块内容 + verdict 文件内容（全部机器可复核）
- 仓库 `git status` / `git log` 验证 agent 未 commit（契约第 7 步遵守情况）

## 停止与升级条件

- 完成：R1-R4（或 claude 不可用时的降级矩阵）全部按预期分类，报告落盘
- 止损：R0 两后端均不可用；或单用例连续 2 次（首轮 + 1 次重试）无法归类
- 升级：发现 runner bug 或 agent 系统性违背契约 → 停止执行、完整记录、交用户决定修复与重验

## 已记录假设

- 真实 agent 在 headless + full-access 下能在 cwd 外写 task files 与 verdict 文件（runner 设计如此；若被拒属验收发现）
- macOS 下 claude 登录态可能存于 Keychain 而非凭据文件，R0 冒烟是唯一可靠判定
- 每用例独立沙箱使 agent 行为差异不互相污染；agent 更新 spec.md/decisions.md 属预期观察项
