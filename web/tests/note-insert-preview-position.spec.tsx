import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import NoteInsertMenu, { type NoteMenuItem } from '@/features/notes/components/NoteInsertMenu'

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }))
vi.mock('@blocknote/react', () => ({ useExtension: () => ({ closeMenu: vi.fn() }) }))
vi.mock('@blocknote/core/extensions', () => ({ SuggestionMenu: {} }))
vi.mock('@/features/notes/components/NoteBlockPreview', () => ({ default: () => <span>preview</span> }))

const item: NoteMenuItem = { title: 'Paragraph', onItemClick: () => {}, preview: 'paragraph' }

describe.each(['ltr', 'rtl'] as const)('%s note insertion preview', dir => {
  it.each([
    { left: 100, right: 400, ltr: 'end', rtl: 'start' },
    { left: 700, right: 1000, ltr: 'start', rtl: 'end' },
    { left: 200, right: 900, ltr: 'inline', rtl: 'inline' },
  ])('chooses an available logical side for $left–$right', geometry => {
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
      left: geometry.left, right: geometry.right, width: geometry.right - geometry.left,
      top: 0, bottom: 400, height: 400, x: geometry.left, y: 0, toJSON() {},
    })
    const { container } = render(<div dir={dir}>
      <NoteInsertMenu items={[item]} selectedIndex={0} loadingState="loaded" onItemClick={vi.fn()} />
    </div>)
    expect(container.querySelector('.dt-note-menu-preview')).toHaveClass(geometry[dir])
    expect(container.querySelector('.dt-note-insert-menu')).toHaveClass(`preview-${geometry[dir]}`)
  })
})
