import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createTestQueryClient, queryWrapper } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import type { Todo } from '../types'
import { useDeleteTodoMutation } from './useDeleteTodoMutation'

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
  const { result } = renderHook(() => useDeleteTodoMutation(), {
    wrapper: queryWrapper(client),
  })
  return { client, result }
}

it('deletes the task by id through the API', async () => {
  vi.mocked(todosApi.remove).mockResolvedValue(undefined)
  const { result } = setup([todoFixture])
  await act(() => result.current.mutateAsync(7))
  expect(todosApi.remove).toHaveBeenCalledWith(7)
})

it('removes only the deleted task from the cached list', async () => {
  const other = { ...todoFixture, id: 3 }
  vi.mocked(todosApi.remove).mockResolvedValue(undefined)
  const { client, result } = setup([todoFixture, other])
  await act(() => result.current.mutateAsync(todoFixture.id))
  expect(client.getQueryData(todoKeys.list)).toEqual([other])
})

it('keeps the cache empty when no list is loaded', async () => {
  vi.mocked(todosApi.remove).mockResolvedValue(undefined)
  const { client, result } = setup()
  await act(() => result.current.mutateAsync(7))
  expect(client.getQueryData(todoKeys.list)).toBeUndefined()
})

it('keeps the task cached and rejects when the API fails', async () => {
  vi.mocked(todosApi.remove).mockRejectedValue(new Error('Cannot delete'))
  const { client, result } = setup([todoFixture])
  await act(() =>
    expect(result.current.mutateAsync(7)).rejects.toThrow('Cannot delete'),
  )
  expect(client.getQueryData(todoKeys.list)).toEqual([todoFixture])
})

it('registers under the delete mutation key', async () => {
  vi.mocked(todosApi.remove).mockResolvedValue(undefined)
  const { client, result } = setup([])
  await act(() => result.current.mutateAsync(7))
  expect(
    client.getMutationCache().findAll({ mutationKey: todoKeys.delete }),
  ).toHaveLength(1)
})
