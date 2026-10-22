import { screen, within } from '@testing-library/react'
import { expect, it } from 'vitest'
import { renderWithProviders } from '../test/queryWrapper'
import { ApplicationHeader } from './ApplicationHeader'

it('links the Taskly title to the home page', () => {
  renderWithProviders(<ApplicationHeader />)
  const link = within(screen.getByRole('banner')).getByRole('link', {
    name: 'Taskly — home',
  })
  expect(link).toHaveAttribute('href', '/')
  expect(
    within(link).getByRole('heading', { level: 2, name: 'Taskly' }),
  ).toBeVisible()
})

it('describes the application as a task list', () => {
  renderWithProviders(<ApplicationHeader />)
  expect(
    within(screen.getByRole('banner')).getByText('Task list'),
  ).toBeVisible()
})
