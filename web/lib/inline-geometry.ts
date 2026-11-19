/** Bridge physical pointer coordinates to a layout's logical inline axis. */
export function inlineDirection(element: Element): 1 | -1 {
  const direction = getComputedStyle(element).direction;
  if (direction === "rtl") return -1;
  if (direction === "ltr") return 1;
  // Useful for detached elements and DOM implementations without inheritance.
  return element.closest('[dir]')?.getAttribute('dir') === 'rtl' ? -1 : 1;
}

/** Unclamped: callers decide whether to clamp, snap, or reject outside points. */
export function inlineRatio(element: Element, clientX: number): number {
  const rect = element.getBoundingClientRect();
  if (rect.width <= 0) return 0;
  return inlineDirection(element) === -1
    ? (rect.right - clientX) / rect.width
    : (clientX - rect.left) / rect.width;
}

/** Works even when DOM order runs right-to-left or the pointer leaves a row. */
export function nearestColumn<T extends Element>(columns: T[], clientX: number): T | null {
  let best: T | null = null;
  let distance = Infinity;
  for (const column of columns) {
    const rect = column.getBoundingClientRect();
    if (rect.width <= 0) continue;
    const next = Math.max(rect.left - clientX, clientX - rect.right, 0);
    if (next < distance) {
      best = column;
      distance = next;
    }
  }
  return best;
}
