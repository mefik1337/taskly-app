import pytest

from pr_test_agent.stacks import get_stack


@pytest.mark.parametrize(
    ("stack", "path", "owned"),
    [
        ("backend", "backend/tests/features/todos/test_router.py", True),
        ("backend", "backend/tests/conftest.py", True),
        ("backend", "backend/app/features/todos/router.py", False),
        ("backend", "frontend/src/lib/http.test.ts", False),
        ("frontend", "frontend/src/lib/http.test.ts", True),
        ("frontend", "frontend/src/features/todos/TodosPage.test.tsx", True),
        ("frontend", "frontend/src/test/fakeApi.ts", True),
        ("frontend", "frontend/src/lib/http.ts", False),
        ("frontend", "frontend/vite.config.ts", False),
        ("frontend", "backend/tests/test_health.py", False),
    ],
)
def test_a_stack_owns_only_its_own_test_files(stack, path, owned):
    assert get_stack(stack).owns_test(path) is owned


def test_an_unknown_stack_is_rejected():
    with pytest.raises(ValueError, match="unknown stack: mobile"):
        get_stack("mobile")
