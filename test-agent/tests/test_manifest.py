from pr_test_agent.diff import FileChange
from pr_test_agent.manifest import build_manifest


def test_changed_source_becomes_a_target_paired_with_its_existing_test():
    changes = [FileChange(path="frontend/src/lib/http.ts", added_lines=[3, 4])]
    manifest = build_manifest(changes, exists=lambda path: path == "frontend/src/lib/http.test.ts")
    assert manifest["files"] == [{
        "path": "frontend/src/lib/http.ts",
        "status": "modified",
        "area": "frontend",
        "kind": "source",
        "coverage_excluded": False,
        "changed_lines": [3, 4],
        "test_path": "frontend/src/lib/http.test.ts",
        "test_exists": True,
        "target": True,
    }]
    assert manifest["targets"] == ["frontend/src/lib/http.ts"]
    assert manifest["areas"] == ["frontend"]


def test_only_live_coverage_tracked_sources_with_new_lines_are_targets():
    changes = [
        FileChange(path="backend/app/features/todos/router.py", added_lines=[12]),
        FileChange(path="backend/app/features/todos/schemas.py", added_lines=[20]),
        FileChange(path="backend/app/core/legacy.py", status="deleted"),
        FileChange(path="backend/app/core/config.py", added_lines=[]),
        FileChange(path="backend/tests/test_factory.py", added_lines=[1]),
        FileChange(path="README.md", added_lines=[5]),
    ]
    manifest = build_manifest(changes, exists=lambda path: False)
    assert manifest["targets"] == ["backend/app/features/todos/router.py"]
    assert [entry["target"] for entry in manifest["files"]] == [True, False, False, False, False, False]
    assert manifest["areas"] == ["backend"]


def test_both_areas_need_verification_when_both_stacks_change():
    changes = [
        FileChange(path="frontend/src/features/todos/TodosPage.test.tsx", added_lines=[9]),
        FileChange(path="backend/app/factory.py", added_lines=[4]),
        FileChange(path=".github/workflows/ci.yml", added_lines=[1]),
    ]
    assert build_manifest(changes, exists=lambda path: True)["areas"] == ["backend", "frontend"]
