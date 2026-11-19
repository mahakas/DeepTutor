import { fireEvent, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TimeGrid } from '@/features/calendar/components/TimeGrid'
import { MonthView } from '@/features/calendar/components/MonthView'
import { addDays } from '@/features/calendar/model/dates'

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: 'fa' } }) }))
afterEach(() => {
  fireEvent(window, new MouseEvent('pointercancel'))
  delete document.body.dataset.calendarDragging
})

describe.each(['week', 'month'] as const)('%s calendar gesture lifecycle', view => {
  it.each([false, true])('cancels an outstanding gesture when unmounted (moved=%s)', moved => {
    const now = new Date(2026, 10, 16)
    const days = Array.from({ length: 7 }, (_, index) => addDays(now, index))
    const onCreate = vi.fn()
    const props = { items: [], footprints: new Map(), now, draft: null, selectedKey: null,
      onCreate, onOpenItem: vi.fn(), onOpenFootprint: vi.fn(), onReschedule: vi.fn(), onDropTask: vi.fn(), onOpenDay: vi.fn() }
    const { container, unmount } = render(view === 'week'
      ? <TimeGrid {...props} days={days} />
      : <MonthView {...props} weeks={[days]} month={10} onShowMore={vi.fn()} />)
    const target = container.querySelector<HTMLElement>(view === 'week' ? '.dt-cal-span-area' : '[data-cal-day]')!
    vi.spyOn(target, 'getBoundingClientRect').mockReturnValue({ left: 0, right: 700, top: 0, bottom: 30, width: 700, height: 30 } as DOMRect)
    fireEvent(target, new MouseEvent('pointerdown', { button: 0, clientX: 100, clientY: 10, bubbles: true }))
    if (moved) fireEvent(window, new MouseEvent('pointermove', { clientX: 200, clientY: 10 }))
    unmount()
    try {
      expect(document.body.dataset.calendarDragging).toBeUndefined()
      fireEvent(window, new MouseEvent('pointerup', { clientX: 200, clientY: 10 }))
      expect(onCreate).not.toHaveBeenCalled()
    } finally {
      // A red baseline run must not leave the old implementation's RAF alive.
      fireEvent(window, new MouseEvent('pointercancel'))
    }
  })
})
