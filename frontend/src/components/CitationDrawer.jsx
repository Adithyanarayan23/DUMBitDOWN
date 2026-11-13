import React, { useEffect, useRef } from 'react';
import { X, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { normalizeCitation } from '../utils/citations';
import glassStyles from '../styles/glass.module.css';
import { useFocusTrap } from '../hooks/useFocusTrap';

const drawerEase = [0.32, 0.72, 0, 1];

/**
 * CitationDrawer - Detail view for a selected source (snippet + links)
 */
function CitationDrawer({ citation, onClose }) {
  const drawerRef = useRef(null);
  useFocusTrap(drawerRef, Boolean(citation));

  useEffect(() => {
    if (!citation) return undefined;
    const previouslyFocused = document.activeElement;
    drawerRef.current?.focus();
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previouslyFocused?.focus?.();
    };
  }, [citation, onClose]);

  const normalized = citation ? normalizeCitation(citation) : null;
  const {
    title,
    authors,
    year,
    contribution,
    snippet,
    scholarUrl,
    pubmedUrl,
    arxivUrl,
    doiUrl,
    apa_citation,
  } = normalized || {};

  return (
    <AnimatePresence>
      {citation && normalized && (
        <motion.div
          className="citation-drawer-overlay"
          onClick={onClose}
          role="presentation"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.165, ease: drawerEase }}
        >
          <motion.aside
            ref={drawerRef}
            tabIndex={-1}
            className={`citation-drawer ${glassStyles.stitchedGlass}`}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Citation details"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.22, ease: drawerEase }}
          >
            <div className="drawer-header">
              <h3>Source detail</h3>
              <button type="button" className="drawer-close" onClick={onClose} aria-label="Close">
                <X size={18} aria-hidden="true" />
              </button>
            </div>

            <h4 className="drawer-title">{title}</h4>
            <p className="drawer-meta">
              {authors} · {year}
            </p>
            <p className="drawer-contrib">Contribution: {contribution.toFixed(1)}%</p>

            {snippet && (
              <div className="drawer-snippet">
                <div className="drawer-snippet-label">Retrieved chunk</div>
                <p>{snippet}</p>
              </div>
            )}

            {apa_citation && (
              <div className="drawer-apa">
                <code>{apa_citation}</code>
              </div>
            )}

            <div className="drawer-links">
              {scholarUrl && (
                <a href={scholarUrl} target="_blank" rel="noopener noreferrer">
                  Scholar <ExternalLink size={12} aria-hidden="true" />
                </a>
              )}
              {pubmedUrl && (
                <a href={pubmedUrl} target="_blank" rel="noopener noreferrer">
                  PubMed <ExternalLink size={12} aria-hidden="true" />
                </a>
              )}
              {arxivUrl && (
                <a href={arxivUrl} target="_blank" rel="noopener noreferrer">
                  arXiv <ExternalLink size={12} aria-hidden="true" />
                </a>
              )}
              {doiUrl && (
                <a href={doiUrl} target="_blank" rel="noopener noreferrer">
                  DOI <ExternalLink size={12} aria-hidden="true" />
                </a>
              )}
            </div>

            <style>{`
              .citation-drawer-overlay {
                position: fixed;
                inset: 0;
                background: rgba(0, 0, 0, 0.55);
                z-index: 120;
                display: flex;
                justify-content: flex-end;
              }
              .citation-drawer {
                width: min(420px, 100%);
                height: 100%;
                padding: var(--space-xl);
                overflow-y: auto;
                background: var(--color-void);
                overscroll-behavior: contain;
                outline: none;
              }
              .drawer-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: var(--space-lg);
              }
              .drawer-header h3 {
                font-family: var(--font-serif);
                color: var(--color-parchment);
                margin: 0;
              }
              .drawer-close {
                background: none;
                border: none;
                color: var(--color-parchment-2);
                cursor: pointer;
                padding: var(--space-xs);
              }
              @media (pointer: coarse) {
                .drawer-close {
                  min-width: 44px;
                  min-height: 44px;
                }
              }
              .drawer-title {
                font-family: var(--font-serif);
                color: var(--color-parchment);
                margin: 0 0 var(--space-sm);
                line-height: 1.4;
              }
              .drawer-meta, .drawer-contrib {
                font-family: var(--font-body);
                font-size: var(--t-caption);
                color: var(--color-parchment-2);
                margin: 0 0 var(--space-sm);
              }
              .drawer-snippet {
                margin: var(--space-lg) 0;
                padding: var(--space-md);
                background: var(--glass-bg);
                border-radius: var(--radius-md);
              }
              .drawer-snippet-label {
                font-size: var(--t-caption);
                color: var(--color-amber);
                letter-spacing: 0.04em;
                margin-bottom: var(--space-sm);
              }
              .drawer-snippet p {
                font-family: var(--font-body);
                font-size: var(--t-caption);
                color: var(--color-parchment);
                line-height: 1.6;
                margin: 0;
              }
              .drawer-apa {
                margin-bottom: var(--space-lg);
              }
              .drawer-apa code {
                font-size: var(--t-caption);
                color: var(--color-parchment-3);
                word-break: break-word;
              }
              .drawer-links {
                display: flex;
                flex-wrap: wrap;
                gap: var(--space-md);
              }
              .drawer-links a {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                color: var(--color-amber);
                font-size: var(--t-caption);
              }
            `}</style>
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default CitationDrawer;
