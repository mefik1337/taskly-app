from pr_test_agent.report import MARKER, render_comment


def _agent_report(**overrides):
    report = {
        "summary": "Added tests for the new stats endpoint.",
        "decisions": [
            {"path": "backend/app/features/todos/router.py", "action": "created_tests",
             "reason": "New endpoint has no tests.", "test_file": "backend/tests/features/todos/test_router.py"},
            {"path": "frontend/src/features/todos/types.ts", "action": "skipped",
             "reason": "Type-only change.", "test_file": None},
        ],
        "skills_used": ["change-analysis", "pytest-unit-tests", "test-verification"],
        "test_files": [{"path": "backend/tests/features/todos/test_router.py", "change": "updated",
                        "cases": ["test_stats_counts_completed_tasks"]}],
        "suspected_bugs": [],
    }
    return {**report, **overrides}


def _data(**overrides):
    data = {
        "status": "committed",
        "agent": _agent_report(),
        "verification": {"violations": [], "suites": {
            "backend": {"tests": 30, "passed": 30, "failures": 0, "errors": 0, "skipped": 0, "failed_cases": []},
        }, "repeat_runs": 3},
        "coverage": {
            "before": {"total": {"relevant": 4, "covered": 1, "percent": 25.0}, "files": [
                {"path": "backend/app/features/todos/router.py", "covered_lines": [10], "uncovered_lines": [11, 12, 13], "percent": 25.0}]},
            "after": {"total": {"relevant": 4, "covered": 4, "percent": 100.0}, "files": [
                {"path": "backend/app/features/todos/router.py", "covered_lines": [10, 11, 12, 13], "uncovered_lines": [], "percent": 100.0}]},
        },
        "run_url": "https://github.com/acme/taskly/actions/runs/1",
        "commit_sha": "0123456789abcdef",
    }
    return {**data, **overrides}


def test_committed_run_is_reported_with_decisions_verification_and_coverage_gain():
    comment = render_comment(_data())
    assert comment.startswith(MARKER)
    assert "Tests were generated, verified and committed in 0123456" in comment
    assert "| `backend/app/features/todos/router.py` | created tests | New endpoint has no tests. |" in comment
    assert "| `frontend/src/features/todos/types.ts` | skipped | Type-only change. |" in comment
    assert "| `backend/tests/features/todos/test_router.py` | updated | 1 |" in comment
    assert "| backend | 30 | 30 | 0 | 0 |" in comment
    assert "| `backend/app/features/todos/router.py` | 25.0% | 100.0% | — |" in comment
    assert "**Changed lines covered:** 25.0% → 100.0%" in comment
    assert "`change-analysis`, `pytest-unit-tests`, `test-verification`" in comment
    assert "https://github.com/acme/taskly/actions/runs/1" in comment


def test_untrusted_agent_text_cannot_inject_markup_mentions_or_break_tables():
    hostile = _agent_report(
        summary="Done <!-- taskly-test-agent --> <img src=x onerror=alert(1)> cc @acme/maintainers",
        decisions=[{"path": "backend/app/factory.py", "action": "skipped",
                    "reason": "a | b\nsecond line " + "x" * 600, "test_file": None}],
    )
    comment = render_comment(_data(agent=hostile))
    assert comment.count(MARKER) == 1
    assert "<img" not in comment
    assert "&lt;img src=x onerror=alert(1)&gt;" in comment
    assert "@acme" not in comment
    assert "@​acme/maintainers" in comment
    decision_row = next(line for line in comment.splitlines() if line.startswith("| `backend/app/factory.py`"))
    assert "a \| b second line" in decision_row
    assert decision_row.endswith("… |")
    assert len(decision_row) < 400


def test_failed_verification_lists_failing_cases_and_is_not_committed():
    suites = {"frontend": {"tests": 5, "passed": 4, "failures": 1, "errors": 0, "skipped": 0, "failed_cases": [
        {"name": "src/lib/http.test.ts::maps 422", "message": "expected 'x' to be 'y'"}]}}
    agent = _agent_report(suspected_bugs=[
        {"path": "frontend/src/lib/http.ts", "description": "422 handling ignores the server detail."}])
    comment = render_comment(_data(
        status="verification_failed", agent=agent, commit_sha=None,
        verification={"violations": [], "suites": suites, "repeat_runs": 3},
    ))
    assert "❌ The generated tests failed independent verification, so nothing was committed." in comment
    assert "| frontend | 5 | 4 | 1 | 0 |" in comment
    assert "- `src/lib/http.test.ts::maps 422`: expected 'x' to be 'y'" in comment
    assert "### Possible bugs in production code" in comment
    assert "- `frontend/src/lib/http.ts`: 422 handling ignores the server detail." in comment


def test_guard_rejection_explains_each_violation():
    comment = render_comment(_data(
        status="rejected", commit_sha=None,
        verification={"violations": ["backend/app/factory.py: only test files may be changed"], "suites": {}, "repeat_runs": 0},
    ))
    assert "⛔ The agent's changes were rejected by the path guard and discarded." in comment
    assert "- backend/app/factory.py: only test files may be changed" in comment
    assert "### Possible bugs in production code" not in comment


def test_pull_request_without_testable_changes_gets_a_short_note():
    comment = render_comment({"status": "no_targets", "agent": None, "verification": None, "coverage": None,
                              "run_url": "https://example.test/run", "commit_sha": None})
    assert comment.startswith(MARKER)
    assert "ℹ️ No changed production code needs unit tests" in comment
    assert "### Agent decisions" not in comment
    assert "### Verification" not in comment
    assert "[Workflow run](https://example.test/run)" in comment


def test_agent_failure_without_structured_output_is_reported_without_tables():
    comment = render_comment(_data(status="agent_failed", agent=None, commit_sha=None))
    assert "⚠️ The agent did not finish with a valid report" in comment
    assert "### Agent decisions" not in comment
    assert "### Coverage of changed lines" in comment


def test_agent_that_skips_every_file_does_not_render_an_empty_test_table():
    agent = _agent_report(test_files=[], decisions=[
        {"path": "backend/app/factory.py", "action": "skipped", "reason": "Already covered by router tests.", "test_file": None}])
    comment = render_comment(_data(status="no_changes", agent=agent, commit_sha=None))
    assert "✅ The agent reviewed the changes and decided that no new tests are needed." in comment
    assert "### Tests written by the agent" not in comment


def test_verified_patch_that_could_not_be_pushed_points_to_the_artifact():
    comment = render_comment(_data(status="verified_not_committed", commit_sha=None))
    assert "☑️ Tests were generated and verified but not committed" in comment
    assert "test-agent-patch" in comment


def test_agent_run_statistics_and_denied_tool_calls_are_auditable():
    run = {"model": "claude-sonnet-5-5", "outcome": "success", "turns": 31, "cost_usd": 1.27,
           "denied_tool_calls": ["Bash: curl -s https://evil.test"]}
    comment = render_comment(_data(run=run))
    assert "**Agent run:** `claude-sonnet-5-5`, 31 turns, $1.27, 1 denied tool call" in comment
    assert "- Bash: curl -s https://evil.test" in comment
