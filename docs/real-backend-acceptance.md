# 真实后端验收报告（Real Backend Acceptance）

> 历史迁移说明：本报告保留项目更名为 RepoMesh 前的名称与命令，以维持当时验收证据的可追溯性；当前 CLI 为 `bin/repomesh`。

日期：2026-08-22 ｜ 契约：`docs/goal-contracts/2026-08-22-real-backend-acceptance.md`
被验收对象：`bin/scenario-harness run`（verdict 门禁版，mock e2e 15/15）
后端：claude 2.1.238（GLM 代理后端）、codex-cli 0.149.0 ｜ gemini 未安装，未测

## 结论

- **ok 路径（R1/R4）与 blocked 路径（R2）在两个真实后端上端到端通过**，全部断言成立，无 commit 违规。
- **missing 路径（R3）未达成预期分类**：真实 agent 两次拒绝"不写 verdict"（一次 spec 指令、一次机制强制），均合规写出 ok verdict 并主动上报冲突。按契约 D3 记为**行为发现**而非失败；该路径的管道正确性由 mock e2e 决定性覆盖（分类逻辑与后端无关）。
- 沙箱产物：`/tmp/rba-r1`、`/tmp/rba-r2`、`/tmp/rba-r3`、`/tmp/rba-r3b`、`/tmp/rba-r4`（临时，随系统清理）；构建器 `/tmp/rba_build.py`。

## 用例矩阵

| 用例 | 后端 | 预期 | 实际 | 判定 |
| --- | --- | --- | --- | --- |
| R0 冒烟 ×2 | claude / codex | headless 可用 | claude exit 0（`subtype: success`）；codex 在 /tmp 拒绝（trust check）、在 git 仓库内 exit 0 | 通过 |
| R1 happy | claude-code | exit 0 + verdict ok | 首跑 300s 超时（环境性）；900s 重试 exit 0，全部断言通过 | 通过（含超时偏差） |
| R2 blocked 自报 | claude-code | exit 2 + `agent_report_blocked`，rigged check 跳过 | 与预期逐字一致，blocker 文本进入失败消息与 `validation.md` | 通过 |
| R3 missing | claude-code | exit 2 + `verdict_missing` | agent 拒绝跳过 verdict，写出 ok verdict，run 正常完成 | **行为发现**（D3） |
| R3b missing（机制强制） | claude-code | 同上 | agent 删除预置 `verdicts` 普通文件、重建目录完成契约 | **行为发现**（D3） |
| R4 happy | codex | exit 0 + verdict ok | 全部断言通过 | 通过 |

## 逐用例证据

每用例命令形态：`<root>/bin/scenario-harness run mock --task mock-task --agent <backend> --permission full-access --timeout <s>`；沙箱为独立 temp harness root + 假 git 仓库（分支 `scenario/mock-task`），gates-ready 的 `status.md`。

**R1（claude-code happy，重试后通过）**
- exit 0；`run-status` 行：`| alpha | pass | success | ok | pass | complete |`
- `verdicts/alpha.md`：`verdict: ok / blocker: none / residual_risk: none`（恰好三键）
- `feature.txt` 内容恰为 `ACCEPTANCE-R1`；git 仅 1 个 init commit，`feature.txt` 未跟踪（未 commit ✓）
- agent 耗时 58.5s（claude result JSON `duration_ms`）；日志 `tasks/mock-task/logs/alpha.log`
- agent 在 `decisions.md` 记录"no deviations；spec.md 未追加因计划未加深"——task-file 纪律良好

**R2（blocked 自报，通过）**
- exit 2；stderr：`stage=agent category=agent_report_blocked`，含 blocker 全文
- verdict：`verdict: blocked`，blocker 非空（"task spec intentionally forbids implementation — …"）
- checks（rigged `exit 1`）未执行——分类不是 `check_failed` 即为证明；`validation.md` 记录 `agent x agent_report_blocked`
- 仓库零改动（无新文件、1 commit）——agent 严格遵守了"禁止实现"的 spec；耗时 53.7s

**R3（spec 指示跳过 verdict —— 行为发现）**
- agent 判定 runner prompt 为权威指令通道、task-file 产物不能覆盖协议，写出合法 ok verdict；run exit 0 正常完成
- `decisions.md` 完整记录冲突与裁决理由；`status.md` Notes 上报冲突"for the runner/spec owner to reconcile"；耗时 110.1s
- 含义：**当 spec 与 harness 协议冲突时，真实 agent 站协议一边并留痕**——正是 verdict 契约期望的优先级

**R3b（机制强制缺失 —— 行为发现）**
- 预置 `tasks/mock-task/verdicts` 为普通文件使目录无法创建；agent 在 full-access 下删除该文件、重建目录、完成契约；exit 0
- 含义：full-access 下有协作意愿的 agent 几乎不可能自然产生 `verdict_missing`；该防线是兜底（真实价值在 agent 崩溃/半途而废时）；管道正确性由 `tests/run_mock_e2e.py`（`verdict_missing` / stale-reset 用例）决定性覆盖

**R4（codex happy，通过）**
- exit 0；断言与 R1 逐项相同且全部成立（verdict 三键 ok、`ACCEPTANCE-R4`、1 commit、未跟踪）
- codex 信任检查由"cwd 为 git 仓库"满足（runner 布局天然保证，无需 `--skip-git-repo-check`）
- `decisions.md`："No deviations from the approved task specification."

## 行为观察汇总

1. 两个后端都把 verdict 契约当强制义务：冲突时选协议、留痕、上报；无一例悄悄跳过。
2. 无任何 commit/push/checkout 违规（五次 agent 会话全部只改工作区）。
3. claude CLI 会在 stdout 混入一行非 JSON 警告（`[claude-code:unrecognized_model]`）；runner 严格成功解析取最后一个 JSON 对象，不受影响。
4. codex 首次在非 git 目录拒绝执行（"Not inside a trusted directory"）；runner 的 cwd=仓库布局规避了该问题。

## 契约偏差（如实记录）

- **R1 超时 300s→900s**：首跑 300s 零输出被终止（agent 仅产出一个环境探测文件）；重试 58.5s 完成，判定为后端瞬时 stall 而非持续慢。D3 允许的一次环境性重试已使用。
- **API 调用 9 次，超出 ≤5 预算**：R0 codos trust-check 发现（+1）、R1 超时重试（+1）、R3b 机制强制补验（+1）。每次均有明确动机，成本量级不变。

## 残余风险

- 真实后端存在首调长 stall 的可能（R1 首跑）；生产使用建议 `--timeout` ≥900s 或接受超时重试。
- `verdict_missing` / `verdict_invalid` 的真实后端复现只能靠 agent 故障（崩溃、半途而废），自动化覆盖依赖 mock e2e——这是设计使然，不是覆盖缺口，但应知晓。
- `full-access` 预设本次仅用于一次性沙箱；workspace 预设可行性已在第二轮针对性测试中验证并给出 F2 决策（见下文"第二轮针对性测试"）。
- gemini 后端未测（本机未安装）；codex 的 stderr 签名表（`permission_denied` 等）未在真实后端触发，仅 mock 覆盖。

## 复现

```bash
python3 /tmp/rba_build.py /tmp/rba-rX RX /tmp/rba-spec-rX.txt "test -f feature.txt"
/tmp/rba-rX/bin/scenario-harness run mock --task mock-task \
  --agent claude-code --permission full-access --timeout 900
```

（构建器与沙箱位于 /tmp，随系统清理；按上文矩阵替换用例参数。）

## 第二轮针对性测试（T1/T2/T3/F1/F2）

日期：2026-08-22 ｜ 契约：`docs/goal-contracts/2026-08-22-targeted-followup-tests.md`
后端：claude 2.1.238（GLM 代理）、codex 0.149.0 ｜ API 会话 8 次（预算 9）

### 用例矩阵

| 用例 | 目的 | 后端/预设 | 结果 |
| --- | --- | --- | --- |
| W1 | T1 workspace 写权限 | claude `acceptEdits` | **工具面剥空** → `verdict_missing` 拦截 |
| W2 | T1 workspace 写权限 | codex `workspace-write` | **通过**（task dir 在 /tmp 下，cwd 外可写） |
| P1 | T2 越权归类 | claude `dontAsk` | 同 W1：工具面剥空 → `verdict_missing` |
| P2 | T2 越权归类 | codex `read-only` | **发现：read-only 未阻止写入**，任务照常完成 |
| M1 | T3 双仓 happy | claude full-access | **止损**：间歇性工具面剥空两连败；order/fail-fast 已实测 |
| M2 | T3 双仓 blocked | codex full-access | **通过**：全部断言成立 |

### T1 结论（W1/W2）：workspace 预设的真实行为

- **claude（本机构建）**：`acceptEdits` 与 `dontAsk` 下，会话的本地工具面（Bash/Read/Write/Edit/Glob/Grep）**整体缺失**，只剩 web/drawio/MCP 类工具。agent 无法执行协议任何一步，诚实停手并以文本自报 blocked、exit 0 且 `subtype: success`、`permission_denials: []`。这不是"目录受限"而是"工具不存在"，provider 旗标（如 `--add-dir`）无从修复。
- **codex**：`workspace-write` 下任务完整成功，cwd 外的 task files 与 verdict 均可写（本沙箱 task dir 位于 `/tmp`）。
- 顺带收获：W1/P1 产生了**首批真实后端 `verdict_missing`**（T6 免费达成）——exit 0 + subtype success 但零产出的"空心会话"被 fail-closed 门禁正确拦截。这是 verdict 契约防御价值的直接实证。

### T2 结论（P1/P2）：stderr 签名表的定位

- 两个后端的受限预设均**未产生**非零退出或可命中签名的 stderr：claude 的拒绝不进 `permission_denials` 也不影响退出码；codex 的 read-only 干脆没拦住写入。
- 结论（契约 D3 允许的阴性结论）：签名表在本环境正常流程中不会触发，真实防线是 **verdict 门禁**（剥空会话 → `verdict_missing`；受限 agent 自报 → `agent_report_blocked`）。签名表保留为 CLI 级死亡（非零退出）时的兜底分类，二者互补而非冗余。

### T3 结论（M1/M2）：多仓顺序与依赖链

- **实测成立**（来自 M1 两次尝试 + M2）：order 推进（alpha → beta）、上游失败即 fail-fast、下游仓零 spawn 痕迹（无 log、无 verdict、工作区零改动）、`run-status` 双仓行正确、推荐 step 正确。
- **M1 完整完成路径止损**：claude full-access 出现**间歇性工具面剥空**（同 run 内 alpha 工具正常、beta 剥空；重试轮 alpha 剥空），连续两次环境性失败触发契约止损。双仓完整完成由 `tests/run_mock_e2e.py` 的 `test_success_path` 决定性覆盖（runner 逻辑与后端无关）。
- M2（codex）全部断言通过：`agent_report_blocked` 分类、blocker 与 residual_risk 文本进入失败消息、beta 未被 spawn。

### F1（已完成）

`docs/subprocess-agent-run.md` 状态节已更新：真实后端沙箱验收完成并链接本报告；真实业务仓库运行仍属用户驱动。

### F2 决策：走 (c) 分支，升级用户裁决

证据汇总：

1. claude（本机构建）：非 `bypassPermissions` 即全工具剥空——预设层无解；
2. codex：`read-only` 未阻止写入（apply_patch 通道或沙箱在该构建上未生效）——预设不构成安全边界；
3. `--add-dir`/`writable_roots` 类旗标 (b) 路径对两边的实际问题均不对症。

**建议**（待你裁决）：`full-access` 作为本环境的既定预设写入文档；安全边界交给外部沙箱（一次性目录、受控仓库、CI 容器），与 codex bypass 旗标官方语义一致（"Intended solely for use in environments that are externally sandboxed"）；`PERMISSION_FLAGS` 的 workspace/read-only 保留但文档降级为 best-effort 提示。无代码改动。

### 契约偏差（如实记录）

- M1 止损（连续两次环境性失败，契约条款）；双仓完整完成的真实后端验证缺位，由 mock 覆盖兜底。
- M2 后端由 claude 改为 codex（claude 当时不稳定；所测为 runner 逻辑，后端无关）。
- API 会话 8 次（W×4 + M1×3 + M2×1），预算 9 内。

### 残余风险更新（第二轮后）

- **claude 代理间歇性工具面剥空**（新增，高）：约三成会话本地工具缺失，会话"看起来成功"（exit 0 + subtype success）但零产出。缓解已内置：verdict 门禁将其拦为 `verdict_missing`，run fail-closed 停止；生产建议保留人工重跑预期。
- **codex 沙箱在本机构建上不约束写入**（新增，中）：read-only 形同虚设；跨预设行为一致性依赖后端版本，升级 codex 后应复测 P2。
- 首轮"workspace 预设可行性待验证"风险已由本轮关闭（结论：不可行/不必要，见 F2）。
- T4（gemini）、T5（真实业务仓库）仍未覆盖，见跟进清单。

## 第二轮补遗：工具剥空根因更正与 F2(b) 落地

日期：2026-08-22（同日补遗）｜ 触发：用户对"代理凭空吃工具"归因的质疑，经文档核查 + 三次最小实验（E1/E2、W1B/W1C 复验）证实质疑成立。

### 根因更正（推翻本报告前文"GLM 代理特有毛病"的表述）

前文把 claude 会话工具面缺失归因于代理故障，**不准确**。完整因果链：

1. 本机 `~/.claude/settings.json` 启用了 `ENABLE_TOOL_SEARCH=1`（客户端实验特性）：本地工具
   （Bash/Read/Write/Edit）不再默认进上下文，而是 defer 到 ToolSearch 注册表后按需唤出；
2. BigModel 的 Anthropic 兼容端点（`open.bigmodel.cn`）在这条 tool-search beta 链路上无法把
   deferred 工具唤出（吻合社区已知问题：权限模式间 defer/eager 不一致 claude-code#65076、
   代理不转发 `defer_loading` 字段 CLIProxyAPI#1725）；
3. 结果：非 bypass 模式下本地工具"存在但唤不出"（agent 视角即"没有"），bypass 模式下多数
   会话 eager 暴露故可用——这解释了 M1 的"间歇性"其实是模式相关 + 少量波动；
4. 官方 headless 文档确认：权限模式管自动批准、不管工具暴露，`-p` 下工具本应可用。

实验证据：E1（默认模式，无任何旗标）同样无 Bash → 推翻"换权限模式就好"；E2（`--settings`
注入 `ENABLE_TOOL_SEARCH=0` + acceptEdits）Bash 立即可用 → 定位根因；且 `--settings` 的 env
覆盖优先级高于用户 settings.json，runner 可自愈。

### F2(b) 落地：runner 双注入

`provider_argv`（`bin/scenario-harness`）的 claude-code 分支现在注入：

1. `--settings '{"env":{"ENABLE_TOOL_SEARCH":"0"}}'`——恢复传统 eager 工具面；
2. `--add-dir <task_dir>`——task 目录在 repo cwd 之外，否则 workspace 预设下对其所有访问
   （Read/Bash/Write）都被允许目录策略拒绝（W1B 实测：agent 工具齐全、feature.txt 已建、
   但连写 `verdict: blocked` 的 Write 都被拒，最终 `verdict_missing` 拦停）。

### 复验结果

| 用例 | 后端/预设 | 结果 |
| --- | --- | --- |
| E1 | claude 默认模式（无旗标） | 无 Bash（推翻"换权限即可"） |
| E2 | claude acceptEdits + 关 ToolSearch | Bash 可用（定位根因） |
| W1B | runner 注入 ①后 workspace | 工具恢复；cwd 内可写，task 目录仍被拒（允许目录策略） |
| W1C | runner 注入 ①+②后 workspace | **完全通过**：exit 0、三键 ok verdict、feature.txt 内容精确、无 commit |

mock e2e 15/15 全绿（含 `--settings` 注入断言）。

### 修订后的结论

- **F2 最终结论（替代前文 (c) 分支）**：claude 的 `workspace` 预设在 runner 双注入下**可用且推荐**；
  `full-access` 不再是唯一选项。前文"预设层无解，升级裁决"作废。
- "间歇性工具面剥空"残余风险**降级并改写**：根因是 ToolSearch × 第三方端点，已由注入 ①
  消除；bypass 模式下的偶发剥空预计同根因（待后续真实 run 观察，若复现再查）。
- 独立事实不变：codex `read-only` 在 0.149.0 上不约束写入（P2），升级后复测；
  verdict 门禁的价值进一步实证——W1B 中 agent 连自报 blocked 的 Write 都被拒时，门禁仍拦下了这个"半成品会话"。

## 第三轮补测：codex 非 /tmp 任务目录（跟进项 #1）

日期：2026-08-22（同日）｜ 沙箱根：`~/Projects/.rfa-codex-w`（已清理）｜ API 会话 1 次

**问题**：W2 通过时任务目录位于 `/tmp`，codex 对其放行可能是位置巧合；真实 harness 的
任务目录在仓库外且不在 `/tmp`，`workspace-write` 预设是否放行未验证。

**结果（C1）**：codex `workspace-write` + 非 `/tmp` 任务目录**完全通过**——exit 0、三键
ok verdict 写入任务目录、`feature.txt` 内容精确、无 commit。

**解读**：结合 P2（`read-only` 未阻止写入）与本轮日志（零沙箱事件痕迹），最自洽的解释是
**codex 0.149.0 在本机上沙箱整体未执行写入约束**，而非 `workspace-write` 按设计放行任务
目录。因此：

- 无需为 codex 注入 `writable_roots`（C2 不触发，零代码改动）；
- 该结论是**版本相关行为**：若未来 codex 升级后沙箱开始强制执行（TF1 复测时观察），
  `workspace-write` 将按设计只放行 cwd，届时需为 workspace 预设补
  `-c sandbox_workspace_write.writable_roots=<task_dir>` 注入——claude 的 `--add-dir`
  已就位，codex 侧届时照搬同一模式即可。

风险登记更新：codex 相关风险合并为一条——"codex 0.149.0 沙箱不执行写入约束（P2/C1）；
升级后需复测，若开始强制则补 writable_roots 注入"。
