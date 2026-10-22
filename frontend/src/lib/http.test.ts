import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { request } from './http'

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status })
}

describe('request', () => {
  it('prefixes the path with /api and sends JSON headers merged with custom ones', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ ok: true }))
    await request('/todos', {
      method: 'POST',
      body: '{}',
      headers: { 'X-Trace': 'abc' },
    })
    expect(fetchMock).toHaveBeenCalledWith('/api/todos', {
      method: 'POST',
      body: '{}',
      headers: { 'Content-Type': 'application/json', 'X-Trace': 'abc' },
    })
  })

  it('sends the JSON content type when no init is given', async () => {
    fetchMock.mockResolvedValue(jsonResponse([]))
    await request('/todos')
    expect(fetchMock).toHaveBeenCalledWith('/api/todos', {
      headers: { 'Content-Type': 'application/json' },
    })
  })

  it('resolves with the parsed JSON body of a successful response', async () => {
    fetchMock.mockResolvedValue(jsonResponse([{ id: 1 }]))
    await expect(request('/todos')).resolves.toEqual([{ id: 1 }])
  })

  it('resolves with undefined for a 204 response', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }))
    await expect(
      request('/todos/1', { method: 'DELETE' }),
    ).resolves.toBeUndefined()
  })

  it('rejects with a connection message when the network fails', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
    await expect(request('/todos')).rejects.toThrow(
      'Cannot connect to the server. Please try again.',
    )
  })

  it('rethrows the original error when the request was aborted', async () => {
    const controller = new AbortController()
    controller.abort()
    const abortError = new DOMException('Aborted', 'AbortError')
    fetchMock.mockRejectedValue(abortError)
    await expect(request('/todos', { signal: controller.signal })).rejects.toBe(
      abortError,
    )
  })

  it('rejects with a task details message for a 422 response', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: [{ msg: 'bad' }] }, 422))
    await expect(request('/todos')).rejects.toThrow(
      'Check the task details: title up to 120 characters, description up to 2000 characters, and a valid due date.',
    )
  })

  it('rejects with the server detail when it is a string', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'Task not found' }, 404))
    await expect(request('/todos/9')).rejects.toThrow('Task not found')
  })

  it('rejects with a generic message when the detail is not a string', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: { code: 1 } }, 500))
    await expect(request('/todos')).rejects.toThrow(
      'The operation failed. Please try again.',
    )
  })

  it('rejects with a generic message when the error body is not JSON', async () => {
    fetchMock.mockResolvedValue(new Response('oops', { status: 500 }))
    await expect(request('/todos')).rejects.toThrow(
      'The operation failed. Please try again.',
    )
  })
})
