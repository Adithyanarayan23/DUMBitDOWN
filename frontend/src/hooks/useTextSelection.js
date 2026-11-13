import { useCallback, useRef, useState } from 'react';
import { clientToPdfPoint, hitTestRegions } from '../utils/bbox';
import {
  clientRectsToPageSpace,
  toolbarPosFromRects,
} from '../utils/selectionGeometry';

/**
 * Capture text selections and region clicks inside a PDF page wrapper.
 * Selection geometry is stored in page-space so highlights survive zoom.
 */
export function useTextSelection({
  pageNumber,
  pageElRef,
  scale,
  tables,
  figures,
  onSelection,
  onRegion,
  clampElRef,
}) {
  const [toolbarPos, setToolbarPos] = useState(null);
  const suppressUntil = useRef(0);

  const clear = useCallback(() => {
    setToolbarPos(null);
    window.getSelection()?.removeAllRanges();
  }, []);

  const handleMouseUp = useCallback(
    (event) => {
      if (Date.now() < suppressUntil.current) return;
      const pageEl = pageElRef?.current;
      if (!pageEl) return;

      const point = clientToPdfPoint(event, pageEl, scale);
      if (point) {
        const hit = hitTestRegions(point, pageNumber, tables, figures);
        if (hit) {
          window.getSelection()?.removeAllRanges();
          setToolbarPos(null);
          onRegion?.(hit, {
            x: event.clientX,
            y: event.clientY,
          });
          return;
        }
      }

      // Defer so browser finishes selection
      requestAnimationFrame(() => {
        const sel = window.getSelection();
        const text = sel?.toString()?.trim() || '';
        if (text.length < 10 || text.length > 5000) {
          setToolbarPos(null);
          return;
        }

        if (!sel.rangeCount) return;
        const range = sel.getRangeAt(0);
        if (!pageEl.contains(range.commonAncestorContainer)) {
          return;
        }

        const rects = clientRectsToPageSpace(range, pageEl, scale);
        if (!rects.length) {
          setToolbarPos(null);
          return;
        }

        const pos = toolbarPosFromRects(
          rects,
          pageEl,
          scale,
          clampElRef?.current
        );

        // Drop native selection — we paint a zoom-safe overlay instead
        window.getSelection()?.removeAllRanges();

        setToolbarPos(pos);
        onSelection?.({ text, page: pageNumber, rects, pos });
      });
    },
    [
      pageNumber,
      pageElRef,
      clampElRef,
      scale,
      tables,
      figures,
      onSelection,
      onRegion,
    ]
  );

  return { toolbarPos, setToolbarPos, handleMouseUp, clear, suppressUntil };
}
