import { act, renderHook, waitFor } from '@testing-library/react'
import { expect, it } from 'vitest'
import { installFakeApi } from '../../../test/fakeApi'
import { createTestQueryClient, queryWrapper } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import type { Todo } from '../types'
import { useDeleteTodoMutation } from './useDeleteTodoMutation'

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

it('removes the task on the server so a reload no longer lists it', async () => {
  installFakeApi([todoFixture, other])
  const { result } = renderDelete([todoFixture, other])
  await act(() => result.current.mutateAsync(7))
  await expect(todosApi.list()).resolves.toEqual([other])
})

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
