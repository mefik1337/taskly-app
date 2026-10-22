from pr_test_agent.guard import find_violations, touched_test_files
from pr_test_agent.stacks import get_stack

BACKEND = get_stack("backend")
FRONTEND = get_stack("frontend")


def added(path: str, mode: str = "100644") -> str:
    return (
        f"diff --git a/{path} b/{path}\nnew file mode {mode}\nindex 0000000..1111111\n"
        f"--- /dev/null\n+++ b/{path}\n@@ -0,0 +1 @@\n+line\n"
    )


def modified(path: str) -> str:
    return f"diff --git a/{path} b/{path}\nindex 1111111..2222222 100644\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-old\n+new\n"


def deleted(path: str) -> str:
    return (
        f"diff --git a/{path} b/{path}\ndeleted file mode 100644\nindex 1111111..0000000\n"
        f"--- a/{path}\n+++ /dev/null\n@@ -1 +0,0 @@\n-line\n"
    )


def renamed(source: str, target: str) -> str:
    return (
        f"diff --git a/{source} b/{target}\nsimilarity index 90%\nrename from {source}\nrename to {target}\n"
        f"index 1111111..2222222 100644\n--- a/{source}\n+++ b/{target}\n@@ -1 +1 @@\n-old\n+new\n"
    )


def test_an_empty_patch_has_no_violations():
    assert find_violations(BACKEND, "") == []


def test_adding_and_updating_test_files_of_the_stack_is_allowed():
    patch = added("frontend/src/lib/http.test.ts") + modified("frontend/src/test/fakeApi.ts")
    assert find_violations(FRONTEND, patch) == []


def test_production_code_ci_agent_files_and_the_other_stack_are_rejected():
    patch = "".join(
        modified(path)
        for path in (
            "backend/app/features/todos/router.py",
            ".github/workflows/test-agent.yml",
            ".claude/agents/test-engineer.md",
            "frontend/src/lib/http.test.ts",
        )
    )
    assert find_violations(BACKEND, patch) == [
        "backend/app/features/todos/router.py: only backend test files may be changed",
        ".github/workflows/test-agent.yml: only backend test files may be changed",
        ".claude/agents/test-engineer.md: only backend test files may be changed",
        "frontend/src/lib/http.test.ts: only backend test files may be changed",
    ]


def test_deleting_tests_is_rejected():
    assert find_violations(BACKEND, deleted("backend/tests/test_health.py")) == [
        "backend/tests/test_health.py: deleting files is not allowed"
    ]


def test_moving_production_code_into_the_test_tree_is_rejected():
    patch = renamed("backend/app/factory.py", "backend/tests/test_factory_copy.py")
    assert find_violations(BACKEND, patch) == [
        "backend/tests/test_factory_copy.py: renamed from backend/app/factory.py, which is not a backend test file"
    ]


def test_symbolic_links_are_rejected_even_inside_the_test_tree():
    assert find_violations(BACKEND, added("backend/tests/link.py", mode="120000")) == [
        "backend/tests/link.py: symbolic links are not allowed"
    ]


def test_paths_escaping_the_repository_are_rejected():
    assert find_violations(BACKEND, modified("backend/tests/../app/factory.py")) == [
        "backend/tests/../app/factory.py: path must stay inside the repository"
    ]


def test_an_oversized_change_set_is_rejected_as_a_whole():
    patch = "".join(added(f"backend/tests/test_{index}.py") for index in range(3))
    assert find_violations(BACKEND, patch, max_files=2) == ["the patch changes 3 files, the limit is 2"]


def test_a_patch_that_cannot_be_parsed_is_rejected():
    patch = "diff --git a/backend/tests/a.py b/backend/tests/a.py\n--- a/backend/tests/a.py\n+++ b/backend/tests/a.py\n@@ -1,5 +1,5 @@\n+x\n"
    [violation] = find_violations(BACKEND, patch)
    assert violation.startswith("the patch cannot be parsed")


def test_the_touched_test_files_are_the_added_and_modified_targets():
    patch = added("frontend/src/lib/http.test.ts") + modified("frontend/src/test/fakeApi.ts")
    assert touched_test_files(patch) == ["frontend/src/lib/http.test.ts", "frontend/src/test/fakeApi.ts"]
