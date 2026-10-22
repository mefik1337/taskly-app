from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import PurePosixPath

BACKEND_EXCLUDED_NAMES = {"__init__.py", "main.py", "schemas.py", "models.py", "types.py", "constants.py"}

FRONTEND_EXCLUDED_PATTERNS = (
    "frontend/src/main.tsx",
    "frontend/src/design-system/*",
    "*/types.ts",
    "*.types.ts",
    "*/index.ts",
    "*/constants.ts",
    "*/constants.tsx",
    "*.constants.ts",
    "frontend/src/features/todos/api/queryKeys.ts",
    "frontend/src/lib/queryClient.ts",
)

FRONTEND_CODE_SUFFIXES = {".ts", ".tsx"}


@dataclass(frozen=True)
class FileClass:
    area: str
    kind: str
    coverage_excluded: bool
    test_path: str | None


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatchcase(path, pattern) for pattern in patterns)


def _area(posix: PurePosixPath) -> str:
    top = posix.parts[0] if posix.parts else ""
    return top if top in {"backend", "frontend"} else "other"


def _other(posix: PurePosixPath) -> FileClass:
    return FileClass(area=_area(posix), kind="other", coverage_excluded=False, test_path=None)


def _classify_frontend(posix: PurePosixPath) -> FileClass:
    if posix.suffix not in FRONTEND_CODE_SUFFIXES:
        return _other(posix)
    if posix.is_relative_to("frontend/src/test") or posix.stem.endswith(".test"):
        return FileClass(area="frontend", kind="test", coverage_excluded=False, test_path=None)
    return FileClass(
        area="frontend",
        kind="source",
        coverage_excluded=_matches_any(str(posix), FRONTEND_EXCLUDED_PATTERNS),
        test_path=str(posix.with_name(f"{posix.stem}.test{posix.suffix}")),
    )


def _classify_backend(posix: PurePosixPath) -> FileClass:
    if posix.suffix != ".py":
        return _other(posix)
    if posix.is_relative_to("backend/tests"):
        return FileClass(area="backend", kind="test", coverage_excluded=False, test_path=None)
    relative = posix.relative_to("backend/app")
    return FileClass(
        area="backend",
        kind="source",
        coverage_excluded=posix.name in BACKEND_EXCLUDED_NAMES,
        test_path=str(PurePosixPath("backend/tests", relative.parent, f"test_{relative.name}")),
    )


def classify_path(path: str) -> FileClass:
    posix = PurePosixPath(path)
    if posix.is_relative_to("frontend/src"):
        return _classify_frontend(posix)
    if posix.is_relative_to("backend/app") or posix.is_relative_to("backend/tests"):
        return _classify_backend(posix)
    return _other(posix)
