---
name: change-analysis
description: Decide which changed Taskly source files need new or updated unit tests, which behaviours those tests must pin, and what to do with tests the change already broke. Use when starting test work from an analysis file or a git diff, or when asked which code is missing tests.
---

# Change analysis

Turns a change into a **test plan**: one decision per target, a classification for every test the change broke, and for every file you will test, the behaviours the tests must pin.

## Steps

1. **Collect the change.** Read the analysis file. For each target, read its diff with `git diff <base>...HEAD -- <path>` (in a backfill, the whole file) and the test file that mirrors it, if one exists.
2. **Read the context files.** Every entry of `changed_files` matters, not only the targets:
   - Test files the author changed may already pin the new behaviour. Read them before deciding.
   - Files the stack's coverage excludes (`schemas.py`, `models.py`, `types.ts`, barrels, constants) never appear as targets, yet their rules surface through a tested seam. A new Pydantic constraint is behaviour of the route; a new field in `types.ts` is behaviour of the components that render it. When such a file changes a rule, add a decision for it and pin the rule at that seam.
3. **Classify the broken tests.** For every entry of `suite.failed_cases`, read the test and the change:
   - **Stale**: it pins behaviour the change replaced on purpose (a route list without the new route, a screen without the new button). Plan the update to the new behaviour.
   - **Regression**: the change broke behaviour that should have survived. Leave the test unchanged and record the defect for `suspected_bugs`.
4. **Decide** for each target, taking the first rule that matches:
   - **skip**: the changed lines carry no behaviour (imports, renames, formatting, type annotations, re-exports, styling props).
   - **skip**: every changed line is covered **and** an existing test asserts the new behaviour. Coverage alone is not enough: a line that runs while no assertion checks its effect is still untested.
   - **update**: a test file for the module exists. Extend it, keeping its structure, fixtures and naming.
   - **create**: no test file exists.
   - **skip**: wiring a unit test cannot exercise meaningfully (module-level `app = create_app()`, the `createRoot(...)` bootstrap). Say so in the reason.
5. **List behaviours** for every create or update. A behaviour is something a caller or user can observe:
   - each branch of new conditional logic, including the fall-through;
   - each error path: HTTP status and body, rejected promise, rendered error message;
   - boundaries: empty input, maximum length, `null` versus missing, the first and last item of an ordering;
   - what crosses the stack's seam: the request sent, the rows stored, what is rendered.

   Name each behaviour as the test you will write (`test_clear_completed_keeps_active_tasks`, `'removes completed tasks when Clear completed is clicked'`).

## Completion

Done when every target has exactly one decision with a one-sentence reason, every failed case in `suite` is classified as stale or regression, and every uncovered changed line of a create or update target maps to at least one listed behaviour or to a stated reason why no unit test can reach it.
