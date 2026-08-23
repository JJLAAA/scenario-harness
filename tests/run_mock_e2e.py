#!/usr/bin/env python3
"""Mock end-to-end self-test for `bin/repomesh run`.

Creates throwaway harness roots, fake git repos, and mock agent backends in
temp directories. Never contacts real agent CLIs and never touches real
business repositories. Exit code 0 means every case passed.

Run from anywhere:  python3 tests/run_mock_e2e.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

REAL_HARNESS_BIN = Path(__file__).resolve().parents[1] / "bin" / "repomesh"
REAL_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"

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

REGISTRY_YAML = textwrap.dedent(
    """\
    repos:
      alpha:
        path: repos/alpha
        description: First mock repo.
        instruction_sources:
          - AGENTS.md
        key_files:
          - src/
        checks:
          - {alpha_checks}
      beta:
        path: repos/beta
        description: Second mock repo.
        instruction_sources:
          - AGENTS.md
        key_files:
          - src/
        checks:
          - test -f done-marker.txt

    edges:
      - from: beta
        to: alpha
        evidence: "beta consumes the alpha artifact"
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

FREE_STATUS_TEMPLATE = """# Status

Mode: `free`

Scenario: none (free task)

Task ID: `{task_id}`

## Repositories

| Repo | Status | Expected Branch | Actual Branch | Checks |
| --- | --- | --- | --- | --- |
{repo_rows}

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


def make_harness_root(
    tmp: Path, checks_override=None, registry=False, registry_checks_override=None
) -> Path:
    """Copy the CLI into a temp root so harness_root() resolves to the temp."""

    root = tmp / "harness"
    (root / "bin").mkdir(parents=True)
    (root / "scenarios" / "mock").mkdir(parents=True)
    (root / "tasks").mkdir(parents=True)
    shutil.copy2(REAL_HARNESS_BIN, root / "bin" / "repomesh")
    shutil.copytree(REAL_TEMPLATES_DIR, root / "templates")
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
    if registry:
        (root / "repos.yaml").write_text(
            REGISTRY_YAML.format(
                alpha_checks=registry_checks_override or "test -f done-marker.txt"
            ),
            encoding="utf-8",
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


def make_free_task(
    root: Path,
    order=("beta", "alpha"),
    step="spec_review_approved",
    planning="complete.",
    spec_review="approved by user.",
    name="free-task",
    branch="scenario/mock-task",
):
    task_dir = root / "tasks" / name
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "spec.md").write_text("# Task Spec\n\nFree mock request.\n", encoding="utf-8")
    (task_dir / "validation.md").write_text("# Validation Report\n", encoding="utf-8")
    repo_rows = "\n".join(
        f"| {repo} | not started | {branch} | - | pending |" for repo in order
    )
    (task_dir / "status.md").write_text(
        FREE_STATUS_TEMPLATE.format(
            task_id=name,
            repo_rows=repo_rows,
            step=step,
            planning=planning,
            spec_review=spec_review,
        ),
        encoding="utf-8",
    )
    return task_dir


def run_cli(root: Path, extra_args, env_extra=None):
    env = dict(os.environ)
    mockbin = root.parent / "mockbin"
    env["PATH"] = f"{mockbin}{os.pathsep}{env['PATH']}"
    for key, value in (env_extra or {}).items():
        env[key] = value
    return sh([str(root / "bin" / "repomesh"), *extra_args], env=env)


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
        cli = str(root / "bin" / "repomesh")
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
                str(root / "bin" / "repomesh"),
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


@case("validate-registry: must-do checks, Q4-a/Q3-B warnings, subset parser")
def test_validate_registry():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw), registry=True)
        cli = str(root / "bin" / "repomesh")
        ok = sh([cli, "validate-registry", "--json"])
        assert ok.returncode == 0, ok.stdout + ok.stderr
        report = json.loads(ok.stdout)
        assert report["status"] == "ok"
        assert [item["key"] for item in report["repos"]] == ["alpha", "beta"]
        assert report["edges"] == [{"from": "beta", "to": "alpha"}]
        assert report["findings"] == []

        # Block the PyYAML import so validation runs on the subset parser.
        blocker = root.parent / "noyaml"
        blocker.mkdir()
        (blocker / "yaml.py").write_text(
            "raise ImportError('yaml blocked for test')\n", encoding="utf-8"
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = str(blocker)
        subset = sh([cli, "validate-registry"], env=env)
        assert subset.returncode == 0, subset.stdout + subset.stderr

    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw), registry=True)
        cli = str(root / "bin" / "repomesh")
        registry_file = root / "repos.yaml"
        base = registry_file.read_text(encoding="utf-8")

        def codes_of(text):
            registry_file.write_text(text, encoding="utf-8")
            result = sh([cli, "validate-registry", "--json"])
            assert result.returncode == 2
            return {item["code"] for item in json.loads(result.stdout)["findings"]}

        assert "edge_endpoint_unknown" in codes_of(base.replace("to: alpha", "to: ghost"))
        assert "duplicate_edge" in codes_of(
            base + "  - from: beta\n    to: alpha\n    evidence: \"duplicate\"\n"
        )
        assert "invalid_edge_evidence" in codes_of(
            base.replace(
                'evidence: "beta consumes the alpha artifact"', 'evidence: ""'
            )
        )
        assert "task_specific_dependency_field" in codes_of(
            base.replace("path: repos/alpha", "path: repos/alpha\n    branch: feature-x")
        )
        assert "repo_path_missing" in codes_of(base.replace("repos/alpha", "repos/ghost"))

    # Q4-a / Q3-B: registry missing a scenario repo -> warning only, exits stay 0.
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw))
        (root / "repos.yaml").write_text(
            "repos:\n  alpha:\n    path: repos/alpha\n", encoding="utf-8"
        )
        cli = str(root / "bin" / "repomesh")
        reg = sh([cli, "validate-registry", "--json"])
        assert reg.returncode == 0
        reg_report = json.loads(reg.stdout)
        assert "repo_not_in_registry" in {
            item["code"] for item in reg_report["findings"]
        }
        assert all(item["level"] == "warning" for item in reg_report["findings"])
        val = sh([cli, "validate-scenario", "mock", "--json"])
        assert val.returncode == 0
        val_report = json.loads(val.stdout)
        assert val_report["status"] == "ok"
        assert "repo_not_in_registry" in {
            item["code"] for item in val_report["findings"]
        }
        assert all(item["level"] == "warning" for item in val_report["findings"])

    # Field divergence between the two files -> warning on both sides.
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw), registry=True)
        registry_file = root / "repos.yaml"
        registry_file.write_text(
            registry_file.read_text(encoding="utf-8").replace(
                "test -f done-marker.txt", "echo divergent-check", 1
            ),
            encoding="utf-8",
        )
        cli = str(root / "bin" / "repomesh")
        reg = sh([cli, "validate-registry", "--json"])
        assert reg.returncode == 0
        assert "registry_field_divergence" in {
            item["code"] for item in json.loads(reg.stdout)["findings"]
        }
        val = sh([cli, "validate-scenario", "mock", "--json"])
        assert val.returncode == 0
        assert "registry_field_divergence" in {
            item["code"] for item in json.loads(val.stdout)["findings"]
        }


@case("init-task --free scaffolds mode and default branch; free CLI variants")
def test_free_init():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw), registry=True)
        cli = str(root / "bin" / "repomesh")
        dry = sh([cli, "init-task", "--free", "2026-08-23-demo", "--request", "free mock", "--dry-run"])
        assert dry.returncode == 0, dry.stderr
        made = sh([cli, "init-task", "--free", "2026-08-23-demo", "--request", "free mock"])
        assert made.returncode == 0, made.stderr
        task_dir = root / "tasks" / "2026-08-23-demo"
        for name in ("spec.md", "status.md", "decisions.md", "validation.md"):
            assert (task_dir / name).exists(), name
        status_text = (task_dir / "status.md").read_text(encoding="utf-8")
        assert "Mode: `free`" in status_text
        assert "Default expected branch: `scenario/2026-08-23-demo`" in status_text
        assert sh([cli, "init-task", "--free"]).returncode == 64
        assert sh([cli, "init-task", "--free", "mock", "x"]).returncode == 64

        # list-tasks: free filter by default; scenario filter excludes the free task.
        listing = sh([cli, "list-tasks", "--json"])
        assert listing.returncode == 0
        data = json.loads(listing.stdout)
        assert [item["task_id"] for item in data["tasks"]] == ["2026-08-23-demo"]
        assert data["tasks"][0]["mode"] == "free"
        scenario_listing = sh([cli, "list-tasks", "mock", "--json"])
        assert json.loads(scenario_listing.stdout)["tasks"] == []

        # preflight/checks free variants run off the task declaration + registry.
        free_task = make_free_task(root)
        pre = sh([cli, "preflight", "--task", "free-task", "--no-write", "--json"])
        assert pre.returncode == 0, pre.stdout + pre.stderr
        pre_report = json.loads(pre.stdout)
        assert [item["key"] for item in pre_report["repos"]] == ["beta", "alpha"]
        assert all(item["branch_result"] == "pass" for item in pre_report["repos"])
        chk = sh([cli, "checks", "--task", "free-task"])
        assert chk.returncode == 0
        assert "test -f done-marker.txt" in chk.stdout
        assert "repo=beta" in chk.stdout and "repo=alpha" in chk.stdout
        single = sh([cli, "checks", "--task", "free-task", "--repo", "alpha"])
        assert single.returncode == 0
        assert "repo=alpha" in single.stdout and "repo=beta" not in single.stdout


@case("free run without gates is rejected (fail-closed, same categories)")
def test_free_run_gates():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw), registry=True)
        task_dir = make_free_task(
            root, step="task_created", planning="not started.", spec_review="pending."
        )
        result = run_cli(root, ["run", "--task", "free-task"])
        assert result.returncode == 2, result.stdout
        assert "planning_gate_missing" in result.stderr
        status_text = (task_dir / "status.md").read_text(encoding="utf-8")
        assert "run-status" in status_text and "planning_gate_missing" in status_text
        assert not (root / "repos" / "beta" / "done-marker.txt").exists()

        make_free_task(
            root,
            step="planning_complete",
            planning="complete.",
            spec_review="pending.",
            name="free-task2",
        )
        result2 = run_cli(root, ["run", "--task", "free-task2"])
        assert result2.returncode == 2, result2.stdout
        assert "spec_review_gate_missing" in result2.stderr
        assert not (root / "repos" / "alpha" / "done-marker.txt").exists()


@case("free run respects the task-declared order, not the registry order")
def test_free_run_order():
    with tempfile.TemporaryDirectory() as raw:
        # Registry lists alpha first; the task declares beta first. alpha is
        # rigged to fail, so reaching beta's marker before the failure proves
        # the declared order (not the registry order) drove the run.
        root = make_harness_root(Path(raw), registry=True)
        make_free_task(root, order=("beta", "alpha"))
        set_mode(root, "alpha", "fail")
        result = run_cli(root, ["run", "--task", "free-task"])
        assert result.returncode == 2, result.stdout
        assert "stage=agent" in result.stderr and "repo=alpha" in result.stderr
        assert (root / "repos" / "beta" / "done-marker.txt").exists()
        assert not (root / "repos" / "alpha" / "done-marker.txt").exists()


def delete_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", re.S | re.M)
    return pattern.sub("", text)


def add_repo_row(status_text: str, row: str) -> str:
    lines = status_text.splitlines()
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].startswith("|"):
            lines.insert(index + 1, row)
            break
    else:
        raise AssertionError("status.md has no table row to append after")
    return "\n".join(lines) + "\n"


def complete_scenario_task(root: Path, name="ct-scenario"):
    cli = str(root / "bin" / "repomesh")
    assert sh([cli, "init-task", "mock", name, "--request", "check-task fixture"]).returncode == 0
    task_dir = root / "tasks" / name
    status = (task_dir / "status.md").read_text(encoding="utf-8")
    status = status.replace(
        "Task initialized. Next step: run preflight before entering business repositories.",
        "current step: spec_review_approved",
    )
    status += "\n## Planning Gate\n\ncomplete.\n\n## Spec Review Gate\n\napproved by user.\n"
    (task_dir / "status.md").write_text(status, encoding="utf-8")
    return task_dir


def complete_free_task(root: Path, name="ct-free"):
    cli = str(root / "bin" / "repomesh")
    assert sh([cli, "init-task", "--free", name, "--request", "check-task fixture"]).returncode == 0
    task_dir = root / "tasks" / name
    status = (task_dir / "status.md").read_text(encoding="utf-8")
    separator = "| --- | --- | --- | --- | --- |\n"
    rows = (
        "| beta | not started | scenario/mock-task | - | pending |\n"
        "| alpha | not started | scenario/mock-task | - | pending |\n"
    )
    assert separator in status
    status = status.replace(separator, separator + rows, 1)
    status = status.replace(
        "Task initialized. Next step: candidate scoping from repos.yaml, then the Planning Pass before entering business repositories.",
        "current step: spec_review_approved",
    )
    status += "\n## Planning Gate\n\ncomplete.\n\n## Spec Review Gate\n\napproved by user.\n"
    (task_dir / "status.md").write_text(status, encoding="utf-8")
    spec = (task_dir / "spec.md").read_text(encoding="utf-8")
    spec = spec.replace("TBD — record the candidate repo set", "Recorded candidate repo set")
    (task_dir / "spec.md").write_text(spec, encoding="utf-8")
    return task_dir


@case("check-task: gate-ready tasks of both modes lint clean")
def test_check_task_happy():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw), registry=True)
        cli = str(root / "bin" / "repomesh")
        scenario_task = complete_scenario_task(root)
        free_task = complete_free_task(root)
        for task_dir, expected_mode in (
            (scenario_task, "scenario:mock"),
            (free_task, "free"),
        ):
            result = sh([cli, "check-task", task_dir.name, "--json"])
            assert result.returncode == 0, result.stdout
            report = json.loads(result.stdout)
            assert report["status"] == "ok"
            assert report["mode"] == expected_mode
            assert report["findings"] == []
            assert report["repos"] and all(item.get("source") for item in report["repos"])


@case("check-task: shape violations are errors with distinct finding codes")
def test_check_task_broken():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw), registry=True)
        cli = str(root / "bin" / "repomesh")

        def lint(task_dir):
            result = sh([cli, "check-task", task_dir.name, "--json"])
            assert result.returncode == 2, result.stdout
            report = json.loads(result.stdout)
            assert report["status"] == "error"
            return report

        def codes(report):
            return {item["code"] for item in report["findings"]}

        # deleted common-core section
        task = complete_scenario_task(root, "ct-broken-section")
        (task / "spec.md").write_text(
            delete_section((task / "spec.md").read_text(encoding="utf-8"), "Scope"),
            encoding="utf-8",
        )
        report = lint(task)
        assert "missing_section" in codes(report)
        assert any("Scope" in item["message"] for item in report["findings"])

        # invalid current step value
        task = complete_scenario_task(root, "ct-broken-step")
        (task / "status.md").write_text(
            (task / "status.md")
            .read_text(encoding="utf-8")
            .replace("current step: spec_review_approved", "current step: banana"),
            encoding="utf-8",
        )
        assert "current_step_invalid" in codes(lint(task))

        # mode-aware: scenario table row not declared in scenario.yaml
        task = complete_scenario_task(root, "ct-broken-row")
        (task / "status.md").write_text(
            add_repo_row(
                (task / "status.md").read_text(encoding="utf-8"),
                "| ghost | not started | scenario/ct-broken-row | - | pending |",
            ),
            encoding="utf-8",
        )
        assert "repo_not_in_scenario" in codes(lint(task))

        # mode-aware: free table row not registered in repos.yaml
        task = complete_free_task(root, "ct-broken-free-row")
        (task / "status.md").write_text(
            add_repo_row(
                (task / "status.md").read_text(encoding="utf-8"),
                "| ghost | not started | scenario/mock-task | - | pending |",
            ),
            encoding="utf-8",
        )
        assert "repo_not_in_registry" in codes(lint(task))

        # invalid mode value
        task = complete_free_task(root, "ct-broken-mode")
        (task / "status.md").write_text(
            (task / "status.md")
            .read_text(encoding="utf-8")
            .replace("Mode: `free`", "Mode: `banana`"),
            encoding="utf-8",
        )
        assert "mode_invalid" in codes(lint(task))

        # mode-aware: mode points at a scenario that does not exist
        task = complete_scenario_task(root, "ct-broken-pointing")
        (task / "status.md").write_text(
            (task / "status.md")
            .read_text(encoding="utf-8")
            .replace("Mode: `scenario:mock`", "Mode: `scenario:ghost`"),
            encoding="utf-8",
        )
        assert "mode_scenario_unknown" in codes(lint(task))

        # mode-aware: mode-specific sections missing
        task = complete_free_task(root, "ct-broken-topology")
        (task / "spec.md").write_text(
            delete_section(
                (task / "spec.md").read_text(encoding="utf-8"), "Task-Declared Topology"
            ),
            encoding="utf-8",
        )
        report = lint(task)
        assert "missing_section" in codes(report)
        assert any(
            "Task-Declared Topology" in item["message"] for item in report["findings"]
        )
        task = complete_scenario_task(root, "ct-broken-order")
        (task / "spec.md").write_text(
            delete_section((task / "spec.md").read_text(encoding="utf-8"), "Scenario Order"),
            encoding="utf-8",
        )
        assert any(
            item["code"] == "missing_section" and "Scenario Order" in item["message"]
            for item in lint(task)["findings"]
        )

        # misaligned table row (column count)
        task = complete_scenario_task(root, "ct-broken-columns")
        (task / "status.md").write_text(
            add_repo_row(
                (task / "status.md").read_text(encoding="utf-8"),
                "| alpha | not started | scenario/ct-broken-columns | - |",
            ),
            encoding="utf-8",
        )
        assert "table_row_misaligned" in codes(lint(task))


@case("check-task: legacy task without Mode line and unrecorded gates are warnings only")
def test_check_task_legacy_warnings():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw))
        cli = str(root / "bin" / "repomesh")
        task = complete_scenario_task(root, "ct-legacy")
        status = (task / "status.md").read_text(encoding="utf-8")
        status = status.replace("Mode: `scenario:mock`\n\n", "")
        status = status.replace("current step: spec_review_approved", "Task initialized.")
        status = status.split("\n## Planning Gate")[0] + "\n"
        (task / "status.md").write_text(status, encoding="utf-8")
        result = sh([cli, "check-task", "ct-legacy", "--json"])
        assert result.returncode == 0, result.stdout
        report = json.loads(result.stdout)
        assert report["status"] == "ok"
        assert report["mode"] == "scenario:mock"  # legacy fallback via Scenario: line
        leveled = {item["code"]: item["level"] for item in report["findings"]}
        assert leveled.get("mode_missing") == "warning"
        assert leveled.get("gate_section_missing") == "warning"
        assert leveled.get("current_step_missing") == "warning"
        assert all(level == "warning" for level in leveled.values())


@case("check-task: init-task output of both modes is error-free (sync lock)")
def test_check_task_self_consistency():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw), registry=True)
        cli = str(root / "bin" / "repomesh")
        assert sh([cli, "init-task", "mock", "ct-fresh", "--request", "fresh"]).returncode == 0
        assert sh([cli, "init-task", "--free", "ct-fresh-free", "--request", "fresh"]).returncode == 0
        expected_warning_codes = {
            "ct-fresh": {"current_step_missing", "gate_section_missing"},
            "ct-fresh-free": {
                "current_step_missing",
                "gate_section_missing",
                "repo_table_empty",
                "candidate_scoping_pending",
            },
        }
        for name, expected in expected_warning_codes.items():
            result = sh([cli, "check-task", name, "--json"])
            assert result.returncode == 0, result.stdout
            report = json.loads(result.stdout)
            assert report["status"] == "ok"
            assert report["findings"], f"{name}: fresh tasks should carry stage warnings"
            assert all(item["level"] == "warning" for item in report["findings"]), name
            assert {item["code"] for item in report["findings"]} == expected, name


@case("check-task: section baseline is extracted from templates/ at runtime")
def test_check_task_template_probe():
    with tempfile.TemporaryDirectory() as raw:
        root = make_harness_root(Path(raw))
        cli = str(root / "bin" / "repomesh")
        task = complete_scenario_task(root, "ct-probe")
        assert sh([cli, "check-task", "ct-probe"]).returncode == 0
        template = root / "templates" / "spec.md"
        template.write_text(
            template.read_text(encoding="utf-8")
            + "\n## Zzz Runtime Probe\n\n<!-- template-driven schema probe -->\n",
            encoding="utf-8",
        )
        result = sh([cli, "check-task", "ct-probe", "--json"])
        assert result.returncode == 2, result.stdout
        report = json.loads(result.stdout)
        assert any(
            item["code"] == "missing_section" and "Zzz Runtime Probe" in item["message"]
            for item in report["findings"]
        )


@case("free run verdict paths unchanged; checks come from the registry")
def test_free_run_verdict_and_checks():
    with tempfile.TemporaryDirectory() as raw:
        # Scenario checks are rigged to fail while the registry check passes:
        # a green free run proves the checks source is repos.yaml.
        root = make_harness_root(
            Path(raw),
            registry=True,
            checks_override="exit 1",
            registry_checks_override=(
                "test -f done-marker.txt && touch registry-checks-ran.txt"
            ),
        )
        for mode, category in (
            ("no-verdict", "verdict_missing"),
            ("blocked", "agent_report_blocked"),
            ("bad-verdict", "verdict_invalid"),
        ):
            make_free_task(root, name=f"free-{mode}")
            set_mode(root, "beta", mode)  # beta is first in the declared order
            result = run_cli(root, ["run", "--task", f"free-{mode}"])
            assert result.returncode == 2, (mode, result.stdout)
            assert f"category={category}" in result.stderr, mode
            if mode == "blocked":
                assert "mock blocker: upstream contract mismatch" in result.stderr
            assert not (root / "repos" / "alpha" / "done-marker.txt").exists()
            set_mode(root, "beta", None)

        task_dir = make_free_task(root, name="free-clean")
        result = run_cli(root, ["run", "--task", "free-clean"])
        assert result.returncode == 0, result.stderr
        for repo in ("beta", "alpha"):
            assert (root / "repos" / repo / "done-marker.txt").exists()
        assert (root / "repos" / "alpha" / "registry-checks-ran.txt").exists()
        status_text = (task_dir / "status.md").read_text(encoding="utf-8")
        assert "| beta | pass | success | ok | pass | complete |" in status_text
        assert "| alpha | pass | success | ok | pass | complete |" in status_text
        assert "Recommended current step: `complete`" in status_text


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
