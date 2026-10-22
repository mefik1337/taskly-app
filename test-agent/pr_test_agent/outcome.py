from typing import Literal

from .models import AgentReport, Analysis, Verification

Status = Literal[
    "not_measured", "no_targets", "agent_failed", "rejected", "verification_failed", "no_changes", "verified"
]


def resolve_status(analysis: Analysis, report: AgentReport | None, verification: Verification | None) -> Status:
    if not analysis.coverage_measured:
        return "not_measured"
    if not analysis.targets:
        return "no_targets"
    if report is None:
        return "agent_failed"
    if verification is not None and verification.violations:
        return "rejected"
    if verification is None or not verification.suites or not all(suite.green for suite in verification.suites):
        return "verification_failed"
    if not verification.patch_files:
        return "no_changes"
    return "verified"
