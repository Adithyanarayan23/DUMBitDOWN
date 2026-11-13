import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

function useMobileSheet() {
  const [mobile, setMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 768px), (pointer: coarse)');
    const apply = () => setMobile(mq.matches);
    apply();
    mq.addEventListener?.('change', apply);
    return () => mq.removeEventListener?.('change', apply);
  }, []);
  return mobile;
}

/**
 * Compact selection action — anchored above highlight, stays over the PDF.
 */
function SelectionToolbar({ pos, onConfirm, onClose }) {
  const mobile = useMobileSheet();
  if (!pos && !mobile) return null;

  const sheetStyle = mobile
    ? {
        position: 'fixed',
        left: 0,
        right: 0,
        bottom: 0,
        transform: 'none',
        zIndex: 50,
        borderRadius: '14px 14px 0 0',
        padding: '12px 14px calc(12px + env(safe-area-inset-bottom))',
      }
    : {
        position: 'fixed',
        left: pos?.x ?? 0,
        top: pos?.y ?? 0,
        transform: 'translate(-50%, -100%)',
        zIndex: 40,
      };

  return (
    <motion.div
      className={`dumb-toolbar ${mobile ? 'sheet' : ''}`}
      initial={{ opacity: 0, y: mobile ? 24 : 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      style={sheetStyle}
      role="toolbar"
      aria-label="Dumb it down"
    >
      {mobile && <div className="sheet-handle" />}
      <button type="button" className="dumb-btn" onClick={onConfirm}>
        Dumb it down
      </button>
      <button type="button" className="dumb-dismiss" onClick={onClose} aria-label="Dismiss">
        ×
      </button>
      <style>{`
        .dumb-toolbar {
          display: inline-flex;
          align-items: center;
          gap: 0;
          padding: 2px;
          background: rgba(13, 8, 6, 0.94);
          border: 1px solid rgba(212, 168, 83, 0.45);
          border-radius: 6px;
          box-shadow: 0 4px 16px rgba(0,0,0,0.45);
          pointer-events: auto;
        }
        .dumb-toolbar.sheet { justify-content: center; width: 100%; }
        .sheet-handle {
          width: 32px;
          height: 3px;
          background: var(--color-gold-stitch);
          border-radius: 2px;
          margin: 0 auto 10px;
          flex-basis: 100%;
        }
        .dumb-btn {
          font-family: var(--font-serif);
          font-size: 13px;
          font-weight: 600;
          letter-spacing: 0.02em;
          color: var(--color-gold);
          background: transparent;
          border: none;
          padding: 7px 12px;
          border-radius: 4px;
          cursor: pointer;
          white-space: nowrap;
        }
        .dumb-btn:hover {
          background: var(--color-amber-tint);
          color: #E8C878;
        }
        .dumb-dismiss {
          font-family: var(--font-body);
          font-size: 15px;
          line-height: 1;
          color: var(--color-parchment-3);
          background: transparent;
          border: none;
          border-left: 1px solid var(--glass-border);
          padding: 7px 9px;
          cursor: pointer;
          border-radius: 0 4px 4px 0;
        }
        .dumb-dismiss:hover {
          color: var(--color-parchment);
          background: var(--glass-bg);
        }
      `}</style>
    </motion.div>
  );
}

export default SelectionToolbar;
export { useMobileSheet };
