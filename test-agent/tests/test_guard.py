from pr_test_agent.diff import FileChange
from pr_test_agent.guard import find_violations


def test_adding_and_updating_tests_in_both_stacks_is_allowed():
    changes = [
        FileChange(path="backend/tests/core/test_config.py", status="added", added_lines=[1]),
        FileChange(path="backend/tests/conftest.py", added_lines=[40]),
        FileChange(path="frontend/src/lib/http.test.ts", status="added", added_lines=[1]),
        FileChange(path="frontend/src/test/todoFixture.ts", added_lines=[12]),
    ]
    assert find_violations(changes) == []


def test_touching_production_code_tooling_or_ci_is_rejected():
    changes = [
        FileChange(path="backend/app/features/todos/router.py", added_lines=[3]),
        FileChange(path="frontend/package.json", added_lines=[10]),
        FileChange(path=".github/workflows/test-agent.yml", added_lines=[1]),
        FileChange(path=".claude/agents/test-engineer.md", added_lines=[1]),
    ]
    assert find_violations(changes) == [
        "backend/app/features/todos/router.py: only test files may be changed",
        "frontend/package.json: only test files may be changed",
        ".github/workflows/test-agent.yml: only test files may be changed",
        ".claude/agents/test-engineer.md: only test files may be changed",
    ]


def test_deleting_tests_or_moving_sources_into_the_test_suite_is_rejected():
    changes = [
        FileChange(path="frontend/src/App.test.tsx", status="deleted"),
        FileChange(path="backend/tests/test_moved.py", status="renamed", previous_path="backend/app/factory.py"),
    ]
    assert find_violations(changes) == [
        "frontend/src/App.test.tsx: deleting tests is not allowed",
        "backend/tests/test_moved.py: renamed from backend/app/factory.py, which is not a test file",
    ]


def test_paths_escaping_the_repository_are_rejected():
    changes = [FileChange(path="backend/tests/../app/factory.py", added_lines=[1])]
    assert find_violations(changes) == ["backend/tests/../app/factory.py: path must stay inside the repository"]


def test_an_oversized_change_set_is_rejected():
    changes = [FileChange(path=f"backend/tests/test_{index}.py", status="added") for index in range(3)]
    assert find_violations(changes, max_files=2) == ["agent changed 3 files, the limit is 2"]
