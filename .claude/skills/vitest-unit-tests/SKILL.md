---
name: vitest-unit-tests
description: Conventions for writing Taskly frontend unit tests with Vitest and React Testing Library (components, hooks with TanStack Query, API client, utilities). Use before creating or editing any frontend *.test.ts or *.test.tsx file.
---

# Frontend unit tests (Vitest + React Testing Library)

## Before writing

Read one neighbouring `*.test.tsx` in the same folder and `src/test/` (shared fixtures and helpers). Reuse `todoFixture` and spread it to vary fields (`{ ...todoFixture, completed: true }`).

## Layout

- `X.ts` / `X.tsx` is tested in `X.test.ts` / `X.test.tsx` next to it.
- Import test APIs explicitly: `import { describe, expect, it, vi } from 'vitest'`.

## Seams

- **Components**: render the component, interact through `userEvent.setup()`, query by role and accessible name (`getByRole('button', { name: 'Save task' })`) or label (`getByLabelText('Status')`). Assert what the user sees and which callbacks fire with which arguments.
- **Design system**: replace it with its test doubles: `vi.mock('<relative path>/design-system', () => import('<relative path>/design-system/mocks'))`. The doubles render native elements and are `vi.fn`, so `vi.mocked(Alert).mock.calls[0][0]` exposes the props a component passed.
- **Hooks and children of the unit**: a component test mocks the hook modules it consumes (`vi.mock('../hooks/useTodosQuery', () => ({ useTodosQuery: vi.fn() }))`) and returns partial results with `as unknown as ReturnType<typeof useTodosQuery>`. Mock a child component only when its own behaviour is irrelevant to the test.
- **Query and mutation hooks**: mock the API module (`vi.mock('../api/todos')`) and render the hook with `renderHook` inside a real `QueryClientProvider` whose client disables retries. Assert the cache through `queryClient.getQueryData(todoKeys.list)` after the mutation settles.
- **HTTP client**: stub the network with `vi.stubGlobal('fetch', vi.fn())`, build responses with `new Response(JSON.stringify(body), { status })`, and restore with `vi.unstubAllGlobals()` in `afterEach`.
- **Time**: `vi.useFakeTimers()` with `vi.setSystemTime(...)` for dates, `act(() => vi.advanceTimersByTime(ms))` for timeouts, and `vi.useRealTimers()` in `afterEach`.

## Writing cases

- `it('<observable behaviour>')`, grouped with `describe` when a file covers several units.
- One behaviour per test; tables of inputs use `it.each`.
- Expected values are literals written independently of the code under test.
- Await every user interaction; wait for asynchronous results with `findBy…` or `waitFor`.
- No snapshot tests, no comments.
- Formatting follows `frontend/.prettierrc.json`; the test runner formats the files you pass it and type-checks the project, so type errors fail the run.
