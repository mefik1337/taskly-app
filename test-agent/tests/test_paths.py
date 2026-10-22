import pytest

from pr_test_agent.paths import classify_path


def test_backend_application_module_is_a_testable_backend_source():
    file_class = classify_path("backend/app/features/todos/repository.py")
    assert file_class.area == "backend"
    assert file_class.kind == "source"
    assert file_class.coverage_excluded is False
    assert file_class.test_path == "backend/tests/features/todos/test_repository.py"


@pytest.mark.parametrize("path", [
    "backend/app/main.py",
    "backend/app/features/todos/__init__.py",
    "backend/app/features/todos/schemas.py",
    "backend/app/features/todos/models.py",
])
def test_backend_modules_omitted_from_coverage_are_flagged_as_excluded(path):
    file_class = classify_path(path)
    assert file_class.kind == "source"
    assert file_class.coverage_excluded is True


@pytest.mark.parametrize("path", [
    "backend/tests/features/todos/test_router.py",
    "backend/tests/conftest.py",
    "backend/tests/mocks.py",
])
def test_backend_test_suite_files_are_classified_as_tests(path):
    file_class = classify_path(path)
    assert file_class.area == "backend"
    assert file_class.kind == "test"
    assert file_class.test_path is None


@pytest.mark.parametrize("path, expected_test_path", [
    ("frontend/src/lib/http.ts", "frontend/src/lib/http.test.ts"),
    ("frontend/src/features/todos/components/TodoList.tsx", "frontend/src/features/todos/components/TodoList.test.tsx"),
])
def test_frontend_module_is_paired_with_a_colocated_test(path, expected_test_path):
    file_class = classify_path(path)
    assert file_class.area == "frontend"
    assert file_class.kind == "source"
    assert file_class.coverage_excluded is False
    assert file_class.test_path == expected_test_path


@pytest.mark.parametrize("path", [
    "frontend/src/lib/http.test.ts",
    "frontend/src/features/todos/TodosPage.test.tsx",
    "frontend/src/test/todoFixture.ts",
    "frontend/src/test/setup.ts",
])
def test_frontend_tests_and_test_support_are_classified_as_tests(path):
    file_class = classify_path(path)
    assert file_class.area == "frontend"
    assert file_class.kind == "test"
    assert file_class.test_path is None


@pytest.mark.parametrize("path", [
    "frontend/src/main.tsx",
    "frontend/src/design-system/components/Button/Button.tsx",
    "frontend/src/features/todos/types.ts",
    "frontend/src/design-system/components/Alert/Alert.types.ts",
    "frontend/src/features/todos/index.ts",
    "frontend/src/features/todos/constants.tsx",
    "frontend/src/features/todos/filters.constants.ts",
    "frontend/src/features/todos/api/queryKeys.ts",
    "frontend/src/lib/queryClient.ts",
])
def test_frontend_modules_omitted_from_coverage_are_flagged_as_excluded(path):
    file_class = classify_path(path)
    assert file_class.kind == "source"
    assert file_class.coverage_excluded is True


@pytest.mark.parametrize("path, area", [
    ("README.md", "other"),
    (".github/workflows/ci.yml", "other"),
    ("docs/release.test.md", "other"),
    ("frontend/package.json", "frontend"),
    ("frontend/src/styles.css", "frontend"),
    ("backend/requirements.txt", "backend"),
    ("backend/app/static/logo.svg", "backend"),
])
def test_non_code_files_are_not_test_targets(path, area):
    file_class = classify_path(path)
    assert file_class.area == area
    assert file_class.kind == "other"
    assert file_class.test_path is None
