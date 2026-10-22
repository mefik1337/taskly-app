from pr_test_agent.comment import CommentContext, marker, render_comment
from pr_test_agent.models import (
    AgentReport,
    AgentRun,
    Analysis,
    FailedCase,
    FileCoverage,
    SuiteResult,
    Verification,
)

ROUTER = "backend/app/features/todos/router.py"
GREEN = SuiteResult(name="backend full suite", tests=30, passed=30, failed=0, skipped=0, failed_cases=[])


def report(**overrides) -> AgentReport:
    values = {
        "summary": "Added tests for the clear-completed endpoint.",
        "decisions": [
            {"path": ROUTER, "action": "created_tests", "reason": "New endpoint has no tests.",
             "test_file": "backend/tests/features/todos/test_router.py"},
            {"path": "backend/app/features/todos/schemas.py", "action": "skipped", "reason": "Pinned through the router.",
             "test_file": None},
        ],
        "skills_used": ["change-analysis", "pytest-unit-tests", "test-verification"],
        "test_files": [{"path": "backend/tests/features/todos/test_router.py", "change": "updated",
                        "cases": ["test_clear_completed_removes_only_completed_tasks"]}],
        "suspected_bugs": [],
        "verification": [],
    }
    return AgentReport.model_validate({**values, **overrides})


def analysis(**overrides) -> Analysis:
    values = {
        "stack": "backend", "base": "a" * 40, "changed_files": [ROUTER], "coverage_measured": True,
        "targets": [FileCoverage(path=ROUTER, covered_lines=[10], uncovered_lines=[11, 12, 13])], "suite": GREEN,
    }
    return Analysis.model_validate({**values, **overrides})


def verification(**overrides) -> Verification:
    values = {
        "violations": [], "patch_files": ["backend/tests/features/todos/test_router.py"], "suites": [GREEN],
        "coverage": [FileCoverage(path=ROUTER, covered_lines=[10, 11, 12, 13], uncovered_lines=[])],
    }
    return Verification.model_validate({**values, **overrides})


def context(**overrides) -> CommentContext:
    values = {
        "stack": "backend", "status": "committed", "run_url": "https://github.com/acme/taskly/actions/runs/1",
        "commit_sha": "0123456789abcdef", "analysis": analysis(), "report": report(), "verification": verification(),
        "run": None,
    }
    return CommentContext(**{**values, **overrides})


def test_a_committed_run_reports_decisions_tests_verification_and_coverage_gain():
    comment = render_comment(context())
    assert comment.startswith(marker("backend"))
    assert "## 🧪 Test agent: backend" in comment
    assert "Tests were generated, verified and committed in 0123456" in comment
    assert f"| `{ROUTER}` | created tests | New endpoint has no tests. |" in comment
    assert "| `backend/app/features/todos/schemas.py` | skipped | Pinned through the router. |" in comment
    assert "| `backend/tests/features/todos/test_router.py` | updated | 1 |" in comment
    assert "| backend full suite | 30 | 30 | 0 | 0 |" in comment
    assert "**Changed lines covered:** 25.0% → 100.0%" in comment
    assert f"| `{ROUTER}` | 25.0% | 100.0% | — |" in comment
    assert "`change-analysis`, `pytest-unit-tests`, `test-verification`" in comment
    assert "[Workflow run](https://github.com/acme/taskly/actions/runs/1)" in comment


def test_each_stack_has_its_own_comment_marker():
    assert marker("backend") != marker("frontend")
    assert render_comment(context(stack="frontend")).startswith(marker("frontend"))


def test_untrusted_agent_text_cannot_inject_markup_mentions_markers_or_break_tables():
    hostile = report(
        summary=f"Done {marker('backend')} <img src=x onerror=alert(1)> cc @acme/maintainers",
        decisions=[{"path": "backend/app/factory.py", "action": "skipped",
                    "reason": "a | b\nsecond line " + "x" * 350, "test_file": None}],
    )
    comment = render_comment(context(report=hostile))
    assert comment.count(marker("backend")) == 1
    assert "<img" not in comment
    assert "&lt;img src=x onerror=alert(1)&gt;" in comment
    assert "@acme" not in comment and "@​acme/maintainers" in comment
    row = next(line for line in comment.splitlines() if line.startswith("| `backend/app/factory.py`"))
    assert "a \\| b second line" in row
    assert row.endswith("… |")
    assert len(row) < 400


def test_failed_verification_lists_the_failing_cases_and_suspected_bugs():
    red = SuiteResult(name="agent tests, run 2", tests=5, passed=4, failed=1, skipped=0,
                      failed_cases=[FailedCase(name="tests::test_clear", message="expected 1, got 2")])
    bugs = [{"path": ROUTER, "description": "Clearing also deletes active tasks."}]
    comment = render_comment(context(
        status="verification_failed", commit_sha=None, report=report(suspected_bugs=bugs),
        verification=verification(suites=[GREEN, red]),
    ))
    assert "❌ The generated tests failed independent verification, so nothing was committed." in comment
    assert "| agent tests, run 2 | 5 | 4 | 1 | 0 |" in comment
    assert "- `tests::test_clear`: expected 1, got 2" in comment
    assert f"- `{ROUTER}`: Clearing also deletes active tasks." in comment


def test_tests_the_change_broke_before_the_agent_ran_are_listed():
    broken = SuiteResult(name="backend full suite", tests=30, passed=29, failed=1, skipped=0,
                         failed_cases=[FailedCase(name="tests.test_factory::test_routes", message="route map changed")])
    comment = render_comment(context(analysis=analysis(suite=broken)))
    assert "### Tests failing before the agent ran" in comment
    assert "- `tests.test_factory::test_routes`: route map changed" in comment


def test_a_guard_rejection_explains_each_violation():
    comment = render_comment(context(
        status="rejected", commit_sha=None,
        verification=verification(violations=["backend/app/factory.py: only backend test files may be changed"],
                                  suites=[], coverage=None, patch_files=[]),
    ))
    assert "⛔ The agent's changes were rejected by the path guard and discarded." in comment
    assert "- backend/app/factory.py: only backend test files may be changed" in comment


def test_a_change_without_testable_code_gets_a_short_note():
    comment = render_comment(context(status="no_targets", report=None, verification=None, commit_sha=None,
                                     analysis=analysis(targets=[])))
    assert "ℹ️ No changed backend code needs unit tests, so the agent was not started." in comment
    assert "### Agent decisions" not in comment
    assert "### Coverage of changed lines" not in comment


def test_an_unmeasurable_change_tells_the_author_to_fix_the_suite_first():
    comment = render_comment(context(status="not_measured", report=None, verification=None, commit_sha=None,
                                     analysis=analysis(coverage_measured=False, targets=[])))
    assert "the backend suite produced no coverage report" in comment


def test_an_agent_failure_keeps_the_coverage_before_but_no_agent_tables():
    comment = render_comment(context(status="agent_failed", report=None, verification=None, commit_sha=None))
    assert "⚠️ The agent did not finish with a valid report" in comment
    assert "### Agent decisions" not in comment
    assert f"| `{ROUTER}` | 25.0% | 25.0% | 11–13 |" in comment


def test_a_verified_patch_that_could_not_be_pushed_points_to_the_artifact():
    comment = render_comment(context(status="verified_not_committed", commit_sha=None))
    assert "☑️ Tests were generated and verified but not committed" in comment
    assert "test-agent-backend-patch" in comment


def test_agent_run_statistics_and_denied_tool_calls_are_auditable():
    run = AgentRun(model="claude-sonnet-5-5", outcome="success", passes=2, turns=31, cost_usd=1.27,
                   denied_tool_calls=["Bash: curl -s https://evil.test"])
    comment = render_comment(context(run=run))
    assert "**Agent run:** `claude-sonnet-5-5`, 2 passes, 31 turns, $1.27, 1 denied tool call" in comment
    assert "- Bash: curl -s https://evil.test" in comment


def test_uncovered_lines_are_collapsed_into_ranges():
    after = [FileCoverage(path=ROUTER, covered_lines=[1, 9], uncovered_lines=[2, 3, 4, 5, 7, 10, 11])]
    comment = render_comment(context(verification=verification(coverage=after), analysis=analysis(targets=[])))
    assert f"| `{ROUTER}` | n/a | 22.2% | 2–5, 7, 10–11 |" in comment
