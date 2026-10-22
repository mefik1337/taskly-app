import { act, renderHook, waitFor } from '@testing-library/react'
import { expect, it } from 'vitest'
import { installFakeApi } from '../../../test/fakeApi'
import { createTestQueryClient, queryWrapper } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import type { Todo } from '../types'
import { useClearCompletedMutation } from './useClearCompletedMutation'
import { useTodosQuery } from './useTodosQuery'

const active: Todo = { ...todoFixture, id: 3, title: 'Other' }
const done: Todo = { ...todoFixture, id: 4, title: 'Done', completed: true }

function renderClear(cached?: Todo[]) {
  const client = createTestQueryClient()
  if (cached) client.setQueryData(todoKeys.list, cached)
  const { result } = renderHook(() => useClearCompletedMutation(), {
    wrapper: queryWrapper(client),
  })
  const cachedList = () => client.getQueryData<Todo[]>(todoKeys.list)
  return { result, cachedList }
}

it('removes only completed tasks from the cached list', async () => {
  installFakeApi([active, done])
  const { result, cachedList } = renderClear([active, done])
  await act(() => result.current.mutateAsync())
  expect(cachedList()).toEqual([active])
})

it('leaves the list unloaded when none is cached', async () => {
  installFakeApi([active, done])
  const { result, cachedList } = renderClear()
  await act(() => result.current.mutateAsync())
  expect(cachedList()).toBeUndefined()
})

it('keeps the cached list and exposes the server message on failure', async () => {
  const api = installFakeApi([active, done])
  api.failNext('DELETE', 500, 'Could not clear tasks.')
  const { result, cachedList } = renderClear([active, done])
  await act(() =>
    expect(result.current.mutateAsync()).rejects.toThrow(
      'Could not clear tasks.',
    ),
  )
  await waitFor(() =>
    expect(result.current.error?.message).toBe('Could not clear tasks.'),
  )
  expect(cachedList()).toEqual([active, done])
})

it('keeps cleared tasks gone when an older list request finishes afterwards', async () => {
  const api = installFakeApi([active, done])
  const { result } = renderHook(
    () => ({ list: useTodosQuery(), clear: useClearCompletedMutation() }),
    { wrapper: queryWrapper(createTestQueryClient()) },
  )
  await waitFor(() => expect(result.current.list.data).toEqual([active, done]))
  const release = api.delayNextResponse('GET')
  act(() => void result.current.list.refetch())
  await waitFor(() => expect(api.requestsTo('GET')).toHaveLength(2))
  await act(() => result.current.clear.mutateAsync())
  await act(async () => release())
  await waitFor(() => expect(result.current.list.isFetching).toBe(false))
  expect(result.current.list.data).toEqual([active])
})
