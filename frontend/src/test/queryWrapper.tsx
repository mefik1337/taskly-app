import { QueryClient } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactElement, ReactNode } from 'react'
import { AppProviders } from '../app/AppProviders'

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity },
      mutations: { retry: false },
    },
  })
}

export function queryWrapper(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <AppProviders client={client}>{children}</AppProviders>
  }
}

export function renderWithProviders(
  ui: ReactElement,
  client = createTestQueryClient(),
) {
  const user = userEvent.setup()
  return { user, client, ...render(ui, { wrapper: queryWrapper(client) }) }
}
