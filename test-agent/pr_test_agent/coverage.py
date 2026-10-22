import json
import subprocess
import sys
import tempfile
from pathlib import Path

from unidiff import PatchSet

from .models import FileCoverage, percent_of


def _diff_cover(diff: str, report: Path, repo: Path) -> dict:
    with tempfile.TemporaryDirectory() as workdir:
        diff_file = Path(workdir, "changes.diff")
        diff_file.write_text(diff, encoding="utf-8")
        output = Path(workdir, "diff-cover.json")
        subprocess.run(
            [
                sys.executable, "-m", "diff_cover.diff_cover_tool", str(report.resolve()),
                "--diff-file", str(diff_file), "--format", f"json:{output}", "--quiet",
            ],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        return json.loads(output.read_text(encoding="utf-8"))["src_stats"]


def changed_line_coverage(diff: str, report: Path, repo: Path) -> list[FileCoverage] | None:
    if not report.is_file():
        return None
    if not diff.strip():
        return []
    paths = {change.path.casefold(): change.path for change in PatchSet(diff)}
    files = []
    for reported_path, stats in sorted(_diff_cover(diff, report, repo).items()):
        normalized = reported_path.replace("\\", "/")
        files.append(
            FileCoverage(
                path=paths.get(normalized.casefold(), normalized),
                covered_lines=sorted(stats["covered_lines"]),
                uncovered_lines=sorted(stats["violation_lines"]),
            )
        )
    return [file for file in files if file.covered_lines or file.uncovered_lines]


def total_percent(files: list[FileCoverage]) -> float | None:
    covered = sum(len(file.covered_lines) for file in files)
    relevant = covered + sum(len(file.uncovered_lines) for file in files)
    return percent_of(covered, relevant)
