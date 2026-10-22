import pytest

from pr_test_agent.outcome import resolve_status

PASSING = {"backend": {"tests": 3, "passed": 3, "failures": 0, "errors": 0, "skipped": 0, "failed_cases": []}}
FAILING = {"backend": {"tests": 3, "passed": 2, "failures": 1, "errors": 0, "skipped": 0, "failed_cases": []}}
ERRORED = {"frontend": {"tests": 1, "passed": 0, "failures": 0, "errors": 1, "skipped": 0, "failed_cases": []}}
REPORT = {"summary": "ok"}


@pytest.mark.parametrize("kwargs, expected", [
    ({"has_targets": False, "agent_report": None, "violations": [], "suites": {}, "patch_changed": False}, "no_targets"),
    ({"has_targets": True, "agent_report": None, "violations": [], "suites": PASSING, "patch_changed": True}, "agent_failed"),
    ({"has_targets": True, "agent_report": REPORT, "violations": ["x"], "suites": PASSING, "patch_changed": True}, "rejected"),
    ({"has_targets": True, "agent_report": REPORT, "violations": [], "suites": FAILING, "patch_changed": True}, "verification_failed"),
    ({"has_targets": True, "agent_report": REPORT, "violations": [], "suites": ERRORED, "patch_changed": True}, "verification_failed"),
    ({"has_targets": True, "agent_report": REPORT, "violations": [], "suites": {}, "patch_changed": True}, "verification_failed"),
    ({"has_targets": True, "agent_report": REPORT, "violations": [], "suites": PASSING, "patch_changed": False}, "no_changes"),
    ({"has_targets": True, "agent_report": REPORT, "violations": [], "suites": PASSING, "patch_changed": True}, "verified"),
])
def test_status_reflects_the_first_failed_stage(kwargs, expected):
    assert resolve_status(**kwargs) == expected
