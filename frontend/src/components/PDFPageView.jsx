import React, { useRef } from 'react';
import { Page } from 'react-pdf';
import RegionOverlay from './RegionOverlay';
import { useTextSelection } from '../hooks/useTextSelection';

/**
 * Single PDF page with text layer + table/figure overlays + zoom-safe highlight.
 */
function PDFPageView({
  pageNumber,
  scale,
  width,
  tables,
  figures,
  activeRegionId,
  highlightRects,
  onSelection,
  onRegion,
  onPageReady,
  clampElRef,
}) {
  const pageElRef = useRef(null);
  const pageTables = (tables || []).filter((t) => t.page === pageNumber);
  const pageFigures = (figures || []).filter((f) => f.page === pageNumber);

  const { handleMouseUp } = useTextSelection({
    pageNumber,
    pageElRef,
    clampElRef,
    scale,
    tables: pageTables,
    figures: pageFigures,
    onSelection,
    onRegion,
  });

  return (
    <div
      className="pdf-page-view"
      ref={pageElRef}
      onMouseUp={handleMouseUp}
      data-page={pageNumber}
    >
      <Page
        pageNumber={pageNumber}
        scale={scale}
        width={width}
        renderTextLayer
        renderAnnotationLayer={false}
        onRenderSuccess={() => onPageReady?.(pageElRef.current)}
        loading={<div className="pdf-page-loading">Loading page {pageNumber}…</div>}
      />
      {highlightRects?.length > 0 && (
        <div className="pdf-persist-highlight" aria-hidden>
          {highlightRects.map((r, i) => (
            <div
              key={i}
              className="pdf-persist-rect"
              style={{
                left: r.x * scale,
                top: r.y * scale,
                width: r.w * scale,
                height: r.h * scale,
              }}
            />
          ))}
        </div>
      )}
      {pageFigures.map((fig) => (
        <RegionOverlay
          key={fig.id}
          bbox={fig.bbox}
          scale={scale}
          kind="figure"
          label={fig.caption || `Figure · p${fig.page}`}
          active={activeRegionId === fig.id}
          onActivate={(e) =>
            onRegion?.(
              { type: 'figure', id: fig.id, meta: fig },
              { x: e.clientX, y: e.clientY }
            )
          }
        />
      ))}
      {pageTables.map((tbl) => (
        <RegionOverlay
          key={tbl.id}
          bbox={tbl.bbox}
          scale={scale}
          kind="table"
          label={tbl.caption || `Table · p${tbl.page}`}
          active={activeRegionId === tbl.id}
          onActivate={(e) =>
            onRegion?.(
              { type: 'table', id: tbl.id, meta: tbl },
              { x: e.clientX, y: e.clientY }
            )
          }
        />
      ))}
      <style>{`
        .pdf-page-view {
          position: relative;
          margin: 0 auto var(--space-md);
          box-shadow: 0 4px 24px rgba(0,0,0,0.35);
          background: #fff;
          width: fit-content;
          overflow: hidden;
          isolation: isolate;
        }
        .pdf-page-view .react-pdf__Page {
          position: relative;
          overflow: hidden !important;
        }
        .pdf-page-view .react-pdf__Page__canvas {
          display: block;
        }
        .pdf-page-view .textLayer {
          overflow: hidden !important;
          z-index: 2;
          line-height: 1;
        }
        .pdf-page-view .textLayer span,
        .pdf-page-view .textLayer br {
          color: transparent;
          pointer-events: all;
        }
        .pdf-page-view ::selection {
          background: rgba(212, 168, 83, 0.35);
          color: transparent;
        }
        .pdf-page-view ::-moz-selection {
          background: rgba(212, 168, 83, 0.35);
          color: transparent;
        }
        .pdf-persist-highlight {
          position: absolute;
          inset: 0;
          pointer-events: none;
          z-index: 3;
        }
        .pdf-persist-rect {
          position: absolute;
          background: rgba(212, 168, 83, 0.38);
          mix-blend-mode: multiply;
          border-radius: 1px;
        }
        .pdf-page-loading {
          padding: 40px;
          color: var(--color-parchment-3);
          font-size: 13px;
        }
      `}</style>
    </div>
  );
}

export default PDFPageView;
