import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { useNotice } from './useNotice'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

it('starts without a notice and exposes a notification callback', () => {
  const { result } = renderHook(() => useNotice())
  expect(result.current.message).toBe('')
  expect(result.current.notify).toEqual(expect.any(Function))
})

it('shows a notified message until it expires after four seconds', () => {
  const { result } = renderHook(() => useNotice())
  act(() => result.current.notify('Task created.'))
  expect(result.current.message).toBe('Task created.')
  act(() => vi.advanceTimersByTime(3999))
  expect(result.current.message).toBe('Task created.')
  act(() => vi.advanceTimersByTime(1))
  expect(result.current.message).toBe('')
})

it('restarts the timeout when a new message arrives', () => {
  const { result } = renderHook(() => useNotice())
  act(() => result.current.notify('First'))
  act(() => vi.advanceTimersByTime(3000))
  act(() => result.current.notify('Second'))
  expect(result.current.message).toBe('Second')
  act(() => vi.advanceTimersByTime(3000))
  expect(result.current.message).toBe('Second')
  act(() => vi.advanceTimersByTime(1000))
  expect(result.current.message).toBe('')
})

it('restarts the timeout when the same message is repeated', () => {
  const { result } = renderHook(() => useNotice())
  act(() => result.current.notify('Saved'))
  act(() => vi.advanceTimersByTime(3000))
  act(() => result.current.notify('Saved'))
  act(() => vi.advanceTimersByTime(3000))
  expect(result.current.message).toBe('Saved')
})

it('keeps the notification callback stable across renders', () => {
  const { result, rerender } = renderHook(() => useNotice())
  const first = result.current.notify
  act(() => result.current.notify('Saved'))
  rerender()
  expect(result.current.notify).toBe(first)
})

it('clears the pending timeout on unmount', () => {
  const { result, unmount } = renderHook(() => useNotice())
  act(() => result.current.notify('Saved'))
  expect(vi.getTimerCount()).toBe(1)
  unmount()
  expect(vi.getTimerCount()).toBe(0)
})
