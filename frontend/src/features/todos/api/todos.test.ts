import { expect, it } from 'vitest'
import { installFakeApi } from '../../../test/fakeApi'
import { todoFixture } from '../../../test/todoFixture'
import { todosApi } from './todos'

it('loads the task list with GET /api/todos', async () => {
  const api = installFakeApi([todoFixture])
  await expect(todosApi.list()).resolves.toEqual([todoFixture])
  expect(api.requests).toEqual([
    { method: 'GET', url: '/api/todos', body: undefined, signal: undefined },
  ])
})

it('hands the abort signal to the list request', async () => {
  const api = installFakeApi()
  const controller = new AbortController()
  await todosApi.list(controller.signal)
  expect(api.requests[0].signal).toBe(controller.signal)
})

it('creates a task with POST /api/todos sending only writable fields', async () => {
  const api = installFakeApi()
  await expect(todosApi.create(todoFixture)).resolves.toMatchObject({
    title: 'Prepare a demo',
    priority: 'medium',
  })
  expect(api.requests).toEqual([
    {
      method: 'POST',
      url: '/api/todos',
      body: {
        title: 'Prepare a demo',
        description: '',
        priority: 'medium',
        due_date: null,
        completed: false,
      },
      signal: undefined,
    },
  ])
})

it('patches a task by id sending only writable fields', async () => {
  const api = installFakeApi([todoFixture])
  await expect(
    todosApi.update(7, { ...todoFixture, completed: true }),
  ).resolves.toMatchObject({ id: 7, completed: true })
  expect(api.requests[0]).toMatchObject({
    method: 'PATCH',
    url: '/api/todos/7',
  })
  expect(api.requests[0].body).toEqual({
    title: 'Prepare a demo',
    description: '',
    priority: 'medium',
    due_date: null,
    completed: true,
  })
})

it('patches only the fields given in a partial update', async () => {
  const api = installFakeApi([{ ...todoFixture, id: 3 }])
  await todosApi.update(3, { completed: false })
  expect(api.requests[0]).toMatchObject({
    method: 'PATCH',
    url: '/api/todos/3',
  })
  expect(api.requests[0].body).toEqual({ completed: false })
})

it('deletes a task by id with DELETE and resolves without a body', async () => {
  const other = { ...todoFixture, id: 3, title: 'Other' }
  const api = installFakeApi([todoFixture, other])
  await expect(todosApi.remove(7)).resolves.toBeUndefined()
  expect(api.requests[0]).toMatchObject({
    method: 'DELETE',
    url: '/api/todos/7',
    body: undefined,
  })
  await expect(todosApi.list()).resolves.toEqual([other])
})
