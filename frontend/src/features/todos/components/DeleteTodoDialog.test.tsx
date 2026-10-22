import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import { useDeleteTodoMutation } from '../hooks/useDeleteTodoMutation'
import { DeleteTodoDialog } from './DeleteTodoDialog'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))
vi.mock('../hooks/useDeleteTodoMutation', () => ({
  useDeleteTodoMutation: vi.fn(),
}))

it('shows a deletion error and allows cancelling without deleting', async () => {
  const user = userEvent.setup()
  const mutateAsync = vi.fn()
  vi.mocked(useDeleteTodoMutation).mockReturnValue({
    isPending: false,
    error: new Error('Could not delete.'),
    mutateAsync,
  } as unknown as ReturnType<typeof useDeleteTodoMutation>)
  const onClose = vi.fn()
  const onDeleted = vi.fn()
  render(
    <DeleteTodoDialog
      todo={todoFixture}
      busy={false}
      onClose={onClose}
      onDeleted={onDeleted}
    />,
  )
  expect(screen.getByRole('dialog', { name: 'Delete task?' })).toBeVisible()
  expect(
    screen.getByText(
      `The task “${todoFixture.title}” will be permanently deleted.`,
    ),
  ).toBeVisible()
  expect(screen.getByTestId('alert')).toHaveTextContent('Could not delete.')
  await user.click(screen.getByRole('button', { name: 'Cancel' }))
  expect(onClose).toHaveBeenCalledTimes(1)
  expect(mutateAsync).not.toHaveBeenCalled()
  expect(onDeleted).not.toHaveBeenCalled()
})

function mockDeletion(
  overrides: Partial<{
    isPending: boolean
    error: Error | null
    mutateAsync: ReturnType<typeof vi.fn>
  }> = {},
) {
  const state = {
    isPending: false,
    error: null,
    mutateAsync: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  }
  vi.mocked(useDeleteTodoMutation).mockReturnValue(
    state as unknown as ReturnType<typeof useDeleteTodoMutation>,
  )
  return state
}

function renderDialog(busy = false) {
  const onClose = vi.fn()
  const onDeleted = vi.fn()
  render(
    <DeleteTodoDialog
      todo={todoFixture}
      busy={busy}
      onClose={onClose}
      onDeleted={onDeleted}
    />,
  )
  return { onClose, onDeleted }
}

it('deletes the task by id and reports the deletion', async () => {
  const user = userEvent.setup()
  const { mutateAsync } = mockDeletion()
  const { onDeleted, onClose } = renderDialog()
  expect(screen.queryByTestId('alert')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Delete task' }))
  await waitFor(() => expect(onDeleted).toHaveBeenCalledTimes(1))
  expect(mutateAsync).toHaveBeenCalledWith(todoFixture.id)
  expect(onClose).not.toHaveBeenCalled()
})

it('stays open without reporting a deletion when the mutation rejects', async () => {
  const user = userEvent.setup()
  const { mutateAsync } = mockDeletion({
    mutateAsync: vi.fn().mockRejectedValue(new Error('Could not delete.')),
  })
  const { onDeleted, onClose } = renderDialog()
  await user.click(screen.getByRole('button', { name: 'Delete task' }))
  await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1))
  expect(onDeleted).not.toHaveBeenCalled()
  expect(onClose).not.toHaveBeenCalled()
  expect(screen.getByRole('dialog', { name: 'Delete task?' })).toBeVisible()
})

it.each([
  ['the deletion is pending', true, false],
  ['other task work is busy', false, true],
])(
  'disables both actions and shows progress while %s',
  async (_, isPending, busy) => {
    const user = userEvent.setup()
    const { mutateAsync } = mockDeletion({ isPending })
    const { onClose } = renderDialog(busy)
    const deleteButton = screen.getByRole('button', { name: 'Deleting…' })
    expect(deleteButton).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Close' })).toBeDisabled()
    await user.click(deleteButton)
    expect(mutateAsync).not.toHaveBeenCalled()
    expect(onClose).not.toHaveBeenCalled()
  },
)
