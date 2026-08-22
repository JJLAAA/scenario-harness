# 子进程 Agent 执行层（Subprocess Agent Run）

`bin/scenario-harness run` 的设计文档：每仓子进程 Agent 执行层。它实现 README
"Single-Session Limits And Per-Repo Sessions" 一节描述的"每仓新会话模式"——每个业务仓库
在自己的目录内获得一个独立的 Agent 进程，仓库本地运行时机制（指令文件、hooks、skills
在会话启动时被发现）正常加载；协调侧的 runner 保持确定性。

设计借鉴了 `deepseek-harness`（dsh）v0.1.0-rc.8 的进程管理缝隙（seam）。传输层刻意做了
不同选择，见[传输层选择](#传输层选择)。

## 架构

两层结构，协调路径中没有 LLM：

```
哑 runner（确定性 Python，无模型）
  └── provider 适配层（spawn / result / terminate）
        ├── claude-code → claude -p <prompt> --output-format json
        ├── codex       → codex exec --json <prompt>
        └── gemini      → gemini -p <prompt>   （实验扩展位）
```

- runner 读取 `scenario.yaml`（order、checks）与 task files（分支、门禁），每仓渲染一份
  prompt，以仓库为 cwd 拉起后端，随后亲自执行仓库 checks 并据此门禁。
- 智能放在每个仓库的子 Agent 会话内部；协调是代码。
- 交接介质是 task files（`spec.md`、`status.md`、`decisions.md`、`validation.md`）
  加上原始日志 `tasks/<task>/logs/<repo>.log`。

## 每仓执行循环

对 scenario order 中的每个仓库（或 `--repo` 指定的单仓）：

1. **门禁预检**（一次，在第一个仓库之前）：`status.md` 必须显示 Planning Gate 已完成、
   Spec Review Gate 已批准或显式跳过。识别两种信号：协议规定的 `current step:` 行
   （达到 `planning_complete`/`spec_review_approved` 或更晚；replanning 状态需要重新评审）
   以及显式的 `## Planning Gate` / `## Spec Review Gate` 章节。门禁缺失 → 拒绝执行，
   退出码 2。
2. **Preflight**：分支必须与任务期望分支精确匹配。runner 绝不创建、切换或重命名分支。
3. **Prompt 渲染**：由 scenario.yaml 数据 + task files 路径驱动的确定性模板。prompt 要求
   子 Agent 核对分支、按序读取 `instruction_sources`、检视 `key_files`、按 `spec.md`
   实现、更新 task files、绝不 commit。
4. **Spawn**：后端以独立会话（`start_new_session=True`）运行，cwd 为仓库目录，env 使用
   显式 overlay。
5. **Checks**：子 Agent 退出后由 runner——而非子 Agent——执行 `repos.<repo>.checks`。
   从不信任自我报告的成功。
6. **门禁**：Agent 严格成功 + 全部 checks 通过 → 下一仓库；否则 run 以 `blocked` 停止，
   失败记录写入 task files。

`--dry-run` 只渲染 prompt 与 argv（不做门禁、不加锁、不 spawn）。

## 借鉴自 dsh rc.8 的机制

| # | 机制 | dsh 来源 | scenario-harness 适配 |
| - | --- | --- | --- |
| 1 | 进程树终止：升级阶梯 + 宽限，整树所有权 | `packages/subprocess`（subprocess seam；`DEFAULT_DISPOSE_GRACE_MS`） | 每次 spawn 独立会话；SIGTERM → `--term-grace`（10s）→ 对进程组 SIGKILL |
| 2 | 父环境清洗（环境变量不得泄漏给子进程） | `packages/subprocess` `scrubbedParentEnv` | 白名单 overlay：基础变量（`PATH`、`HOME`、locale 等）+ 认证/代理前缀（`ANTHROPIC_*`、`OPENAI_*` 等）；其余全部丢弃 |
| 3 | 严格成功映射 + 类型化失败分类 | `subagent-claude-code/src/run.ts`（仅 SDK `success` 子类型算完成；stage × category） | exit 0 是必要条件而非充分条件（claude-code 结果 JSON `subtype: error_*` → `invalid_success`）；失败按 stage（`gates`/`preflight`/`agent`/`checks`）× category 分类 |
| 4 | 非交互权限白名单 + 保守缺省 | `subagent-claude-code` `CLAUDE_CODE_PERMISSION_MODES`、`subagent-codex` `CODEX_PERMISSION_MODES` | 三个非交互预设：`workspace`（缺省：允许编辑、拒绝提权——`read-only` 无法实现任务）、`read-only`、`full-access` |
| 5 | stderr 签名匹配（协议不上报的失败） | `subagent-codex/src/wire.ts` `STDERR_PERMISSION_SIGNATURES` | 对原始日志 stderr 的签名表（`permission_denied`、`sandbox_violation` 等），映射进失败 category |
| 6 | Provider 契约：一个缝隙、多个后端 | `packages/subagent` 能力家族（`SubagentStartRequest/Result`） | `--agent {claude-code,codex,gemini}`；每个 provider 是同一个 spawn/result/terminate 契约内的 argv 构造器 |

## 传输层选择

dsh 把 Agent 作为活的子代理嵌入：Claude Code 走官方 Agent SDK，Codex 走其 app-server
JSON-RPC 协议并维护版本锁定的 wire 适配器（`wire.ts`，"app-server 0.147.0"）。那种深度换来
流式消息映射、可续期子代理和中途控制——一次性批处理 runner 全都用不上。

本项目改用公开的 headless CLI 接口：

- 零新增依赖（纯 Python 标准库；不需要 Node 工具链，不需要针对内部版本维护 wire 协议）；
- `claude -p --output-format json` 与 `codex exec --json` 是有公开文档的契约，对
  发 prompt / 收结果 / 拿退出码已经足够；
- 借来的缝隙（进程所有权、失败分类、provider 契约）与传输层正交。

升级路径：provider 契约意味着某个后端将来可以长出基于 SDK 或 app-server 的适配器，
而 runner 一行不改。

## 失败分类

Stage：`gates`、`preflight`、`agent`、`checks`。
Category 包括：`planning_gate_missing`、`spec_review_gate_missing`、
`branch_fail`/`branch_not_configured`、`nonzero_exit`、`signal`、`timeout`、
`invalid_success`、`permission_denied`、`sandbox_violation`、`check_failed`、
`check_timeout`。

每个失败写入 `validation.md`（标记块 `run-validation`）与 `status.md`（标记块
`run-status`），并给出推荐的 current step（`blocked`，或每个仓库完成后的
`repo_complete:<repo-key>`）。退出码：`0` 完成；`2` 门禁/仓库失败；`64` 用法、锁、
spawn 或非 POSIX 平台错误。

## 安全属性

- **单写者**：`tasks/<task>/.run.lock`（O_CREAT|O_EXCL，记录 pid；pid 已死的陈锁会被回收）。
- **不改 git 状态**：runner 与子 Agent prompt 都禁止 commit、push、checkout 和建分支。
- **checks 归 runner**：机器验证，绝不采用 Agent 自报。
- **恢复介质**：只有 task files；恢复即重跑 `run`，它不自动跳过任何东西——每次都重新
  核对门禁、分支与锁。

## Headless 运行时激活核查（对照官方文档）

后端在仓库目录内以 headless 方式拉起时，哪些仓库本地运行时机制真正激活：

| 机制 | `claude -p` | `codex exec` |
| --- | --- | --- |
| cwd 下的 `AGENTS.md` / 指令文件 | 加载 | 加载 |
| 项目/用户 settings hooks（`.claude/settings.json`） | 加载——官方原文 "headless mode reuses the same settings, hooks, and permission rules as the interactive CLI" | 不适用（无仓库级 hooks 概念；受管理的 lifecycle hooks 在 `requirements.toml`，不在仓库里） |
| Skills | 加载 | 不适用 |
| `config.toml` | 不适用 | 默认加载（存在 `--ignore-user-config` 可跳过） |
| MCP servers | 部分——远程/deferred 工具在 `-p` 下有已知可见性 bug（claude-code issue #43298） | 会初始化（`required = true` 的服务初始化失败会令 exec 退出），但需要审批的 MCP 工具调用在 stdin 关闭时被自动取消（codex issue #24135） |
| Subagent frontmatter hooks | 不激活——需要通过交互式对话接受工作区信任；`-p` 会话不算数 | 不适用 |

对本 runner 的启示：

- 文档级合规路径不受影响：渲染出的 prompt 始终要求子 Agent 按序读取
  `instruction_sources`，这正是本 harness 规定的静态兜底入口。
- 工作流依赖 subagent frontmatter hooks 的仓库，必须先在仓库里开一次交互式
  Claude Code 会话完成预信任；目前没有 headless 的 `--trust` 旗标（特性请求 #23109）。
- 场景的实现阶段不应依赖需审批的 MCP 工具；sandbox/approval 预设由 provider 层显式设置。
- headless 下 hooks 失败通常是非阻塞的，所以 hooks 不能是唯一强制层——这也是为什么
  runner 要亲自重跑仓库 checks（机器验证层留在 runner 手里）。

来源：Claude Code headless 与 hooks 文档（code.claude.com/docs/en/headless、/hooks）、
Codex 非交互模式文档（learn.chatgpt.com/docs/non-interactive-mode），以及两个 MCP
例外对应的公开 issue。

## 不从 dsh 搬的东西

Cordis 式 DI 服务架构、PTY/前台进程管理、可续期后台子代理、profile/插件体系、进程内
subagent 驱动、app-server wire 适配器。那些服务于完整的 Agent 宿主；本 harness 保持一个
哑的串行 runner。

## 状态

已在 `bin/scenario-harness run` 实现；由 `tests/run_mock_e2e.py` 自测（mock 后端、
临时仓库、零外部副作用）。在真实业务仓库上用真实 Agent 验收属于用户驱动的步骤，
在自动化测试之外。
