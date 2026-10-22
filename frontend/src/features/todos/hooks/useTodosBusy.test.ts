import { act, renderHook, waitFor } from '@testing-library/react'
import { expect, it } from 'vitest'
import { installFakeApi, type Method } from '../../../test/fakeApi'
import { createTestQueryClient, queryWrapper } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import { useCreateTodoMutation } from './useCreateTodoMutation'
import { useDeleteTodoMutation } from './useDeleteTodoMutation'
import { useTodosBusy } from './useTodosBusy'
import { useTodosQuery } from './useTodosQuery'
import { useUpdateTodoMutation } from './useUpdateTodoMutation'

function renderBusy() {
  return renderHook(
    () => ({
      busy: useTodosBusy(),
      create: useCreateTodoMutation(),
      update: useUpdateTodoMutation(),
      remove: useDeleteTodoMutation(),
    }),
    { wrapper: queryWrapper(createTestQueryClient()) },
  ).result
}

type Hooks = ReturnType<typeof renderBusy>['current']

it('is idle while no task is being saved', () => {
  installFakeApi([todoFixture])
  expect(renderBusy().current.busy).toBe(false)
})

it.each<[string, Method, (hooks: Hooks) => void]>([
  ['created', 'POST', (hooks) => hooks.create.mutate(todoFixture)],
  [
    'updated',
    'PATCH',
    (hooks) => hooks.update.mutate({ id: 7, input: { completed: true } }),
  ],
  ['deleted', 'DELETE', (hooks) => hooks.remove.mutate(7)],
])(
  'is busy while a task is being %s and idle once the server answers',
  async (_, method, start) => {
    const api = installFakeApi([todoFixture])
    const release = api.delayNextResponse(method)
    const result = renderBusy()
    act(() => start(result.current))
    await waitFor(() => expect(result.current.busy).toBe(true))
    act(() => release())
    await waitFor(() => expect(result.current.busy).toBe(false))
  },
)

it('stays idle while the task list is loading', async () => {
  const api = installFakeApi([todoFixture])
  const release = api.delayNextResponse('GET')
  const { result } = renderHook(
    () => ({ busy: useTodosBusy(), list: useTodosQuery() }),
    { wrapper: queryWrapper(createTestQueryClient()) },
  )
  await waitFor(() => expect(api.requests).toHaveLength(1))
  expect(result.current.list.isFetching).toBe(true)
  expect(result.current.busy).toBe(false)
  act(() => release())
})
