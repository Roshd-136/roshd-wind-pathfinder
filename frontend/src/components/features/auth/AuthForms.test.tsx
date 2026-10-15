import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeAll, describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import i18n from '../../../i18n'
import { VerifyEmailPanel } from './VerifyEmailPanel'
import { ResetPasswordForm } from './ResetPasswordForm'

function renderWithProviders(ui: React.ReactElement, initialEntries: string[] = ['/']) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('VerifyEmailPanel', () => {
  beforeAll(async () => {
    await i18n.changeLanguage('en')
  })

  it('shows the manual hint when no token is present in the URL', () => {
    renderWithProviders(<VerifyEmailPanel onDone={() => {}} />)
    expect(screen.getByText(/verification link has been sent/i)).toBeInTheDocument()
  })

  it('renders a back-to-login action', () => {
    renderWithProviders(<VerifyEmailPanel onDone={() => {}} />)
    expect(screen.getByRole('button', { name: /back to login/i })).toBeInTheDocument()
  })
})

describe('ResetPasswordForm', () => {
  beforeAll(async () => {
    await i18n.changeLanguage('en')
  })

  it('shows the reset-token field when the URL has no token', () => {
    renderWithProviders(<ResetPasswordForm onBack={() => {}} />)
    expect(screen.getByLabelText(/reset code/i)).toBeInTheDocument()
  })

  it('hides the reset-token field when a token is supplied in the URL', () => {
    renderWithProviders(<ResetPasswordForm onBack={() => {}} />, ['/auth?token=abc123'])
    expect(screen.queryByLabelText(/reset code/i)).not.toBeInTheDocument()
  })
})
