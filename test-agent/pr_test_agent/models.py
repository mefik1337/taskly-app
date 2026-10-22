from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def percent_of(covered: int, relevant: int) -> float | None:
    return round(100 * covered / relevant, 1) if relevant else None


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FileCoverage(Model):
    path: str
    covered_lines: list[int]
    uncovered_lines: list[int]

    @property
    def percent(self) -> float | None:
        return percent_of(len(self.covered_lines), len(self.covered_lines) + len(self.uncovered_lines))


class FailedCase(Model):
    name: str
    message: str


class SuiteResult(Model):
    name: str
    tests: int
    passed: int
    failed: int
    skipped: int
    failed_cases: list[FailedCase]

    @property
    def green(self) -> bool:
        return self.tests > 0 and self.failed == 0


class Decision(Model):
    path: str
    action: Literal["created_tests", "updated_tests", "skipped"]
    reason: str = Field(max_length=400)
    test_file: str | None


class WrittenTestFile(Model):
    path: str
    change: Literal["created", "updated"]
    cases: list[str]


class SuspectedBug(Model):
    path: str
    description: str = Field(max_length=400)


class VerificationStep(Model):
    stack: Literal["backend", "frontend"]
    command: str
    passed: bool


class AgentReport(Model):
    summary: str = Field(max_length=600)
    decisions: list[Decision]
    skills_used: list[str]
    test_files: list[WrittenTestFile]
    suspected_bugs: list[SuspectedBug]
    verification: list[VerificationStep]


class AgentRun(Model):
    model: str | None
    outcome: str
    passes: int
    turns: int | None
    cost_usd: float
    denied_tool_calls: list[str]


class Analysis(Model):
    stack: Literal["backend", "frontend"]
    base: str | None
    changed_files: list[str]
    coverage_measured: bool
    targets: list[FileCoverage]
    suite: SuiteResult


class Verification(Model):
    violations: list[str]
    patch_files: list[str]
    suites: list[SuiteResult]
    coverage: list[FileCoverage] | None
