from pr_test_agent.suites import read_suite

PYTEST = """<?xml version="1.0" encoding="utf-8"?>
<testsuites name="pytest tests"><testsuite name="pytest" errors="1" failures="1" skipped="1" tests="4">
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


def test_a_pytest_report_counts_outcomes_and_names_every_failing_case(tmp_path):
    report = tmp_path / "junit.xml"
    report.write_text(PYTEST, encoding="utf-8")
    suite = read_suite("backend", report)
    assert (suite.tests, suite.passed, suite.failed, suite.skipped) == (4, 1, 2, 1)
    assert [(case.name, case.message) for case in suite.failed_cases] == [
        ("tests.core.test_config::test_builds_url_from_environment", "AssertionError: assert 5433 == 5432"),
        ("tests.api.test_health::test_health_queries_database", "fixture 'client' not found"),
    ]
    assert not suite.green


def test_a_vitest_report_with_only_passing_cases_is_green(tmp_path):
    report = tmp_path / "junit.xml"
    report.write_text(VITEST, encoding="utf-8")
    suite = read_suite("frontend", report)
    assert (suite.tests, suite.passed, suite.failed_cases) == (2, 2, [])
    assert suite.green


def test_a_missing_report_is_a_failed_suite_so_a_crashed_runner_never_passes(tmp_path):
    suite = read_suite("backend", tmp_path / "missing.xml")
    assert not suite.green
    assert [case.message for case in suite.failed_cases] == [
        "No test report was produced; the runner failed before running tests."
    ]


def test_an_empty_suite_is_not_green(tmp_path):
    report = tmp_path / "junit.xml"
    report.write_text('<testsuites><testsuite name="pytest" tests="0"/></testsuites>', encoding="utf-8")
    assert not read_suite("backend", report).green


def test_terminal_colour_codes_are_stripped_and_long_messages_truncated(tmp_path):
    report = tmp_path / "junit.xml"
    report.write_text(
        '<testsuite><testcase classname="tests.test_factory" name="test_routes">'
        "<failure message=\"Left contains #x1B[33m'/api/todos/completed'#x1B[39;49;00m\">trace</failure></testcase>"
        f'<testcase classname="tests.test_x" name="test_long"><failure message="{"x" * 500}"/></testcase>'
        "</testsuite>",
        encoding="utf-8",
    )
    first, second = read_suite("backend", report).failed_cases
    assert first.message == "Left contains '/api/todos/completed'"
    assert len(second.message) == 300
