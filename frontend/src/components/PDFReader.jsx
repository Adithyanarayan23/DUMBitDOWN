import React, { useCallback, useEffect, useRef, useState } from 'react';
import '../utils/pdfSetup';
import { Document } from 'react-pdf';
import { ChevronLeft, ChevronRight, Minus, Plus } from 'lucide-react';
import PDFPageView from './PDFPageView';
import SelectionToolbar from './SelectionToolbar';
import RegionToolbar from './RegionToolbar';
import { toolbarPosFromRects } from '../utils/selectionGeometry';

import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

/**
 * PDF.js reader — highlight → Dumb it down.
 * Highlights persist across zoom via page-space rect overlays.
 */
function PDFReader({ file, manifest, onDumbDown, visionAvailable = true }) {
  const [numPages, setNumPages] = useState(null);
  const [page, setPage] = useState(1);
  const [scale, setScale] = useState(1.1);
  const [selection, setSelection] = useState(null); // { text, page, rects, pos }
  const [region, setRegion] = useState(null);
  const [regionPos, setRegionPos] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const scrollRef = useRef(null);
  const savedSelectionRef = useRef(null);

  const tables = manifest?.tables || [];
  const figures = manifest?.figures || [];

  const clearTools = () => {
    setSelection(null);
    setRegion(null);
    setRegionPos(null);
    savedSelectionRef.current = null;
    window.getSelection()?.removeAllRanges();
  };

  const repositionToolbar = useCallback(() => {
    const saved = savedSelectionRef.current;
    if (!saved?.rects?.length) return;
    const pageEl = scrollRef.current?.querySelector?.(
      `[data-page="${saved.page}"]`
    );
    if (!pageEl) return;
    const pos = toolbarPosFromRects(
      saved.rects,
      pageEl,
      scale,
      scrollRef.current
    );
    if (!pos) return;
    const next = { ...saved, pos };
    savedSelectionRef.current = next;
    setSelection((prev) => {
      if (
        prev?.text === next.text &&
        prev?.pos?.x === pos.x &&
        prev?.pos?.y === pos.y &&
        prev?.rects === next.rects
      ) {
        return prev;
      }
      return next;
    });
  }, [scale]);

  // Reposition after zoom / scroll / resize
  useEffect(() => {
    repositionToolbar();
    const el = scrollRef.current;
    if (!el) return undefined;
    const onScroll = () => repositionToolbar();
    el.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', repositionToolbar);
    return () => {
      el.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', repositionToolbar);
    };
  }, [repositionToolbar, scale, page]);

  const setZoom = (next) => {
    if (selection?.text && selection?.rects) {
      savedSelectionRef.current = {
        text: selection.text,
        page: selection.page,
        rects: selection.rects,
        pos: selection.pos,
      };
    }
    setScale(next);
  };

  return (
    <div className="pdf-reader">
      <div className="pdf-reader-toolbar">
        <button
          type="button"
          className="nav-btn"
          disabled={page <= 1}
          onClick={() => {
            clearTools();
            setPage((p) => Math.max(1, p - 1));
          }}
          aria-label="Previous page"
        >
          <ChevronLeft size={16} />
        </button>
        <span className="page-indicator">
          {page} / {numPages || manifest?.metadata?.pages || '—'}
        </span>
        <button
          type="button"
          className="nav-btn"
          disabled={!numPages || page >= numPages}
          onClick={() => {
            clearTools();
            setPage((p) => Math.min(numPages, p + 1));
          }}
          aria-label="Next page"
        >
          <ChevronRight size={16} />
        </button>
        <div className="zoom-group">
          <button
            type="button"
            className="nav-btn"
            onClick={() => setZoom(Math.max(0.7, +(scale - 0.1).toFixed(2)))}
            aria-label="Zoom out"
          >
            <Minus size={14} />
          </button>
          <span className="zoom-label">{Math.round(scale * 100)}%</span>
          <button
            type="button"
            className="nav-btn"
            onClick={() => setZoom(Math.min(2, +(scale + 0.1).toFixed(2)))}
            aria-label="Zoom in"
          >
            <Plus size={14} />
          </button>
        </div>
      </div>

      {manifest?.quality?.scanned_risk && (
        <div className="scanned-banner">
          This PDF may be scanned — text selection may not work well.
        </div>
      )}

      <div className="pdf-reader-scroll" ref={scrollRef}>
        {loadError && <div className="pdf-error">{loadError}</div>}
        <Document
          file={file}
          onLoadSuccess={({ numPages: n }) => {
            setNumPages(n);
            setLoadError(null);
          }}
          onLoadError={(err) => setLoadError(err?.message || 'Failed to load PDF')}
          loading={<div className="pdf-loading">Opening PDF…</div>}
        >
          <PDFPageView
            pageNumber={page}
            scale={scale}
            tables={tables}
            figures={figures}
            activeRegionId={region?.id}
            highlightRects={
              selection?.page === page ? selection.rects : null
            }
            clampElRef={scrollRef}
            onPageReady={repositionToolbar}
            onSelection={(sel) => {
              setRegion(null);
              setRegionPos(null);
              savedSelectionRef.current = sel;
              setSelection(sel);
            }}
            onRegion={(hit, pos) => {
              setSelection(null);
              savedSelectionRef.current = null;
              setRegion(hit);
              setRegionPos(pos);
            }}
          />
        </Document>
      </div>

      {selection?.text && selection?.pos && (
        <SelectionToolbar
          pos={selection.pos}
          onClose={clearTools}
          onConfirm={() => {
            onDumbDown?.({
              type: 'text',
              text: selection.text,
              page: selection.page,
            });
            clearTools();
          }}
        />
      )}

      {region && regionPos && (
        <RegionToolbar
          region={region}
          pos={regionPos}
          visionAvailable={visionAvailable}
          onClose={clearTools}
          onConfirm={() => {
            onDumbDown?.({
              type: region.type,
              id: region.id,
              page: region.meta?.page,
              label: region.meta?.caption,
            });
            clearTools();
          }}
        />
      )}

      <style>{`
        .pdf-reader {
          display: flex;
          flex-direction: column;
          height: 100%;
          min-height: 0;
        }
        .pdf-reader-toolbar {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          border-bottom: 1px solid var(--glass-border);
          flex-shrink: 0;
        }
        .nav-btn {
          background: var(--glass-bg);
          border: 1px solid var(--glass-border);
          color: var(--color-parchment);
          border-radius: 4px;
          padding: 4px 8px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
        }
        .nav-btn:disabled { opacity: 0.4; cursor: default; }
        .nav-btn:not(:disabled):hover {
          border-color: var(--color-gold);
          color: var(--color-gold);
        }
        .page-indicator, .zoom-label {
          font-size: 12px;
          color: var(--color-parchment-2);
          font-family: var(--font-body);
          font-weight: 500;
          letter-spacing: 0.02em;
          min-width: 48px;
          text-align: center;
          font-variant-numeric: tabular-nums;
        }
        .zoom-label {
          color: var(--color-gold);
          min-width: 40px;
        }
        .zoom-group {
          margin-left: auto;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .scanned-banner {
          font-family: var(--font-serif);
          font-size: 12px;
          color: var(--color-amber);
          background: var(--color-amber-tint);
          border-bottom: 1px solid var(--glass-border);
          padding: 8px 12px;
        }
        .pdf-reader-scroll {
          flex: 1;
          overflow: auto;
          padding: var(--space-md);
          min-height: 0;
          background: rgba(0,0,0,0.25);
        }
        .pdf-loading, .pdf-error {
          text-align: center;
          padding: 40px;
          color: var(--color-parchment-2);
        }
        .pdf-error { color: var(--color-error); }
      `}</style>
    </div>
  );
}

export default PDFReader;
