import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createTestQueryClient, queryWrapper } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import type { Todo } from '../types'
import { useCreateTodoMutation } from './useCreateTodoMutation'

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
  const { result } = renderHook(() => useCreateTodoMutation(), {
    wrapper: queryWrapper(client),
  })
  return { client, result }
}

it('sends the input to the API', async () => {
  vi.mocked(todosApi.create).mockResolvedValue(todoFixture)
  const { result } = setup([])
  await act(() => result.current.mutateAsync(todoFixture))
  expect(todosApi.create).toHaveBeenCalledWith(todoFixture)
})

it('prepends the saved task to the cached list', async () => {
  const older = { ...todoFixture, id: 3, title: 'Older' }
  const saved = { ...todoFixture, id: 8, title: 'Saved' }
  vi.mocked(todosApi.create).mockResolvedValue(saved)
  const { client, result } = setup([older])
  await act(() => result.current.mutateAsync(saved))
  expect(client.getQueryData(todoKeys.list)).toEqual([saved, older])
})

it('replaces a cached copy of the saved task instead of duplicating it', async () => {
  const stale = { ...todoFixture, id: 8, title: 'Stale' }
  const other = { ...todoFixture, id: 3 }
  const saved = { ...todoFixture, id: 8, title: 'Saved' }
  vi.mocked(todosApi.create).mockResolvedValue(saved)
  const { client, result } = setup([stale, other])
  await act(() => result.current.mutateAsync(saved))
  expect(client.getQueryData(todoKeys.list)).toEqual([saved, other])
})

it('creates the cached list when none is loaded yet', async () => {
  vi.mocked(todosApi.create).mockResolvedValue(todoFixture)
  const { client, result } = setup()
  await act(() => result.current.mutateAsync(todoFixture))
  expect(client.getQueryData(todoKeys.list)).toEqual([todoFixture])
})

it('leaves the cache untouched and rejects when the API fails', async () => {
  vi.mocked(todosApi.create).mockRejectedValue(new Error('Server down'))
  const { client, result } = setup([todoFixture])
  await act(() =>
    expect(result.current.mutateAsync(todoFixture)).rejects.toThrow(
      'Server down',
    ),
  )
  expect(client.getQueryData(todoKeys.list)).toEqual([todoFixture])
})

it('registers under the create mutation key', async () => {
  vi.mocked(todosApi.create).mockResolvedValue(todoFixture)
  const { client, result } = setup([])
  await act(() => result.current.mutateAsync(todoFixture))
  expect(
    client.getMutationCache().findAll({ mutationKey: todoKeys.create }),
  ).toHaveLength(1)
})
