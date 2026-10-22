import { screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { renderWithProviders } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import type { Todo } from '../types'
import { TodoList } from './TodoList'

const second: Todo = { ...todoFixture, id: 9, title: 'Second' }

function renderList(
  props: Partial<{
    todos: Todo[]
    hasTodos: boolean
    loading: boolean
    failed: boolean
    busy: boolean
  }> = {},
) {
  const callbacks = {
    onCreate: vi.fn(),
    onToggle: vi.fn(),
    onEdit: vi.fn(),
    onDelete: vi.fn(),
  }
  const { user } = renderWithProviders(
    <TodoList
      todos={[]}
      hasTodos={false}
      loading={false}
      failed={false}
      busy={false}
      {...props}
      {...callbacks}
    />,
  )
  return { user, ...callbacks }
}

it('shows loading feedback while tasks load', () => {
  renderList({ loading: true })
  expect(screen.getByRole('status')).toHaveTextContent('Loading your tasks…')
  expect(screen.queryByRole('heading')).not.toBeInTheDocument()
})

it('invites creating the first task when there are none', async () => {
  const { user, onCreate } = renderList()
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Add your first task' }))
  expect(onCreate).toHaveBeenCalledTimes(1)
})

it('blocks creating the first task while busy', () => {
  renderList({ busy: true })
  expect(
    screen.getByRole('button', { name: 'Add your first task' }),
  ).toBeDisabled()
})

it('reports no matching tasks when the filters hide every task', () => {
  renderList({ hasTodos: true })
  expect(
    screen.getByRole('heading', { name: 'No matching tasks' }),
  ).toBeVisible()
})

it('reports an unavailable list when loading failed and no tasks are known', () => {
  renderList({ failed: true })
  expect(
    screen.getByRole('heading', {
      name: 'The task list is temporarily unavailable',
    }),
  ).toBeVisible()
  expect(screen.getByText('Try again to load your tasks.')).toBeVisible()
  expect(
    screen.queryByRole('button', { name: 'Add your first task' }),
  ).not.toBeInTheDocument()
})

it('keeps showing known tasks when a refetch failed', () => {
  renderList({ todos: [todoFixture], hasTodos: true, failed: true })
  expect(screen.getAllByRole('listitem')).toHaveLength(1)
  expect(
    screen.queryByText('The task list is temporarily unavailable'),
  ).not.toBeInTheDocument()
})

it('lists the tasks in the given order', () => {
  renderList({ todos: [second, todoFixture], hasTodos: true })
  expect(
    screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent),
  ).toEqual(['Second', 'Prepare a demo'])
})

it.each([
  ['checkbox', 'Complete: Second', 'onToggle'],
  ['button', 'Edit: Second', 'onEdit'],
  ['button', 'Delete: Second', 'onDelete'],
] as const)(
  'hands the clicked task to %s "%s"',
  async (role, name, handler) => {
    const { user, ...callbacks } = renderList({
      todos: [todoFixture, second],
      hasTodos: true,
    })
    await user.click(screen.getByRole(role, { name }))
    expect(callbacks[handler]).toHaveBeenCalledWith(second)
  },
)

it('disables the actions of every task while busy', () => {
  renderList({ todos: [todoFixture, second], hasTodos: true, busy: true })
  expect(screen.getAllByRole('checkbox')).toHaveLength(2)
  for (const checkbox of screen.getAllByRole('checkbox'))
    expect(checkbox).toBeDisabled()
  for (const button of screen.getAllByRole('button'))
    expect(button).toBeDisabled()
})
