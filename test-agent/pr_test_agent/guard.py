from pathlib import PurePosixPath

from .diff import FileChange
from .paths import classify_path

DEFAULT_MAX_FILES = 25


def _is_safe(path: str) -> bool:
    posix = PurePosixPath(path)
    return not posix.is_absolute() and ".." not in posix.parts


def _is_test(path: str) -> bool:
    return classify_path(path).kind == "test"


def _violation(change: FileChange) -> str | None:
    if not _is_safe(change.path) or (change.previous_path and not _is_safe(change.previous_path)):
        return f"{change.path}: path must stay inside the repository"
    if not _is_test(change.path):
        return f"{change.path}: only test files may be changed"
    if change.status == "deleted":
        return f"{change.path}: deleting tests is not allowed"
    if change.previous_path and not _is_test(change.previous_path):
        return f"{change.path}: renamed from {change.previous_path}, which is not a test file"
    return None


def find_violations(changes: list[FileChange], max_files: int = DEFAULT_MAX_FILES) -> list[str]:
    if len(changes) > max_files:
        return [f"agent changed {len(changes)} files, the limit is {max_files}"]
    return [violation for change in changes if (violation := _violation(change))]
