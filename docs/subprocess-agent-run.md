# Subprocess Agent Run Layer

Design for `bin/scenario-harness run`: the per-repo subprocess agent execution
layer. It implements the "per-repo session pattern" described in the README
section *Single-Session Limits And Per-Repo Sessions* — each business repository
gets its own agent process started inside that repository, so repo-local
runtime mechanisms (instruction files, hooks, skills discovered at session
start) activate normally, while the coordinating runner stays deterministic.

The design borrows the process-management seams of
`deepseek-harness` (dsh) v0.1.0-rc.8. The transport is deliberately different;
see [Transport Choice](#transport-choice).

## Architecture

Two layers, no LLM in the coordination path:

```
dumb runner (deterministic Python, no model)
  └── provider adapter (spawn / result / terminate)
        ├── claude-code → claude -p <prompt> --output-format json
        ├── codex       → codex exec --json <prompt>
        └── gemini      → gemini -p <prompt>   (experimental slot)
```

- The runner reads `scenario.yaml` (order, checks), task files (branches,
  gates), renders one prompt per repo, spawns the backend with the repo as
  cwd, then runs the repo checks itself and gates on them.
- Intelligence lives inside each per-repo agent session; coordination is code.
- Handoff medium is the task files (`spec.md`, `status.md`, `decisions.md`,
  `validation.md`) plus raw logs under `tasks/<task>/logs/<repo>.log`.

## Per-Repo Loop

For each repo in scenario order (or the single `--repo`):

1. **Gate precheck** (once, before the first repo): `status.md` must show the
   Planning Gate complete and the Spec Review Gate approved or explicitly
   skipped. Signals honored: the protocol `current step:` line
   (`planning_complete`/`spec_review_approved` or later, replanning states
   require a fresh review) and explicit `## Planning Gate` / `## Spec Review
   Gate` sections. Missing gates → refusal, exit 2.
2. **Preflight**: branch must exactly match the task-expected branch. The
   runner never creates, checks out, or renames branches.
3. **Prompt render**: deterministic template over scenario.yaml data +
   task-file paths. The prompt orders the child agent to verify the branch,
   read `instruction_sources` in order, inspect `key_files`, implement per
   `spec.md`, update task files, and never commit.
4. **Spawn**: backend runs in its own session (`start_new_session=True`) with
   the repo as cwd and an explicit env overlay.
5. **Checks**: the runner — not the child agent — runs `repos.<repo>.checks`
   after the agent exits. Self-reported success is never trusted.
6. **Gate**: agent strict-success + all checks pass → next repo; otherwise the
   run stops as `blocked`, with the failure recorded in task files.

`--dry-run` renders prompts and argv only (no gates, lock, or spawn).

## Borrowed From dsh rc.8

| # | Mechanism | dsh source | scenario-harness adaptation |
| - | --- | --- | --- |
| 1 | Process-tree termination with escalation ladder + grace, whole-tree ownership | `packages/subprocess` (subprocess seam; `DEFAULT_DISPOSE_GRACE_MS`) | own session per spawn; SIGTERM → `--term-grace` (10s) → SIGKILL to the process group |
| 2 | Scrubbed parent environment (ambient vars must not leak into children) | `packages/subprocess` `scrubbedParentEnv` | allowlist overlay: base vars (`PATH`, `HOME`, locale, …) + auth/proxy prefixes (`ANTHROPIC_*`, `OPENAI_*`, …); everything else dropped |
| 3 | Strict success mapping + typed failure taxonomy | `subagent-claude-code/src/run.ts` (only SDK `success` subtype completes; stage × category) | exit 0 is necessary but not sufficient (claude-code result JSON `subtype: error_*` → `invalid_success`); failures classified stage (`gates`/`preflight`/`agent`/`checks`) × category |
| 4 | Unattended permission whitelist with conservative default | `subagent-claude-code` `CLAUDE_CODE_PERMISSION_MODES`, `subagent-codex` `CODEX_PERMISSION_MODES` | three non-interactive presets: `workspace` (default: edits allowed, escalations denied — `read-only` cannot implement), `read-only`, `full-access` |
| 5 | stderr signature matching for protocol-blind failures | `subagent-codex/src/wire.ts` `STDERR_PERMISSION_SIGNATURES` | signature table over the raw log stderr (`permission_denied`, `sandbox_violation`, …), mapped into the failure category |
| 6 | Provider contract: one seam, multiple backends | `packages/subagent` capability family (`SubagentStartRequest/Result`) | `--agent {claude-code,codex,gemini}`; each provider is an argv builder inside one spawn/result/terminate contract |

## Transport Choice

dsh embeds agents as live subagents: Claude Code through the official Agent
SDK, Codex through its app-server JSON-RPC protocol with a version-pinned wire
adapter (`wire.ts`, "app-server 0.147.0"). That depth buys streaming message
mapping, continuable children, and mid-run control — none of which a one-shot
batch runner needs.

This harness uses the public headless CLI interfaces instead:

- zero new dependencies (pure Python stdlib; no Node toolchain, no wire
  protocol to maintain against pinned internal versions);
- `claude -p --output-format json` and `codex exec --json` are documented
  public contracts, sufficient for send-prompt / get-result / exit-code;
- the borrowed seams (process ownership, failure taxonomy, provider
  contract) are orthogonal to transport.

Upgrade path: the provider contract means a backend can later grow an
SDK-based or app-server-based adapter without touching the runner.

## Failure Taxonomy

Stages: `gates`, `preflight`, `agent`, `checks`.
Categories include: `planning_gate_missing`, `spec_review_gate_missing`,
`branch_fail`/`branch_not_configured`, `nonzero_exit`, `signal`, `timeout`,
`invalid_success`, `permission_denied`, `sandbox_violation`,
`check_failed`, `check_timeout`.

Every failure is written to `validation.md` (marked block `run-validation`)
and `status.md` (marked block `run-status`) with the recommended current step
(`blocked`, or `repo_complete:<repo-key>` after each completed repo). Exit
codes: `0` complete, `2` gate/repo failures, `64` usage, lock, spawn, or
non-POSIX platform.

## Safety Properties

- **Single writer**: `tasks/<task>/.run.lock` (O_CREAT|O_EXCL, pid recorded;
  stale locks whose pid is dead are reclaimed).
- **No git mutations**: the runner and the child prompt both forbid commit,
  push, checkout, and branch creation.
- **Checks are runner-owned**: machine verification, never agent self-report.
- **Recovery medium**: task files only; resuming re-runs `run`, which skips
  nothing automatically — it re-checks gates, branch, and locks each time.

## Not Borrowed From dsh

Cordis-style DI service architecture, PTY/foreground process management,
continuable background subagents, profile/plugin system, in-process subagent
drivers, app-server wire adapter. Those serve a full agent host; this harness
keeps a dumb serial runner.

## Status

Implemented in `bin/scenario-harness run`; self-tested by
`tests/run_mock_e2e.py` (mock backends, temp repos, zero external side
effects). Real-agent validation on actual business repositories is a
user-driven step outside the automated tests.
