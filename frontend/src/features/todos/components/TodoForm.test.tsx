import { screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { renderWithProviders } from '../../../test/queryWrapper'
import type { TodoInput } from '../types'
import { TodoForm } from './TodoForm'

function renderForm(
  props: Partial<{
    initial: TodoInput
    busy: boolean
    error: string | null
  }> = {},
) {
  const onSubmit = vi.fn().mockResolvedValue(undefined)
  const onCancel = vi.fn()
  const { user } = renderWithProviders(
    <TodoForm
      busy={false}
      error={null}
      {...props}
      onSubmit={onSubmit}
      onCancel={onCancel}
    />,
  )
  return { user, onSubmit, onCancel }
}

const existing: TodoInput = {
  title: 'Existing',
  description: 'Notes',
  priority: 'low',
  due_date: '2026-11-15',
  completed: true,
}

it('focuses the title field', () => {
  renderForm()
  expect(screen.getByLabelText('Task title *')).toHaveFocus()
})

it('rejects a whitespace-only title without submitting', async () => {
  const { user, onSubmit } = renderForm()
  await user.type(screen.getByLabelText('Task title *'), '   ')
  await user.click(screen.getByRole('button', { name: 'Save task' }))
  expect(screen.getByText('Enter a task title.')).toBeVisible()
  expect(onSubmit).not.toHaveBeenCalled()
})

it('describes a validation error on the invalid field', async () => {
  const { user } = renderForm()
  const title = screen.getByLabelText('Task title *')
  expect(title).not.toHaveAccessibleDescription()
  await user.click(screen.getByRole('button', { name: 'Save task' }))
  expect(title).toBeInvalid()
  expect(title).toHaveAccessibleDescription('Enter a task title.')
})

it('rejects a title longer than 120 characters without submitting', async () => {
  const { user, onSubmit } = renderForm({
    initial: { ...existing, title: 'a'.repeat(121) },
  })
  await user.click(screen.getByRole('button', { name: 'Save task' }))
  expect(screen.getByLabelText('Task title *')).toHaveAccessibleDescription(
    'The title must be at most 120 characters.',
  )
  expect(onSubmit).not.toHaveBeenCalled()
})

it('rejects a description longer than 2000 characters without submitting', async () => {
  const { user, onSubmit } = renderForm({
    initial: { ...existing, description: 'd'.repeat(2001) },
  })
  await user.click(screen.getByRole('button', { name: 'Save task' }))
  const description = screen.getByLabelText('Description (optional)')
  expect(description).toBeInvalid()
  expect(description).toHaveAccessibleDescription(
    'The description must be at most 2000 characters.',
  )
  expect(onSubmit).not.toHaveBeenCalled()
})

it('clears the error and submits once the title is fixed', async () => {
  const { user, onSubmit } = renderForm()
  await user.click(screen.getByRole('button', { name: 'Save task' }))
  await user.type(screen.getByLabelText('Task title *'), 'Fixed')
  await user.click(screen.getByRole('button', { name: 'Save task' }))
  expect(screen.queryByText('Enter a task title.')).not.toBeInTheDocument()
  expect(screen.getByLabelText('Task title *')).toBeValid()
  expect(onSubmit).toHaveBeenCalledTimes(1)
})

it('submits trimmed values and the selected priority', async () => {
  const { user, onSubmit } = renderForm()
  await user.type(screen.getByLabelText('Task title *'), '  Prepare a demo  ')
  await user.selectOptions(screen.getByLabelText('Priority'), 'High')
  await user.click(screen.getByRole('button', { name: 'Save task' }))
  expect(onSubmit).toHaveBeenCalledWith({
    title: 'Prepare a demo',
    description: '',
    priority: 'high',
    due_date: null,
    completed: false,
  })
})

it('submits a trimmed description and the typed due date', async () => {
  const { user, onSubmit } = renderForm()
  await user.type(screen.getByLabelText('Task title *'), 'Demo')
  await user.type(
    screen.getByLabelText('Description (optional)'),
    '  Bring slides  ',
  )
  await user.type(screen.getByLabelText('Due date (optional)'), '2026-12-31')
  await user.click(screen.getByRole('button', { name: 'Save task' }))
  expect(onSubmit).toHaveBeenCalledWith({
    title: 'Demo',
    description: 'Bring slides',
    priority: 'medium',
    due_date: '2026-12-31',
    completed: false,
  })
})

it('prefills the fields from the initial task', () => {
  renderForm({ initial: existing })
  expect(screen.getByLabelText('Task title *')).toHaveValue('Existing')
  expect(screen.getByLabelText('Description (optional)')).toHaveValue('Notes')
  expect(screen.getByLabelText('Priority')).toHaveValue('low')
  expect(screen.getByLabelText('Due date (optional)')).toHaveValue('2026-11-15')
})

it('sends a cleared due date as null', async () => {
  const { user, onSubmit } = renderForm({ initial: existing })
  await user.clear(screen.getByLabelText('Due date (optional)'))
  await user.click(screen.getByRole('button', { name: 'Save task' }))
  expect(onSubmit).toHaveBeenCalledWith({
    title: 'Existing',
    description: 'Notes',
    priority: 'low',
    due_date: null,
    completed: true,
  })
})

it('shows the server error as an alert', () => {
  renderForm({ error: 'Server rejected the task.' })
  expect(screen.getByRole('alert')).toHaveTextContent(
    'Server rejected the task.',
  )
})

it('shows no alert without a server error', () => {
  renderForm()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})

it('cancels through the Cancel button', async () => {
  const { user, onCancel, onSubmit } = renderForm()
  await user.click(screen.getByRole('button', { name: 'Cancel' }))
  expect(onCancel).toHaveBeenCalledTimes(1)
  expect(onSubmit).not.toHaveBeenCalled()
})

it('disables fields and actions and shows saving progress while busy', () => {
  renderForm({ busy: true })
  expect(screen.getByLabelText('Task title *')).toBeDisabled()
  expect(screen.getByLabelText('Description (optional)')).toBeDisabled()
  expect(screen.getByLabelText('Priority')).toBeDisabled()
  expect(screen.getByLabelText('Due date (optional)')).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled()
})
