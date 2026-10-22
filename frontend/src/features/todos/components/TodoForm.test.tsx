import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { TodoForm } from './TodoForm'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))

describe('TodoForm', () => {
  it('rejects a whitespace-only title without submitting', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(
      <TodoForm
        onSubmit={onSubmit}
        onCancel={vi.fn()}
        busy={false}
        error={null}
      />,
    )
    await user.type(screen.getByLabelText(/Task title/), '   ')
    await user.click(screen.getByRole('button', { name: 'Save task' }))
    expect(screen.getByText('Enter a task title.')).toBeVisible()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('submits trimmed values and the selected priority', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    render(
      <TodoForm
        onSubmit={onSubmit}
        onCancel={vi.fn()}
        busy={false}
        error={null}
      />,
    )
    await user.type(screen.getByLabelText(/Task title/), '  Prepare a demo  ')
    await user.selectOptions(screen.getByLabelText('Priority'), 'high')
    await user.click(screen.getByRole('button', { name: 'Save task' }))
    expect(onSubmit).toHaveBeenCalledWith({
      title: 'Prepare a demo',
      description: '',
      priority: 'high',
      due_date: null,
      completed: false,
    })
  })

  it('submits a trimmed description and the chosen due date', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    render(
      <TodoForm
        onSubmit={onSubmit}
        onCancel={vi.fn()}
        busy={false}
        error={null}
      />,
    )
    await user.type(screen.getByLabelText(/Task title/), 'Demo')
    await user.type(
      screen.getByLabelText('Description (optional)'),
      '  Bring slides  ',
    )
    fireEvent.change(screen.getByLabelText('Due date (optional)'), {
      target: { value: '2026-12-31' },
    })
    await user.click(screen.getByRole('button', { name: 'Save task' }))
    expect(onSubmit).toHaveBeenCalledWith({
      title: 'Demo',
      description: 'Bring slides',
      priority: 'medium',
      due_date: '2026-12-31',
      completed: false,
    })
  })

  it('prefills initial values and sends a cleared due date as null', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    render(
      <TodoForm
        initial={{
          title: 'Existing',
          description: 'Notes',
          priority: 'low',
          due_date: '2026-11-15',
          completed: true,
        }}
        onSubmit={onSubmit}
        onCancel={vi.fn()}
        busy={false}
        error={null}
      />,
    )
    expect(screen.getByLabelText(/Task title/)).toHaveValue('Existing')
    expect(screen.getByLabelText('Description (optional)')).toHaveValue('Notes')
    expect(screen.getByLabelText('Priority')).toHaveValue('low')
    const dueDate = screen.getByLabelText('Due date (optional)')
    expect(dueDate).toHaveValue('2026-11-15')
    fireEvent.change(dueDate, { target: { value: '' } })
    await user.click(screen.getByRole('button', { name: 'Save task' }))
    expect(onSubmit).toHaveBeenCalledWith({
      title: 'Existing',
      description: 'Notes',
      priority: 'low',
      due_date: null,
      completed: true,
    })
  })

  it('rejects a title longer than 120 characters without submitting', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(
      <TodoForm
        initial={{
          title: 'a'.repeat(121),
          description: '',
          priority: 'medium',
          due_date: null,
          completed: false,
        }}
        onSubmit={onSubmit}
        onCancel={vi.fn()}
        busy={false}
        error={null}
      />,
    )
    await user.click(screen.getByRole('button', { name: 'Save task' }))
    expect(
      screen.getByText('The title must be at most 120 characters.'),
    ).toBeVisible()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('shows the server error passed by the caller', () => {
    render(
      <TodoForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        busy={false}
        error="Server rejected the task."
      />,
    )
    expect(screen.getByTestId('alert')).toHaveTextContent(
      'Server rejected the task.',
    )
  })

  it('shows no alert without a server error', () => {
    render(
      <TodoForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        busy={false}
        error={null}
      />,
    )
    expect(screen.queryByTestId('alert')).not.toBeInTheDocument()
  })

  it('calls onCancel when cancelling', async () => {
    const onCancel = vi.fn()
    const user = userEvent.setup()
    render(
      <TodoForm
        onSubmit={vi.fn()}
        onCancel={onCancel}
        busy={false}
        error={null}
      />,
    )
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('disables fields and actions and shows saving progress while busy', () => {
    render(<TodoForm onSubmit={vi.fn()} onCancel={vi.fn()} busy error={null} />)
    expect(screen.getByLabelText(/Task title/)).toBeDisabled()
    expect(screen.getByLabelText('Priority')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled()
  })
})
