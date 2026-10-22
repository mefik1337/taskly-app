import { screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { renderWithProviders } from '../test/queryWrapper'
import { SuccessNotice } from './SuccessNotice'

it('shows nothing without a message', () => {
  renderWithProviders(<SuccessNotice message="" />)
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
})

it('announces the message as a status', () => {
  renderWithProviders(<SuccessNotice message="Task created." />)
  expect(screen.getByRole('status')).toHaveTextContent('Task created.')
})

it('replaces the previous message with the new one', () => {
  const { rerender } = renderWithProviders(
    <SuccessNotice message="Task created." />,
  )
  rerender(<SuccessNotice message="Task deleted." />)
  expect(screen.getByRole('status')).toHaveTextContent('Task deleted.')
  expect(screen.queryByText('Task created.')).not.toBeInTheDocument()
})

it('removes the notice when the message is cleared', () => {
  const { rerender } = renderWithProviders(
    <SuccessNotice message="Task created." />,
  )
  rerender(<SuccessNotice message="" />)
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
})
