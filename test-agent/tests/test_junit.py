from pr_test_agent.junit import summarize_junit

PYTEST = """<?xml version="1.0" encoding="utf-8"?>
<testsuites name="pytest tests"><testsuite name="pytest" errors="0" failures="1" skipped="1" tests="4">
<testcase classname="tests.core.test_config" name="test_explicit_url_wins" time="0.001"/>
<testcase classname="tests.core.test_config" name="test_builds_url_from_environment" time="0.001">
<failure message="AssertionError: assert 5433 == 5432">trace</failure></testcase>
<testcase classname="tests.api.test_health" name="test_health_reports_ok" time="0.001"><skipped message="no db"/></testcase>
<testcase classname="tests.api.test_health" name="test_health_queries_database" time="0.002">
<error message="fixture 'client' not found">trace</error></testcase>
</testsuite></testsuites>
"""

VITEST = """<?xml version="1.0" encoding="UTF-8" ?>
<testsuites name="vitest tests" tests="2" failures="0" errors="0" time="1.2">
<testsuite name="src/lib/http.test.ts" tests="2" failures="0" errors="0" skipped="0">
<testcase classname="src/lib/http.test.ts" name="request &gt; returns parsed JSON" time="0.01"></testcase>
<testcase classname="src/lib/http.test.ts" name="request &gt; maps 422 to a validation message" time="0.01"></testcase>
</testsuite></testsuites>
"""


def test_pytest_report_is_summarized_with_each_failing_case():
    assert summarize_junit(PYTEST) == {
        "tests": 4,
        "passed": 1,
        "failures": 1,
        "errors": 1,
        "skipped": 1,
        "failed_cases": [
            {"name": "tests.core.test_config::test_builds_url_from_environment", "message": "AssertionError: assert 5433 == 5432"},
            {"name": "tests.api.test_health::test_health_queries_database", "message": "fixture 'client' not found"},
        ],
    }


def test_vitest_report_with_only_passing_cases():
    summary = summarize_junit(VITEST)
    assert (summary["tests"], summary["passed"], summary["failed_cases"]) == (2, 2, [])
