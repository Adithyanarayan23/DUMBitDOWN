/** Convert PDF-point bboxes to CSS overlay styles. */

export function bboxToStyle(bbox, scale) {
  if (!bbox || bbox.length < 4) return { display: 'none' };
  const [x0, y0, x1, y1] = bbox;
  return {
    position: 'absolute',
    left: x0 * scale,
    top: y0 * scale,
    width: Math.max(0, (x1 - x0) * scale),
    height: Math.max(0, (y1 - y0) * scale),
    pointerEvents: 'auto',
  };
}

/** Hit-test a point (PDF coords) against regions. Figures win over tables. */
export function hitTestRegions(point, pageNumber, tables = [], figures = []) {
  const [x, y] = point;
  const pageFigures = figures.filter((f) => f.page === pageNumber);
  for (const fig of pageFigures) {
    if (pointInBbox(x, y, fig.bbox)) {
      return { type: 'figure', id: fig.id, meta: fig };
    }
  }
  const pageTables = tables.filter((t) => t.page === pageNumber);
  for (const tbl of pageTables) {
    if (pointInBbox(x, y, tbl.bbox)) {
      return { type: 'table', id: tbl.id, meta: tbl };
    }
  }
  return null;
}

export function pointInBbox(x, y, bbox) {
  if (!bbox || bbox.length < 4) return false;
  const [x0, y0, x1, y1] = bbox;
  return x >= x0 && x <= x1 && y >= y0 && y <= y1;
}

/**
 * Convert a mouse event on a page wrapper into PDF-point coordinates.
 * pageEl should be the positioned wrapper containing the canvas.
 */
export function clientToPdfPoint(event, pageEl, scale) {
  if (!pageEl || !scale) return null;
  const rect = pageEl.getBoundingClientRect();
  const x = (event.clientX - rect.left) / scale;
  const y = (event.clientY - rect.top) / scale;
  return [x, y];
}
