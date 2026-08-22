# Goal Contract v1

状态：GOAL READY（待确认）

> 本文件是待执行契约。收到"确认 Goal Contract"后按此执行；承接 `docs/goal-contracts/2026-08-22-real-backend-acceptance.md` 的验收结论与跟进清单（T1/T2/T3/F1/F2）。

## Goal

用真实后端在一次性沙箱中完成三项针对性测试（workspace 预设写权限 T1、stderr 签名真实触发 T2、多仓顺序与依赖链 T3），落一次文档修正 F1，并依据 T1 证据对 F2（预设与写权限）作出 bounded 决策，全部产出追加进验收报告。

## 交付物

- `docs/real-backend-acceptance.md` 追加"第二轮针对性测试"章节：每用例命令、退出码、分类、关键证据、结论
- `docs/subprocess-agent-run.md` 状态节修正（F1）：补充真实后端验收已完成并链接报告
- F2 决策记录（写入验收报告；若属小改动则含代码修正与验证）
- 若 T1 证据触发 F2 小改动：`bin/scenario-harness` provider 层旗标修正 + mock e2e 全绿 + 沙箱复验

## 范围

In scope（六个测试用例 + 两项跟进）：

- **W1（T1·claude）**：R1 等价任务，`--permission workspace`；观察 task files/verdict（cwd 外）是否可写，读取 claude result JSON 的 `permission_denials` 字段作硬证据
- **W2（T1·codex）**：同任务，codex `--sandbox workspace-write`；观察沙箱对 cwd 外写入的行为（可能顺带产生真实后端的 `verdict_missing`/blocked）
- **P1（T2·claude）**：实现类任务，`--permission read-only`（`dontAsk`）；观察最终分类与真实 stderr 是否命中签名表
- **P2（T2·codex）**：同任务，`--sandbox read-only`
- **M1（T3·happy）**：双仓沙箱（beta `depends_on` alpha），claude `full-access`；断言按序完成、两仓 verdict ok、`repo_complete` 推进
- **M2（T3·blocked）**：同沙箱，alpha spec 强制 blocked 自报；断言 run 停止、beta 从未被 spawn（无 beta 日志/verdict）
- **F1**：`subprocess-agent-run.md` 状态节一句话修正 + 链接
- **F2 决策树**（依据 W1/W2 证据）：(a) workspace 预设下 cwd 外可写 → 记录"真实仓库可用 workspace"，F2 关闭；(b) 被拒但 provider 层旗标可解（claude `--add-dir <task_dir>`、codex `-c sandbox_workspace_write.writable_roots=<task_dir>`）→ 实现旗标注入并沙箱复验；(c) 旗标不可解 → 停止，升级给用户裁决（文件位置调整属架构变更）

Out of scope：

- T4（gemini）、T5（真实业务仓库）、T6（崩溃复现）
- verdict 之外的新功能；mock e2e 已覆盖逻辑的重测；commit/push

## 验收标准

- [ ] W1/W2 有明确结论：workspace 预设下 cwd 外写 task files/verdict 的真实行为（可写/被拒/变通），证据落报告（含 `permission_denials` 或日志摘录）
- [ ] P1/P2 有明确结论：read-only 下越权操作最终如何被归类（`permission_denied` 签名命中 / `nonzero_exit` / `agent_report_blocked` / 其他），真实 stderr 文本与签名表的匹配情况落报告
- [ ] M1：exit 0，两仓按序 complete、verdict 均 ok；M2：exit 2 `agent_report_blocked`，beta 无 spawn 痕迹
- [ ] F1 落盘；F2 按 (a)/(b)/(c) 决策树出结论，(b) 路径含代码修正且 `python3 tests/run_mock_e2e.py` 全绿 + 沙箱复验通过
- [ ] 报告追加章节含全部证据与残余风险更新

## 上下文与依赖

- 沿用已验证的资产：`/tmp/rba_build.py` 沙箱构建器（执行时扩展双仓与预设变体）、claude 2.1.238（GLM 代理）与 codex 0.149.0 均可用、首调 stall 风险已知（`--timeout 900`）
- 权限旗标定义在 `bin/scenario-harness` 的 `PERMISSION_FLAGS`（claude: `acceptEdits`/`dontAsk`/`bypassPermissions`；codex: `--sandbox workspace-write`/`read-only`/bypass）

## 决策权限

Agent 可自主决定：

- 用例沙箱构造细节、断言采集方式、报告行文；F2 (b) 路径的旗标注入实现细节

必须询问使用者（已定版为默认值，确认即采纳）：

- **D1 成本预算**：≤9 次真实 agent 会话（W×2、P×2、M1×2 仓、M2×1 仓、F2(b) 复验 ≤2），单仓 `--timeout 900`；行为发现不重试冲刷（沿用上轮 D3 原则）
- **D2 F2 决策树**：如上 (a)/(b)/(c)；(c) 或证据不明确时停止升级，不擅自做架构变更
- **D3 测试结论可以是阴性**：P1/P2 若证明签名表在真实后端正常流程中不会触发（agent 自适应后 exit 0 + blocked verdict），这是合法结论而非测试失败，如实记录

## 验证方式

- 每用例退出码 + stderr 分类 + 日志（`tasks/<task>/logs/<repo>.log`）+ verdict/task files 状态，全部机器可复核
- F2(b) 修正后：mock e2e 15 用例全绿 + W 路径沙箱复验

## 停止与升级条件

- 完成：六用例结论 + F1 + F2 决策全部落报告
- 止损：单用例连续 2 次环境性失败（stall/超时）；F2(b) 旗标注入后沙箱复验失败且无快速解
- 升级：F2 走到 (c)；或发现 runner 新 bug（记录不修，另立任务）

## 已记录假设

- claude result JSON 的 `permission_denials` 字段能如实反映 headless 下的拒绝（冒烟时该字段存在且为空数组）
- codex `workspace-write` 的 writable_roots 可通过 `-c` 覆写（若 (b) 路径需要；不可覆写则按 (c) 升级）
- 双仓用例中 beta 的 `depends_on` 声明会被 validate-scenario 接受（mock e2e 双仓结构同款）
