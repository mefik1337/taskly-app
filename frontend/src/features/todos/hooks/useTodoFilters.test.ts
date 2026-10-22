import { act, renderHook } from '@testing-library/react'
import { expect, it } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import type { Todo } from '../types'
import { useTodoFilters } from './useTodoFilters'

const older: Todo = {
  ...todoFixture,
  id: 1,
  title: 'Write report',
  priority: 'high',
  created_at: '2026-09-01T12:00:00Z',
}
const newer: Todo = {
  ...todoFixture,
  id: 2,
  title: 'Buy milk',
  completed: true,
  priority: 'low',
  created_at: '2026-10-05T12:00:00Z',
}

it('starts with all tasks, an empty search and newest first', () => {
  const { result } = renderHook(() => useTodoFilters([older, newer]))
  expect(result.current.filter).toBe('all')
  expect(result.current.search).toBe('')
  expect(result.current.sort).toBe('newest')
  expect(result.current.visible).toEqual([newer, older])
})

it('narrows visible tasks by status', () => {
  const { result } = renderHook(() => useTodoFilters([older, newer]))
  act(() => result.current.setFilter('completed'))
  expect(result.current.filter).toBe('completed')
  expect(result.current.visible).toEqual([newer])
})

it('narrows visible tasks by search text', () => {
  const { result } = renderHook(() => useTodoFilters([older, newer]))
  act(() => result.current.setSearch('report'))
  expect(result.current.search).toBe('report')
  expect(result.current.visible).toEqual([older])
})

it('reorders visible tasks by the selected sort', () => {
  const { result } = renderHook(() => useTodoFilters([newer, older]))
  act(() => result.current.setSort('priority'))
  expect(result.current.sort).toBe('priority')
  expect(result.current.visible).toEqual([older, newer])
})

it('recomputes visible tasks when the source list changes', () => {
  const { result, rerender } = renderHook(
    ({ todos }) => useTodoFilters(todos),
    { initialProps: { todos: [older] } },
  )
  rerender({ todos: [older, newer] })
  expect(result.current.visible).toEqual([newer, older])
})
