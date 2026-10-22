from dataclasses import dataclass, field
from pathlib import PurePosixPath


@dataclass
class LineCoverage:
    executable: set[int] = field(default_factory=set)
    covered: set[int] = field(default_factory=set)


def parse_lcov(text: str, prefix: str) -> dict[str, LineCoverage]:
    coverage: dict[str, LineCoverage] = {}
    current: LineCoverage | None = None
    for line in text.splitlines():
        if line.startswith("SF:"):
            path = str(PurePosixPath(prefix, line[3:].replace("\\", "/")))
            current = coverage.setdefault(path, LineCoverage())
        elif line.startswith("DA:") and current is not None:
            number, hits = line[3:].split(",")[:2]
            current.executable.add(int(number))
            if int(hits) > 0:
                current.covered.add(int(number))
        elif line == "end_of_record":
            current = None
    return coverage


def _percent(covered: int, relevant: int) -> float | None:
    return round(100 * covered / relevant, 1) if relevant else None


def _file_diff_coverage(path: str, changed_lines: list[int], coverage: dict[str, LineCoverage]) -> dict:
    report = coverage.get(path)
    changed = set(changed_lines)
    relevant = changed & report.executable if report else changed
    covered = relevant & report.covered if report else set()
    return {
        "path": path,
        "covered_lines": sorted(covered),
        "uncovered_lines": sorted(relevant - covered),
        "percent": _percent(len(covered), len(relevant)),
    }


def diff_coverage(manifest: dict, coverage: dict[str, LineCoverage]) -> dict:
    files = [
        _file_diff_coverage(entry["path"], entry["changed_lines"], coverage)
        for entry in manifest["files"]
        if entry["target"]
    ]
    covered = sum(len(item["covered_lines"]) for item in files)
    relevant = covered + sum(len(item["uncovered_lines"]) for item in files)
    return {
        "files": files,
        "total": {"relevant": relevant, "covered": covered, "percent": _percent(covered, relevant)},
    }
