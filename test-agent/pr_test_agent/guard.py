from pathlib import PurePosixPath

from unidiff import PatchedFile, PatchSet, UnidiffParseError

from .stacks import Stack

DEFAULT_MAX_FILES = 25


def _strip_prefix(path: str) -> str:
    return path[2:] if path.startswith(("a/", "b/")) else path


def _inside_repository(path: str) -> bool:
    posix = PurePosixPath(path)
    return not posix.is_absolute() and ".." not in posix.parts


def _violation(stack: Stack, change: PatchedFile) -> str | None:
    path = change.path
    source = _strip_prefix(change.source_file)
    if not _inside_repository(path) or (change.is_rename and not _inside_repository(source)):
        return f"{path}: path must stay inside the repository"
    if not stack.owns_test(path):
        return f"{path}: only {stack.name} test files may be changed"
    if change.is_removed_file:
        return f"{path}: deleting files is not allowed"
    if change.is_rename and not stack.owns_test(source):
        return f"{path}: renamed from {source}, which is not a {stack.name} test file"
    if change.is_symlink:
        return f"{path}: symbolic links are not allowed"
    return None


def find_violations(stack: Stack, patch: str, max_files: int = DEFAULT_MAX_FILES) -> list[str]:
    try:
        changes = PatchSet(patch)
    except UnidiffParseError as error:
        return [f"the patch cannot be parsed: {error}"]
    if len(changes) > max_files:
        return [f"the patch changes {len(changes)} files, the limit is {max_files}"]
    return [violation for change in changes if (violation := _violation(stack, change))]


def touched_test_files(patch: str) -> list[str]:
    return [change.path for change in PatchSet(patch) if not change.is_removed_file]
