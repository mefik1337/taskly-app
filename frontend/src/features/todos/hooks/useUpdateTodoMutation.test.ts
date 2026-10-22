import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createTestQueryClient, queryWrapper } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import type { Todo } from '../types'
import { useUpdateTodoMutation } from './useUpdateTodoMutation'

vi.mock('../api/todos', () => ({
  todosApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  },
}))
beforeEach(() => vi.clearAllMocks())

function setup(initial?: Todo[]) {
  const client = createTestQueryClient()
  if (initial) client.setQueryData(todoKeys.list, initial)
  const { result } = renderHook(() => useUpdateTodoMutation(), {
    wrapper: queryWrapper(client),
  })
  return { client, result }
}

it('sends the id and partial input to the API', async () => {
  vi.mocked(todosApi.update).mockResolvedValue(todoFixture)
  const { result } = setup([todoFixture])
  await act(() =>
    result.current.mutateAsync({ id: 7, input: { completed: true } }),
  )
  expect(todosApi.update).toHaveBeenCalledWith(7, { completed: true })
})

it('replaces the saved task in the cached list keeping the order', async () => {
  const first = { ...todoFixture, id: 3 }
  const last = { ...todoFixture, id: 9 }
  const saved = { ...todoFixture, completed: true }
  vi.mocked(todosApi.update).mockResolvedValue(saved)
  const { client, result } = setup([first, todoFixture, last])
  await act(() =>
    result.current.mutateAsync({ id: 7, input: { completed: true } }),
  )
  expect(client.getQueryData(todoKeys.list)).toEqual([first, saved, last])
})

it('keeps the cache empty when no list is loaded', async () => {
  vi.mocked(todosApi.update).mockResolvedValue(todoFixture)
  const { client, result } = setup()
  await act(() => result.current.mutateAsync({ id: 7, input: {} }))
  expect(client.getQueryData(todoKeys.list)).toBeUndefined()
})

it('leaves the cache untouched and rejects when the API fails', async () => {
  vi.mocked(todosApi.update).mockRejectedValue(new Error('Cannot save'))
  const { client, result } = setup([todoFixture])
  await act(() =>
    expect(
      result.current.mutateAsync({ id: 7, input: { completed: true } }),
    ).rejects.toThrow('Cannot save'),
  )
  expect(client.getQueryData(todoKeys.list)).toEqual([todoFixture])
})

it('registers under the update mutation key', async () => {
  vi.mocked(todosApi.update).mockResolvedValue(todoFixture)
  const { client, result } = setup([])
  await act(() => result.current.mutateAsync({ id: 7, input: {} }))
  expect(
    client.getMutationCache().findAll({ mutationKey: todoKeys.update }),
  ).toHaveLength(1)
})
