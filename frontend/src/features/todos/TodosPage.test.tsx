import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { SuccessNotice } from '../../components/SuccessNotice'
import { useNotice } from '../../hooks/useNotice'
import { todoFixture } from '../../test/todoFixture'
import { DeleteTodoDialog } from './components/DeleteTodoDialog'
import { TodoEditor } from './components/TodoEditor'
import { TodoFilters } from './components/TodoFilters'
import { TodoList } from './components/TodoList'
import { TodosHeader } from './components/TodosHeader'
import { useTodoFilters } from './hooks/useTodoFilters'
import { useTodosBusy } from './hooks/useTodosBusy'
import { useTodosQuery } from './hooks/useTodosQuery'
import { useUpdateTodoMutation } from './hooks/useUpdateTodoMutation'
import { TodosPage } from './TodosPage'

vi.mock('../../design-system', () => import('../../design-system/mocks'))
vi.mock('../../hooks/useNotice', () => ({ useNotice: vi.fn() }))
vi.mock('./hooks/useTodoFilters', () => ({ useTodoFilters: vi.fn() }))
vi.mock('./hooks/useTodosBusy', () => ({ useTodosBusy: vi.fn() }))
vi.mock('./hooks/useTodosQuery', () => ({ useTodosQuery: vi.fn() }))
vi.mock('./hooks/useUpdateTodoMutation', () => ({
  useUpdateTodoMutation: vi.fn(),
}))
vi.mock('./components/TodosHeader', () => ({
  TodosHeader: vi.fn(() => <h1>Tasks</h1>),
}))
vi.mock('./components/TodoFilters', () => ({ TodoFilters: vi.fn(() => null) }))
vi.mock('./components/TodoList', () => ({
  TodoList: vi.fn(() => <p>Task list</p>),
}))
vi.mock('./components/TodoEditor', () => ({
  TodoEditor: vi.fn(() => <p>Editor open</p>),
}))
vi.mock('./components/DeleteTodoDialog', () => ({
  DeleteTodoDialog: vi.fn(() => <p>Delete dialog open</p>),
}))
vi.mock('../../components/SuccessNotice', () => ({
  SuccessNotice: vi.fn(() => null),
}))

beforeEach(() => vi.clearAllMocks())

const filterState = {
  filter: 'all' as const,
  search: '',
  sort: 'newest' as const,
  visible: [todoFixture],
  setFilter: vi.fn(),
  setSearch: vi.fn(),
  setSort: vi.fn(),
}

function setup({
  query = {},
  mutation = {},
  busy = false,
  message = '',
}: {
  query?: Record<string, unknown>
  mutation?: Record<string, unknown>
  busy?: boolean
  message?: string
} = {}) {
  const notify = vi.fn()
  const mutateAsync = vi.fn()
  const reset = vi.fn()
  const refetch = vi.fn().mockResolvedValue(undefined)
  vi.mocked(useTodosQuery).mockReturnValue({
    data: [todoFixture],
    isPending: false,
    isFetching: false,
    isError: false,
    error: null,
    refetch,
    ...query,
  } as unknown as ReturnType<typeof useTodosQuery>)
  vi.mocked(useUpdateTodoMutation).mockReturnValue({
    error: null,
    reset,
    mutateAsync,
    ...mutation,
  } as unknown as ReturnType<typeof useUpdateTodoMutation>)
  vi.mocked(useTodosBusy).mockReturnValue(busy)
  vi.mocked(useNotice).mockReturnValue({ message, notify })
  vi.mocked(useTodoFilters).mockReturnValue(filterState)
  render(<TodosPage />)
  return { notify, mutateAsync, reset, refetch }
}

function lastListProps() {
  return vi.mocked(TodoList).mock.lastCall![0]
}

it('displays a query failure and resets mutation errors before retrying', async () => {
  const user = userEvent.setup()
  const { refetch, reset } = setup({
    query: {
      data: [],
      isError: true,
      error: new Error('The server is unavailable.'),
    },
  })
  expect(screen.getByTestId('alert')).toHaveTextContent(
    'The server is unavailable.',
  )
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  await waitFor(() => expect(refetch).toHaveBeenCalledTimes(1))
  expect(reset).toHaveBeenCalledTimes(1)
  expect(reset.mock.invocationCallOrder[0]).toBeLessThan(
    refetch.mock.invocationCallOrder[0],
  )
})

it('prefers the toggle error over the query error in the alert', () => {
  setup({
    query: { error: new Error('Query failed') },
    mutation: { error: new Error('Toggle failed') },
  })
  expect(screen.getByTestId('alert')).toHaveTextContent('Toggle failed')
  expect(screen.queryByText('Query failed')).not.toBeInTheDocument()
})

it('shows no alert when nothing failed', () => {
  setup()
  expect(screen.queryByTestId('alert')).not.toBeInTheDocument()
})

it.each([
  ['refetching', { isFetching: true }, false],
  ['busy', {}, true],
])('disables retrying while %s', (_, query, busy) => {
  setup({ query: { ...query, error: new Error('Failed') }, busy })
  expect(screen.getByRole('button', { name: 'Try again' })).toBeDisabled()
})

it('passes filter state, visible tasks and status flags to its children', () => {
  setup({ query: { isPending: true, isError: true } })
  expect(vi.mocked(TodoFilters).mock.lastCall![0]).toEqual({
    filter: 'all',
    search: '',
    sort: 'newest',
    onFilterChange: filterState.setFilter,
    onSearchChange: filterState.setSearch,
    onSortChange: filterState.setSort,
  })
  expect(lastListProps()).toEqual(
    expect.objectContaining({
      todos: [todoFixture],
      hasTodos: true,
      loading: true,
      failed: true,
      busy: false,
    }),
  )
  expect(useTodoFilters).toHaveBeenCalledWith([todoFixture])
})

it('treats missing query data as an empty task list', () => {
  setup({ query: { data: undefined } })
  expect(useTodoFilters).toHaveBeenCalledWith([])
  expect(lastListProps().hasTodos).toBe(false)
})

it.each([
  ['loading', { isPending: true }, false, true],
  ['busy', {}, true, true],
  ['idle', {}, false, false],
])('sets the header disabled state while %s', (_, query, busy, disabled) => {
  setup({ query, busy })
  expect(vi.mocked(TodosHeader).mock.lastCall![0].disabled).toBe(disabled)
})

it('forwards the current notice message', () => {
  setup({ message: 'Task deleted.' })
  expect(vi.mocked(SuccessNotice).mock.lastCall![0]).toEqual({
    message: 'Task deleted.',
  })
})

it.each([
  [false, true, 'Another task complete. Well done!'],
  [true, false, 'Task marked as active.'],
])(
  'toggles a task with completed %s and announces the saved state',
  async (completed, next, notice) => {
    const { mutateAsync, notify } = setup()
    mutateAsync.mockResolvedValue({ ...todoFixture, completed: next })
    act(() => lastListProps().onToggle({ ...todoFixture, completed }))
    await waitFor(() => expect(notify).toHaveBeenCalledWith(notice))
    expect(mutateAsync).toHaveBeenCalledWith({
      id: todoFixture.id,
      input: { completed: next },
    })
  },
)

it('does not toggle while busy', () => {
  const { mutateAsync } = setup({ busy: true })
  act(() => lastListProps().onToggle(todoFixture))
  expect(mutateAsync).not.toHaveBeenCalled()
})

it('does not announce anything when toggling fails', async () => {
  const { mutateAsync, notify } = setup()
  mutateAsync.mockRejectedValue(new Error('Cannot save'))
  act(() => lastListProps().onToggle(todoFixture))
  await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1))
  await act(async () => {})
  expect(notify).not.toHaveBeenCalled()
})

it('opens the editor for a new task from the header and the list', () => {
  setup()
  expect(TodoEditor).not.toHaveBeenCalled()
  act(() => vi.mocked(TodosHeader).mock.lastCall![0].onCreate())
  expect(vi.mocked(TodoEditor).mock.lastCall![0]).toEqual(
    expect.objectContaining({ todo: 'new', busy: false }),
  )
  act(() => vi.mocked(TodoEditor).mock.lastCall![0].onClose())
  expect(screen.queryByText('Editor open')).not.toBeInTheDocument()
  act(() => lastListProps().onCreate())
  expect(screen.getByText('Editor open')).toBeVisible()
  expect(vi.mocked(TodoEditor).mock.lastCall![0].todo).toBe('new')
})

it('closes the editor and announces the notice after saving an edited task', () => {
  const { notify } = setup()
  act(() => lastListProps().onEdit(todoFixture))
  expect(vi.mocked(TodoEditor).mock.lastCall![0].todo).toBe(todoFixture)
  act(() => vi.mocked(TodoEditor).mock.lastCall![0].onSaved('Changes saved.'))
  expect(screen.queryByText('Editor open')).not.toBeInTheDocument()
  expect(notify).toHaveBeenCalledWith('Changes saved.')
})

it('opens the delete dialog for a task and closes it without a notice', () => {
  const { notify } = setup({ busy: true })
  expect(DeleteTodoDialog).not.toHaveBeenCalled()
  act(() => lastListProps().onDelete(todoFixture))
  expect(vi.mocked(DeleteTodoDialog).mock.lastCall![0]).toEqual(
    expect.objectContaining({ todo: todoFixture, busy: true }),
  )
  act(() => vi.mocked(DeleteTodoDialog).mock.lastCall![0].onClose())
  expect(screen.queryByText('Delete dialog open')).not.toBeInTheDocument()
  expect(notify).not.toHaveBeenCalled()
})

it('closes the delete dialog and announces the deletion', () => {
  const { notify } = setup()
  act(() => lastListProps().onDelete(todoFixture))
  act(() => vi.mocked(DeleteTodoDialog).mock.lastCall![0].onDeleted())
  expect(screen.queryByText('Delete dialog open')).not.toBeInTheDocument()
  expect(notify).toHaveBeenCalledWith('Task deleted.')
})
