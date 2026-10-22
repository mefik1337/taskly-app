import json

from pr_test_agent.cli import main

SOURCE_DIFF = """\
diff --git a/backend/app/core/config.py b/backend/app/core/config.py
index 1111111..2222222 100644
--- a/backend/app/core/config.py
+++ b/backend/app/core/config.py
@@ -9,0 +10,2 @@ def resolve_database_url(database_url: str | None = None) -> str:
+    if not explicit_url:
+        raise RuntimeError("missing")
"""

AGENT_PATCH = """\
diff --git a/backend/app/core/config.py b/backend/app/core/config.py
index 1111111..2222222 100644
--- a/backend/app/core/config.py
+++ b/backend/app/core/config.py
@@ -1 +1 @@
-import os
+import os, sys
"""


def _write(path, content):
    path.write_text(content, encoding="utf-8")
    return str(path)


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_manifest_command_writes_targets_for_the_diff(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "backend/tests/core").mkdir(parents=True)
    (tmp_path / "backend/tests/core/test_config.py").write_text("", encoding="utf-8")
    diff = _write(tmp_path / "pr.diff", SOURCE_DIFF)
    assert main(["manifest", "--diff", diff, "--out", "manifest.json"]) == 0
    manifest = _read_json(tmp_path / "manifest.json")
    assert manifest["targets"] == ["backend/app/core/config.py"]
    assert manifest["files"][0]["test_exists"] is True
    assert manifest["files"][0]["changed_lines"] == [10, 11]


def test_guard_command_fails_and_records_violations_for_source_edits(tmp_path):
    patch = _write(tmp_path / "agent.patch", AGENT_PATCH)
    out = tmp_path / "violations.json"
    assert main(["guard", "--diff", patch, "--out", str(out)]) == 1
    assert _read_json(out) == ["backend/app/core/config.py: only test files may be changed"]


def test_diff_coverage_command_merges_reports_of_both_stacks(tmp_path):
    manifest = {"targets": [], "files": [
        {"path": "backend/app/core/config.py", "changed_lines": [10, 11], "target": True},
        {"path": "frontend/src/lib/http.ts", "changed_lines": [3], "target": True},
    ]}
    manifest_path = _write(tmp_path / "manifest.json", json.dumps(manifest))
    backend_lcov = _write(tmp_path / "backend.lcov", "SF:app/core/config.py\nDA:10,1\nDA:11,0\nend_of_record\n")
    frontend_lcov = _write(tmp_path / "frontend.lcov", "SF:src\lib\http.ts\nDA:3,2\nend_of_record\n")
    out = tmp_path / "coverage.json"
    assert main([
        "diff-coverage", "--manifest", manifest_path, "--out", str(out),
        "--lcov", f"backend={backend_lcov}", "--lcov", f"frontend={frontend_lcov}",
        "--lcov", f"frontend={tmp_path / 'missing.lcov'}",
    ]) == 0
    assert _read_json(out)["total"] == {"relevant": 3, "covered": 2, "percent": 66.7}


def test_status_and_render_commands_produce_the_pull_request_comment(tmp_path, capsys):
    manifest = _write(tmp_path / "manifest.json", json.dumps({"targets": ["backend/app/core/config.py"], "files": []}))
    junit = _write(tmp_path / "backend.xml", '<testsuite><testcase classname="t" name="a"/></testsuite>')
    suites = tmp_path / "suites.json"
    assert main(["junit", "--report", f"backend={junit}", "--out", str(suites)]) == 0
    agent = _write(tmp_path / "agent.json", json.dumps({
        "summary": "Covered the new guard clause.", "decisions": [], "skills_used": ["change-analysis"],
        "test_files": [], "suspected_bugs": [],
    }))
    status_args = ["--manifest", manifest, "--agent-report", agent, "--suites", str(suites)]
    assert main(["status", *status_args, "--patch", str(tmp_path / "empty.patch")]) == 0
    assert capsys.readouterr().out.strip() == "no_changes"
    comment = tmp_path / "comment.md"
    assert main([
        "render", "--status", "no_changes", *status_args, "--run-url", "https://example.test/run",
        "--out", str(comment),
    ]) == 0
    text = comment.read_text(encoding="utf-8")
    assert "decided that no new tests are needed" in text
    assert "| backend | 1 | 1 | 0 | 0 |" in text


def test_manifest_all_mode_targets_every_source_line_for_a_coverage_backfill(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    files = {
        "backend/app/core/config.py": "import os\n\nVALUE = 1\n",
        "backend/app/main.py": "app = None\n",
        "backend/app/__pycache__/config.cpython-312.pyc": "binary",
        "frontend/src/lib/http.ts": "export const a = 1\nexport const b = 2\n",
        "frontend/src/lib/http.test.ts": "it('works', () => {})\n",
        "frontend/src/styles.css": "body {}\n",
    }
    for path, content in files.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(content, encoding="utf-8")
    assert main(["manifest", "--all", "--out", "manifest.json"]) == 0
    manifest = _read_json(tmp_path / "manifest.json")
    assert manifest["targets"] == ["backend/app/core/config.py", "frontend/src/lib/http.ts"]
    by_path = {entry["path"]: entry for entry in manifest["files"]}
    assert set(by_path) == {"backend/app/core/config.py", "backend/app/main.py", "frontend/src/lib/http.ts"}
    assert by_path["backend/app/core/config.py"]["changed_lines"] == [1, 2, 3]
    assert by_path["frontend/src/lib/http.ts"]["test_exists"] is True


def test_manifest_area_filter_keeps_only_files_of_that_stack(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for path in ("backend/app/core/config.py", "frontend/src/lib/http.ts"):
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text("x = 1\n", encoding="utf-8")
    assert main(["manifest", "--all", "--area", "frontend", "--out", "manifest.json"]) == 0
    manifest = _read_json(tmp_path / "manifest.json")
    assert manifest["targets"] == ["frontend/src/lib/http.ts"]
    assert manifest["areas"] == ["frontend"]


def test_transcript_command_writes_report_only_when_the_agent_produced_one(tmp_path):
    finished = _write(tmp_path / "ok.jsonl", "\n".join([
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "change-analysis"}}]}}),
        json.dumps({"type": "result", "subtype": "success", "num_turns": 3, "total_cost_usd": 0.1,
                    "structured_output": {"summary": "Nothing to add.", "skills_used": []}}),
    ]))
    crashed = _write(tmp_path / "crashed.jsonl", json.dumps({"type": "result", "subtype": "error_max_turns"}))
    assert main(["transcript", "--in", finished, "--report-out", str(tmp_path / "report.json"),
                 "--run-out", str(tmp_path / "run.json")]) == 0
    assert _read_json(tmp_path / "report.json") == {"summary": "Nothing to add.", "skills_used": ["change-analysis"]}
    assert _read_json(tmp_path / "run.json")["turns"] == 3
    assert main(["transcript", "--in", crashed, "--report-out", str(tmp_path / "missing.json"),
                 "--run-out", str(tmp_path / "crashed-run.json")]) == 0
    assert not (tmp_path / "missing.json").exists()
    assert _read_json(tmp_path / "crashed-run.json")["outcome"] == "error_max_turns"


def test_junit_command_records_a_missing_report_as_a_failed_suite(tmp_path):
    out = tmp_path / "suites.json"
    assert main(["junit", "--report", f"frontend={tmp_path / 'never-written.xml'}", "--out", str(out)]) == 0
    assert _read_json(out) == {"frontend": {
        "tests": 0, "passed": 0, "failures": 0, "errors": 1, "skipped": 0,
        "failed_cases": [{"name": "frontend", "message": "No test report was produced; the runner failed before running tests."}],
    }}


def test_redact_command_scrubs_secrets_named_by_environment_variable(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oauth-token-value-123")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    transcript = _write(tmp_path / "transcript.jsonl", '{"leak": "oauth-token-value-123"}\n')
    assert main(["redact", "--file", transcript, "--env", "CLAUDE_CODE_OAUTH_TOKEN", "--env", "ANTHROPIC_API_KEY"]) == 0
    assert (tmp_path / "transcript.jsonl").read_text(encoding="utf-8") == '{"leak": "[REDACTED]"}\n'
