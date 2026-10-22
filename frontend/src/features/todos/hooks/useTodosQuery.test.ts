import { act, renderHook, waitFor } from '@testing-library/react'
import { expect, it } from 'vitest'
import { installFakeApi } from '../../../test/fakeApi'
import { createTestQueryClient, queryWrapper } from '../../../test/queryWrapper'
import { todoFixture } from '../../../test/todoFixture'
import { useTodosQuery } from './useTodosQuery'

function renderQuery() {
  const client = createTestQueryClient()
  const { result } = renderHook(() => useTodosQuery(), {
    wrapper: queryWrapper(client),
  })
  return { client, result }
}

it('loads the tasks from GET /api/todos', async () => {
  const api = installFakeApi([todoFixture])
  const { result } = renderQuery()
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(result.current.data).toEqual([todoFixture])
  expect(api.requests).toMatchObject([{ method: 'GET', url: '/api/todos' }])
})

it('exposes the server message when loading fails', async () => {
  const api = installFakeApi()
  api.failNext('GET', 503, 'The server is unavailable.')
  const { result } = renderQuery()
  await waitFor(() => expect(result.current.isError).toBe(true))
  expect(result.current.error?.message).toBe('The server is unavailable.')
})

it('aborts the request when the query is cancelled', async () => {
  const api = installFakeApi([todoFixture])
  const release = api.delayNextResponse('GET')
  const { client } = renderQuery()
  await waitFor(() => expect(api.requests).toHaveLength(1))
  await act(() => client.cancelQueries())
  expect(api.requests[0].signal?.aborted).toBe(true)
  release()
})
