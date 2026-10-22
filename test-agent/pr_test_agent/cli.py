import argparse
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path

from .comment import CommentContext, render_comment
from .guard import find_violations
from .models import AgentReport, AgentRun, Analysis, Verification
from .outcome import resolve_status
from .pipeline import Runner, analyze, script_runner, selfcheck, verify
from .redact import redact
from .settings import claude_settings
from .stacks import STACKS, get_stack
from .transcript import summarize_transcript
from .workspace import Workspace

RunnerFactory = Callable[[Path], Runner]


def _analyze(args, repo: Path, runner_factory: RunnerFactory) -> int:
    analysis = analyze(repo, get_stack(args.stack), Workspace(args.workspace), args.base, runner_factory(repo))
    print(json.dumps({"targets": [file.path for file in analysis.targets], "suite_green": analysis.suite.green}))
    return 0


def _selfcheck(args, repo: Path, runner_factory: RunnerFactory) -> int:
    suite = selfcheck(repo, get_stack(args.stack), Workspace(args.workspace), runner_factory(repo))
    return 0 if suite.green else 1


def _verify(args, repo: Path, runner_factory: RunnerFactory) -> int:
    verify(repo, get_stack(args.stack), Workspace(args.workspace), runner_factory(repo))
    return 0


def _guard(args, *_) -> int:
    workspace = Workspace(args.workspace)
    violations = find_violations(get_stack(args.stack), workspace.text(Path(args.patch) if args.patch else workspace.patch_path))
    for violation in violations:
        print(violation, file=sys.stderr)
    return 1 if violations else 0


def _status(args, *_) -> int:
    workspace = Workspace(args.workspace)
    analysis = workspace.read(Analysis)
    if analysis is None:
        print("not_measured")
        return 0
    print(resolve_status(analysis, workspace.read(AgentReport), workspace.read(Verification)))
    return 0


def _comment(args, *_) -> int:
    workspace = Workspace(args.workspace)
    comment = render_comment(CommentContext(
        stack=args.stack,
        status=args.status,
        run_url=args.run_url,
        commit_sha=args.commit_sha or None,
        analysis=workspace.read(Analysis),
        report=workspace.read(AgentReport),
        verification=workspace.read(Verification),
        run=workspace.read(AgentRun),
    ))
    Path(args.out).write_text(comment, encoding="utf-8")
    return 0


def _transcript(args, *_) -> int:
    workspace = Workspace(args.workspace)
    summary = summarize_transcript(workspace.text(workspace.transcript_path).splitlines())
    (workspace.root / "agent-report.json").unlink(missing_ok=True)
    if summary.report is not None:
        workspace.write(summary.report)
    workspace.write(summary.run)
    if summary.session_id:
        workspace.session_path.write_text(summary.session_id, encoding="utf-8")
    return 0


def _redact(args, *_) -> int:
    path = Path(args.file)
    if path.is_file():
        secrets = [os.environ.get(name) for name in args.env]
        path.write_text(redact(path.read_text(encoding="utf-8"), secrets), encoding="utf-8")
    return 0


def _schema(*_) -> int:
    print(json.dumps(AgentReport.model_json_schema()))
    return 0


def _settings(args, *_) -> int:
    print(json.dumps(claude_settings(get_stack(args.stack)), indent=2))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pr_test_agent")
    commands = parser.add_subparsers(dest="command", required=True)

    def command(name: str, handler, *, stack: bool = False, workspace: bool = False) -> argparse.ArgumentParser:
        sub = commands.add_parser(name)
        sub.set_defaults(handler=handler)
        if stack:
            sub.add_argument("--stack", required=True, choices=sorted(STACKS))
        if workspace:
            sub.add_argument("--workspace", required=True)
        return sub

    analysis = command("analyze", _analyze, stack=True, workspace=True)
    source = analysis.add_mutually_exclusive_group(required=True)
    source.add_argument("--base")
    source.add_argument("--all", dest="base", action="store_const", const=None)
    command("selfcheck", _selfcheck, stack=True, workspace=True)
    command("verify", _verify, stack=True, workspace=True)
    command("guard", _guard, stack=True, workspace=True).add_argument("--patch")
    command("status", _status, workspace=True)
    comment = command("comment", _comment, stack=True, workspace=True)
    comment.add_argument("--status", required=True)
    comment.add_argument("--run-url", required=True)
    comment.add_argument("--commit-sha")
    comment.add_argument("--out", required=True)
    command("transcript", _transcript, workspace=True)
    redaction = command("redact", _redact)
    redaction.add_argument("--file", required=True)
    redaction.add_argument("--env", action="append", required=True)
    command("schema", _schema)
    command("claude-settings", _settings, stack=True)
    return parser


def main(argv: list[str] | None = None, repo: Path | None = None, runner_factory: RunnerFactory | None = None) -> int:
    args = _parser().parse_args(argv)
    return args.handler(args, repo or Path.cwd(), runner_factory or script_runner)
