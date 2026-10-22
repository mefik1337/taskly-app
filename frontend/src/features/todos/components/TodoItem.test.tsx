import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { Badge, Text } from '../../../design-system'
import { todoFixture } from '../../../test/todoFixture'
import type { Todo } from '../types'
import { TodoItem } from './TodoItem'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))
beforeEach(() => vi.clearAllMocks())

it('shows an active task and forwards edit requests', async () => {
  const user = userEvent.setup()
  const onEdit = vi.fn()
  const onToggle = vi.fn()
  const onDelete = vi.fn()
  render(
    <TodoItem
      todo={todoFixture}
      busy={false}
      onEdit={onEdit}
      onToggle={onToggle}
      onDelete={onDelete}
    />,
  )
  expect(screen.getByRole('heading', { name: todoFixture.title })).toBeVisible()
  expect(screen.getByText('To do')).toBeVisible()
  expect(screen.getByText('Medium')).toBeVisible()
  expect(screen.getByRole('checkbox')).not.toBeChecked()
  await user.click(
    screen.getByRole('button', { name: `Edit: ${todoFixture.title}` }),
  )
  expect(onEdit).toHaveBeenCalledTimes(1)
  expect(onToggle).not.toHaveBeenCalled()
  expect(onDelete).not.toHaveBeenCalled()
})

function renderItem(todo: Todo, busy = false) {
  const callbacks = { onEdit: vi.fn(), onToggle: vi.fn(), onDelete: vi.fn() }
  render(<TodoItem todo={todo} busy={busy} {...callbacks} />)
  return callbacks
}

it('shows a completed task with its description and a mark-as-active toggle', () => {
  renderItem({
    ...todoFixture,
    completed: true,
    priority: 'high',
    description: 'Slides and notes',
  })
  expect(screen.getByText('Completed')).toBeVisible()
  expect(screen.getByText('High')).toBeVisible()
  expect(screen.getByText('Slides and notes')).toBeVisible()
  expect(screen.getByText(`#${todoFixture.id}`)).toBeVisible()
  expect(
    screen.getByRole('checkbox', {
      name: `Mark as active: ${todoFixture.title}`,
    }),
  ).toBeChecked()
})

it('omits the description and due date when they are empty', () => {
  renderItem(todoFixture)
  expect(screen.queryByText(/overdue/)).not.toBeInTheDocument()
  expect(
    vi.mocked(Text).mock.calls.some(([props]) => props.preserveWhitespace),
  ).toBe(false)
  expect(Badge).toHaveBeenCalledTimes(1)
})

it('marks a past due date of an active task as overdue', () => {
  renderItem({ ...todoFixture, due_date: '2000-01-15' })
  expect(screen.getByText(/15 Jan 2000/)).toHaveTextContent(
    '15 Jan 2000 · overdue',
  )
  expect(vi.mocked(Badge).mock.calls[1][0]).toEqual(
    expect.objectContaining({ variant: 'warning' }),
  )
})

it('shows a future due date without the overdue marker', () => {
  renderItem({ ...todoFixture, due_date: '2999-03-04' })
  expect(screen.getByText('4 Mar 2999')).toBeVisible()
  expect(screen.queryByText(/overdue/)).not.toBeInTheDocument()
  expect(vi.mocked(Badge).mock.calls[1][0]).toEqual(
    expect.objectContaining({ variant: 'neutral' }),
  )
})

it('forwards toggle and delete requests', async () => {
  const user = userEvent.setup()
  const { onToggle, onDelete, onEdit } = renderItem(todoFixture)
  await user.click(
    screen.getByRole('checkbox', { name: `Complete: ${todoFixture.title}` }),
  )
  expect(onToggle).toHaveBeenCalledTimes(1)
  await user.click(
    screen.getByRole('button', { name: `Delete: ${todoFixture.title}` }),
  )
  expect(onDelete).toHaveBeenCalledTimes(1)
  expect(onEdit).not.toHaveBeenCalled()
})

it('disables every action while busy', async () => {
  const user = userEvent.setup()
  const callbacks = renderItem(todoFixture, true)
  expect(screen.getByRole('checkbox')).toBeDisabled()
  expect(
    screen.getByRole('button', { name: `Edit: ${todoFixture.title}` }),
  ).toBeDisabled()
  expect(
    screen.getByRole('button', { name: `Delete: ${todoFixture.title}` }),
  ).toBeDisabled()
  await user.click(screen.getByRole('checkbox'))
  expect(callbacks.onToggle).not.toHaveBeenCalled()
})
