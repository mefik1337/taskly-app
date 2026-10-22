---
name: test-verification
description: Run Taskly unit tests through the sanctioned runners, triage failures, check stability and changed-line coverage. Use after writing or editing tests, and whenever a test run fails.
---

# Test verification

A test is finished when it is **green twice in a row**, covers the lines it was written for, and leaves the rest of the suite green.

## Runners

| Stack | Command | What it does |
| --- | --- | --- |
| Backend | `test-agent/bin/run-backend-tests <test files…>` | pytest with branch coverage of `backend/app`; prints uncovered lines per module |
| Frontend | `test-agent/bin/run-frontend-tests <test files…>` | Prettier on the given files, `tsc --noEmit` for the whole project, then Vitest with coverage |

Paths are repository-relative (`backend/tests/core/test_config.py`, `frontend/src/lib/http.test.ts`). With no arguments a runner executes the whole suite of its stack.

## Loop

1. Run the runner with the test files you touched.
2. On failure, read the assertion message and the code under test, then classify:
   - **Test defect**: wrong query, wrong fixture, wrong expectation from misreading the code, missing `await`. Fix the test.
   - **Stale test**: an existing test pins behaviour the change replaced on purpose (a route map without the new route, a component rendered without a newly required provider or mock). Update it to the new behaviour and list that file and case in the report.
   - **Production defect**: the expectation follows from the code's evident intent (its name, its callers, the API contract, the UI copy) and the code contradicts it. Remove that one assertion and record the defect for `suspected_bugs`.
   - **Environment**: missing dependency, unreachable service. Stop and report it; tests cannot fix it.
3. Repeat. After three failed fix attempts on the same test case, delete that case and report why.
4. **Stability**: once green, run the same files again. A test that flips is nondeterministic (real time, ordering, unawaited async); fix the cause and restart the loop.
5. **Coverage**: compare the runner's uncovered lines with the targets' `uncovered_lines`. Each changed line still uncovered needs either another test case or a reason in the report.
6. **Suite**: run the runner once without arguments for every stack you touched, so shared fixtures and helpers you edited break nothing else.

## Completion

Done when, for every stack you touched, the last two runs of your test files passed, the full-suite run passed, and every changed line of every target is covered or has a stated reason.
