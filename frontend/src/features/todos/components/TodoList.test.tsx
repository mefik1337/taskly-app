import { render, screen } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import { TodoEmptyState } from './TodoEmptyState'
import { TodoItem } from './TodoItem'
import { TodoList } from './TodoList'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))
vi.mock('./TodoEmptyState', () => ({
  TodoEmptyState: vi.fn(() => <p>Empty task list</p>),
}))
vi.mock('./TodoItem', () => ({ TodoItem: vi.fn(() => <li>Task</li>) }))
beforeEach(() => vi.clearAllMocks())

function baseProps() {
  return {
    todos: [],
    hasTodos: false,
    failed: false,
    busy: false,
    onCreate: vi.fn(),
    onToggle: vi.fn(),
    onEdit: vi.fn(),
    onDelete: vi.fn(),
  }
}

it('shows loading feedback before showing an empty list', () => {
  const props = baseProps()
  const { rerender } = render(<TodoList {...props} loading />)
  expect(screen.getByRole('status')).toHaveTextContent('Loading your tasks…')
  expect(screen.queryByText('Empty task list')).not.toBeInTheDocument()
  rerender(<TodoList {...props} loading={false} />)
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
  expect(screen.getByText('Empty task list')).toBeVisible()
})

it('reports an unavailable list when loading failed and no tasks are known', () => {
  render(<TodoList {...baseProps()} loading={false} failed />)
  expect(
    screen.getByRole('heading', {
      name: 'The task list is temporarily unavailable',
    }),
  ).toBeVisible()
  expect(screen.getByText('Try again to load your tasks.')).toBeVisible()
  expect(TodoEmptyState).not.toHaveBeenCalled()
})

it('keeps showing known tasks when a refetch failed', () => {
  render(
    <TodoList
      {...baseProps()}
      todos={[todoFixture]}
      hasTodos
      loading={false}
      failed
    />,
  )
  expect(screen.getAllByRole('listitem')).toHaveLength(1)
  expect(
    screen.queryByText('The task list is temporarily unavailable'),
  ).not.toBeInTheDocument()
})

it('renders one item per task in order and forwards each callback with its task', () => {
  const props = baseProps()
  const second = { ...todoFixture, id: 9, title: 'Second' }
  render(
    <TodoList
      {...props}
      todos={[todoFixture, second]}
      hasTodos
      busy
      loading={false}
    />,
  )
  expect(screen.getAllByRole('listitem')).toHaveLength(2)
  const calls = vi.mocked(TodoItem).mock.calls
  expect(calls.map(([item]) => item.todo)).toEqual([todoFixture, second])
  expect(calls[0][0].busy).toBe(true)
  calls[1][0].onToggle()
  calls[1][0].onEdit()
  calls[0][0].onDelete()
  expect(props.onToggle).toHaveBeenCalledWith(second)
  expect(props.onEdit).toHaveBeenCalledWith(second)
  expect(props.onDelete).toHaveBeenCalledWith(todoFixture)
})

it('passes known-task state, busy flag and create callback to the empty state', () => {
  const props = baseProps()
  render(<TodoList {...props} hasTodos busy loading={false} />)
  expect(vi.mocked(TodoEmptyState).mock.calls[0][0]).toEqual({
    hasTodos: true,
    disabled: true,
    onCreate: props.onCreate,
  })
})
