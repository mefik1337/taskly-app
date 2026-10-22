# Solution: unit test agent and per-stack PR workflow

A custom Claude Code agent (`test-engineer`) with four reusable skills writes and updates unit tests for Taskly's FastAPI backend and React frontend. A GitHub Actions workflow runs it on every pull request, **once per stack the pull request touches**. Deterministic Python tooling around the agent measures the change, limits what the agent may touch, re-runs everything it produced without secrets, and reports the result in a sticky comment per stack.

```
PR touches backend/**  ──► Test agent (backend)  ─┐
PR touches frontend/** ──► Test agent (frontend) ─┤  reusable test-agent.yml, input: stack
                                                   ▼
 analyze ───────────► generate ─────────────────► verify ─────────────────► publish
 (read only)          (read + AI credential)      (read, no secrets)        (write, no AI)
 suite + coverage     test-engineer + skills      guard the patch           status
 diff-cover on the    selfcheck the full suite    apply, full suite         commit to the PR branch
 changed lines        one repair pass if red      agent tests re-run x2     sticky comment per stack
                      patch + report              coverage after            re-dispatch ci-<stack>.yml
```

## Technical decisions

| Decision | Rationale |
| --- | --- |
| **One run per stack** (`test-agent-backend.yml`, `test-agent-frontend.yml` → reusable `test-agent.yml`; `ci-backend.yml`, `ci-frontend.yml`, `ci-test-agent.yml`) | A backend change never installs, runs or judges the frontend, and the reverse. Each stack has its own path filter, concurrency group, artifacts, sticky comment and CI. The agent's sandbox is also scoped to that stack. |
| **A `Stack` module with two adapters** (`test-agent/pr_test_agent/stacks.py`) | Test paths, runner, coverage report and skill live in one place per stack. The guard, the permission rules and the pipeline read them from there, so no list of paths is copied between YAML, bash, Python and JSON. |
| **Each stack's own tooling produces the evidence** | pytest + coverage.py and Vitest + V8 each write JUnit and Cobertura XML with their own configuration. [`diff-cover`](https://github.com/Bachmann1234/diff_cover) turns those reports into changed-line coverage, so the coverage exclusions exist only in `pyproject.toml` and `vite.config.ts`. [`junitparser`](https://github.com/weiwei/junitparser) reads results, [`unidiff`](https://github.com/matiasb/python-unidiff) parses the agent's patch, and [`pathspec`](https://github.com/cpburnz/python-pathspec) matches paths with the same gitignore semantics as Claude Code's permission rules. Nothing is parsed by hand. |
| **Pydantic models are the contract** (`models.py`) | Every artifact passed between jobs (`analysis.json`, `agent-report.json`, `verification.json`, …) is a validated model. The JSON schema given to `claude --json-schema` is generated from `AgentReport`, and the transcript is validated against the same model. Output that breaks the contract becomes `agent_failed` instead of a crash later on. |
| **Orchestration in a tested pipeline, not in YAML** (`pipeline.py`) | `analyze`, `selfcheck` and `verify` run the stack's runner, apply the patch, re-run the agent's tests and measure coverage. A runner seam (the real bash runner in CI, a fake in tests) lets the gates that decide whether a commit lands be tested end to end. The YAML only wires jobs together. |
| **The analysis tells the agent what the change already broke** | `analyze` runs the full suite before the agent starts. Failing cases arrive in `analysis.json`, and `change-analysis` classifies each as stale (update it) or regression (report it). |
| **Self-check and one repair pass** | After the agent stops, the workflow runs the full suite itself. If it is red, the same agent session is resumed once with the failing cases. |
| **Independent verification without secrets** | `verify` guards the patch, applies it to a clean checkout, runs the full suite and re-runs the agent's test files twice (a flakiness check). Only a fully green result is committed. |
| **Defence in depth on what the agent may change** | 1) Permission rules generated per stack (`dontAsk` mode: anything not allowed is denied; edits only to that stack's test files; Bash only for that stack's runner and read-only git). 2) The runners accept only test paths and unset every credential before running PR code. 3) A guard rejects patches that touch anything except that stack's tests, delete files, add symlinks, escape the repository, exceed 25 files or cannot be parsed. It runs in `verify` and again right before the commit. |
| **Least privilege and supply chain** | Only the `generate` job references the AI credential, and only in the two steps that start the agent. The credential is an environment secret of `test-agent`, which only that job enters. The callers pass `secrets: inherit` because a called workflow otherwise sees no secrets at all. Only `publish` can write, and it runs neither AI nor PR code. Tooling dependencies are installed from hash-pinned requirements into an isolated venv, and every action is pinned to a commit SHA. |
| **Credential containment and untrusted text** | Environment-dumping commands are denied, and the transcript and patch are redacted before upload. No PR text is interpolated into scripts or the prompt. Everything the agent writes into the comment is HTML-escaped, mention-neutralised, length-capped and table-safe (a Jinja2 template with one sanitising filter). |
| **Tests at behavioural seams** | The skills allow substitutes only at process and browser boundaries: SQLite for the database, an in-memory `fetch` fake for the network, the clock, and a `<dialog>` polyfill. Mocking in-house modules, asserting call order and testing framework behaviour are rejected patterns. |

## Running the PR workflow

**Prerequisites**

1. GitHub Actions enabled. This fork enforces SHA-pinned actions.
2. An environment named `test-agent` holding one secret: `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`, uses a Claude subscription) or `ANTHROPIC_API_KEY`.
3. Optional repository variables: `TEST_AGENT_MODEL` (default `claude-sonnet-5-5`), `TEST_AGENT_MAX_TURNS` (default `80`), `TEST_AGENT_MAX_BUDGET_USD` (default `5`), `TEST_AGENT_AUTO_COMMIT` (default `true`).

**Triggers.** A non-draft pull request from a branch of this repository. `backend/**` starts the backend run and `frontend/**` starts the frontend run; a pull request touching both gets two independent runs and two comments. Fork pull requests (which never receive secrets), pull requests labelled `skip-test-agent` and pushes by the bot are skipped. A new push cancels the in-flight run of the same stack.

**Results in the pull request.** One sticky comment per stack and the job summary show the outcome, the tests the change broke, every agent decision with its reason, the tests written, the verification table, changed-line coverage before and after, the skills the agent actually invoked, and run statistics including denied tool calls. Artifacts per stack: `-analysis`, `-output` (patch, report, redacted transcript), `-verification` and, when not committed, `-patch`. The check fails when the guard rejects the patch or verification is red.

**Locally**, the same commands drive a dry run or a coverage backfill:

```sh
python -m venv test-agent/.venv && test-agent/.venv/bin/pip install --require-hashes -r test-agent/requirements-dev.txt
test-agent/.venv/bin/python test-agent/main.py analyze --stack backend --all --workspace .test-agent/backend
test-agent/bin/run-agent --stack backend --mode run
test-agent/.venv/bin/python test-agent/main.py verify --stack backend --workspace .test-agent/backend
test-agent/.venv/bin/python test-agent/main.py claude-settings --stack backend   # print the agent sandbox
```

`--all` diffs the stack against the empty tree, so every line counts as changed. `--base <sha>` measures a pull request.

## Where things are defined

| Path | Role |
| --- | --- |
| `.claude/agents/test-engineer.md` | The agent: inputs (analysis file, one stack), boundaries, a five-step workflow with completion criteria, and the report contract. |
| `.claude/skills/change-analysis/` | One decision per target, a stale-or-regression verdict for every test the change broke, and the behaviours to pin. |
| `.claude/skills/pytest-unit-tests/` | Backend seams (TestClient on the real app over SQLite, real repository sessions), naming and rejected patterns. |
| `.claude/skills/vitest-unit-tests/` | Frontend seams (real components, hooks and design system over the `fetch` fake), queries, user events and rejected patterns. |
| `.claude/skills/test-verification/` | Run → triage (test defect, stale test, production defect, environment) → stability → coverage → full suite. |
| `test-agent/pr_test_agent/` | `stacks`, `settings`, `models`, `pipeline`, `coverage`, `suites`, `guard`, `transcript`, `outcome`, `comment` (+ `templates/comment.md.j2`), `cli`. |
| `test-agent/bin/` | `run-agent` (pinned flags, generated sandbox and schema, fixed prompt) and the two sandboxed test runners. |
| `.github/workflows/`, `.github/actions/` | The reusable agent workflow, its two per-stack callers, three CI workflows, and the stack and tooling setup actions. |

During a run the agent reads `analysis.json`, invokes `change-analysis`, then `pytest-unit-tests` or `vitest-unit-tests`, writes the tests, and finishes with `test-verification`. The skills listed in the comment come from the `Skill` calls in the transcript, not from the agent's own claims.

## Example runs

### 1. Rebuilding the existing tests with the agent

The first backfill followed the repository's original testing style: `Mock(spec=Session)`, a mocked repository, and mocked design system and hooks. An independent review rejected the frontend suite and accepted the backend suite only with changes, because the tests asserted wiring instead of behaviour. The root cause was the skills, which prescribed those mocks. After the skills were rewritten, the same `test-engineer` agent rebuilt both suites in two passes. A second review approved the backend and accepted the frontend with changes, and those changes were made.

| Stack | Tests | Coverage of the stack | What changed |
| --- | --- | --- | --- |
| Backend | 95 → 91 | 100% lines and branches | Route tests run the real app on SQLite and assert response bodies and the field each 422 names. Repository tests round-trip through real sessions. Mapper, validator and mock-based tests are deleted. |
| Frontend | 139 → 161 | 100% lines, 97.1% branches | Pages and components run against the `fetch` fake with the real design system. `design-system/mocks.tsx` is deleted. Request shapes are asserted only in the API tests. |

The rebuilt frontend tests found two production defects. They are reported here rather than written into the tests as expected behaviour:

- A fast double click on Save or Delete sends the request twice. `if (pending) return` reads `pending` from the last render.
- "Newest first" compares `created_at` as strings, so `2026-10-01T10:00:00-02:00` (12:00 UTC) sorts below `2026-10-01T11:00:00Z`.

### 2. Pull request demo

The "Clear completed" feature is split into one pull request per stack. PR #1, which mixed both stacks, was closed. In both new pull requests the author wrote the pure logic test-first and left the wiring untested on purpose, so the agent has real work to do.

**Backend: [PR #2](https://github.com/mefik1337/taskly-app/pull/2), [run 39771412141](https://github.com/mefik1337/taskly-app/actions/runs/39771412141).** Only `CI (backend)` and `Test agent (backend)` ran.

| Changed file | Agent decision | Reason given |
| --- | --- | --- |
| `backend/app/features/todos/repository.py` | skipped | The author's new tests already cover `delete_completed` and assert the count and the rows kept. |
| `backend/app/features/todos/router.py` | updated tests | The `clear_completed_todos` route body (line 24) was uncovered and had no route-level test. |
| `backend/app/features/todos/schemas.py` | updated tests | `ClearedTodos` is excluded from coverage, so its `{deleted: int}` body is pinned through the route tests. |

- **Skills invoked**, observed in the transcript: `change-analysis`, `pytest-unit-tests`, `test-verification`.
- **Tests written:** two route tests in `test_router.py`. One deletes two of three tasks and checks `{"deleted": 2}` plus the remaining list. The other runs with nothing completed and checks `{"deleted": 0}` with the list unchanged.
- **Independent verification:** full suite 95/95, and the agent's test file re-run twice (46/46 each time).
- **Changed-line coverage:** 88.9% → 100%. `router.py` went from 75% to 100%.
- **Commit:** the bot committed the tests to the branch (`test: add backend unit tests for #2`) and dispatched `CI (backend)`, which passed.
- **Run:** Sonnet, 17 turns, $0.13 API-equivalent. Two compound shell commands were denied by the sandbox and listed in the comment; the agent switched to `Read` and `Edit`.

**Frontend: [PR #3](https://github.com/mefik1337/taskly-app/pull/3).** Only `CI (frontend)` and `Test agent (frontend)` ran.

The first run ([39771416725](https://github.com/mefik1337/taskly-app/actions/runs/39771416725)) wrote nothing. The comment showed why: every `Edit` of a frontend test file was denied. The generated sandbox denied the stack's production root, `frontend/src`, and that root also holds the frontend tests; deny wins over allow. The safety net held: nothing was committed, coverage stayed at 50%, and the comment listed each denied call. The fix removed that rule, because `dontAsk` already refuses anything not allowed and the guard rejects it. A tooling test now checks that no deny rule shadows a test file the stack owns. The status for a run without changes was also reworded: "no new tests are needed" became "changed no files, see the decisions".

The second run ([39772076120](https://github.com/mefik1337/taskly-app/actions/runs/39772076120)) wrote the tests and passed verification, but `CI (frontend)` then failed its format check on the bot's commit. It exposed two more defects:

- The frontend runner formats the files it runs, so verification tested formatted files while `publish` committed the raw patch. Now `verify` saves the tested files as `verified.patch`, and `publish` guards and commits exactly that.
- A denied compound shell command convinced the agent that Bash was unavailable, so it never ran its own tests. The agent definition and `test-verification` now say that a refused compound command must be rewritten as one plain runner call.

The final run ([39772879802](https://github.com/mefik1337/taskly-app/actions/runs/39772879802)), on a branch reset to the author's commit, completed the whole flow:

| Changed file | Agent decision | Reason given |
| --- | --- | --- |
| `TodosPage.tsx` | updated tests | The clear flow, success notice, error alert and busy-disable were untested. The `if (busy) return` guard is unreachable because the button is disabled. |
| `api/todos.ts` | updated tests | The `clearCompleted` request (`DELETE /api/todos/completed`) and its result had no test. |
| `hooks/useClearCompletedMutation.ts` | created tests | A new hook with no test file. Cache pruning and the failure path needed pinning. |
| `components/TodosHeader.tsx` | updated tests | The Clear completed button has visibility, count and disabled branches that no test covered. |
| `test/fakeApi.ts` | updated tests | The shared fake was extended with `DELETE /api/todos/completed`. |
| `utils/todos.ts`, `api/queryKeys.ts`, `types.ts` | skipped | Already pinned by the author's tests, a constant key exercised through the hook, and a type-only addition. |

- **Skills invoked:** `change-analysis`, `vitest-unit-tests`, `test-verification`.
- **Tests written:** 12 cases in five files. The agent ran them through the runner and they passed twice in a row.
- **Independent verification:** full suite 177/177, and the agent's test files re-run twice (36/36 each time).
- **Changed-line coverage:** 50% → 100%. `api/todos.ts` went from 0% to 100%, and `useClearCompletedMutation.ts` from 33% to 100%.
- **Commit:** the bot committed `test: add frontend unit tests for #3` and dispatched `CI (frontend)`. The format check, type-check and tests all passed.
- **Run:** Sonnet, 27 turns, $0.26 API-equivalent, one denied compound command, which the agent rewrote.

## Assumptions

- Pull request authors are repository collaborators. Fork pull requests are skipped, because running an agent with credentials on untrusted code is out of scope.
- A "unit test" may use an in-memory SQLite database or an in-memory `fetch` fake. These are the fastest substitutes that keep Taskly's own code real.
- Files excluded from coverage in the project configuration (schemas, models, types, barrels, the design system) need no dedicated tests. Rules declared in them are pinned through the seam that uses them.
- Committing verified tests to the pull request branch is acceptable. `TEST_AGENT_AUTO_COMMIT=false` switches to attaching the patch instead.

## Limitations

- The agent runs PR test code while its credential is in the parent process. The runners scrub credentials and fork pull requests are excluded, but the runner has no network egress control.
- V8 coverage is coarse for JSX, so frontend changed-line percentages are an indicator, not proof.
- Correctness is checked by execution, re-runs and review. No mutation testing proves that each assertion catches a regression.
- Model output varies. Borderline decisions (for example, whether a trivial helper needs a test) can differ between runs.
- The bot's commit gets CI through `workflow_dispatch`. The `pull_request` runs GitHub creates for that push wait for approval (`action_required`). Branch protection that requires `pull_request`-event checks would need adjusting.
- When both stacks commit to the same branch, the second push rebases only if the first touched no file of its stack. Otherwise the patch is attached instead.

## What I would change for production

- A GitHub App token with fine-grained permissions instead of `GITHUB_TOKEN`, and an egress firewall (for example `harden-runner` in block mode) on `generate`.
- Mutation testing (`mutmut`, `Stryker`) in `verify`, rejecting tests that kill no mutants.
- An evaluation set of pull requests with known good tests, run in CI before any change to prompts, skills, model or Claude Code version.
- A "suggest" mode that posts tests as a stacked pull request for teams that do not want bot commits on feature branches.
- A dashboard of cost, turns, outcome distribution and denied tool calls per run.
