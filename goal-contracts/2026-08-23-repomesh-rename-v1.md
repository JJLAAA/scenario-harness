# Goal Contract v1

状态：GOAL CONTRACT 已确认

## Goal

将项目从 Scenario Harness 完整更名为 RepoMesh，包括代码、CLI、持久化标记、当前文档、测试、图表、GitHub 仓库、Git remote 和本地目录，不保留旧运行兼容层。

## 交付物

- 项目展示名称统一为 `RepoMesh`。
- CLI 从 `bin/scenario-harness` 彻底替换为 `bin/repomesh`。
- CLI program name、帮助文本、生成内容统一使用 `repomesh`。
- 持久化标记从 `scenario-harness:*` 替换为 `repomesh:*`。
- 测试、模板、AGENTS.md、CLAUDE.md、中英文 README 和当前设计文档完成同步。
- `scenario-harness-workflow.html/png` 重命名为 `repomesh-workflow.html/png`，内容同步并完成视觉验证。
- 历史 Goal Contract 和真实后端验收报告保留当时名称及命令，并增加历史迁移说明。
- GitHub 仓库更名为 `JLA97/repomesh`。
- `origin` 更新为新仓库地址。
- 本地目录更名为 `/Users/leo/Projects/repomesh`。
- 所有改动直接提交并推送至 `main`。

## 范围

In scope：

- `README.md`、`README.zh.md` 的品牌和项目定位。
- `AGENTS.md`、`CLAUDE.md` 中的项目名、CLI 路径和相关协议措辞。
- `bin/scenario-harness` 文件名及所有品牌相关实现。
- `tests/`、`templates/` 和当前操作性文档中的 CLI 引用。
- 当前架构图、HTML/PNG 工作流资产及其文件名。
- 当前设计文档中的现行命令和产品名称。
- GitHub 仓库名、Git remote、本地目录名。
- 直接在 `main` commit 和 push。
- 全仓链接、路径和交叉引用修复。

Out of scope：

- 不改变 Scenario Task 与 Free Task 的业务语义。
- 不重命名合法的 `scenario` 概念、`scenarios/` 目录、`scenario.yaml` 或 `validate-scenario` 等模式专属命令。
- 不提供旧 CLI wrapper、alias、deprecated command 或旧标记读取能力。
- 不改写历史 Goal Contract 和验收报告中的历史命令。
- 不重构与更名无关的代码。
- 不发布 package、release 或公告。

## 验收标准

- [ ] 当前产品面统一使用 `RepoMesh` / `repomesh`。
- [ ] `bin/repomesh` 存在、可执行，`bin/scenario-harness` 不存在。
- [ ] `bin/repomesh --help` 正常，program name 和描述无旧品牌。
- [ ] 新写入标记使用 `repomesh:*`，实现中不存在旧标记兼容逻辑。
- [ ] 更新后的完整 mock E2E 测试全部通过。
- [ ] README、协议、模板、测试和当前文档不存在失效的旧 CLI 路径。
- [ ] 除明确列入历史资料白名单的内容外，受版本控制文件中不存在 `Scenario Harness`、`scenario-harness` 或旧持久化标记。
- [ ] 历史资料保留原始事实，并明确说明项目后来更名为 RepoMesh。
- [ ] 工作流 HTML/PNG 使用新文件名和新品牌，PNG 已重新生成并完成视觉检查。
- [ ] GitHub 仓库可通过 `JLA97/repomesh` 访问，默认分支仍为 `main`。
- [ ] 本地仓库位于 `/Users/leo/Projects/repomesh`，`origin` 指向新地址。
- [ ] `main` 已 commit、push，最终工作树干净。

## 上下文与依赖

- 当前仓库：`/Users/leo/Projects/scenario-harness`。
- 当前分支：`main`，与 `origin/main` 对齐，初始工作树干净。
- 当前远程：`git@github.com:JLA97/scenario-harness.git`。
- GitHub 当前登录账户对 `JLA97/scenario-harness` 具有 `ADMIN` 权限。
- GitHub 默认分支为 `main`。
- 历史资料白名单包括现有 `docs/goal-contracts/*.md` 与 `docs/real-backend-acceptance.md`；其历史命令不作事实改写。
- 项目显示名使用 `RepoMesh`，技术标识、CLI、仓库名和目录名使用小写 `repomesh`。

## 决策权限

Agent 可自主决定：

- 更名的安全执行顺序。
- 内部变量、测试 fixture、文案和链接的具体调整方式。
- 历史迁移说明的统一格式。
- Git commit message。
- 为保持现有测试语义所需的局部测试调整。
- GitHub 仓库更名和 remote 更新的具体安全命令。

必须询问使用者：

- 需要改变 Scenario/Free Task 业务语义。
- 发现必须保留旧 CLI 或旧标记兼容才能避免已知数据损坏。
- 需要删除或改写历史事实。
- `main` 被保护、远端发生非快进冲突，或必须覆盖他人改动。
- 需要发布 Release、Package、公告或执行其他未授权外部操作。

## 验证方式

- 运行更新后的 mock E2E 测试套件。
- 对 CLI 执行语法检查和 `--help` smoke test。
- 使用 `rg` 对旧品牌、旧 CLI 路径和旧标记做全仓扫描，并应用明确的历史资料白名单。
- 检查所有重命名文件和交叉引用。
- 渲染并查看新的工作流 PNG。
- 通过 GitHub API/CLI核验仓库名、权限和默认分支。
- 检查 `git remote -v`、当前分支、提交状态和最终干净工作树。
- 从新本地目录再次运行核心 smoke test。

## 停止与升级条件

- 完成：全部验收标准通过，`main` 已推送，GitHub、remote 和本地目录均完成更名。
- 止损：测试经过针对性修复后仍失败，或更名导致无法安全恢复的路径/标记冲突时，停止后续外部迁移并保留当前可恢复状态。
- 升级：GitHub 权限失效、分支保护阻止直接推送、远端非快进、本地目录迁移失败，或者发现历史资料之外仍有必须保留的外部兼容依赖时，停止并向使用者报告。

## 已记录假设

- GitHub 仓库目标名 `JLA97/repomesh` 当前可用。
- GitHub 重命名产生的旧 URL 重定向可以保留外部链接的基本可达性，但项目本身不承诺旧 CLI 或旧标记兼容。
- “彻底替换”针对当前产品面；明确列入白名单的历史证据允许保留旧名称。
- 用户已明确授权直接更新 `main`、commit、push、重命名 GitHub 仓库、更新 remote 和迁移本地目录。
