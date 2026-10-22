---
name: vitest-unit-tests
description: Conventions for writing Taskly frontend unit tests with Vitest and React Testing Library (pages, components, TanStack Query hooks, API client, utilities). Use before creating or editing any frontend *.test.ts or *.test.tsx file.
---

# Frontend unit tests (Vitest + React Testing Library)

A frontend test is a **user story in miniature**: it renders real Taskly code, acts the way a user does and asserts what the user would see. It survives any refactor that keeps the screen behaving the same.

## Before writing

Read `src/test/` (the fetch fake, the query client factory, fixtures) and one neighbouring `*.test.tsx`. Extend the shared helpers in `src/test/` instead of building a second copy in a test file.

## Layout

- `X.ts` / `X.tsx` is tested in `X.test.ts` / `X.test.tsx` next to it.
- Import test APIs explicitly: `import { describe, expect, it, vi } from 'vitest'`.

## Seams

Everything Taskly owns runs for real: the design system, child components, hooks, the API module and `lib/http`. The test substitutes only what the browser or the network provides.

| Substitute | How |
| --- | --- |
| Network | the fetch fake in `src/test/` (`vi.stubGlobal('fetch', …)` under the hood); assert the requests it recorded: method, URL, JSON body |
| Clock | `vi.useFakeTimers({ toFake: ['Date'] })` with `vi.setSystemTime(...)`; timeouts with `vi.advanceTimersByTime` inside `act` |
| Browser APIs jsdom lacks | polyfills in `src/test/setup.ts` (for example `HTMLDialogElement.showModal`) |

Pages and components render inside a fresh `createTestQueryClient()` provider per test. Hook tests use `renderHook` with the same provider and assert the hook's returned state; read the query cache only when the cache itself is the hook's contract.

## Querying and acting

- Query by role and accessible name (`getByRole('button', { name: 'Save task' })`), then by label (`getByLabelText('Due date')`), then by visible text. Test ids are a last resort for elements with no accessible name.
- Act through `const user = userEvent.setup()` and `await user.click(...)`, `user.type`, `user.clear`, `user.selectOptions`, `user.keyboard('{Escape}')`.
- Wait for asynchronous results with `findBy…` or `waitFor`; observe a pending state with a request the fake leaves unresolved.
- Accessibility is behaviour: assert `toBeInvalid()`, `toHaveAccessibleDescription(...)`, `getByRole('alert')`, `getByRole('status')` where the UI promises them.

## Writing cases

- `it('<what the user sees or can do>')`: `it('shows the server message when saving fails')`, `it('disables Save while the task is being created')`.
- One behaviour per test; tables of inputs use `it.each`.
- Expected values are literals written independently of the code under test.
- Small render helpers (`renderPage()`) keep setup out of each case.
- Each contract lives at **one layer**: the request shape (method, URL, body) in `api/*.test.ts`; hooks assert the state they return; components and pages assert what the screen shows.
- A test for an edge case or a bug uses data that **fails against the naive implementation**; when it would pass anyway, choose other data.
- No snapshots, no comments. Formatting follows `frontend/.prettierrc.json`; the runner formats the files you pass and type-checks the project.

## Rejected patterns

Each of these passes while the screen is broken or fails while it works; replace it with the seams above.

- `vi.mock` of any Taskly module (design system, hooks, child components, `api/*`, `lib/*`).
- Reading props from mocks (`mock.calls`, `lastCall`) or calling a child's callback by hand.
- Asserting styling variants, colours, class names or call order.
- `fireEvent` where `userEvent` can act.
- A test whose expected value is a constant restated, or what a mock was told to return.
- Asserting the fake's own state or the ids it generates; read results back through the code under test.
- Triggering library internals (`client.refetchQueries()`) where a user event (window focus, a click) takes the same path.
