import { act, renderHook, waitFor } from '@testing-library/react'
import { expect, it } from 'vitest'
import { installFakeApi } from '../../../test/fakeApi'
import { createTestQueryClient, queryWrapper } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import type { Todo } from '../types'
import { useDeleteTodoMutation } from './useDeleteTodoMutation'
import { useTodosQuery } from './useTodosQuery'

const other: Todo = { ...todoFixture, id: 3, title: 'Other' }

function renderDelete(cached?: Todo[]) {
  const client = createTestQueryClient()
  if (cached) client.setQueryData(todoKeys.list, cached)
  const { result } = renderHook(() => useDeleteTodoMutation(), {
    wrapper: queryWrapper(client),
  })
  const cachedList = () => client.getQueryData<Todo[]>(todoKeys.list)
  return { result, cachedList }
}

it('removes only the deleted task from the cached list', async () => {
  installFakeApi([todoFixture, other])
  const { result, cachedList } = renderDelete([todoFixture, other])
  await act(() => result.current.mutateAsync(7))
  expect(cachedList()).toEqual([other])
})

it('leaves the list unloaded when none is cached', async () => {
  installFakeApi([todoFixture])
  const { result, cachedList } = renderDelete()
  await act(() => result.current.mutateAsync(7))
  expect(cachedList()).toBeUndefined()
})

it('keeps the task cached and exposes the server message when the task is already gone', async () => {
  installFakeApi([])
  const { result, cachedList } = renderDelete([todoFixture])
  await act(() =>
    expect(result.current.mutateAsync(7)).rejects.toThrow('Task not found.'),
  )
  await waitFor(() =>
    expect(result.current.error?.message).toBe('Task not found.'),
  )
  expect(cachedList()).toEqual([todoFixture])
})

it('keeps the task deleted when an older list request finishes afterwards', async () => {
  const api = installFakeApi([todoFixture, other])
  const { result } = renderHook(
    () => ({ list: useTodosQuery(), remove: useDeleteTodoMutation() }),
    { wrapper: queryWrapper(createTestQueryClient()) },
  )
  await waitFor(() =>
    expect(result.current.list.data).toEqual([todoFixture, other]),
  )
  const release = api.delayNextResponse('GET')
  act(() => void result.current.list.refetch())
  await waitFor(() => expect(api.requestsTo('GET')).toHaveLength(2))
  await act(() => result.current.remove.mutateAsync(7))
  await act(async () => release())
  await waitFor(() => expect(result.current.list.isFetching).toBe(false))
  expect(result.current.list.data).toEqual([other])
})
