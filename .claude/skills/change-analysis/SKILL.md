---
name: change-analysis
description: Decide which changed Taskly source files need new or updated unit tests and which behaviours those tests must pin. Use when starting test work from a change manifest or a git diff, or when asked which code is missing tests.
---

# Change analysis

Turns a change into a test plan: one decision per changed source file, and for every file you will test, the list of behaviours the tests must pin.

## Steps

1. **Collect the change.** Read the manifest (`python -m pr_test_agent manifest` output). For each `target`, read its diff with `git diff <base>...HEAD -- <path>`; in backfill mode, read the whole file. Read the existing test file at `test_path` when `test_exists` is true.
2. **Read the context files.** Non-target entries still matter:
   - Test files the author changed (`kind: test`) may already pin the new behaviour. Read them before deciding.
   - Sources with `coverage_excluded: true` (`schemas.py`, `models.py`, `types.ts`, barrels, constants) hold no logic of their own, but their rules surface through a tested seam. A new Pydantic constraint in `schemas.py` is behaviour of the router; a new field in `types.ts` is behaviour of the components that render it. When such a file changes a rule, add a decision row for it and pin the rule at that seam.
3. **Decide** for each target, taking the first rule that matches:
   - **skip**: the changed lines carry no behaviour (imports, renames, formatting, type annotations, re-exports, class names or styling props in JSX).
   - **skip**: every changed line is covered **and** an existing test asserts the new behaviour. Coverage alone is not enough: a line that runs but whose effect no assertion checks is still untested.
   - **update**: a test file for the module exists. Extend it, keeping its structure, fixtures and naming.
   - **create**: no test file exists. Create it at `test_path`.
   - **skip**: the code is wiring a unit test cannot exercise meaningfully (module-level `app = create_app()`, `createRoot(...)` bootstrap). Say so in the reason.
4. **List behaviours** for every create or update. A behaviour is something a caller can observe:
   - each branch of new conditional logic, including the fall-through;
   - each error path: raised exception, HTTP status, rejected promise, rendered error message;
   - boundaries: empty input, maximum length, `null` versus missing, the first and last item of an ordering;
   - the contract with collaborators: what is sent to the API or repository, what is returned or rendered to the caller.

   Name each behaviour as the test name you will write (`test_update_returns_404_for_missing_task`, `'disables saving while the mutation is pending'`).

## Completion

Done when every manifest target has exactly one decision with a one-sentence reason, and every uncovered changed line of a create or update target maps to at least one listed behaviour or to a stated reason why no unit test can reach it.
