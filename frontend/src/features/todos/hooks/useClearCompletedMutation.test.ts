import { act, renderHook, waitFor } from '@testing-library/react'
import { expect, it } from 'vitest'
import { installFakeApi } from '../../../test/fakeApi'
import { createTestQueryClient, queryWrapper } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import type { Todo } from '../types'
import { useClearCompletedMutation } from './useClearCompletedMutation'

const active: Todo = { ...todoFixture, id: 3, title: 'Other' }
const done: Todo = { ...todoFixture, id: 4, title: 'Done', completed: true }
const doneToo: Todo = { ...done, id: 5, title: 'Done too' }

function renderClear(cached?: Todo[]) {
  const client = createTestQueryClient()
  if (cached) client.setQueryData(todoKeys.list, cached)
  const { result } = renderHook(() => useClearCompletedMutation(), {
    wrapper: queryWrapper(client),
  })
  const cachedList = () => client.getQueryData<Todo[]>(todoKeys.list)
  return { result, cachedList }
}

it('resolves with the number of removed tasks', async () => {
  installFakeApi([active, done, doneToo])
  const { result } = renderClear([active, done, doneToo])
  await expect(act(() => result.current.mutateAsync())).resolves.toEqual({
    deleted: 2,
  })
})

it('removes only completed tasks from the cached list and the server', async () => {
  installFakeApi([active, done])
  const { result, cachedList } = renderClear([active, done])
  await act(() => result.current.mutateAsync())
  expect(cachedList()).toEqual([active])
  await expect(todosApi.list()).resolves.toEqual([active])
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
