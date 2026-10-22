import subprocess
from pathlib import Path

from pr_test_agent.coverage import changed_line_coverage, total_percent
from pr_test_agent.models import FileCoverage


def cobertura(source: Path, filename: str, hits: dict[int, int]) -> str:
    lines = "".join(f'<line number="{number}" hits="{count}"/>' for number, count in hits.items())
    return (
        '<?xml version="1.0" ?><coverage version="7"><sources>'
        f"<source>{source}</source></sources><packages><package name=\"app\"><classes>"
        f'<class name="{filename}" filename="{filename}"><methods/><lines>{lines}</lines></class>'
        "</classes></package></packages></coverage>"
    )


def added_lines_diff(path: str, numbers: list[int], total: int) -> str:
    body = "".join(f"+line {number}\n" if number in numbers else f" line {number}\n" for number in range(1, total + 1))
    old = total - len(numbers)
    return (
        f"diff --git a/{path} b/{path}\nindex 1111111..2222222 100644\n--- a/{path}\n+++ b/{path}\n"
        f"@@ -1,{old} +1,{total} @@\n{body}"
    )


def repository(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    return tmp_path


def test_changed_executable_lines_are_split_into_covered_and_uncovered(tmp_path):
    repo = repository(tmp_path)
    report = tmp_path / "coverage.xml"
    report.write_text(cobertura(repo / "backend" / "app", "router.py", {1: 1, 2: 3, 3: 0, 4: 0}), encoding="utf-8")
    diff = added_lines_diff("backend/app/router.py", [2, 3, 5], total=5)
    assert changed_line_coverage(diff, report, repo) == [
        FileCoverage(path="backend/app/router.py", covered_lines=[2], uncovered_lines=[3])
    ]


def test_files_the_stack_excludes_from_coverage_are_not_targets(tmp_path):
    repo = repository(tmp_path)
    report = tmp_path / "coverage.xml"
    report.write_text(cobertura(repo / "backend" / "app", "router.py", {1: 1}), encoding="utf-8")
    diff = added_lines_diff("backend/app/schemas.py", [1], total=1)
    assert changed_line_coverage(diff, report, repo) == []


def test_paths_keep_the_case_they_have_in_the_diff(tmp_path):
    repo = repository(tmp_path)
    report = tmp_path / "coverage.xml"
    report.write_text(cobertura(repo / "frontend", "src/useClearCompleted.ts", {1: 0}), encoding="utf-8")
    diff = added_lines_diff("frontend/src/useClearCompleted.ts", [1], total=1)
    [file] = changed_line_coverage(diff, report, repo)
    assert file.path == "frontend/src/useClearCompleted.ts"


def test_without_a_coverage_report_nothing_can_be_measured(tmp_path):
    repo = repository(tmp_path)
    assert changed_line_coverage(added_lines_diff("backend/app/x.py", [1], 1), tmp_path / "none.xml", repo) is None


def test_an_empty_diff_has_nothing_to_measure(tmp_path):
    repo = repository(tmp_path)
    report = tmp_path / "coverage.xml"
    report.write_text(cobertura(repo / "backend" / "app", "router.py", {1: 1}), encoding="utf-8")
    assert changed_line_coverage("", report, repo) == []


def test_the_total_is_the_share_of_covered_changed_lines_across_files():
    files = [
        FileCoverage(path="a.py", covered_lines=[1, 2, 3], uncovered_lines=[4]),
        FileCoverage(path="b.py", covered_lines=[], uncovered_lines=[1, 2, 3, 4]),
    ]
    assert total_percent(files) == 37.5
    assert files[0].percent == 75.0
    assert total_percent([]) is None
