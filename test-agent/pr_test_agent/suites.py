import re
from pathlib import Path

from junitparser import Error, Failure, JUnitXml, Skipped, TestCase

from .models import FailedCase, SuiteResult

MAX_MESSAGE_LENGTH = 300
ANSI_SEQUENCE = re.compile(r"(?:\x1b|#x1B)\[[0-9;]*[A-Za-z]")
MISSING_REPORT = "No test report was produced; the runner failed before running tests."


def _cases(path: Path) -> list[TestCase]:
    xml = JUnitXml.fromfile(str(path))
    return [case for suite in xml for case in suite] if isinstance(xml, JUnitXml) else list(xml)


def _failure(case: TestCase) -> FailedCase | None:
    problem = next((result for result in case.result if isinstance(result, (Failure, Error))), None)
    if problem is None:
        return None
    message = ANSI_SEQUENCE.sub("", problem.message or (problem.text or "").strip())
    return FailedCase(name=f"{case.classname or ''}::{case.name or ''}", message=message[:MAX_MESSAGE_LENGTH])


def read_suite(name: str, path: Path) -> SuiteResult:
    if not path.is_file():
        return SuiteResult(
            name=name, tests=0, passed=0, failed=1, skipped=0,
            failed_cases=[FailedCase(name=name, message=MISSING_REPORT)],
        )
    cases = _cases(path)
    failed_cases = [failure for case in cases if (failure := _failure(case))]
    skipped = sum(1 for case in cases if any(isinstance(result, Skipped) for result in case.result))
    return SuiteResult(
        name=name,
        tests=len(cases),
        passed=len(cases) - len(failed_cases) - skipped,
        failed=len(failed_cases),
        skipped=skipped,
        failed_cases=failed_cases,
    )
