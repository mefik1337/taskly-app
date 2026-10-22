import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { AppProviders } from './app/AppProviders'
import { installFakeApi } from './test/fakeApi'
import { createTestQueryClient } from './test/queryWrapper'
import { todoFixture } from './test/todoFixture'
import App from './App'

it('renders the Taskly header and the tasks loaded from the server', async () => {
  installFakeApi([todoFixture])
  render(
    <AppProviders client={createTestQueryClient()}>
      <App />
    </AppProviders>,
  )
  expect(screen.getByRole('link', { name: 'Taskly — home' })).toBeVisible()
  expect(screen.getByRole('heading', { level: 1, name: 'Tasks' })).toBeVisible()
  expect(
    await screen.findByRole('heading', { name: 'Prepare a demo' }),
  ).toBeVisible()
})
