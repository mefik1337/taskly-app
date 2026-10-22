from collections.abc import Callable
from pathlib import Path

from .diff import FileChange
from .paths import classify_path

CODE_KINDS = {"source", "test"}
SOURCE_ROOTS = ("backend/app", "frontend/src")


def _entry(change: FileChange, exists: Callable[[str], bool]) -> dict:
    file_class = classify_path(change.path)
    return {
        "path": change.path,
        "status": change.status,
        "area": file_class.area,
        "kind": file_class.kind,
        "coverage_excluded": file_class.coverage_excluded,
        "changed_lines": change.added_lines,
        "test_path": file_class.test_path,
        "test_exists": bool(file_class.test_path) and exists(file_class.test_path),
        "target": (
            file_class.kind == "source"
            and not file_class.coverage_excluded
            and change.status != "deleted"
            and bool(change.added_lines)
        ),
    }


def build_manifest(changes: list[FileChange], exists: Callable[[str], bool]) -> dict:
    files = [_entry(change, exists) for change in changes]
    return {
        "files": files,
        "targets": [entry["path"] for entry in files if entry["target"]],
        "areas": sorted({entry["area"] for entry in files if entry["kind"] in CODE_KINDS}),
    }


def snapshot_changes(root: Path) -> list[FileChange]:
    changes = []
    for source_root in SOURCE_ROOTS:
        for file in sorted((root / source_root).rglob("*")):
            path = file.relative_to(root).as_posix()
            if file.is_file() and classify_path(path).kind == "source":
                line_count = len(file.read_text(encoding="utf-8").splitlines())
                changes.append(FileChange(path=path, status="snapshot", added_lines=list(range(1, line_count + 1))))
    return changes
