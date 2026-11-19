import { test, expect } from '@playwright/test'
import fa from '../locales/fa/app.json'

test.setTimeout(120_000)

// Test a Persian browser preference without mutating the account's saved locale.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('deeptutor-language', 'fa')
    localStorage.setItem('deeptutor-response-language', 'fa')
  })
})

for (const direction of ['rtl', 'ltr'] as const) {
  test(`mobile drawer leaves the viewport and reopens on the correct edge (${direction})`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/chat')
    const trigger = page.getByRole('button', { name: fa['Open navigation'], exact: true })
    await expect(trigger).toBeVisible()
    await page.evaluate(dir => { document.documentElement.dir = dir }, direction)
    const drawer = page.locator('aside').first().locator('..')
    await expect(drawer).toHaveAttribute('inert', '')
    await expect.poll(async () => {
      const box = (await drawer.boundingBox())!
      return direction === 'rtl' ? box.x >= 389 : box.x + box.width <= 1
    }).toBe(true)
    await trigger.click()
    await expect(drawer).not.toHaveAttribute('inert', '')
    await expect.poll(async () => {
      const box = (await drawer.boundingBox())!
      return box.x >= -1 && box.x + box.width <= 391
    }).toBe(true)
    await page.keyboard.press('Escape')
    await expect(drawer).toHaveAttribute('inert', '')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })

  test(`settings switches keep their thumbs within their tracks (${direction})`, async ({ page }) => {
    await page.goto('/settings/tools')
    const switches = page.locator('button[role="switch"]')
    await expect(switches.first()).toBeVisible()
    await page.evaluate(dir => { document.documentElement.dir = dir }, direction)
    const checkBounds = async () => {
      const failures = await switches.evaluateAll(nodes => nodes.flatMap(node => {
        const track = node.getBoundingClientRect()
        if (track.width > 70 || !track.width) return []
        const thumb = node.querySelector('span')?.getBoundingClientRect()
        return thumb && (thumb.left < track.left - 1 || thumb.right > track.right + 1)
          ? [node.getAttribute('aria-label') || 'unnamed switch'] : []
      }))
      expect(failures).toEqual([])
    }
    await checkBounds()
    const enabled = page.locator('button[role="switch"]:not(:disabled)').first()
    await enabled.click()
    await checkBounds()
  })
}

test('Persian desktop shell, directional icons and nested LTR content stay consistent', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/chat')
  await expect(page.locator('html')).toHaveAttribute('lang', 'fa-IR')
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  await expect(page.locator('aside').first()).toBeVisible()
  const sidebar = (await page.locator('aside').first().boundingBox())!
  expect(sidebar.x).toBeGreaterThan(1100)
  const scales = await page.evaluate(() => {
    const fixture = document.createElement('div')
    fixture.innerHTML = '<svg class="lucide-chevron-right"></svg><div dir="ltr"><svg class="lucide-chevron-right"></svg></div>'
    document.body.append(fixture)
    const values = [...fixture.querySelectorAll('svg')].map(node => getComputedStyle(node).scale)
    fixture.remove()
    return values
  })
  expect(scales[0]).toBe('-1 1')
  expect(scales[1]).toBe('none')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('calendar headings and Persian day numbers describe the same Gregorian month', async ({ page }) => {
  await page.goto('/calendar')
  await expect(page.getByRole('button', { name: fa['New event'], exact: true })).toBeVisible()
  const expected = await page.evaluate(() => {
    const now = new Date()
    return {
      title: new Intl.DateTimeFormat('fa', { calendar: 'gregory', year: 'numeric', month: 'long' }).format(now),
      key: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`,
      day: new Intl.NumberFormat('fa').format(now.getDate()),
    }
  })
  await expect(page.getByRole('heading', { name: expected.title, exact: true })).toBeVisible()
  // The first day includes its month name; compare its localized digit prefix.
  await expect(page.locator(`[data-cal-day="${expected.key}"] .dt-cal-cell-date`)).toContainText(expected.day)
})
