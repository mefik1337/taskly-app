import { QueryClient, useQueryClient } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { useTheme } from 'styled-components'
import { beforeEach, expect, it, vi } from 'vitest'
import { GlobalStyles, theme } from '../design-system'
import { queryClient } from '../lib/queryClient'
import { AppProviders } from './AppProviders'

vi.mock('../design-system', () => import('../design-system/mocks'))
beforeEach(() => vi.clearAllMocks())

let seenClient: QueryClient | undefined
let seenTheme: unknown

function Probe() {
  seenClient = useQueryClient()
  seenTheme = useTheme()
  return <p>Child content</p>
}

beforeEach(() => {
  seenClient = undefined
  seenTheme = undefined
})

it('renders children with the supplied query client, theme and global styles', () => {
  const client = new QueryClient()
  render(
    <AppProviders client={client}>
      <Probe />
    </AppProviders>,
  )
  expect(screen.getByText('Child content')).toBeVisible()
  expect(seenClient).toBe(client)
  expect(seenTheme).toBe(theme)
  expect(GlobalStyles).toHaveBeenCalled()
})

it('uses the application query client by default', () => {
  render(
    <AppProviders>
      <Probe />
    </AppProviders>,
  )
  expect(seenClient).toBe(queryClient)
})
