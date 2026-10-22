from pathlib import Path
from typing import TypeVar

from .models import AgentReport, AgentRun, Analysis, Model, SuiteResult, Verification

M = TypeVar("M", bound=Model)

FILES: dict[type[Model], str] = {
    Analysis: "analysis.json",
    AgentReport: "agent-report.json",
    AgentRun: "agent-run.json",
    SuiteResult: "selfcheck.json",
    Verification: "verification.json",
}


class Workspace:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.diff_path = self.root / "pr.diff"
        self.patch_path = self.root / "agent.patch"
        self.verified_patch_path = self.root / "verified.patch"
        self.transcript_path = self.root / "transcript.jsonl"
        self.session_path = self.root / "session.txt"
        self.selfcheck_path = self.root / FILES[SuiteResult]

    def run_dir(self, name: str) -> Path:
        return self.root / name

    def write(self, model: Model) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / FILES[type(model)]).write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")

    def read(self, kind: type[M]) -> M | None:
        path = self.root / FILES[kind]
        return kind.model_validate_json(path.read_text(encoding="utf-8")) if path.is_file() else None

    def text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.is_file() else ""
