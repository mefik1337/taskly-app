import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import { useCreateTodoMutation } from '../hooks/useCreateTodoMutation'
import { useUpdateTodoMutation } from '../hooks/useUpdateTodoMutation'
import type { TodoInput } from '../types'
import { TodoEditor } from './TodoEditor'
import { TodoForm } from './TodoForm'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))
vi.mock('../hooks/useCreateTodoMutation', () => ({
  useCreateTodoMutation: vi.fn(),
}))
vi.mock('../hooks/useUpdateTodoMutation', () => ({
  useUpdateTodoMutation: vi.fn(),
}))
vi.mock('./TodoForm', () => ({
  TodoForm: vi.fn(
    ({ onSubmit }: { onSubmit: (input: TodoInput) => Promise<void> }) => (
      <button onClick={() => void onSubmit(todoFixture)}>Submit form</button>
    ),
  ),
}))
beforeEach(() => vi.clearAllMocks())

function mockMutations(
  create: Partial<{ isPending: boolean; error: Error | null }> = {},
  update: Partial<{ isPending: boolean; error: Error | null }> = {},
) {
  const createAsync = vi.fn().mockResolvedValue(todoFixture)
  const updateAsync = vi.fn().mockResolvedValue(todoFixture)
  vi.mocked(useCreateTodoMutation).mockReturnValue({
    isPending: false,
    error: null,
    mutateAsync: createAsync,
    ...create,
  } as unknown as ReturnType<typeof useCreateTodoMutation>)
  vi.mocked(useUpdateTodoMutation).mockReturnValue({
    isPending: false,
    error: null,
    mutateAsync: updateAsync,
    ...update,
  } as unknown as ReturnType<typeof useUpdateTodoMutation>)
  return { createAsync, updateAsync }
}

function lastFormProps() {
  return vi.mocked(TodoForm).mock.lastCall![0]
}

it('creates a new task and reports a successful save', async () => {
  const user = userEvent.setup()
  const create = vi.fn().mockResolvedValue(todoFixture)
  const update = vi.fn()
  vi.mocked(useCreateTodoMutation).mockReturnValue({
    isPending: false,
    error: null,
    mutateAsync: create,
  } as unknown as ReturnType<typeof useCreateTodoMutation>)
  vi.mocked(useUpdateTodoMutation).mockReturnValue({
    isPending: false,
    error: null,
    mutateAsync: update,
  } as unknown as ReturnType<typeof useUpdateTodoMutation>)
  const onSaved = vi.fn()
  render(
    <TodoEditor todo="new" busy={false} onClose={vi.fn()} onSaved={onSaved} />,
  )
  expect(screen.getByRole('dialog', { name: 'New task' })).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Submit form' }))
  await waitFor(() => expect(onSaved).toHaveBeenCalledWith('New task added.'))
  expect(create).toHaveBeenCalledWith(todoFixture)
  expect(update).not.toHaveBeenCalled()
})

it('passes an empty initial value to the form for a new task', () => {
  mockMutations()
  render(
    <TodoEditor todo="new" busy={false} onClose={vi.fn()} onSaved={vi.fn()} />,
  )
  expect(lastFormProps()).toEqual(
    expect.objectContaining({ initial: undefined, busy: false, error: null }),
  )
})

it('updates an existing task by id and reports saved changes', async () => {
  const user = userEvent.setup()
  const { createAsync, updateAsync } = mockMutations()
  const onSaved = vi.fn()
  const existing = { ...todoFixture, id: 12, title: 'Existing' }
  render(
    <TodoEditor
      todo={existing}
      busy={false}
      onClose={vi.fn()}
      onSaved={onSaved}
    />,
  )
  expect(screen.getByRole('dialog', { name: 'Edit task' })).toBeVisible()
  expect(lastFormProps().initial).toBe(existing)
  await user.click(screen.getByRole('button', { name: 'Submit form' }))
  await waitFor(() => expect(onSaved).toHaveBeenCalledWith('Changes saved.'))
  expect(updateAsync).toHaveBeenCalledWith({ id: 12, input: todoFixture })
  expect(createAsync).not.toHaveBeenCalled()
})

it('does not report a save when the mutation rejects', async () => {
  const user = userEvent.setup()
  const { updateAsync } = mockMutations()
  updateAsync.mockRejectedValue(new Error('Cannot save'))
  const onSaved = vi.fn()
  render(
    <TodoEditor
      todo={todoFixture}
      busy={false}
      onClose={vi.fn()}
      onSaved={onSaved}
    />,
  )
  await user.click(screen.getByRole('button', { name: 'Submit form' }))
  await waitFor(() => expect(updateAsync).toHaveBeenCalledTimes(1))
  expect(onSaved).not.toHaveBeenCalled()
})

it('shows the error of the mutation matching the edited task', () => {
  mockMutations(
    { error: new Error('Create failed') },
    { error: new Error('Update failed') },
  )
  const { rerender } = render(
    <TodoEditor
      todo={todoFixture}
      busy={false}
      onClose={vi.fn()}
      onSaved={vi.fn()}
    />,
  )
  expect(lastFormProps().error).toBe('Update failed')
  rerender(
    <TodoEditor todo="new" busy={false} onClose={vi.fn()} onSaved={vi.fn()} />,
  )
  expect(lastFormProps().error).toBe('Create failed')
})

it.each([
  ['the mutation is pending', true, false],
  ['other task work is busy', false, true],
])(
  'marks the form busy and ignores submissions while %s',
  async (_, isPending, busy) => {
    const user = userEvent.setup()
    const { createAsync } = mockMutations({ isPending })
    const onSaved = vi.fn()
    render(
      <TodoEditor todo="new" busy={busy} onClose={vi.fn()} onSaved={onSaved} />,
    )
    expect(lastFormProps().busy).toBe(true)
    expect(screen.getByRole('button', { name: 'Close' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Submit form' }))
    expect(createAsync).not.toHaveBeenCalled()
    expect(onSaved).not.toHaveBeenCalled()
  },
)

it('closes through the form cancel callback', () => {
  mockMutations()
  const onClose = vi.fn()
  render(
    <TodoEditor todo="new" busy={false} onClose={onClose} onSaved={vi.fn()} />,
  )
  lastFormProps().onCancel()
  expect(onClose).toHaveBeenCalledTimes(1)
})
