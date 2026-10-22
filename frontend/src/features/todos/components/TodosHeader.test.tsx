import { screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { renderWithProviders } from '../../../test/queryWrapper'
import { TodosHeader } from './TodosHeader'

it('introduces the tasks page', () => {
  renderWithProviders(<TodosHeader disabled={false} onCreate={vi.fn()} />)
  expect(screen.getByRole('heading', { level: 1, name: 'Tasks' })).toBeVisible()
  expect(
    screen.getByText('Create, organize, and complete tasks.'),
  ).toBeVisible()
})

it('starts task creation from New task', async () => {
  const onCreate = vi.fn()
  const { user } = renderWithProviders(
    <TodosHeader disabled={false} onCreate={onCreate} />,
  )
  await user.click(screen.getByRole('button', { name: 'New task' }))
  expect(onCreate).toHaveBeenCalledTimes(1)
})

it('blocks New task while disabled', async () => {
  const onCreate = vi.fn()
  const { user } = renderWithProviders(
    <TodosHeader disabled onCreate={onCreate} />,
  )
  const button = screen.getByRole('button', { name: 'New task' })
  expect(button).toBeDisabled()
  await user.click(button)
  expect(onCreate).not.toHaveBeenCalled()
})

it('offers Clear completed with the count and triggers it', async () => {
  const onClear = vi.fn()
  const { user } = renderWithProviders(
    <TodosHeader
      disabled={false}
      completedCount={2}
      onCreate={vi.fn()}
      onClearCompleted={onClear}
    />,
  )
  await user.click(screen.getByRole('button', { name: 'Clear completed (2)' }))
  expect(onClear).toHaveBeenCalledTimes(1)
})

it('hides Clear completed when no task is completed', () => {
  renderWithProviders(
    <TodosHeader
      disabled={false}
      completedCount={0}
      onCreate={vi.fn()}
      onClearCompleted={vi.fn()}
    />,
  )
  expect(screen.queryByRole('button', { name: /Clear completed/ })).toBeNull()
})

it('hides Clear completed without a handler', () => {
  renderWithProviders(
    <TodosHeader disabled={false} completedCount={2} onCreate={vi.fn()} />,
  )
  expect(screen.queryByRole('button', { name: /Clear completed/ })).toBeNull()
})

it('blocks Clear completed while disabled', () => {
  renderWithProviders(
    <TodosHeader
      disabled
      completedCount={1}
      onCreate={vi.fn()}
      onClearCompleted={vi.fn()}
    />,
  )
  expect(
    screen.getByRole('button', { name: 'Clear completed (1)' }),
  ).toBeDisabled()
})
