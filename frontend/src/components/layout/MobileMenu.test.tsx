import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it } from 'vitest'
import { MobileMenuButton, MobileMenuPanel } from './MobileMenu'
import { StepsWizard } from '../features/routing/StepsWizard'
import { useUiStore } from '../../store/useUiStore'
import { useSettingsStore } from '../../store/useSettingsStore'

/**
 * آزمون منوی موبایل — دکمهٔ منو باید داخل ردیف جستجوی ویزارد (سمتِ مقابل
 * ذره‌بین) باشد و پنل زیر ویزارد باز شود با دکمهٔ بستن روی خود پنل (بازخورد
 * تست موبایل): قبلاً دکمهٔ شناور گوشهٔ ویزارد را می‌پوشاند و aside زیر md
 * مخفی بود، یعنی روی گوشی عملاً منویی باز نمیشد.
 */

const initialUiState = useUiStore.getState()
const initialSettingsState = useSettingsStore.getState()

function withProviders(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MemoryRouter>,
  )
}

const wizardBase = {
  origin: null,
  destination: null,
  hasResult: false,
  step: 1 as 1 | 2 | 3,
  onBack: () => {},
  onNext: () => {},
  canNext: false,
  onCalculate: () => {},
  canCalculate: false,
  isCalculating: false,
}

describe('MobileMenu', () => {
  beforeEach(() => {
    useUiStore.setState(initialUiState, true)
    useSettingsStore.setState(initialSettingsState, true)
  })

  it('trigger opens the sidebar state and stays mobile-only (md:hidden)', () => {
    withProviders(<MobileMenuButton />)
    expect(useUiStore.getState().isSidebarOpen).toBe(false)
    fireEvent.click(screen.getByTestId('mobile-menu-trigger'))
    expect(useUiStore.getState().isSidebarOpen).toBe(true)
    expect(screen.getByTestId('mobile-menu-trigger').className).toContain('md:hidden')
  })

  it('panel renders beneath the wizard only when open, with its own close button', () => {
    withProviders(
      <>
        <MobileMenuButton />
        <MobileMenuPanel />
      </>,
    )
    // بسته: هیچی (پیشتر aside دسکتاپ زیر md مخفی بود و منوی موبایل وجود نداشت)
    expect(screen.queryByTestId('mobile-menu-panel')).toBeNull()

    fireEvent.click(screen.getByTestId('mobile-menu-trigger'))
    expect(screen.getByTestId('mobile-menu-panel')).toBeInTheDocument()
    // محتوا: نام اپ + هر چهار آیتم + دکمهٔ بستن روی خود پنل
    expect(screen.getByText('WindPath')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Map' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Settings' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'About' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Profile' })).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('mobile-menu-close'))
    expect(useUiStore.getState().isSidebarOpen).toBe(false)
    expect(screen.queryByTestId('mobile-menu-panel')).toBeNull()
  })

  it('outside click and item navigation both close the panel', () => {
    withProviders(
      <>
        <MobileMenuButton />
        <MobileMenuPanel />
      </>,
    )
    fireEvent.click(screen.getByTestId('mobile-menu-trigger'))
    // پردهٔ تیرهٔ مودال
    const backdrop = screen.getByTestId('mobile-menu-backdrop')
    expect(backdrop.className).toContain('bg-black/50')
    fireEvent.click(backdrop)
    expect(useUiStore.getState().isSidebarOpen).toBe(false)
    expect(screen.queryByTestId('mobile-menu-panel')).toBeNull()

    // انتخاب آیتم ناوبری هم پنل را می‌بندد
    fireEvent.click(screen.getByTestId('mobile-menu-trigger'))
    fireEvent.click(screen.getByRole('link', { name: 'About' }))
    expect(useUiStore.getState().isSidebarOpen).toBe(false)
  })

  it('theme toggle inside the menu flips the settings store', () => {
    withProviders(
      <>
        <MobileMenuButton />
        <MobileMenuPanel />
      </>,
    )
    fireEvent.click(screen.getByTestId('mobile-menu-trigger'))
    const before = useSettingsStore.getState().theme
    fireEvent.click(screen.getByRole('button', { name: 'Theme' }))
    const after = useSettingsStore.getState().theme
    expect(after).not.toBe(before)
  })
})

describe('StepsWizard menuSlot', () => {
  beforeEach(() => {
    useUiStore.setState(initialUiState, true)
  })

  it('renders the slot beside the search input (opposite the magnifier) in step 1', () => {
    withProviders(<StepsWizard {...wizardBase} step={1} menuSlot={<span data-testid="menu-slot" />} />)
    expect(screen.getByTestId('menu-slot')).toBeInTheDocument()
  })

  it('renders the slot at the end corner in step 3 where the next arrow is always disabled', () => {
    withProviders(
      <StepsWizard {...wizardBase} step={3} hasResult={true} menuSlot={<span data-testid="menu-slot" />} />,
    )
    const slot = screen.getByTestId('menu-slot').parentElement
    // قابِ اسلات در گام ۳ موضع مطلق گوشهٔ end دارد (جای فلش غیرفعال)
    expect(slot?.className).toContain('end-2')
  })
})
