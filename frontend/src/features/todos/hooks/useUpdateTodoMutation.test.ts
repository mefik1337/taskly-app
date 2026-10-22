import { act, renderHook, waitFor } from '@testing-library/react'
import { expect, it } from 'vitest'
import { installFakeApi } from '../../../test/fakeApi'
import { createTestQueryClient, queryWrapper } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import type { Todo } from '../types'
import { useUpdateTodoMutation } from './useUpdateTodoMutation'

const first: Todo = { ...todoFixture, id: 3, title: 'First' }
const last: Todo = { ...todoFixture, id: 9, title: 'Last' }

function renderUpdate(cached?: Todo[]) {
  const client = createTestQueryClient()
  if (cached) client.setQueryData(todoKeys.list, cached)
  const { result } = renderHook(() => useUpdateTodoMutation(), {
    wrapper: queryWrapper(client),
  })
  const cachedList = () => client.getQueryData<Todo[]>(todoKeys.list)
  return { result, cachedList }
}

it('resolves with the saved task changed only in the given fields', async () => {
  installFakeApi([{ ...todoFixture, description: 'Slides' }])
  const { result } = renderUpdate()
  let saved!: Todo
  await act(async () => {
    saved = await result.current.mutateAsync({
      id: 7,
      input: { completed: true },
    })
  })
  expect(saved).toMatchObject({
    id: 7,
    title: 'Prepare a demo',
    description: 'Slides',
    completed: true,
  })
})

it('replaces the saved task in the cached list keeping the order', async () => {
  installFakeApi([first, todoFixture, last])
  const { result, cachedList } = renderUpdate([first, todoFixture, last])
  await act(() =>
    result.current.mutateAsync({ id: 7, input: { completed: true } }),
  )
  expect(cachedList()).toEqual([
    first,
    expect.objectContaining({ id: 7, completed: true }),
    last,
  ])
})

it('leaves the list unloaded when none is cached', async () => {
  installFakeApi([todoFixture])
  const { result, cachedList } = renderUpdate()
  await act(() =>
    result.current.mutateAsync({ id: 7, input: { completed: true } }),
  )
  expect(cachedList()).toBeUndefined()
})

it('keeps the cache and exposes the server message when the task is gone', async () => {
  installFakeApi([])
  const { result, cachedList } = renderUpdate([todoFixture])
  await act(() =>
    expect(
      result.current.mutateAsync({ id: 7, input: { completed: true } }),
    ).rejects.toThrow('Task not found.'),
  )
  await waitFor(() =>
    expect(result.current.error?.message).toBe('Task not found.'),
  )
  expect(cachedList()).toEqual([todoFixture])
})
