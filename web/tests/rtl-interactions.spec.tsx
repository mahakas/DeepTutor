import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useRef } from 'react'
import { inlineDirection, inlineRatio, nearestColumn } from '@/lib/inline-geometry'
import { useSplitPane } from '@/features/co-writer/hooks/useSplitPane'
import { ReadingPanelSeparator } from '@/components/reading/workspace/ReadingPanelSeparator'
import { TimeGrid } from '@/features/calendar/components/TimeGrid'
import { Toggle } from '@/components/settings/Toggle'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: 'fa' } }),
}))

const rect = (left: number, width: number) =>
  ({ left, right: left + width, top: 0, bottom: 1200, width, height: 1200, x: left, y: 0, toJSON() {} })

beforeEach(() => {
  vi.stubGlobal('PointerEvent', MouseEvent)
  Object.defineProperty(HTMLElement.prototype, 'setPointerCapture', { configurable: true, value: vi.fn() })
  Object.defineProperty(HTMLElement.prototype, 'hasPointerCapture', { configurable: true, value: () => false })
})
afterEach(() => {
  document.documentElement.removeAttribute('dir')
  vi.unstubAllGlobals()
})

function SplitPane({ dir }: { dir: 'ltr' | 'rtl' }) {
  const ref = useRef<HTMLDivElement>(null)
  const split = useSplitPane(ref)
  return (
    <div ref={ref} dir={dir} data-testid="split" style={{ direction: dir }}>
      <button onPointerDown={split.handleSplitterPointerDown as never}>resize</button>
      <output>{split.editorRatio.toFixed(2)}</output>
    </div>
  )
}

describe.each(['ltr', 'rtl'] as const)('%s pointer geometry', dir => {
  it('measures a ratio from inline-start and respects nested direction overrides', () => {
    const { container } = render(<div dir={dir} style={{ direction: dir }} />)
    const node = container.firstElementChild!
    vi.spyOn(node, 'getBoundingClientRect').mockReturnValue(rect(100, 400))
    expect(inlineDirection(node)).toBe(dir === 'rtl' ? -1 : 1)
    expect(inlineRatio(node, 200)).toBe(dir === 'rtl' ? 0.75 : 0.25)
  })

  it('resizes the editor relative to its actual inline-start edge', async () => {
    render(<SplitPane dir={dir} />)
    const node = screen.getByTestId('split')
    vi.spyOn(node, 'getBoundingClientRect').mockReturnValue(rect(100, 400))
    // Allow the saved-ratio animation frame to finish before dragging.
    await act(() => new Promise<void>(resolve => requestAnimationFrame(() => resolve())))
    fireEvent.pointerDown(screen.getByText('resize'), { button: 0, clientX: 300 })
    fireEvent.pointerMove(window, { clientX: 200 })
    expect(screen.getByRole('status')).toHaveTextContent(dir === 'rtl' ? '0.75' : '0.25')
    fireEvent.pointerUp(window)
    fireEvent.pointerMove(window, { clientX: 400 })
    expect(screen.getByRole('status')).toHaveTextContent(dir === 'rtl' ? '0.75' : '0.25')
  })

  it('resizes either reading panel toward the physical keyboard arrow', () => {
    const onResize = vi.fn()
    const { rerender } = render(
      <div dir={dir}>
        <ReadingPanelSeparator label="resize" width={300} min={100} max={500} direction={1} onResize={onResize} />
      </div>
    )
    fireEvent.keyDown(screen.getByRole('separator'), { key: 'ArrowLeft' })
    expect(onResize).toHaveBeenLastCalledWith(dir === 'rtl' ? 310 : 290)
    rerender(
      <div dir={dir}>
        <ReadingPanelSeparator label="resize" width={300} min={100} max={500} direction={-1} onResize={onResize} />
      </div>
    )
    fireEvent.keyDown(screen.getByRole('separator'), { key: 'ArrowRight', shiftKey: true })
    expect(onResize).toHaveBeenLastCalledWith(dir === 'rtl' ? 340 : 260)
    fireEvent.keyDown(screen.getByRole('separator'), { key: 'Home' })
    expect(onResize).toHaveBeenLastCalledWith(100)
    fireEvent.keyDown(screen.getByRole('separator'), { key: 'End' })
    expect(onResize).toHaveBeenLastCalledWith(500)
  })

  it('creates an all-day event in the date under the pointer, with a physical anchor', () => {
    const onCreate = vi.fn()
    const days = [new Date(2026, 10, 16), new Date(2026, 10, 17)]
    const { container } = render(
      <div dir={dir}>
        <TimeGrid days={days} items={[]} footprints={new Map()} now={days[0]} draft={null} selectedKey={null}
          onCreate={onCreate} onOpenItem={vi.fn()} onOpenFootprint={vi.fn()} onReschedule={vi.fn()}
          onDropTask={vi.fn()} onOpenDay={vi.fn()} />
      </div>
    )
    const row = container.querySelector<HTMLElement>('.dt-cal-span-area')!
    vi.spyOn(row, 'getBoundingClientRect').mockReturnValue(rect(100, 400))
    fireEvent.pointerDown(row, { button: 0, clientX: 450, clientY: 20 })
    fireEvent.pointerUp(window, { clientX: 450, clientY: 20 })
    expect(onCreate).toHaveBeenCalledTimes(1)
    const [draft, anchor] = onCreate.mock.calls[0]
    expect(draft.start.getDate()).toBe(dir === 'rtl' ? 16 : 17)
    expect(draft.end.getDate()).toBe(dir === 'rtl' ? 17 : 18)
    expect(anchor.left).toBe(300)
    expect(anchor.right).toBe(500)
  })
})

it('finds the nearest visible calendar column regardless of DOM order', () => {
  const nodes = [document.createElement('div'), document.createElement('div')]
  vi.spyOn(nodes[0], 'getBoundingClientRect').mockReturnValue(rect(300, 200))
  vi.spyOn(nodes[1], 'getBoundingClientRect').mockReturnValue(rect(100, 200))
  expect(nearestColumn(nodes, 450)).toBe(nodes[0])
  expect(nearestColumn(nodes, 150)).toBe(nodes[1])
  expect(nearestColumn(nodes, 700)).toBe(nodes[0])
  expect(nearestColumn(nodes, -50)).toBe(nodes[1])
  expect(nearestColumn([], 100)).toBeNull()
})

it('positions a settings switch thumb using logical offsets in both states', () => {
  const onChange = vi.fn()
  const { rerender } = render(<Toggle checked={false} onChange={onChange} />)
  const button = screen.getByRole('switch')
  expect(button.firstElementChild).toHaveClass('start-0.5')
  fireEvent.click(button)
  expect(onChange).toHaveBeenCalledWith(true)
  rerender(<Toggle checked onChange={onChange} />)
  expect(button.firstElementChild).toHaveClass('start-[18px]')
  expect(button.firstElementChild?.className).not.toContain('translate-x')
})
