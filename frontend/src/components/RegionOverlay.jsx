import React from 'react';
import { bboxToStyle } from '../utils/bbox';

/**
 * Quiet dashed overlay — badge only on hover/active.
 */
function RegionOverlay({ bbox, scale, kind, label, active, onActivate }) {
  const style = bboxToStyle(bbox, scale);
  const short =
    kind === 'table'
      ? 'Table'
      : label?.toLowerCase?.().includes('caption')
        ? 'Figure · caption'
        : 'Figure';

  return (
    <div
      className={`region-overlay region-${kind} ${active ? 'active' : ''}`}
      style={{ ...style, pointerEvents: 'none', zIndex: 3 }}
      aria-hidden={!active}
    >
      <button
        type="button"
        className="region-badge"
        style={{ pointerEvents: 'auto' }}
        title={label || kind}
        aria-label={label || (kind === 'table' ? 'Analyze table' : 'Analyze figure')}
        onClick={(e) => {
          e.stopPropagation();
          onActivate?.(e);
        }}
      >
        {short}
      </button>
      <style>{`
        .region-overlay {
          border: 1px dashed rgba(212, 168, 83, 0.18);
          background: transparent;
          padding: 0;
          margin: 0;
          transition: border-color 0.15s ease, background 0.15s ease;
        }
        .region-overlay:hover,
        .region-overlay.active {
          border-color: rgba(212, 168, 83, 0.55);
          background: rgba(212, 168, 83, 0.06);
        }
        .region-overlay.region-figure:hover,
        .region-overlay.region-figure.active {
          border-color: rgba(212, 168, 83, 0.65);
        }
        .region-badge {
          position: absolute;
          top: -16px;
          left: 0;
          font-family: var(--font-body);
          font-size: 10px;
          letter-spacing: 0.02em;
          color: var(--color-void);
          background: var(--color-gold);
          padding: 2px 6px;
          border-radius: 3px;
          border: none;
          cursor: pointer;
          white-space: nowrap;
          max-width: 160px;
          overflow: hidden;
          text-overflow: ellipsis;
          opacity: 0.4;
          transition: opacity 0.15s ease;
          z-index: 4;
        }
        .region-overlay:hover .region-badge,
        .region-overlay.active .region-badge {
          opacity: 1;
        }
        .region-overlay.region-table .region-badge {
          background: var(--color-amber);
        }
      `}</style>
    </div>
  );
}

export default RegionOverlay;
