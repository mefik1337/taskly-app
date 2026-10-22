import { screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { renderWithProviders } from '../../../test/queryWrapper'
import type { Filter, Sort } from '../types'
import { TodoFilters } from './TodoFilters'

function renderFilters(
  values: { filter?: Filter; search?: string; sort?: Sort } = {},
) {
  const callbacks = {
    onFilterChange: vi.fn(),
    onSearchChange: vi.fn(),
    onSortChange: vi.fn(),
  }
  const { user } = renderWithProviders(
    <TodoFilters
      filter={values.filter ?? 'all'}
      search={values.search ?? ''}
      sort={values.sort ?? 'newest'}
      {...callbacks}
    />,
  )
  return { user, ...callbacks }
}

it('shows the current search, status and sort order', () => {
  renderFilters({ filter: 'completed', search: 'demo', sort: 'due' })
  expect(screen.getByLabelText('Search tasks')).toHaveValue('demo')
  expect(screen.getByLabelText('Status')).toHaveValue('completed')
  expect(screen.getByLabelText('Sort by')).toHaveValue('due')
})

it('reports typed search text', async () => {
  const { user, onSearchChange } = renderFilters()
  await user.type(screen.getByLabelText('Search tasks'), 'm')
  expect(onSearchChange).toHaveBeenCalledWith('m')
})

it('reports the chosen status', async () => {
  const { user, onFilterChange } = renderFilters()
  await user.selectOptions(screen.getByLabelText('Status'), 'To do')
  expect(onFilterChange).toHaveBeenCalledWith('active')
})

it('reports the chosen sort order', async () => {
  const { user, onSortChange } = renderFilters()
  await user.selectOptions(screen.getByLabelText('Sort by'), 'Due date')
  expect(onSortChange).toHaveBeenCalledWith('due')
})
