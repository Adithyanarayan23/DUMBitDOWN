import React from 'react';
import { motion } from 'framer-motion';
import { useMobileSheet } from './SelectionToolbar';

/**
 * Quiet region prompt — Dumb it down only.
 */
function RegionToolbar({ region, pos, onConfirm, onClose, visionAvailable = true }) {
  const mobile = useMobileSheet();
  if (!region || (!pos && !mobile)) return null;

  const title =
    region.meta?.caption ||
    (region.type === 'table'
      ? `Table · page ${region.meta?.page}`
      : `Figure · page ${region.meta?.page}`);

  const style = mobile
    ? {
        position: 'fixed',
        left: 0,
        right: 0,
        bottom: 0,
        transform: 'none',
        zIndex: 50,
        borderRadius: '14px 14px 0 0',
        maxWidth: 'none',
        padding: '12px 14px calc(12px + env(safe-area-inset-bottom))',
      }
    : {
        position: 'fixed',
        left: Math.min(Math.max(pos.x, 120), window.innerWidth - 160),
        top: Math.max(48, pos.y - 8),
        transform: 'translate(-50%, -100%)',
        zIndex: 40,
      };

  return (
    <motion.div
      className={`region-dumb-toolbar ${mobile ? 'sheet' : ''}`}
      initial={{ opacity: 0, y: mobile ? 24 : 4 }}
      animate={{ opacity: 1, y: 0 }}
      style={style}
      role="toolbar"
      aria-label="Dumb it down"
    >
      {mobile && <div className="sheet-handle" />}
      <div className="region-title">{title}</div>
      <div className="region-actions">
        <button type="button" className="dumb-btn" onClick={onConfirm}>
          Dumb it down
        </button>
        <button type="button" className="dumb-dismiss" onClick={onClose} aria-label="Dismiss">
          ×
        </button>
      </div>
      {region.type === 'table' && (region.meta?.confidence ?? 1) < 0.5 && (
        <div className="region-warn">Detection uncertain — try selecting the text instead</div>
      )}
      {region.type === 'figure' && !visionAvailable && (
        <div className="region-warn">Caption-only (figure vision needs Gemini)</div>
      )}
      <style>{`
        .region-dumb-toolbar {
          min-width: 160px;
          max-width: 280px;
          padding: 6px 8px;
          background: rgba(13, 8, 6, 0.94);
          border: 1px solid rgba(212, 168, 83, 0.45);
          border-radius: 6px;
          box-shadow: 0 4px 16px rgba(0,0,0,0.45);
        }
        .region-dumb-toolbar.sheet { max-width: none; }
        .sheet-handle {
          width: 32px;
          height: 3px;
          background: var(--glass-border);
          border-radius: 2px;
          margin: 0 auto 8px;
        }
        .region-title {
          font-family: var(--font-serif);
          font-size: 12px;
          color: var(--color-parchment-3);
          margin-bottom: 4px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .region-actions {
          display: flex;
          align-items: center;
          gap: 2px;
        }
        .dumb-btn {
          font-family: var(--font-serif);
          font-size: 13px;
          font-weight: 600;
          color: var(--color-gold);
          background: transparent;
          border: none;
          padding: 6px 10px;
          border-radius: 4px;
          cursor: pointer;
        }
        .dumb-btn:hover { background: var(--color-amber-tint); color: #E8C878; }
        .dumb-dismiss {
          font-size: 16px;
          color: var(--color-parchment-3);
          background: transparent;
          border: none;
          padding: 4px 8px;
          cursor: pointer;
          border-radius: 6px;
        }
        .region-warn {
          margin-top: 4px;
          font-size: 11px;
          color: var(--color-parchment-3);
        }
      `}</style>
    </motion.div>
  );
}

export default RegionToolbar;
