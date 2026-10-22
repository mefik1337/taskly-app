from functools import cached_property
from typing import Literal

from pathspec import GitIgnoreSpec
from pydantic import BaseModel, ConfigDict

StackName = Literal["backend", "frontend"]


class Stack(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: StackName
    root: str
    production_root: str
    test_patterns: tuple[str, ...]
    runner: str
    coverage_report: str
    test_skill: str

    @cached_property
    def _tests(self) -> GitIgnoreSpec:
        return GitIgnoreSpec.from_lines(self.test_patterns)

    def owns_test(self, path: str) -> bool:
        return self._tests.match_file(path)


STACKS: dict[str, Stack] = {
    "backend": Stack(
        name="backend",
        root="backend",
        production_root="backend/app",
        test_patterns=("backend/tests/**",),
        runner="test-agent/bin/run-backend-tests",
        coverage_report="backend/coverage/coverage.xml",
        test_skill="pytest-unit-tests",
    ),
    "frontend": Stack(
        name="frontend",
        root="frontend",
        production_root="frontend/src",
        test_patterns=("frontend/src/**/*.test.ts", "frontend/src/**/*.test.tsx", "frontend/src/test/**"),
        runner="test-agent/bin/run-frontend-tests",
        coverage_report="frontend/coverage/cobertura-coverage.xml",
        test_skill="vitest-unit-tests",
    ),
}


def get_stack(name: str) -> Stack:
    if name not in STACKS:
        raise ValueError(f"unknown stack: {name}")
    return STACKS[name]
