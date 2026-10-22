import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createTestQueryClient, queryWrapper } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useTodosQuery } from './useTodosQuery'

vi.mock('../api/todos', () => ({
  todosApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  },
}))
beforeEach(() => vi.clearAllMocks())

it('loads tasks with an abort signal and caches them under the list key', async () => {
  vi.mocked(todosApi.list).mockResolvedValue([todoFixture])
  const client = createTestQueryClient()
  const { result } = renderHook(() => useTodosQuery(), {
    wrapper: queryWrapper(client),
  })
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(result.current.data).toEqual([todoFixture])
  expect(todosApi.list).toHaveBeenCalledWith(expect.any(AbortSignal))
  expect(client.getQueryData(todoKeys.list)).toEqual([todoFixture])
})

it('exposes the API error when loading fails', async () => {
  vi.mocked(todosApi.list).mockRejectedValue(new Error('Server down'))
  const { result } = renderHook(() => useTodosQuery(), {
    wrapper: queryWrapper(createTestQueryClient()),
  })
  await waitFor(() => expect(result.current.isError).toBe(true))
  expect(result.current.error?.message).toBe('Server down')
})
