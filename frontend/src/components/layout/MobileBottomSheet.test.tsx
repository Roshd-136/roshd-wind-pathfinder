import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { MobileBottomSheet } from './MobileBottomSheet'
import { useUiStore } from '../../store/useUiStore'

/**
 * آزمون شیت پایینِ موبایل — رفتار کشیدنی و سنجاقها (بازخورد تست موبایل):
 * جمع‌شدن پیشفرض فقط با دسته و عنوان، بازشدن با کشیدن دسته به بالا
 * (با فاصله از سقف) و بستن با کشیدن به پایین. jsdom اندازهٔ واقعی ندارد؛
 * `offsetHeight` ورقها با defineProperty شبیهسازی میشود تا ریاضیاتِ
 * سنجاقِ جمع (ارتفاع شیت منهای نوار دسته) درست حساب شود.
 */

// اسنپ‌شات حالت اولیهٔ استور برای بازنشانیِ تمیز بین آزمونها
const initialUiState = useUiStore.getState()

const COLLAPSED = 'translate-y-[calc(100%-3.5rem)]'
const OPEN = 'translate-y-0'

/** شیت ۴۰۰px و نوار دسته ۵۶px → سنجاقِ جمع در y=۳۴۴ است. */
function mockSheetHeights() {
  const sheet = screen.getByTestId('mobile-sheet')
  const grab = screen.getByTestId('mobile-sheet-grab')
  Object.defineProperty(sheet, 'offsetHeight', { configurable: true, get: () => 400 })
  Object.defineProperty(grab, 'offsetHeight', { configurable: true, get: () => 56 })
}

function contentEl() {
  return document.getElementById('mobile-sheet-content') as HTMLElement
}

describe('MobileBottomSheet', () => {
  beforeEach(() => {
    useUiStore.setState(initialUiState, true)
    render(
      <MobileBottomSheet title="route settings">
        <p>panel body</p>
      </MobileBottomSheet>,
    )
  })

  it('starts collapsed showing only the title bar (peek snap)', () => {
    const sheet = screen.getByTestId('mobile-sheet')
    expect(sheet.className).toContain(COLLAPSED)
    const grab = screen.getByRole('button', { name: 'route settings' })
    expect(grab).toHaveAttribute('aria-expanded', 'false')
    // محتوای جمعشده از ترتیب تب و درخت دسترسپذیری خارج است
    expect(contentEl()).toHaveAttribute('inert')
  })

  it('opens on handle click and closes on second click', () => {
    const grab = screen.getByRole('button', { name: 'route settings' })
    fireEvent.click(grab)
    expect(screen.getByTestId('mobile-sheet').className).toContain(OPEN)
    expect(grab).toHaveAttribute('aria-expanded', 'true')
    expect(contentEl()).not.toHaveAttribute('inert')

    fireEvent.click(grab)
    expect(screen.getByTestId('mobile-sheet').className).toContain(COLLAPSED)
  })

  it('pins to the live drag position while the handle is dragged', () => {
    mockSheetHeights()
    const sheet = screen.getByTestId('mobile-sheet')
    const handle = screen.getByTestId('mobile-sheet-grab')
    const grab = screen.getByRole('button', { name: 'route settings' })

    fireEvent.pointerDown(handle, { clientY: 500 })
    // شیت جمعشده: شروع کشش از سنجاق جمع (y=۳۴۴)
    expect(sheet.style.transform).toBe('translateY(344px)')
    expect(sheet.style.transition).toBe('none')

    fireEvent.pointerMove(handle, { clientY: 250 })
    expect(sheet.style.transform).toBe('translateY(94px)')

    fireEvent.pointerUp(handle)
    // زیر نیمهٔ سنجاق جمع → باز میشود؛ استایل درونخطی پاک میشود
    expect(grab).toHaveAttribute('aria-expanded', 'true')
    expect(sheet.style.transform).toBe('')
    expect(sheet.className).toContain(OPEN)
  })

  it('closes when the open sheet is dragged down', () => {
    mockSheetHeights()
    const grab = screen.getByRole('button', { name: 'route settings' })
    fireEvent.click(grab)
    expect(grab).toHaveAttribute('aria-expanded', 'true')

    fireEvent.pointerDown(grab, { clientY: 0 })
    fireEvent.pointerMove(grab, { clientY: 300 })
    fireEvent.pointerUp(grab)

    expect(grab).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByTestId('mobile-sheet').className).toContain(COLLAPSED)
  })

  it('ignores the synthetic click after a real drag (no snap toggle)', () => {
    mockSheetHeights()
    const grab = screen.getByRole('button', { name: 'route settings' })

    // کشیدن به بالا → باز؛ clickِ مصنوعی پس از رهاکردن نباید آن را ببندد
    fireEvent.pointerDown(grab, { clientY: 500 })
    fireEvent.pointerMove(grab, { clientY: 250 })
    fireEvent.pointerUp(grab)
    expect(grab).toHaveAttribute('aria-expanded', 'true')

    fireEvent.click(grab)
    expect(grab).toHaveAttribute('aria-expanded', 'true')
  })

  it('dims the map behind the open sheet; tapping the backdrop closes it', () => {
    const grab = screen.getByRole('button', { name: 'route settings' })
    // جمعشده: بدون پرده — نقشه کاملاً در دسترس است
    expect(screen.queryByTestId('mobile-sheet-backdrop')).toBeNull()

    fireEvent.click(grab)
    const backdrop = screen.getByTestId('mobile-sheet-backdrop')
    expect(backdrop.className).toContain('bg-black/50')

    fireEvent.click(backdrop)
    expect(useUiStore.getState().isMobileSheetOpen).toBe(false)
    expect(screen.queryByTestId('mobile-sheet-backdrop')).toBeNull()
  })
})
