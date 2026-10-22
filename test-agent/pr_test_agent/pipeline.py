import os
import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from unidiff import PatchSet

from .coverage import changed_line_coverage
from .guard import find_violations, touched_test_files
from .models import Analysis, SuiteResult, Verification
from .stacks import Stack
from .suites import read_suite
from .workspace import Workspace

Runner = Callable[[Stack, Path, Sequence[str]], None]


def script_runner(repo: Path) -> Runner:
    def run(stack: Stack, out_dir: Path, test_files: Sequence[str]) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "TEST_AGENT_OUT": str(out_dir.resolve())}
        subprocess.run([shutil.which("bash") or "bash", stack.runner, *test_files], cwd=repo, env=env, check=False)

    return run


def _git(repo: Path, *args: str, stdin: str | None = None) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, input=stdin, check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout


def _diff(repo: Path, stack: Stack, base: str | None) -> str:
    if base is None:
        empty_tree = _git(repo, "hash-object", "-t", "tree", "--stdin", stdin="").strip()
        return _git(repo, "diff", "--no-color", empty_tree, "HEAD", "--", stack.root)
    return _git(repo, "diff", "--no-color", "--find-renames", f"{base}...HEAD", "--", stack.root)


def _run_suite(
    repo: Path, stack: Stack, runner: Runner, out_dir: Path, name: str, test_files: Sequence[str] = ()
) -> SuiteResult:
    runner(stack, out_dir, test_files)
    if not test_files:
        report = repo / stack.coverage_report
        if report.is_file():
            shutil.copyfile(report, out_dir / "coverage.xml")
    return read_suite(name, out_dir / "junit.xml")


def _tested_patch(repo: Path, patch_files: list[str]) -> str:
    if not patch_files:
        return ""
    _git(repo, "add", "--intent-to-add", "--", *patch_files)
    return _git(repo, "diff", "--no-color", "--binary", "--", *patch_files)


def analyze(repo: Path, stack: Stack, workspace: Workspace, base: str | None, runner: Runner) -> Analysis:
    diff = _diff(repo, stack, base)
    workspace.root.mkdir(parents=True, exist_ok=True)
    workspace.diff_path.write_text(diff, encoding="utf-8")
    out_dir = workspace.run_dir("before")
    suite = _run_suite(repo, stack, runner, out_dir, f"{stack.name} full suite")
    coverage = changed_line_coverage(diff, out_dir / "coverage.xml", repo)
    analysis = Analysis(
        stack=stack.name,
        base=base,
        changed_files=[change.path for change in PatchSet(diff)],
        coverage_measured=coverage is not None,
        targets=coverage or [],
        suite=suite,
    )
    workspace.write(analysis)
    return analysis


def selfcheck(repo: Path, stack: Stack, workspace: Workspace, runner: Runner) -> SuiteResult:
    suite = _run_suite(repo, stack, runner, workspace.run_dir("selfcheck"), f"{stack.name} full suite")
    workspace.write(suite)
    return suite


def verify(repo: Path, stack: Stack, workspace: Workspace, runner: Runner) -> Verification:
    patch = workspace.text(workspace.patch_path)
    violations = find_violations(stack, patch)
    if violations:
        verification = Verification(violations=violations, patch_files=[], suites=[], coverage=None)
        workspace.write(verification)
        return verification
    patch_files = touched_test_files(patch)
    if patch_files:
        _git(repo, "apply", "--whitespace=nowarn", str(workspace.patch_path.resolve()))
    out_dir = workspace.run_dir("verify")
    suites = [_run_suite(repo, stack, runner, out_dir, f"{stack.name} full suite")]
    coverage = changed_line_coverage(workspace.text(workspace.diff_path), out_dir / "coverage.xml", repo)
    if patch_files:
        suites += [
            _run_suite(repo, stack, runner, workspace.run_dir(f"rerun-{attempt}"), f"agent tests, run {attempt}", patch_files)
            for attempt in (2, 3)
        ]
    workspace.verified_patch_path.write_text(_tested_patch(repo, patch_files), encoding="utf-8")
    verification = Verification(violations=[], patch_files=patch_files, suites=suites, coverage=coverage)
    workspace.write(verification)
    return verification
