import { screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { installFakeApi } from '../../../test/fakeApi'
import { renderWithProviders } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import { DeleteTodoDialog } from './DeleteTodoDialog'

function renderDialog(busy = false) {
  const onClose = vi.fn()
  const onDeleted = vi.fn()
  const { user } = renderWithProviders(
    <DeleteTodoDialog
      todo={todoFixture}
      busy={busy}
      onClose={onClose}
      onDeleted={onDeleted}
    />,
  )
  return { user, onClose, onDeleted }
}

it('asks to confirm deleting the named task', () => {
  installFakeApi([todoFixture])
  renderDialog()
  expect(screen.getByRole('dialog', { name: 'Delete task?' })).toBeVisible()
  expect(
    screen.getByText('The task “Prepare a demo” will be permanently deleted.'),
  ).toBeVisible()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})

it('deletes the task with DELETE and reports the deletion', async () => {
  const api = installFakeApi([todoFixture])
  const { user, onDeleted, onClose } = renderDialog()
  await user.click(screen.getByRole('button', { name: 'Delete task' }))
  await waitFor(() => expect(onDeleted).toHaveBeenCalledTimes(1))
  expect(api.requests).toMatchObject([
    { method: 'DELETE', url: '/api/todos/7' },
  ])
  expect(onClose).not.toHaveBeenCalled()
})

it('shows Deleting… and blocks closing while the deletion is pending', async () => {
  const api = installFakeApi([todoFixture])
  const release = api.delayNextResponse('DELETE')
  const { user, onClose, onDeleted } = renderDialog()
  await user.click(screen.getByRole('button', { name: 'Delete task' }))
  expect(
    await screen.findByRole('button', { name: 'Deleting…' }),
  ).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Close' })).toBeDisabled()
  expect(screen.getByRole('dialog', { name: 'Delete task?' })).toHaveAttribute(
    'aria-busy',
    'true',
  )
  await user.keyboard('{Escape}')
  await user.click(screen.getByRole('dialog', { name: 'Delete task?' }))
  expect(onClose).not.toHaveBeenCalled()
  release()
  await waitFor(() => expect(onDeleted).toHaveBeenCalledTimes(1))
})

it('blocks every action while other task work is busy', () => {
  installFakeApi([todoFixture])
  renderDialog(true)
  expect(screen.getByRole('button', { name: 'Deleting…' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Close' })).toBeDisabled()
})

it('stays open with the server error and lets the user retry', async () => {
  const api = installFakeApi([todoFixture])
  api.failNext('DELETE', 500, 'Database unavailable')
  const { user, onDeleted } = renderDialog()
  await user.click(screen.getByRole('button', { name: 'Delete task' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Database unavailable',
  )
  expect(onDeleted).not.toHaveBeenCalled()
  await user.click(screen.getByRole('button', { name: 'Delete task' }))
  await waitFor(() => expect(onDeleted).toHaveBeenCalledTimes(1))
  expect(api.requestsTo('DELETE')).toHaveLength(2)
})

it('closes without deleting on Cancel', async () => {
  const api = installFakeApi([todoFixture])
  const { user, onClose } = renderDialog()
  await user.click(screen.getByRole('button', { name: 'Cancel' }))
  expect(onClose).toHaveBeenCalledTimes(1)
  expect(api.requests).toEqual([])
})

it('closes on the Close button', async () => {
  installFakeApi([todoFixture])
  const { user, onClose } = renderDialog()
  await user.click(screen.getByRole('button', { name: 'Close' }))
  expect(onClose).toHaveBeenCalledTimes(1)
})

it('closes on Escape', async () => {
  installFakeApi([todoFixture])
  const { user, onClose } = renderDialog()
  await user.keyboard('{Escape}')
  expect(onClose).toHaveBeenCalledTimes(1)
  expect(screen.getByRole('dialog', { name: 'Delete task?' })).toBeVisible()
})

it('closes when the backdrop is clicked', async () => {
  installFakeApi([todoFixture])
  const { user, onClose } = renderDialog()
  await user.click(screen.getByRole('dialog', { name: 'Delete task?' }))
  expect(onClose).toHaveBeenCalledTimes(1)
})

it('stays open when the dialog content is clicked', async () => {
  installFakeApi([todoFixture])
  const { user, onClose } = renderDialog()
  await user.click(
    screen.getByText('The task “Prepare a demo” will be permanently deleted.'),
  )
  expect(onClose).not.toHaveBeenCalled()
})
