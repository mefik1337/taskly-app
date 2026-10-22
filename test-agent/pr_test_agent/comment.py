import html
import re
from pathlib import Path
from typing import Literal

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel

from .coverage import total_percent
from .models import AgentReport, AgentRun, Analysis, Verification
from .outcome import Status

FinalStatus = Status | Literal["committed", "verified_not_committed"]

MENTION = re.compile(r"@(?=[\w-])")
CELL_LIMIT = 300

HEADLINES = {
    "committed": "✅ Tests were generated, verified and committed in {commit}.",
    "verification_failed": "❌ The generated tests failed independent verification, so nothing was committed.",
    "rejected": "⛔ The agent's changes were rejected by the path guard and discarded.",
    "no_targets": "ℹ️ No changed {stack} code needs unit tests, so the agent was not started.",
    "not_measured": (
        "⚠️ Changed lines could not be measured: the {stack} suite produced no coverage report. "
        "Fix the build so the suite runs, then push again."
    ),
    "agent_failed": "⚠️ The agent did not finish with a valid report, so nothing was committed.",
    "no_changes": "ℹ️ The agent changed no files. Its decisions below give the reason for each one.",
    "verified_not_committed": (
        "☑️ Tests were generated and verified but not committed. "
        "Download the `test-agent-{stack}-patch` artifact and apply it with `git apply`."
    ),
}

ACTIONS = {"created_tests": "created tests", "updated_tests": "updated tests", "skipped": "skipped"}


class CommentContext(BaseModel):
    stack: str
    status: FinalStatus
    run_url: str
    commit_sha: str | None = None
    analysis: Analysis | None = None
    report: AgentReport | None = None
    verification: Verification | None = None
    run: AgentRun | None = None


def marker(stack: str) -> str:
    return f"<!-- taskly-test-agent:{stack} -->"


def _text(value: object, limit: int = CELL_LIMIT) -> str:
    collapsed = " ".join(str(value).split())
    if len(collapsed) > limit:
        collapsed = collapsed[: limit - 1] + "…"
    return MENTION.sub("@​", html.escape(collapsed, quote=False)).replace("|", "\\|")


def _code(value: object) -> str:
    return f"`{_text(value).replace('`', '')}`"


def _percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}%"


def _ranges(lines: list[int]) -> str:
    spans: list[list[int]] = []
    for line in sorted(lines):
        if spans and line == spans[-1][1] + 1:
            spans[-1][1] = line
        else:
            spans.append([line, line])
    return ", ".join(str(start) if start == end else f"{start}–{end}" for start, end in spans) or "—"


def _environment() -> Environment:
    environment = Environment(
        loader=FileSystemLoader(Path(__file__).parent / "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
        autoescape=False,
    )
    environment.filters.update(text=_text, code=_code, percent=_percent, ranges=_ranges)
    return environment


TEMPLATE = _environment().get_template("comment.md.j2")


def render_comment(context: CommentContext) -> str:
    analysis, verification = context.analysis, context.verification
    before = analysis.targets if analysis else []
    after = verification.coverage if verification and verification.coverage is not None else before
    rendered = TEMPLATE.render(
        marker=marker(context.stack),
        stack=context.stack,
        headline=HEADLINES[context.status].format(commit=(context.commit_sha or "")[:7], stack=context.stack),
        report=context.report,
        run=context.run,
        verification=verification,
        broken_before=analysis.suite.failed_cases if analysis else [],
        failing=[case for suite in verification.suites for case in suite.failed_cases] if verification else [],
        actions=ACTIONS,
        before={file.path: file.percent for file in before},
        coverage_after=after,
        total_before=total_percent(before),
        total_after=total_percent(after),
        run_url=context.run_url,
    )
    return re.sub(r"\n{3,}", "\n\n", rendered).strip() + "\n"
