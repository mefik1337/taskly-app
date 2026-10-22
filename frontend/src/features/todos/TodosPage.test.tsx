import { focusManager } from '@tanstack/react-query'
import { act, screen, waitFor, within } from '@testing-library/react'
import { expect, it, onTestFinished } from 'vitest'
import { installFakeApi } from '../../test/fakeApi'
import { renderWithProviders } from '../../test/queryWrapper'
import { todoFixture } from '../../test/todoFixture'
import { todosApi } from './api/todos'
import type { Todo } from './types'
import { TodosPage } from './TodosPage'

const groceries: Todo = {
  ...todoFixture,
  id: 8,
  title: 'Buy groceries',
  completed: true,
  created_at: '2026-10-05T12:00:00Z',
}

function renderPage() {
  return renderWithProviders(<TodosPage />)
}

function taskTitles() {
  return within(screen.getByRole('region', { name: 'Task list' }))
    .getAllByRole('heading', { level: 3 })
    .map((heading) => heading.textContent)
}

it('shows loading feedback until the tasks arrive', async () => {
  const api = installFakeApi([todoFixture])
  const release = api.delayNextResponse('GET')
  renderPage()
  expect(await screen.findByRole('status')).toHaveTextContent(
    'Loading your tasks…',
  )
  expect(screen.getByRole('button', { name: 'New task' })).toBeDisabled()
  release()
  expect(
    await screen.findByRole('heading', { name: 'Prepare a demo' }),
  ).toBeVisible()
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'New task' })).toBeEnabled()
})

it('lists the tasks from the server newest first', async () => {
  installFakeApi([todoFixture, groceries])
  renderPage()
  await screen.findByRole('heading', { name: 'Prepare a demo' })
  expect(taskTitles()).toEqual(['Buy groceries', 'Prepare a demo'])
})

it('narrows the list by search text and status', async () => {
  installFakeApi([todoFixture, groceries])
  const { user } = renderPage()
  await screen.findByRole('heading', { name: 'Prepare a demo' })
  await user.type(screen.getByLabelText('Search tasks'), 'demo')
  expect(taskTitles()).toEqual(['Prepare a demo'])
  await user.selectOptions(screen.getByLabelText('Status'), 'Completed')
  expect(
    screen.getByRole('heading', { name: 'No matching tasks' }),
  ).toBeVisible()
})

it('completes a task and shows the success notice', async () => {
  installFakeApi([todoFixture])
  const { user } = renderPage()
  await user.click(
    await screen.findByRole('checkbox', { name: 'Complete: Prepare a demo' }),
  )
  expect(await screen.findByRole('status')).toHaveTextContent(
    'Another task complete. Well done!',
  )
  expect(
    screen.getByRole('checkbox', { name: 'Mark as active: Prepare a demo' }),
  ).toBeChecked()
})

it('marks a completed task active again and says so', async () => {
  installFakeApi([groceries])
  const { user } = renderPage()
  await user.click(
    await screen.findByRole('checkbox', {
      name: 'Mark as active: Buy groceries',
    }),
  )
  expect(await screen.findByRole('status')).toHaveTextContent(
    'Task marked as active.',
  )
  expect(
    screen.getByRole('checkbox', { name: 'Complete: Buy groceries' }),
  ).not.toBeChecked()
})

it('disables task actions while a task is being saved', async () => {
  const api = installFakeApi([todoFixture])
  const release = api.delayNextResponse('PATCH')
  const { user } = renderPage()
  await user.click(
    await screen.findByRole('checkbox', { name: 'Complete: Prepare a demo' }),
  )
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'New task' })).toBeDisabled(),
  )
  expect(
    screen.getByRole('button', { name: 'Edit: Prepare a demo' }),
  ).toBeDisabled()
  expect(screen.getByRole('checkbox')).toBeDisabled()
  release()
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'New task' })).toBeEnabled(),
  )
})

it('shows the server error and reloads the list on Try again', async () => {
  const api = installFakeApi([todoFixture])
  api.failNext('GET', 503, 'The server is unavailable.')
  const { user } = renderPage()
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'The server is unavailable.',
  )
  expect(
    screen.getByRole('heading', {
      name: 'The task list is temporarily unavailable',
    }),
  ).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  expect(
    await screen.findByRole('heading', { name: 'Prepare a demo' }),
  ).toBeVisible()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})

it('keeps the tasks when a refresh on window focus fails and reloads on Try again', async () => {
  const api = installFakeApi([todoFixture])
  const { user } = renderPage()
  await screen.findByRole('heading', { name: 'Prepare a demo' })
  api.failNext('GET', 503, 'The server is unavailable.')
  onTestFinished(() => focusManager.setFocused(undefined))
  act(() => {
    focusManager.setFocused(false)
    focusManager.setFocused(true)
  })
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'The server is unavailable.',
  )
  expect(screen.getByRole('heading', { name: 'Prepare a demo' })).toBeVisible()
  const release = api.delayNextResponse('GET')
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  expect(screen.getByRole('button', { name: 'Try again' })).toBeDisabled()
  release()
  await waitFor(() =>
    expect(screen.queryByRole('alert')).not.toBeInTheDocument(),
  )
})

it('shows a failed toggle of a task deleted elsewhere and Try again reloads the list without it', async () => {
  installFakeApi([todoFixture])
  const { user } = renderPage()
  const checkbox = await screen.findByRole('checkbox', {
    name: 'Complete: Prepare a demo',
  })
  await todosApi.remove(7)
  await user.click(checkbox)
  expect(await screen.findByRole('alert')).toHaveTextContent('Task not found.')
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Prepare a demo' })).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  expect(
    await screen.findByRole('heading', { name: 'Add your first task' }),
  ).toBeVisible()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})

it('adds a task through the New task dialog', async () => {
  installFakeApi([todoFixture])
  const { user } = renderPage()
  await screen.findByRole('heading', { name: 'Prepare a demo' })
  await user.click(screen.getByRole('button', { name: 'New task' }))
  const dialog = screen.getByRole('dialog', { name: 'New task' })
  await user.type(within(dialog).getByLabelText('Task title *'), 'Buy milk')
  await user.selectOptions(within(dialog).getByLabelText('Priority'), 'High')
  await user.click(within(dialog).getByRole('button', { name: 'Save task' }))
  expect(await screen.findByRole('status')).toHaveTextContent('New task added.')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(taskTitles()).toEqual(['Buy milk', 'Prepare a demo'])
  const [added] = within(
    screen.getByRole('region', { name: 'Task list' }),
  ).getAllByRole('listitem')
  expect(within(added).getByText('High')).toBeVisible()
})

it('opens the New task dialog from the empty list', async () => {
  installFakeApi()
  const { user } = renderPage()
  await user.click(
    await screen.findByRole('button', { name: 'Add your first task' }),
  )
  expect(screen.getByRole('dialog', { name: 'New task' })).toBeVisible()
})

it('closes the editor without saving on Cancel', async () => {
  const api = installFakeApi([todoFixture])
  const { user } = renderPage()
  await screen.findByRole('heading', { name: 'Prepare a demo' })
  await user.click(screen.getByRole('button', { name: 'New task' }))
  await user.click(screen.getByRole('button', { name: 'Cancel' }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(api.requestsTo('POST')).toEqual([])
})

it('edits a task and shows the saved changes', async () => {
  installFakeApi([todoFixture])
  const { user } = renderPage()
  await user.click(
    await screen.findByRole('button', { name: 'Edit: Prepare a demo' }),
  )
  const dialog = screen.getByRole('dialog', { name: 'Edit task' })
  const title = within(dialog).getByLabelText('Task title *')
  await user.clear(title)
  await user.type(title, 'Prepare the keynote')
  await user.click(within(dialog).getByRole('button', { name: 'Save task' }))
  expect(await screen.findByRole('status')).toHaveTextContent('Changes saved.')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(taskTitles()).toEqual(['Prepare the keynote'])
})

it('deletes a task after confirmation', async () => {
  installFakeApi([todoFixture])
  const { user } = renderPage()
  await user.click(
    await screen.findByRole('button', { name: 'Delete: Prepare a demo' }),
  )
  await user.click(screen.getByRole('button', { name: 'Delete task' }))
  expect(await screen.findByRole('status')).toHaveTextContent('Task deleted.')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(
    screen.queryByRole('heading', { name: 'Prepare a demo' }),
  ).not.toBeInTheDocument()
  expect(
    screen.getByRole('heading', { name: 'Add your first task' }),
  ).toBeVisible()
})

it('keeps the task when deletion is cancelled', async () => {
  const api = installFakeApi([todoFixture])
  const { user } = renderPage()
  await user.click(
    await screen.findByRole('button', { name: 'Delete: Prepare a demo' }),
  )
  await user.click(screen.getByRole('button', { name: 'Cancel' }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Prepare a demo' })).toBeVisible()
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
  expect(api.requestsTo('DELETE')).toEqual([])
})

it('clears completed tasks and reports how many were removed', async () => {
  installFakeApi([todoFixture, groceries])
  const { user } = renderPage()
  await user.click(
    await screen.findByRole('button', { name: 'Clear completed (1)' }),
  )
  expect(await screen.findByRole('status')).toHaveTextContent(
    'Removed 1 completed task.',
  )
  expect(taskTitles()).toEqual(['Prepare a demo'])
  expect(
    screen.queryByRole('button', { name: /Clear completed/ }),
  ).not.toBeInTheDocument()
})

it('shows the server error when clearing completed tasks fails and dismisses it on Try again', async () => {
  const api = installFakeApi([groceries])
  const { user } = renderPage()
  const clear = await screen.findByRole('button', {
    name: 'Clear completed (1)',
  })
  api.failNext('DELETE', 500, 'Could not clear tasks.')
  await user.click(clear)
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Could not clear tasks.',
  )
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  await waitFor(() =>
    expect(screen.queryByRole('alert')).not.toBeInTheDocument(),
  )
})

it('keeps the page locked while completed tasks are being cleared', async () => {
  const api = installFakeApi([todoFixture, groceries])
  const release = api.delayNextResponse('DELETE')
  const { user } = renderPage()
  await user.click(
    await screen.findByRole('button', { name: 'Clear completed (1)' }),
  )
  await waitFor(() =>
    expect(
      screen.getByRole('button', { name: 'Clear completed (1)' }),
    ).toBeDisabled(),
  )
  expect(screen.getByRole('button', { name: 'New task' })).toBeDisabled()
  release()
  expect(await screen.findByRole('status')).toHaveTextContent(
    'Removed 1 completed task.',
  )
  expect(screen.getByRole('button', { name: 'New task' })).toBeEnabled()
})
