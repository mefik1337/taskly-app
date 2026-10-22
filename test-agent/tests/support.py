import subprocess
from pathlib import Path

PASSING = '<testsuite><testcase classname="tests.test_router" name="test_list"/></testsuite>'
FAILING = (
    '<testsuite><testcase classname="tests.test_factory" name="test_routes">'
    '<failure message="route map changed"/></testcase></testsuite>'
)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


class FakeRunner:
    def __init__(self, repo: Path, hits: dict[int, int], junit: str = PASSING):
        self.repo, self.hits, self.junit = repo, hits, junit
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, stack, out_dir: Path, test_files):
        self.calls.append(tuple(test_files))
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "junit.xml").write_text(self.junit, encoding="utf-8")
        lines = "".join(f'<line number="{line}" hits="{count}"/>' for line, count in self.hits.items())
        report = self.repo / stack.coverage_report
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            f'<coverage><sources><source>{self.repo / "backend" / "app"}</source></sources><packages><package>'
            f'<classes><class name="router.py" filename="router.py"><lines>{lines}</lines></class></classes>'
            "</package></packages></coverage>",
            encoding="utf-8",
        )


def make_repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "backend" / "app").mkdir(parents=True)
    (repo / "backend" / "tests").mkdir()
    git(tmp_path, "init", "--quiet", str(repo))
    git(repo, "config", "user.email", "dev@example.com")
    git(repo, "config", "user.name", "Dev")
    (repo / "backend" / "app" / "router.py").write_text("a\nb\n", encoding="utf-8")
    (repo / "backend" / "tests" / "test_router.py").write_text("def test_list():\n    pass\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", "base")
    return repo


def open_pull_request(repo: Path) -> str:
    base = git(repo, "rev-parse", "HEAD")
    (repo / "backend" / "app" / "router.py").write_text("a\nb\nc\nd\n", encoding="utf-8")
    git(repo, "commit", "--quiet", "-am", "feature")
    return base




def agent_patch(repo: Path, path: str, content: str) -> str:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    git(repo, "add", "--intent-to-add", path)
    patch = git(repo, "diff", "--no-color") + "\n"
    git(repo, "reset", "--quiet", "--hard")
    git(repo, "clean", "--quiet", "-fd")
    return patch
