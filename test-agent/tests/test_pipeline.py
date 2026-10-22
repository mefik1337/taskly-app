from pr_test_agent.models import Analysis, FileCoverage, Verification
from pr_test_agent.guard import touched_test_files
from pr_test_agent.pipeline import analyze, script_runner, selfcheck, verify
from pr_test_agent.stacks import get_stack
from tests.support import FAILING, FakeRunner, agent_patch

BACKEND = get_stack("backend")


def test_analysis_measures_the_changed_lines_of_the_pull_request(repo, pull_request, workspace):
    runner = FakeRunner(repo, hits={1: 1, 2: 1, 3: 1, 4: 0})
    analysis = analyze(repo, BACKEND, workspace, base=pull_request, runner=runner)
    assert analysis.targets == [FileCoverage(path="backend/app/router.py", covered_lines=[3], uncovered_lines=[4])]
    assert analysis.changed_files == ["backend/app/router.py"]
    assert analysis.coverage_measured and analysis.suite.green
    assert runner.calls == [()]
    assert workspace.read(Analysis) == analysis


def test_analysis_reports_tests_the_change_already_broke(repo, pull_request, workspace):
    analysis = analyze(repo, BACKEND, workspace, base=pull_request, runner=FakeRunner(repo, {3: 0}, junit=FAILING))
    assert [case.name for case in analysis.suite.failed_cases] == ["tests.test_factory::test_routes"]


def test_a_backfill_treats_every_line_of_the_stack_as_changed(repo, workspace):
    analysis = analyze(repo, BACKEND, workspace, base=None, runner=FakeRunner(repo, hits={1: 1, 2: 0}))
    assert analysis.targets == [FileCoverage(path="backend/app/router.py", covered_lines=[1], uncovered_lines=[2])]


def test_without_a_coverage_report_the_change_is_not_measured(repo, pull_request, workspace):
    def crashing_runner(stack, out_dir, test_files):
        out_dir.mkdir(parents=True, exist_ok=True)

    analysis = analyze(repo, BACKEND, workspace, base=pull_request, runner=crashing_runner)
    assert not analysis.coverage_measured
    assert analysis.targets == []
    assert not analysis.suite.green


def test_selfcheck_runs_the_full_suite_and_records_the_failures(repo, workspace):
    suite = selfcheck(repo, BACKEND, workspace, runner=FakeRunner(repo, {1: 1}, junit=FAILING))
    assert not suite.green
    assert workspace.selfcheck_path.is_file()


def test_verification_applies_the_patch_runs_the_suite_and_reruns_the_agent_tests_twice(repo, pull_request, workspace):
    runner = FakeRunner(repo, hits={1: 1, 2: 1, 3: 1, 4: 1})
    analyze(repo, BACKEND, workspace, base=pull_request, runner=runner)
    workspace.patch_path.write_text(
        agent_patch(repo, "backend/tests/test_new.py", "def test_new():\n    pass\n"), encoding="utf-8"
    )
    runner.calls.clear()
    verification = verify(repo, BACKEND, workspace, runner=runner)
    assert (repo / "backend" / "tests" / "test_new.py").is_file()
    assert runner.calls == [(), ("backend/tests/test_new.py",), ("backend/tests/test_new.py",)]
    assert [suite.name for suite in verification.suites] == [
        "backend full suite", "agent tests, run 2", "agent tests, run 3"
    ]
    assert verification.coverage == [FileCoverage(path="backend/app/router.py", covered_lines=[3, 4], uncovered_lines=[])]
    assert verification.patch_files == ["backend/tests/test_new.py"]
    assert workspace.read(Verification) == verification


def test_a_patch_outside_the_test_tree_is_rejected_before_anything_runs(repo, pull_request, workspace):
    runner = FakeRunner(repo, hits={1: 1})
    analyze(repo, BACKEND, workspace, base=pull_request, runner=runner)
    workspace.patch_path.write_text(agent_patch(repo, "backend/app/router.py", "hacked\n"), encoding="utf-8")
    runner.calls.clear()
    verification = verify(repo, BACKEND, workspace, runner=runner)
    assert verification.violations == ["backend/app/router.py: only backend test files may be changed"]
    assert runner.calls == []
    assert (repo / "backend" / "app" / "router.py").read_text(encoding="utf-8") == "a\nb\nc\nd\n"


def test_an_empty_patch_still_verifies_the_suite_without_reruns(repo, pull_request, workspace):
    runner = FakeRunner(repo, hits={3: 1, 4: 1})
    analyze(repo, BACKEND, workspace, base=pull_request, runner=runner)
    runner.calls.clear()
    verification = verify(repo, BACKEND, workspace, runner=runner)
    assert runner.calls == [()]
    assert verification.patch_files == []


def test_the_script_runner_runs_the_stack_runner_with_the_output_directory_and_test_files(repo, tmp_path):
    script = repo / BACKEND.runner
    script.parent.mkdir(parents=True)
    script.write_text('#!/usr/bin/env bash\nprintf "%s " "$@" > "$TEST_AGENT_OUT/args.txt"\n', encoding="utf-8")
    out_dir = tmp_path / "out"
    script_runner(repo)(BACKEND, out_dir, ["backend/tests/test_router.py"])
    assert (out_dir / "args.txt").read_text(encoding="utf-8") == "backend/tests/test_router.py "


def test_verification_records_the_tested_files_as_they_were_after_the_runner_formatted_them(repo, pull_request, workspace):
    class FormattingRunner(FakeRunner):
        def __call__(self, stack, out_dir, test_files):
            super().__call__(stack, out_dir, test_files)
            for path in test_files:
                test = self.repo / path
                test.write_text(test.read_text(encoding="utf-8").replace("pass ", "pass"), encoding="utf-8")

    runner = FormattingRunner(repo, hits={3: 1, 4: 1})
    analyze(repo, BACKEND, workspace, base=pull_request, runner=runner)
    workspace.patch_path.write_text(agent_patch(repo, "backend/tests/test_new.py", "def test_new():\n    pass \n"))
    verify(repo, BACKEND, workspace, runner=runner)
    verified = workspace.text(workspace.verified_patch_path)
    assert "+    pass\n" in verified
    assert "pass \n" not in verified
    assert touched_test_files(verified) == ["backend/tests/test_new.py"]
