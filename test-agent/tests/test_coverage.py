from pr_test_agent.coverage import LineCoverage, diff_coverage, parse_lcov

LCOV = r"""TN:
SF:app\api\dependencies.py
DA:1,1
DA:11,0
DA:12,3
end_of_record
SF:app/core/config.py
DA:5,0
end_of_record
"""


def test_lcov_records_are_keyed_by_repository_path_with_hit_and_missed_lines():
    coverage = parse_lcov(LCOV, prefix="backend")
    assert coverage == {
        "backend/app/api/dependencies.py": LineCoverage(executable={1, 11, 12}, covered={1, 12}),
        "backend/app/core/config.py": LineCoverage(executable={5}, covered=set()),
    }


def _manifest(*files):
    return {"targets": [path for path, _ in files], "files": [
        {"path": path, "changed_lines": lines, "target": True} for path, lines in files
    ]}


def test_diff_coverage_counts_only_changed_executable_lines_of_targets():
    manifest = _manifest(("backend/app/core/config.py", [4, 5, 6, 7]))
    coverage = {"backend/app/core/config.py": LineCoverage(executable={1, 5, 6, 7}, covered={1, 5})}
    result = diff_coverage(manifest, coverage)
    assert result["files"] == [{
        "path": "backend/app/core/config.py",
        "covered_lines": [5],
        "uncovered_lines": [6, 7],
        "percent": 33.3,
    }]
    assert result["total"] == {"relevant": 3, "covered": 1, "percent": 33.3}


def test_target_missing_from_the_report_counts_every_changed_line_as_uncovered():
    manifest = _manifest(("frontend/src/lib/new.ts", [1, 2]), ("frontend/src/lib/http.ts", [8]))
    coverage = {"frontend/src/lib/http.ts": LineCoverage(executable={8}, covered={8})}
    result = diff_coverage(manifest, coverage)
    assert result["files"][0] == {
        "path": "frontend/src/lib/new.ts",
        "covered_lines": [],
        "uncovered_lines": [1, 2],
        "percent": 0.0,
    }
    assert result["total"] == {"relevant": 3, "covered": 1, "percent": 33.3}


def test_changes_without_executable_lines_have_no_percentage():
    manifest = _manifest(("backend/app/factory.py", [2]))
    coverage = {"backend/app/factory.py": LineCoverage(executable={9}, covered={9})}
    result = diff_coverage(manifest, coverage)
    assert result["files"][0]["percent"] is None
    assert result["total"] == {"relevant": 0, "covered": 0, "percent": None}
