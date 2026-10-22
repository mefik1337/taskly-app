import pytest

from pr_test_agent.models import AgentReport, Analysis, FailedCase, FileCoverage, SuiteResult, Verification
from pr_test_agent.outcome import resolve_status

GREEN = SuiteResult(name="backend full suite", tests=3, passed=3, failed=0, skipped=0, failed_cases=[])
RED = SuiteResult(
    name="agent tests, run 3", tests=3, passed=2, failed=1, skipped=0,
    failed_cases=[FailedCase(name="tests::test_x", message="flaky")],
)
TARGET = FileCoverage(path="backend/app/router.py", covered_lines=[], uncovered_lines=[3])
REPORT = AgentReport(summary="ok", decisions=[], skills_used=[], test_files=[], suspected_bugs=[], verification=[])


def analysis(**overrides) -> Analysis:
    values = {"stack": "backend", "base": "a" * 40, "changed_files": [TARGET.path], "coverage_measured": True,
              "targets": [TARGET], "suite": GREEN}
    return Analysis(**{**values, **overrides})


def verification(**overrides) -> Verification:
    values = {"violations": [], "patch_files": ["backend/tests/test_router.py"], "suites": [GREEN], "coverage": [TARGET]}
    return Verification(**{**values, **overrides})


@pytest.mark.parametrize(
    ("inputs", "expected"),
    [
        ((analysis(coverage_measured=False, targets=[]), None, None), "not_measured"),
        ((analysis(targets=[]), None, None), "no_targets"),
        ((analysis(), None, verification()), "agent_failed"),
        ((analysis(), REPORT, verification(violations=["x"], suites=[])), "rejected"),
        ((analysis(), REPORT, None), "verification_failed"),
        ((analysis(), REPORT, verification(suites=[GREEN, RED])), "verification_failed"),
        ((analysis(), REPORT, verification(suites=[])), "verification_failed"),
        ((analysis(), REPORT, verification(patch_files=[])), "no_changes"),
        ((analysis(), REPORT, verification()), "verified"),
    ],
    ids=["not-measured", "no-targets", "no-report", "guard", "no-verification", "red-rerun", "no-suites",
         "empty-patch", "verified"],
)
def test_the_status_is_decided_by_the_first_stage_that_did_not_succeed(inputs, expected):
    assert resolve_status(*inputs) == expected
