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
