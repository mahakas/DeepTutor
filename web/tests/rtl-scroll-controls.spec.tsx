import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PartnerRoster } from '@/components/sidebar/PartnerRoster'
import { LearningBoard } from '@/components/space/learning/LearningBoard'
import QuizConfigPanel from '@/components/quiz/QuizConfigPanel'
import { DEFAULT_QUIZ_CONFIG } from '@/lib/quiz-types'

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: 'fa' } }) }))
vi.mock('next/link', () => ({ default: ({ children, prefetch: _prefetch, ...props }: React.ComponentProps<'a'> & { prefetch?: boolean }) => <a {...props}>{children}</a> }))
vi.mock('@/components/partners/PartnerAvatar', () => ({ default: () => null }))

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(200)
  vi.spyOn(HTMLElement.prototype, 'scrollWidth', 'get').mockReturnValue(600)
})

describe.each(['ltr', 'rtl'] as const)('%s horizontal controls', dir => {
  const sign = dir === 'rtl' ? -1 : 1
  it('maps the learning-board slider to native signed scrollLeft', () => {
    render(<div dir={dir}><LearningBoard pathId="path" modules={[]} revision={1} zh={false} onStartTutoring={vi.fn()} /></div>)
    const viewport = screen.getByRole('region', { name: 'Board' })
    const slider = screen.getByRole('slider', { name: 'Board' })
    viewport.scrollLeft = sign * 120
    fireEvent.scroll(viewport)
    expect(slider).toHaveValue('120')
    fireEvent.change(slider, { target: { value: '220' } })
    expect(viewport.scrollLeft).toBe(sign * 220)
  })

  it('scrolls the partner roster forward with the wheel, releasing it at the boundary', async () => {
    const { container } = render(<div dir={dir}><PartnerRoster partners={[]} activeHref="" /></div>)
    const strip = container.querySelector<HTMLElement>('.dt-partner-roster')!
    const event = new WheelEvent('wheel', { deltaY: 100, cancelable: true })
    strip.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
    expect(strip.scrollLeft).toBe(sign * 100)
    strip.scrollLeft = sign * 400
    const boundary = new WheelEvent('wheel', { deltaY: 100, cancelable: true })
    strip.dispatchEvent(boundary)
    expect(boundary.defaultPrevented).toBe(false)
    fireEvent.scroll(strip)
    await waitFor(() => expect(strip.style.getPropertyValue('--dt-roster-fade-l')).toBe(dir === 'rtl' ? '0.0px' : '20.8px'))
    expect(strip.style.getPropertyValue('--dt-roster-fade-r')).toBe(dir === 'rtl' ? '20.8px' : '0.0px')
  })

  it('adjusts quiz type counts in the same direction as the visual segments', () => {
    const onChange = vi.fn()
    render(<div dir={dir}>
      <QuizConfigPanel value={{ ...DEFAULT_QUIZ_CONFIG, num_questions: 10, question_types: ['choice', 'concept'], per_type_counts: { choice: 5, concept: 5 } }} onChange={onChange} uploadedPdf={null} onUploadPdf={vi.fn()} />
    </div>)
    const handle = screen.getByRole('separator', { name: 'Drag to adjust ratio' })
    Object.defineProperty(handle, 'setPointerCapture', { configurable: true, value: vi.fn() })
    vi.spyOn(handle.parentElement!, 'getBoundingClientRect').mockReturnValue({ left: 0, right: 400, width: 400 } as DOMRect)
    // jsdom does not implement PointerEvent; use mouse coordinate fields.
    fireEvent(handle, new MouseEvent('pointerdown', { bubbles: true, clientX: 200 }))
    fireEvent(handle, new MouseEvent('pointermove', { bubbles: true, clientX: 280 }))
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ per_type_counts: dir === 'rtl' ? { choice: 3, concept: 7 } : { choice: 7, concept: 3 } }))
    expect(handle.style.insetInlineStart).toBe('50%')
    expect(handle.style.left).toBe('')
  })
})
