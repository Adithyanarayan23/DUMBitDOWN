/**
 * Helpers for zoom-safe PDF text selection highlights.
 * Rects are stored in unscaled page coordinates (PDF user space).
 */

export function clientRectsToPageSpace(range, pageEl, scale) {
  if (!range || !pageEl || !scale) return [];
  const pageRect = pageEl.getBoundingClientRect();
  const safeScale = scale || 1;
  return Array.from(range.getClientRects())
    .filter((r) => r.width >= 2 && r.height >= 2)
    .map((r) => ({
      x: (r.left - pageRect.left) / safeScale,
      y: (r.top - pageRect.top) / safeScale,
      w: r.width / safeScale,
      h: r.height / safeScale,
    }));
}

export function boundsOfRects(rects) {
  if (!rects?.length) return null;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const r of rects) {
    minX = Math.min(minX, r.x);
    minY = Math.min(minY, r.y);
    maxX = Math.max(maxX, r.x + r.w);
    maxY = Math.max(maxY, r.y + r.h);
  }
  return { minX, minY, maxX, maxY, midX: (minX + maxX) / 2, midY: (minY + maxY) / 2 };
}

/**
 * Place the floating toolbar above the selection, clamped inside the page
 * and the reader scroll pane so it never straddles the chat column.
 */
export function toolbarPosFromRects(rects, pageEl, scale, clampEl) {
  const bounds = boundsOfRects(rects);
  if (!bounds || !pageEl) return null;

  const pageRect = pageEl.getBoundingClientRect();
  const clampRect = clampEl?.getBoundingClientRect?.() || pageRect;
  const padX = 88;
  const padY = 36;

  let x = pageRect.left + bounds.midX * scale;
  let y = pageRect.top + bounds.minY * scale - 10;

  const left = Math.max(pageRect.left, clampRect.left) + padX;
  const right = Math.min(pageRect.right, clampRect.right) - padX;
  const top = Math.max(pageRect.top, clampRect.top) + padY;
  const bottom = Math.min(pageRect.bottom, clampRect.bottom) - 8;

  if (right > left) {
    x = Math.min(Math.max(x, left), right);
  } else {
    x = (Math.max(pageRect.left, clampRect.left) + Math.min(pageRect.right, clampRect.right)) / 2;
  }

  // Prefer above selection; if clipped, sit just below the first line
  if (y < top) {
    y = pageRect.top + bounds.minY * scale + Math.min(bounds.maxY - bounds.minY, 28) * scale + 12;
  }
  y = Math.min(Math.max(y, top), bottom);

  return { x, y };
}
