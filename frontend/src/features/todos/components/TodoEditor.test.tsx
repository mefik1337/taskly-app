import { screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { installFakeApi } from '../../../test/fakeApi'
import { renderWithProviders } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import type { Todo } from '../types'
import { TodoEditor } from './TodoEditor'

function renderEditor(todo: Todo | 'new', busy = false) {
  const onClose = vi.fn()
  const onSaved = vi.fn()
  const { user } = renderWithProviders(
    <TodoEditor todo={todo} busy={busy} onClose={onClose} onSaved={onSaved} />,
  )
  return { user, onClose, onSaved }
}

it('opens a New task dialog with an empty form', () => {
  installFakeApi()
  renderEditor('new')
  expect(screen.getByRole('dialog', { name: 'New task' })).toBeVisible()
  expect(screen.getByLabelText('Task title *')).toHaveValue('')
  expect(screen.getByLabelText('Task title *')).toHaveFocus()
})

it('reports a new task as added after saving it', async () => {
  installFakeApi()
  const { user, onSaved } = renderEditor('new')
  await user.type(screen.getByLabelText('Task title *'), 'Buy milk')
  await user.click(screen.getByRole('button', { name: 'Save task' }))
  await waitFor(() => expect(onSaved).toHaveBeenCalledWith('New task added.'))
})

it('opens an Edit task dialog prefilled with the task', () => {
  installFakeApi([todoFixture])
  renderEditor({ ...todoFixture, description: 'Slides' })
  expect(screen.getByRole('dialog', { name: 'Edit task' })).toBeVisible()
  expect(screen.getByLabelText('Task title *')).toHaveValue('Prepare a demo')
  expect(screen.getByLabelText('Description (optional)')).toHaveValue('Slides')
})

it('reports the changes as saved after editing a task', async () => {
  installFakeApi([todoFixture])
  const { user, onSaved } = renderEditor(todoFixture)
  await user.clear(screen.getByLabelText('Task title *'))
  await user.type(screen.getByLabelText('Task title *'), 'Prepare the keynote')
  await user.click(screen.getByRole('button', { name: 'Save task' }))
  await waitFor(() => expect(onSaved).toHaveBeenCalledWith('Changes saved.'))
})

it.each([
  ['a new task', 'new', 'POST', 'Database unavailable'],
  ['an edited task', todoFixture, 'PATCH', 'Task not found.'],
] as const)(
  'keeps the editor for %s open with the server error when saving fails',
  async (_, todo, method, detail) => {
    const api = installFakeApi([todoFixture])
    api.failNext(method, 500, detail)
    const { user, onSaved } = renderEditor(todo)
    await user.type(screen.getByLabelText('Task title *'), 'X')
    await user.click(screen.getByRole('button', { name: 'Save task' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(detail)
    expect(onSaved).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Save task' })).toBeEnabled()
  },
)

it('shows Saving… and blocks closing while the save is pending', async () => {
  const api = installFakeApi()
  const release = api.delayNextResponse('POST')
  const { user, onClose, onSaved } = renderEditor('new')
  await user.type(screen.getByLabelText('Task title *'), 'Buy milk')
  await user.click(screen.getByRole('button', { name: 'Save task' }))
  expect(await screen.findByRole('button', { name: 'Saving…' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Close' })).toBeDisabled()
  expect(screen.getByRole('dialog', { name: 'New task' })).toHaveAttribute(
    'aria-busy',
    'true',
  )
  await user.keyboard('{Escape}')
  expect(onClose).not.toHaveBeenCalled()
  release()
  await waitFor(() => expect(onSaved).toHaveBeenCalledWith('New task added.'))
})

it('keeps the form disabled while other task work is busy', () => {
  installFakeApi()
  renderEditor('new', true)
  expect(screen.getByLabelText('Task title *')).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Close' })).toBeDisabled()
})

it('closes without saving on Cancel', async () => {
  const api = installFakeApi()
  const { user, onClose } = renderEditor('new')
  await user.click(screen.getByRole('button', { name: 'Cancel' }))
  expect(onClose).toHaveBeenCalledTimes(1)
  expect(api.requests).toEqual([])
})
