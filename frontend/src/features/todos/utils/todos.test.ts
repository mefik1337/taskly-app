import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { formatDate, isOverdue, selectTodos, validateTodo } from './todos'
import type { Todo } from '../types'

const base: Todo = {
  id: 1,
  title: 'Sprint plan',
  description: '',
  priority: 'medium',
  completed: false,
  due_date: null,
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
}

describe('selectTodos', () => {
  it('combines status with a case-insensitive search in the description', () => {
    const matching = { ...base, description: 'Discuss the API' }
    const todos = [
      matching,
      { ...matching, id: 2, completed: true },
      { ...base, id: 3 },
    ]
    expect(selectTodos(todos, 'active', ' api ', 'newest')).toEqual([matching])
  })

  it('sorts by priority without changing the source array', () => {
    const high: Todo = { ...base, id: 2, priority: 'high' }
    const todos = [base, high]
    expect(selectTodos(todos, 'all', '', 'priority')).toEqual([high, base])
    expect(todos).toEqual([base, high])
  })

  it('breaks priority ties by the higher id first', () => {
    const first = { ...base, id: 4 }
    const second = { ...base, id: 9 }
    const low: Todo = { ...base, id: 10, priority: 'low' }
    expect(selectTodos([first, low, second], 'all', '', 'priority')).toEqual([
      second,
      first,
      low,
    ])
  })

  it('sorts by due date with undated tasks last and ties by higher id', () => {
    const undated = { ...base, id: 5 }
    const later = { ...base, id: 2, due_date: '2026-12-01' }
    const soonOld = { ...base, id: 3, due_date: '2026-11-01' }
    const soonNew = { ...base, id: 4, due_date: '2026-11-01' }
    expect(
      selectTodos([undated, later, soonOld, soonNew], 'all', '', 'due'),
    ).toEqual([soonNew, soonOld, later, undated])
  })

  it('sorts newest by creation time and ties by higher id', () => {
    const oldest = { ...base, id: 9, created_at: '2026-09-01T12:00:00Z' }
    const sameA = { ...base, id: 2 }
    const sameB = { ...base, id: 3 }
    const newest = { ...base, id: 1, created_at: '2026-10-02T08:00:00Z' }
    expect(
      selectTodos([oldest, sameA, newest, sameB], 'all', '', 'newest'),
    ).toEqual([newest, sameB, sameA, oldest])
  })

  it('keeps only completed tasks for the completed filter', () => {
    const done = { ...base, id: 2, completed: true }
    expect(selectTodos([base, done], 'completed', '', 'newest')).toEqual([done])
  })

  it('matches the search in the title', () => {
    const other = { ...base, id: 2, title: 'Buy milk' }
    expect(selectTodos([base, other], 'all', 'SPRINT', 'newest')).toEqual([
      base,
    ])
  })
})

describe('validateTodo', () => {
  const input = {
    title: 'Plan',
    description: '',
    priority: 'medium' as const,
    due_date: null,
    completed: false,
  }

  it('accepts a valid task without a due date', () => {
    expect(validateTodo(input)).toEqual({})
  })

  it('rejects an empty title', () => {
    expect(validateTodo({ ...input, title: '' })).toEqual({
      title: 'Enter a task title.',
    })
  })

  it('accepts a 120 character title and rejects 121 characters', () => {
    expect(validateTodo({ ...input, title: 'a'.repeat(120) })).toEqual({})
    expect(validateTodo({ ...input, title: 'a'.repeat(121) })).toEqual({
      title: 'The title must be at most 120 characters.',
    })
  })

  it('measures the title length after trimming', () => {
    expect(validateTodo({ ...input, title: `  ${'a'.repeat(120)}  ` })).toEqual(
      {},
    )
  })

  it('accepts a 2000 character description and rejects 2001 characters', () => {
    expect(validateTodo({ ...input, description: 'd'.repeat(2000) })).toEqual(
      {},
    )
    expect(validateTodo({ ...input, description: 'd'.repeat(2001) })).toEqual({
      description: 'The description must be at most 2000 characters.',
    })
  })

  it('accepts a valid calendar date', () => {
    expect(validateTodo({ ...input, due_date: '2028-02-29' })).toEqual({})
  })

  it.each(['2026-02-30', '2026-13-01', '26-01-01', '2026-1-5', 'tomorrow'])(
    'rejects the invalid due date %s',
    (due_date) => {
      expect(validateTodo({ ...input, due_date })).toEqual({
        due_date: 'Enter a valid date.',
      })
    },
  )

  it('reports every invalid field at once', () => {
    expect(
      validateTodo({
        ...input,
        title: ' ',
        description: 'd'.repeat(2001),
        due_date: 'x',
      }),
    ).toEqual({
      title: 'Enter a task title.',
      description: 'The description must be at most 2000 characters.',
      due_date: 'Enter a valid date.',
    })
  })
})

describe('isOverdue', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 9, 22, 10, 0, 0))
  })
  afterEach(() => vi.useRealTimers())

  it('is true for an active task due before today', () => {
    expect(isOverdue({ ...base, due_date: '2026-10-21' })).toBe(true)
  })

  it('is false for an active task due today or later', () => {
    expect(isOverdue({ ...base, due_date: '2026-10-22' })).toBe(false)
    expect(isOverdue({ ...base, due_date: '2026-10-23' })).toBe(false)
  })

  it('is false for a completed task due in the past', () => {
    expect(
      isOverdue({ ...base, completed: true, due_date: '2026-01-01' }),
    ).toBe(false)
  })

  it('is false for a task without a due date', () => {
    expect(isOverdue(base)).toBe(false)
  })

  it('compares with the local date when UTC has already moved to the next day', () => {
    vi.setSystemTime(new Date('2026-10-22T02:00:00Z'))
    expect(new Date().getDate()).toBe(21)
    expect(isOverdue({ ...base, due_date: '2026-10-21' })).toBe(false)
    expect(isOverdue({ ...base, due_date: '2026-10-20' })).toBe(true)
  })
})

describe('formatDate', () => {
  it('formats an ISO date as day, short month and year', () => {
    expect(formatDate('2026-03-05')).toBe('5 Mar 2026')
  })

  it('keeps the calendar day at year boundaries west of UTC', () => {
    expect(new Date(2026, 11, 31).getTimezoneOffset()).toBe(300)
    expect(formatDate('2026-12-31')).toBe('31 Dec 2026')
    expect(formatDate('2027-01-01')).toBe('1 Jan 2027')
  })
})
