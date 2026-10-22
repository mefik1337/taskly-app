import { screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { renderWithProviders } from '../../../test/queryWrapper'
import { TodoEmptyState } from './TodoEmptyState'

it('invites creating the first task when there are no tasks', async () => {
  const onCreate = vi.fn()
  const { user } = renderWithProviders(
    <TodoEmptyState hasTodos={false} disabled={false} onCreate={onCreate} />,
  )
  expect(
    screen.getByRole('heading', { name: 'Add your first task' }),
  ).toBeVisible()
  expect(
    screen.getByText('Write down what you need to do and get started.'),
  ).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Add your first task' }))
  expect(onCreate).toHaveBeenCalledTimes(1)
})

it('blocks creating the first task while disabled', async () => {
  const onCreate = vi.fn()
  const { user } = renderWithProviders(
    <TodoEmptyState hasTodos={false} disabled onCreate={onCreate} />,
  )
  const button = screen.getByRole('button', { name: 'Add your first task' })
  expect(button).toBeDisabled()
  await user.click(button)
  expect(onCreate).not.toHaveBeenCalled()
})

it('reports no matching tasks without a create button when tasks exist', () => {
  renderWithProviders(
    <TodoEmptyState hasTodos disabled={false} onCreate={vi.fn()} />,
  )
  expect(
    screen.getByRole('heading', { name: 'No matching tasks' }),
  ).toBeVisible()
  expect(
    screen.getByText('Change the status filter or search to find your tasks.'),
  ).toBeVisible()
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
})
