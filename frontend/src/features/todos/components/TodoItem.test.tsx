import { screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { renderWithProviders } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import type { Todo } from '../types'
import { TodoItem } from './TodoItem'

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 9, 22, 10, 0, 0))
})
afterEach(() => vi.useRealTimers())

function renderItem(todo: Todo, busy = false) {
  const callbacks = { onEdit: vi.fn(), onToggle: vi.fn(), onDelete: vi.fn() }
  const { user } = renderWithProviders(
    <ul>
      <TodoItem todo={todo} busy={busy} {...callbacks} />
    </ul>,
  )
  return { user, ...callbacks }
}

it('shows the title, number, status and priority of a plain active task', () => {
  renderItem(todoFixture)
  expect(
    screen.getByRole('heading', { level: 3, name: 'Prepare a demo' }),
  ).toBeVisible()
  expect(screen.getByText('#7')).toBeVisible()
  expect(screen.getByText('To do')).toBeVisible()
  expect(screen.getByText('Medium')).toBeVisible()
  expect(
    screen.getByRole('checkbox', { name: 'Complete: Prepare a demo' }),
  ).not.toBeChecked()
})

it('shows the description of a task that has one', () => {
  renderItem({ ...todoFixture, description: 'Slides and notes' })
  expect(screen.getByText('Slides and notes')).toBeVisible()
})

it('shows no due date for a task without one', () => {
  renderItem(todoFixture)
  expect(
    screen.queryByText(/\d{1,2} [A-Z][a-z]{2} \d{4}/),
  ).not.toBeInTheDocument()
})

it('shows a completed task with a checked mark-as-active checkbox', () => {
  renderItem({ ...todoFixture, completed: true, priority: 'high' })
  expect(screen.getByText('Completed')).toBeVisible()
  expect(screen.getByText('High')).toBeVisible()
  expect(
    screen.getByRole('checkbox', { name: 'Mark as active: Prepare a demo' }),
  ).toBeChecked()
})

it('marks an active task due yesterday as overdue', () => {
  renderItem({ ...todoFixture, due_date: '2026-10-21' })
  expect(screen.getByText(/21 Oct 2026/)).toHaveTextContent(
    '21 Oct 2026 · overdue',
  )
})

it('shows a task due today without the overdue marker', () => {
  renderItem({ ...todoFixture, due_date: '2026-10-22' })
  expect(screen.getByText('22 Oct 2026')).toBeVisible()
  expect(screen.queryByText(/overdue/)).not.toBeInTheDocument()
})

it('does not mark a completed task due in the past as overdue', () => {
  renderItem({ ...todoFixture, completed: true, due_date: '2026-10-01' })
  expect(screen.getByText('1 Oct 2026')).toBeVisible()
  expect(screen.queryByText(/overdue/)).not.toBeInTheDocument()
})

it.each([
  ['checkbox', 'Complete: Prepare a demo', 'onToggle'],
  ['button', 'Edit: Prepare a demo', 'onEdit'],
  ['button', 'Delete: Prepare a demo', 'onDelete'],
] as const)(
  'reports a click on the %s "%s" through %s only',
  async (role, name, handler) => {
    const { user, ...callbacks } = renderItem(todoFixture)
    await user.click(screen.getByRole(role, { name }))
    expect(callbacks[handler]).toHaveBeenCalledTimes(1)
    const others = Object.entries(callbacks).filter(([key]) => key !== handler)
    for (const [, callback] of others) expect(callback).not.toHaveBeenCalled()
  },
)

it('disables every action while busy', async () => {
  const { user, onToggle } = renderItem(todoFixture, true)
  expect(screen.getByRole('checkbox')).toBeDisabled()
  expect(
    screen.getByRole('button', { name: 'Edit: Prepare a demo' }),
  ).toBeDisabled()
  expect(
    screen.getByRole('button', { name: 'Delete: Prepare a demo' }),
  ).toBeDisabled()
  await user.click(screen.getByRole('checkbox'))
  expect(onToggle).not.toHaveBeenCalled()
})
