import { vi } from 'vitest'
import type { Todo } from '../features/todos/types'

export type Method = 'GET' | 'POST' | 'PATCH' | 'DELETE'

export interface RecordedRequest {
  method: Method
  url: string
  body: unknown
  signal: AbortSignal | undefined
}

interface Failure {
  status: number
  detail?: unknown
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export function installFakeApi(
  initialTodos: Todo[] = [],
  options: { nextId?: number } = {},
) {
  let todos = initialTodos.map((todo) => ({ ...todo }))
  let nextId =
    options.nextId ?? Math.max(0, ...todos.map((todo) => todo.id)) + 1
  const requests: RecordedRequest[] = []
  const failures: Record<Method, Failure[]> = {
    GET: [],
    POST: [],
    PATCH: [],
    DELETE: [],
  }
  const delayedResponses: Record<Method, Promise<void>[]> = {
    GET: [],
    POST: [],
    PATCH: [],
    DELETE: [],
  }

  function route(method: Method, url: string, body: unknown): Response {
    if (method === 'DELETE' && url === '/api/todos/completed') {
      const deleted = todos.filter((todo) => todo.completed).length
      todos = todos.filter((todo) => !todo.completed)
      return json({ deleted })
    }
    const match = /^\/api\/todos(?:\/(\d+))?$/.exec(url)
    if (!match) return json({ detail: 'Not Found' }, 404)
    const now = new Date().toISOString()
    if (!match[1]) {
      if (method === 'GET') return json(todos)
      if (method === 'POST') {
        const created = {
          ...(body as object),
          id: nextId++,
          created_at: now,
          updated_at: now,
        } as Todo
        todos = [created, ...todos]
        return json(created, 201)
      }
      return json({ detail: 'Method Not Allowed' }, 405)
    }
    const id = Number(match[1])
    const existing = todos.find((todo) => todo.id === id)
    if (!existing) return json({ detail: 'Task not found.' }, 404)
    if (method === 'PATCH') {
      const saved = { ...existing, ...(body as object), updated_at: now }
      todos = todos.map((todo) => (todo.id === id ? saved : todo))
      return json(saved)
    }
    if (method === 'DELETE') {
      todos = todos.filter((todo) => todo.id !== id)
      return new Response(null, { status: 204 })
    }
    return json({ detail: 'Method Not Allowed' }, 405)
  }

  const fetchFake = vi.fn(
    async (input: RequestInfo | URL, init: RequestInit = {}) => {
      const method = (init.method ?? 'GET') as Method
      const url = String(input)
      const body =
        typeof init.body === 'string' ? JSON.parse(init.body) : undefined
      requests.push({ method, url, body, signal: init.signal ?? undefined })
      const failure = failures[method].shift()
      const response = failure
        ? json({ detail: failure.detail }, failure.status)
        : route(method, url, body)
      await delayedResponses[method].shift()
      return response
    },
  )
  vi.stubGlobal('fetch', fetchFake)

  return {
    requests,
    requestsTo(method: Method) {
      return requests.filter((request) => request.method === method)
    },
    failNext(method: Method, status: number, detail?: unknown) {
      failures[method].push({ status, detail })
    },
    delayNextResponse(method: Method) {
      let release!: () => void
      delayedResponses[method].push(
        new Promise<void>((resolve) => {
          release = resolve
        }),
      )
      return release
    },
  }
}
