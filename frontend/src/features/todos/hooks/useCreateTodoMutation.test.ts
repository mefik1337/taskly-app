import { act, renderHook, waitFor } from '@testing-library/react'
import { expect, it } from 'vitest'
import { installFakeApi } from '../../../test/fakeApi'
import { createTestQueryClient, queryWrapper } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import type { Todo, TodoInput } from '../types'
import { useCreateTodoMutation } from './useCreateTodoMutation'
import { useTodosQuery } from './useTodosQuery'

const input: TodoInput = {
  title: 'Buy milk',
  description: 'Two litres',
  priority: 'high',
  due_date: '2026-11-02',
  completed: false,
}
const older: Todo = { ...todoFixture, id: 3, title: 'Older' }

function renderCreate(cached?: Todo[]) {
  const client = createTestQueryClient()
  if (cached) client.setQueryData(todoKeys.list, cached)
  const { result } = renderHook(() => useCreateTodoMutation(), {
    wrapper: queryWrapper(client),
  })
  const cachedList = () => client.getQueryData<Todo[]>(todoKeys.list)
  async function create() {
    let created!: Todo
    await act(async () => {
      created = await result.current.mutateAsync(input)
    })
    return created
  }
  return { result, cachedList, create }
}

it('prepends the created task to the cached list', async () => {
  installFakeApi([older])
  const { cachedList, create } = renderCreate([older])
  const created = await create()
  expect(cachedList()).toEqual([created, older])
})

it('replaces a cached copy of the created task instead of duplicating it', async () => {
  installFakeApi([older], { nextId: 40 })
  const stale = { ...todoFixture, id: 40, title: 'Stale copy' }
  const { cachedList, create } = renderCreate([stale, older])
  const created = await create()
  expect(cachedList()).toEqual([created, older])
})

it('starts the cached list when none is loaded yet', async () => {
  installFakeApi()
  const { cachedList, create } = renderCreate()
  const created = await create()
  expect(cachedList()).toEqual([created])
})

it('keeps the cache and exposes the server message when creation fails', async () => {
  const api = installFakeApi([older])
  api.failNext('POST', 500, 'Database unavailable')
  const { result, cachedList } = renderCreate([older])
  await act(() =>
    expect(result.current.mutateAsync(input)).rejects.toThrow(
      'Database unavailable',
    ),
  )
  await waitFor(() =>
    expect(result.current.error?.message).toBe('Database unavailable'),
  )
  expect(cachedList()).toEqual([older])
})

it('keeps the created task when an older list request finishes afterwards', async () => {
  const api = installFakeApi([older])
  const { result } = renderHook(
    () => ({ list: useTodosQuery(), create: useCreateTodoMutation() }),
    { wrapper: queryWrapper(createTestQueryClient()) },
  )
  await waitFor(() => expect(result.current.list.data).toEqual([older]))
  const release = api.delayNextResponse('GET')
  act(() => void result.current.list.refetch())
  await waitFor(() => expect(api.requestsTo('GET')).toHaveLength(2))
  let created!: Todo
  await act(async () => {
    created = await result.current.create.mutateAsync(input)
  })
  await act(async () => release())
  await waitFor(() => expect(result.current.list.isFetching).toBe(false))
  expect(result.current.list.data).toEqual([created, older])
})
