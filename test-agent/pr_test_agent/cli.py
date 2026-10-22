import argparse
import json
import os
import sys
from pathlib import Path

from .coverage import LineCoverage, diff_coverage, parse_lcov
from .diff import parse_unified_diff
from .guard import find_violations
from .junit import summarize_junit
from .manifest import build_manifest, snapshot_changes
from .outcome import resolve_status
from .report import render_comment


def _read_text(path: str | None) -> str | None:
    if not path or not Path(path).is_file():
        return None
    return Path(path).read_text(encoding="utf-8")


def _read_json(path: str | None, default=None):
    text = _read_text(path)
    return json.loads(text) if text and text.strip() else default


def _write_json(path: str, data) -> None:
    Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _pairs(values: list[str] | None) -> list[tuple[str, str]]:
    return [tuple(value.split("=", 1)) for value in values or []]


def _manifest(args) -> int:
    if args.all:
        changes = snapshot_changes(Path.cwd())
    else:
        changes = parse_unified_diff(_read_text(args.diff) or "")
    _write_json(args.out, build_manifest(changes, exists=os.path.isfile))
    return 0


def _guard(args) -> int:
    violations = find_violations(parse_unified_diff(_read_text(args.diff) or ""))
    _write_json(args.out, violations)
    for violation in violations:
        print(violation, file=sys.stderr)
    return 1 if violations else 0


def _diff_coverage(args) -> int:
    coverage: dict[str, LineCoverage] = {}
    for area, path in _pairs(args.lcov):
        text = _read_text(path)
        if text is not None:
            coverage.update(parse_lcov(text, prefix=area))
    _write_json(args.out, diff_coverage(_read_json(args.manifest), coverage))
    return 0


def _junit(args) -> int:
    suites = {}
    for suite, path in _pairs(args.report):
        text = _read_text(path)
        if text is not None:
            suites[suite] = summarize_junit(text)
    _write_json(args.out, suites)
    return 0


def _status(args) -> int:
    print(resolve_status(
        has_targets=bool(_read_json(args.manifest, {}).get("targets")),
        agent_report=_read_json(args.agent_report),
        violations=_read_json(args.violations, []),
        suites=_read_json(args.suites, {}),
        patch_changed=bool((_read_text(args.patch) or "").strip()),
    ))
    return 0


def _render(args) -> int:
    before = _read_json(args.coverage_before)
    after = _read_json(args.coverage_after)
    suites = _read_json(args.suites)
    violations = _read_json(args.violations, [])
    comment = render_comment({
        "status": args.status,
        "agent": _read_json(args.agent_report),
        "verification": {"violations": violations, "suites": suites or {}} if suites is not None or violations else None,
        "coverage": {"before": before, "after": after or before} if before else None,
        "run_url": args.run_url,
        "commit_sha": args.commit_sha,
    })
    Path(args.out).write_text(comment, encoding="utf-8")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pr_test_agent")
    commands = parser.add_subparsers(dest="command", required=True)

    manifest = commands.add_parser("manifest")
    source = manifest.add_mutually_exclusive_group(required=True)
    source.add_argument("--diff")
    source.add_argument("--all", action="store_true")
    manifest.add_argument("--out", required=True)
    manifest.set_defaults(handler=_manifest)

    guard = commands.add_parser("guard")
    guard.add_argument("--diff", required=True)
    guard.add_argument("--out", required=True)
    guard.set_defaults(handler=_guard)

    coverage = commands.add_parser("diff-coverage")
    coverage.add_argument("--manifest", required=True)
    coverage.add_argument("--lcov", action="append")
    coverage.add_argument("--out", required=True)
    coverage.set_defaults(handler=_diff_coverage)

    junit = commands.add_parser("junit")
    junit.add_argument("--report", action="append")
    junit.add_argument("--out", required=True)
    junit.set_defaults(handler=_junit)

    for name, handler in (("status", _status), ("render", _render)):
        command = commands.add_parser(name)
        command.add_argument("--manifest")
        command.add_argument("--agent-report")
        command.add_argument("--violations")
        command.add_argument("--suites")
        command.add_argument("--patch")
        command.set_defaults(handler=handler)
        if name == "render":
            command.add_argument("--status", required=True)
            command.add_argument("--coverage-before")
            command.add_argument("--coverage-after")
            command.add_argument("--commit-sha")
            command.add_argument("--run-url", required=True)
            command.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return args.handler(args)
