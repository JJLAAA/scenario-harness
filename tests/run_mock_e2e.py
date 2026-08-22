#!/usr/bin/env python3
"""Mock end-to-end self-test for `bin/scenario-harness run`.

Creates throwaway harness roots, fake git repos, and mock agent backends in
temp directories. Never contacts real agent CLIs and never touches real
business repositories. Exit code 0 means every case passed.

Run from anywhere:  python3 tests/run_mock_e2e.py
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

REAL_HARNESS_BIN = Path(__file__).resolve().parents[1] / "bin" / "scenario-harness"

MOCK_AGENT = textwrap.dedent(
    '''\
    #!/usr/bin/env python3
    import json, os, re, subprocess, sys, time

    argv = sys.argv[1:]
    prompt = argv[argv.index("-p") + 1] if "-p" in argv else ""
    match = re.search(r"(\\S*/tasks/\\S*?)/status\\.md", prompt)
    task_dir = match.group(1).strip("`") if match else None
    control_path = os.path.join(os.getcwd(), "mock-agent-control.json")
    mode = "success"
    if os.path.exists(control_path):
        with open(control_path, "r", encoding="utf-8") as handle:
            mode = json.load(handle).get("mode", "success")

    if mode == "fail":
        print("mock agent: deliberate failure", file=sys.stderr)
        sys.exit(1)
    if mode == "hang":
        child = subprocess.Popen(["sleep", "600"])
        with open("mock-pids.txt", "w", encoding="utf-8") as handle:
            handle.write(f"agent={os.getpid()}\\nchild={child.pid}\\n")
        time.sleep(600)
        sys.exit(1)
    if mode == "env-dump":
        with open("env-dump.txt", "w", encoding="utf-8") as handle:
            for name in sorted(os.environ):
                handle.write(f"{name}={os.environ[name]}\\n")

    with open("done-marker.txt", "w", encoding="utf-8") as handle:
        handle.write("done\\n")
    if task_dir:
        with open(os.path.join(task_dir, "validation.md"), "a", encoding="utf-8") as handle:
            handle.write("\\nmock-child: appended task-file update\\n")
        if mode != "no-verdict":
            verdict = "verdict: ok\\nblocker: none\\nresidual_risk: none\\n"
            if mode == "blocked":
                verdict = (
                    "verdict: blocked\\n"
                    "blocker: mock blocker: upstream contract mismatch\\n"
                    "residual_risk: none\\n"
                )
            elif mode == "bad-verdict":
                verdict = "verdict: yes\\nblocker: none\\nresidual_risk: none\\n"
            verdicts_dir = os.path.join(task_dir, "verdicts")
            os.makedirs(verdicts_dir, exist_ok=True)
            verdict_path = os.path.join(verdicts_dir, os.path.basename(os.getcwd()) + ".md")
            with open(verdict_path, "w", encoding="utf-8") as handle:
                handle.write(verdict)
    print(json.dumps({"type": "result", "subtype": "success"}))
    sys.exit(0)
    '''
)

SCENARIO_YAML = textwrap.dedent(
    """\
    order:
      - alpha
      - beta

    repos:
      alpha:
        path: repos/alpha
        role: source
        description: First mock repo.
        outputs:
          - id: alpha-artifact
            type: file
            name: alpha marker artifact
            description: Marker artifact produced by alpha.
        instruction_sources:
          - AGENTS.md
        key_files:
          - src/
        checks:
          - test -f done-marker.txt
      beta:
        path: repos/beta
        role: consumer
        description: Second mock repo.
        depends_on:
          - repo: alpha
            output: alpha-artifact
            reason: Consumes the alpha artifact.
        instruction_sources:
          - AGENTS.md
        key_files:
          - src/
        checks:
          - test -f done-marker.txt
    """
)

STATUS_TEMPLATE = """# Status

Scenario: `mock`
Task ID: `mock-task`

## Repositories

| Repo | Status | Expected Branch | Actual Branch | Checks |
| --- | --- | --- | --- | --- |
| alpha | not started | scenario/mock-task | - | pending |
| beta | not started | scenario/mock-task | - | pending |

## Current Step

current step: {step}

## Planning Gate

{planning}

## Spec Review Gate

{spec_review}

## Blockers

None.
"""


def sh(args, **kwargs):
    return subprocess.run(args, text=True, capture_output=True, **kwargs)


def make_git_repo(path: Path, branch: str):
    path.mkdir(parents=True)
    sh(
        ["git", "-c", "init.defaultBranch=" + branch, "init", "-q", str(path)]
    )
    sh(["git", "-C", str(path), "config", "user.email", "mock@example.com"])
    sh(["git", "-C", str(path), "config", "user.name", "Mock"])
    (path / "AGENTS.md").write_text("# Mock repo instructions\n", encoding="utf-8")
    (path / "src").mkdir()
    (path / "src" / "keep.txt").write_text("keep\n", encoding="utf-8")
    sh(["git", "-C", str(path), "add", "."])
    sh(["git", "-C", str(path), "commit", "-q", "-m", "init"])


def make_harness_root(tmp: Path, checks_override=None) -> Path:
    """Copy the CLI into a temp root so harness_root() resolves to the temp."""

    root = tmp / "harness"
    (root / "bin").mkdir(parents=True)
    (root / "scenarios" / "mock").mkdir(parents=True)
    (root / "tasks").mkdir(parents=True)
    shutil.copy2(REAL_HARNESS_BIN, root / "bin" / "scenario-harness")
    scenario_yaml = SCENARIO_YAML
    if checks_override:
        scenario_yaml = SCENARIO_YAML.replace(
            "test -f done-marker.txt", checks_override
        )
    (root / "scenarios" / "mock" / "scenario.yaml").write_text(
        scenario_yaml, encoding="utf-8"
    )
    (root / "scenarios" / "mock" / "README.md").write_text(
        "# Mock scenario\n\nMock SOP for the run self-test.\n", encoding="utf-8"
    )
    for key in ("alpha", "beta"):
        make_git_repo(root / "repos" / key, "scenario/mock-task")
    mockbin = tmp / "mockbin"
    mockbin.mkdir()
    (mockbin / "claude").write_text(MOCK_AGENT, encoding="utf-8")
    (mockbin / "claude").chmod(0o755)
    return root


def make_task(root: Path, step="spec_review_approved", planning="complete.", spec_review="approved by user."):
    task_dir = root / "tasks" / "mock-task"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "spec.md").write_text("# Task Spec\n\nMock request.\n", encoding="utf-8")
    (task_dir / "validation.md").write_text("# Validation Report\n", encoding="utf-8")
    (task_dir / "status.md").write_text(
        STATUS_TEMPLATE.format(step=step, planning=planning, spec_review=spec_review),
        encoding="utf-8",
    )
    return task_dir


def run_cli(root: Path, extra_args, env_extra=None):
    env = dict(os.environ)
    mockbin = root.parent / "mockbin"
    env["PATH"] = f"{mockbin}{os.pathsep}{env['PATH']}"
    for key, value in (env_extra or {}).items():
        env[key] = value
    return sh([str(root / "bin" / "scenario-harness"), *extra_args], env=env)


def set_mode(root: Path, repo: str, mode: str | None):
    control = root / "repos" / repo / "mock-agent-control.json"
    if mode is None:
        control.unlink(missing_ok=True)
        return
    control.write_text(json.dumps({"mode": mode}), encoding="utf-8")


CASES = []


def case(name):
    def register(func):
        CASES.append((name, func))
        return func

    return register


@case("regression: existing commands still work")
def test_regression():
    # Real harness: the example scenario's business repos are not cloned on
    # this machine, so validation legitimately exits 2 with only
    # repo_path_missing findings; listing commands stay healthy.
    validate = sh([str(REAL_HARNESS_BIN), "validate-scenario", "example-contract-change", "--json"])
    assert validate.returncode == 2
    report = json.loads(validate.stdout)
    codes = {item["code"] for item in report["findings"]}
    assert codes and codes <= {"repo_path_missing"}
    plan = sh([str(REAL_HARNESS_BIN), "plan-scenario", "example-contract-change", "--json"])
    assert plan.returncode == 2 and json.loads(plan.stdout)["scenario"] == "example-contract-change"
    init = sh([str(REAL_HARNESS_BIN), "init-task", "example-contract-change", "zz-test", "--dry-run"])
    assert init.returncode == 2 and "not created" in init.stderr
    assert sh([str(REAL_HARNESS_BIN), "checks", "example-contract-change"]).returncode == 0

    # Temp harness with a fully valid scenario: every command exits 0.
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw))
        cli = str(root / "bin" / "scenario-harness")
        assert sh([cli, "validate-scenario", "mock"]).returncode == 0
        assert sh([cli, "plan-scenario", "mock", "--json"]).returncode == 0
        assert sh([cli, "init-task", "mock", "t2", "--dry-run"]).returncode == 0
        assert sh([cli, "list-tasks", "mock"]).returncode == 0
        assert sh([cli, "checks", "mock"]).returncode == 0


@case("dry-run on example-contract-change renders correct prompts")
def test_dry_run_real_scenario():
    with tempfile.TemporaryDirectory() as raw:
        task_dir = Path(raw) / "demo-task"
        task_dir.mkdir()
        (task_dir / "status.md").write_text(
            STATUS_TEMPLATE.format(
                step="planning_complete",
                planning="complete.",
                spec_review="pending.",
            ).replace("mock-task", "demo-task").replace("| alpha |", "| contract-repo |").replace("| beta |", "| consumer-repo |").replace(
                "scenario/mock-task", "scenario/demo"
            )
            + "\n| worker-repo | not started | scenario/demo | - | pending |\n",
            encoding="utf-8",
        )
        result = sh(
            [
                str(REAL_HARNESS_BIN),
                "run",
                "example-contract-change",
                "--task",
                str(task_dir),
                "--dry-run",
            ]
        )
        assert result.returncode == 0, result.stderr
        out = result.stdout
        assert "contract-repo" in out and "consumer-repo" in out and "worker-repo" in out
        assert "Expected task branch (exact match required): `scenario/demo`" in out
        assert ".trellis/workflow.md" in out
        assert "openapi.yaml" in out
        assert '"claude"' in out and "--output-format" in out
        assert "--settings" in out  # claude argv carries the tool-search override
        assert "Do NOT run git commit" in out
        assert "verdicts/contract-repo.md" in out
        assert "verdict: ok" in out and "residual_risk:" in out


@case("run refuses when the Planning Gate is missing")
def test_gate_planning_missing():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw))
        task_dir = make_task(root, step="task_created", planning="not started.", spec_review="pending.")
        result = run_cli(root, ["run", "mock", "--task", str(task_dir)])
        assert result.returncode == 2, result.stdout
        assert "planning" in result.stderr.lower()
        status_text = (task_dir / "status.md").read_text(encoding="utf-8")
        assert "run-status" in status_text and "planning_gate_missing" in status_text
        assert not (root / "repos" / "alpha" / "done-marker.txt").exists()


@case("run refuses when the Spec Review Gate is missing")
def test_gate_spec_missing():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw))
        task_dir = make_task(root, step="planning_complete", planning="complete.", spec_review="pending.")
        result = run_cli(root, ["run", "mock", "--task", str(task_dir)])
        assert result.returncode == 2, result.stdout
        assert "spec review" in result.stderr.lower()
        assert not (root / "repos" / "alpha" / "done-marker.txt").exists()


@case("success path completes scenario order and writes task files")
def test_success_path():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw))
        task_dir = make_task(root)
        result = run_cli(root, ["run", "mock", "--task", "mock-task"])
        assert result.returncode == 0, result.stderr
        for repo in ("alpha", "beta"):
            assert (root / "repos" / repo / "done-marker.txt").exists()
            assert (task_dir / "logs" / f"{repo}.log").exists()
            assert (task_dir / "verdicts" / f"{repo}.md").exists()
        status_text = (task_dir / "status.md").read_text(encoding="utf-8")
        validation_text = (task_dir / "validation.md").read_text(encoding="utf-8")
        assert "Recommended current step: `complete`" in status_text, status_text[-800:]
        assert "| alpha | pass | success | ok | pass | complete |" in status_text
        assert "| beta | pass | success | ok | pass | complete |" in status_text
        assert "mock-child: appended task-file update" in validation_text
        assert "run-validation" in validation_text
        assert not (task_dir / ".run.lock").exists()


@case("agent failure blocks the run and records the taxonomy")
def test_agent_failure():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw))
        task_dir = make_task(root)
        set_mode(root, "alpha", "fail")
        result = run_cli(root, ["run", "mock", "--task", "mock-task"])
        assert result.returncode == 2, result.stdout
        assert "stage=agent" in result.stderr and "nonzero_exit" in result.stderr
        validation_text = (task_dir / "validation.md").read_text(encoding="utf-8")
        assert "`agent` x category `nonzero_exit`" in validation_text
        assert not (root / "repos" / "beta" / "done-marker.txt").exists()
        assert not (task_dir / ".run.lock").exists()


@case("check failure blocks the run even after agent success")
def test_check_failure():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw), checks_override="exit 1")
        task_dir = make_task(root)
        result = run_cli(root, ["run", "mock", "--task", "mock-task"])
        assert result.returncode == 2, result.stdout
        assert "stage=checks" in result.stderr and "check_failed" in result.stderr
        assert (root / "repos" / "alpha" / "done-marker.txt").exists()
        assert not (root / "repos" / "beta" / "done-marker.txt").exists()


@case("timeout triggers the termination ladder and kills the process group")
def test_timeout_tree_kill():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw))
        task_dir = make_task(root)
        set_mode(root, "alpha", "hang")
        started = time.monotonic()
        result = run_cli(
            root,
            ["run", "mock", "--task", "mock-task", "--timeout", "2", "--term-grace", "2"],
        )
        duration = time.monotonic() - started
        assert result.returncode == 2, result.stdout
        assert "stage=agent" in result.stderr and "category=timeout" in result.stderr
        assert duration < 30
        pids = {}
        for line in (root / "repos" / "alpha" / "mock-pids.txt").read_text().splitlines():
            key, value = line.split("=")
            pids[key] = int(value)
        for name, pid in pids.items():
            try:
                os.kill(pid, 0)
                alive = True
            except ProcessLookupError:
                alive = False
            except PermissionError:
                alive = True
            assert not alive, f"{name} pid {pid} survived the termination ladder"
        assert not (task_dir / ".run.lock").exists()


@case("concurrent second run is rejected by the task lock; stale locks are reclaimed")
def test_lock():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw))
        task_dir = make_task(root)
        set_mode(root, "alpha", "hang")
        env = dict(os.environ)
        env["PATH"] = f"{root.parent / 'mockbin'}{os.pathsep}{env['PATH']}"
        first = subprocess.Popen(
            [
                str(root / "bin" / "scenario-harness"),
                "run",
                "mock",
                "--task",
                "mock-task",
                "--timeout",
                "120",
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            lock_path = task_dir / ".run.lock"
            deadline = time.monotonic() + 15
            while not lock_path.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            assert lock_path.exists(), "first run never took the lock"

            second = run_cli(root, ["run", "mock", "--task", "mock-task"])
            assert second.returncode == 64, second.stdout
            assert "locked" in second.stderr.lower()
        finally:
            first.send_signal(signal.SIGKILL)
            first.wait()
            pids = {}
            pid_file = root / "repos" / "alpha" / "mock-pids.txt"
            if pid_file.exists():
                for line in pid_file.read_text().splitlines():
                    key, value = line.split("=")
                    pids[key] = int(value)
                for pid in [pids.get("agent"), pids.get("child")]:
                    if pid:
                        try:
                            os.killpg(pid, signal.SIGKILL)
                        except (ProcessLookupError, PermissionError):
                            pass
        assert (task_dir / ".run.lock").exists(), "lock should remain after SIGKILL"

        set_mode(root, "alpha", None)
        result = run_cli(root, ["run", "mock", "--task", "mock-task"])
        assert result.returncode == 0, result.stderr
        assert (root / "repos" / "beta" / "done-marker.txt").exists()


@case("env overlay passes allowlisted variables and drops ambient ones")
def test_env_overlay():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw))
        task_dir = make_task(root)
        set_mode(root, "alpha", "env-dump")
        result = run_cli(
            root,
            ["run", "mock", "--task", "mock-task", "--repo", "alpha"],
            env_extra={"HARNESS_PRIVATE_LEAK": "secret-value"},
        )
        assert result.returncode == 0, result.stderr
        dump = (root / "repos" / "alpha" / "env-dump.txt").read_text(encoding="utf-8")
        assert "PATH=" in dump and "HOME=" in dump
        assert "HARNESS_PRIVATE_LEAK" not in dump


@case("--repo runs a single repo and gates still apply")
def test_single_repo_mode():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw))
        task_dir = make_task(root, step="planning_complete", planning="complete.", spec_review="pending.")
        result = run_cli(root, ["run", "mock", "--task", "mock-task", "--repo", "alpha"])
        assert result.returncode == 2
        assert "spec review" in result.stderr.lower()


@case("missing verdict file blocks the run (fail-closed)")
def test_verdict_missing():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw))
        task_dir = make_task(root)
        set_mode(root, "alpha", "no-verdict")
        result = run_cli(root, ["run", "mock", "--task", "mock-task"])
        assert result.returncode == 2, result.stdout
        assert "stage=agent" in result.stderr and "verdict_missing" in result.stderr
        status_text = (task_dir / "status.md").read_text(encoding="utf-8")
        assert "| alpha | pass | verdict_missing | missing | - | blocked |" in status_text
        assert not (root / "repos" / "beta" / "done-marker.txt").exists()
        assert not (task_dir / ".run.lock").exists()


@case("self-reported blocked verdict blocks the run before checks")
def test_verdict_blocked():
    with tempfile.TemporaryDirectory() as raw:
        # checks are rigged to fail; reaching check_failed would prove checks ran
        root = make_harness_root(Path(raw), checks_override="exit 1")
        task_dir = make_task(root)
        set_mode(root, "alpha", "blocked")
        result = run_cli(root, ["run", "mock", "--task", "mock-task"])
        assert result.returncode == 2, result.stdout
        assert "stage=agent" in result.stderr and "agent_report_blocked" in result.stderr
        assert "mock blocker: upstream contract mismatch" in result.stderr
        validation_text = (task_dir / "validation.md").read_text(encoding="utf-8")
        assert "`agent` x category `agent_report_blocked`" in validation_text
        assert "mock blocker: upstream contract mismatch" in validation_text
        assert not (root / "repos" / "beta" / "done-marker.txt").exists()
        assert not (task_dir / ".run.lock").exists()


@case("malformed verdict file blocks the run")
def test_verdict_invalid():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw))
        task_dir = make_task(root)
        set_mode(root, "alpha", "bad-verdict")
        result = run_cli(root, ["run", "mock", "--task", "mock-task"])
        assert result.returncode == 2, result.stdout
        assert "stage=agent" in result.stderr and "verdict_invalid" in result.stderr
        assert not (root / "repos" / "beta" / "done-marker.txt").exists()


@case("stale verdicts from an earlier run are reset before spawn")
def test_verdict_stale_reset():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw))
        task_dir = make_task(root)
        verdicts = task_dir / "verdicts"
        verdicts.mkdir()
        (verdicts / "alpha.md").write_text(
            "verdict: ok\nblocker: none\nresidual_risk: none\n", encoding="utf-8"
        )
        set_mode(root, "alpha", "no-verdict")
        result = run_cli(root, ["run", "mock", "--task", "mock-task"])
        assert result.returncode == 2, result.stdout
        assert "verdict_missing" in result.stderr

        set_mode(root, "alpha", None)
        result = run_cli(root, ["run", "mock", "--task", "mock-task"])
        assert result.returncode == 0, result.stderr
        assert (root / "repos" / "beta" / "done-marker.txt").exists()


def main() -> int:
    failures = 0
    for name, func in CASES:
        try:
            func()
            print(f"PASS: {name}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL: {name}: {exc}")
        except Exception as exc:  # noqa: BLE001 - report unexpected errors per case
            failures += 1
            print(f"ERROR: {name}: {exc!r}")
    print(f"\n{len(CASES) - failures}/{len(CASES)} cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
