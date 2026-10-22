import { useMutation } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { expect, it } from 'vitest'
import { createTestQueryClient, queryWrapper } from '../../../test/queryWrapper'
import { todoKeys } from '../api/queryKeys'
import { useTodosBusy } from './useTodosBusy'

function renderWithMutation(mutationKey: readonly string[]) {
  let resolve: () => void = () => {}
  const pending = new Promise<void>((done) => {
    resolve = done
  })
  const { result } = renderHook(
    () => ({
      busy: useTodosBusy(),
      mutation: useMutation({ mutationKey, mutationFn: () => pending }),
    }),
    { wrapper: queryWrapper(createTestQueryClient()) },
  )
  return { result, resolve }
}

it('is idle when no mutation runs', () => {
  const { result } = renderWithMutation(todoKeys.create)
  expect(result.current.busy).toBe(false)
})

it.each([
  { name: 'create', key: todoKeys.create },
  { name: 'update', key: todoKeys.update },
  { name: 'delete', key: todoKeys.delete },
])(
  'is busy while a $name mutation is pending and idle once it settles',
  async ({ key }) => {
    const { result, resolve } = renderWithMutation(key)
    act(() => result.current.mutation.mutate())
    await waitFor(() => expect(result.current.busy).toBe(true))
    act(() => resolve())
    await waitFor(() => expect(result.current.busy).toBe(false))
  },
)

it('ignores mutations outside the tasks key', async () => {
  const { result, resolve } = renderWithMutation(['profile', 'update'])
  act(() => result.current.mutation.mutate())
  await waitFor(() => expect(result.current.mutation.isPending).toBe(true))
  expect(result.current.busy).toBe(false)
  act(() => resolve())
})
