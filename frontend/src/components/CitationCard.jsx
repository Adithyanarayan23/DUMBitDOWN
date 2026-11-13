import React from 'react';
import { ExternalLink, Check } from 'lucide-react';
import glassStyles from '../styles/glass.module.css';
import { normalizeCitation } from '../utils/citations';

/**
 * CitationCard - Glass card with wax seal, contribution bar, Scholar/PubMed/arXiv links
 */
function CitationCard({ citation, onSelect }) {
  const {
    title,
    authors,
    year,
    contribution,
    apa_citation,
    pubmedUrl,
    arxivUrl,
    doiUrl,
    scholarUrl,
  } = normalizeCitation(citation);

  const handleClick = () => {
    if (onSelect) onSelect(citation);
  };

  return (
    <div
      className={`citation-card ${glassStyles.stitchedGlass}${onSelect ? ' citation-card--clickable' : ''}`}
      onClick={handleClick}
      onKeyDown={onSelect ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleClick(); } } : undefined}
      role={onSelect ? 'button' : undefined}
      tabIndex={onSelect ? 0 : undefined}
    >
      <div className="wax-seal">
        <Check size={12} />
      </div>

      <h3 className="citation-title">{title}</h3>

      <p className="citation-meta">
        {authors}{year ? ` • ${year}` : ''}
      </p>

      <div className="contribution-section">
        <div className="contribution-label">
          Contribution: {contribution.toFixed(1)}%
        </div>
        <div className="contribution-track">
          <div
            className="contribution-fill"
            style={{
              transform: `scaleX(${Math.min(100, Math.max(0, contribution)) / 100})`,
            }}
          />
        </div>
      </div>

      {apa_citation && (
        <div className="apa-block">
          <code>{apa_citation}</code>
        </div>
      )}

      <div className="citation-links" onClick={(e) => e.stopPropagation()}>
        {scholarUrl && (
          <a
            href={scholarUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="citation-link"
          >
            Scholar
            <ExternalLink size={12} />
          </a>
        )}
        {pubmedUrl && (
          <a
            href={pubmedUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="citation-link"
          >
            PubMed
            <ExternalLink size={12} />
          </a>
        )}
        {arxivUrl && (
          <a
            href={arxivUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="citation-link"
          >
            arXiv
            <ExternalLink size={12} />
          </a>
        )}
        {doiUrl && (
          <a
            href={doiUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="citation-link"
          >
            DOI
            <ExternalLink size={12} />
          </a>
        )}
      </div>

      <style>{`
        .citation-card {
          position: relative;
          padding: var(--space-lg);
          margin-bottom: var(--space-md);
        }

        .citation-card--clickable {
          cursor: pointer;
        }

        .citation-card--clickable:hover {
          outline: 1px solid var(--color-gold);
        }

        .citation-card--clickable:focus-visible {
          outline: 2px solid var(--color-amber);
          outline-offset: 2px;
        }

        .wax-seal {
          position: absolute;
          top: var(--space-md);
          right: var(--space-md);
          width: 24px;
          height: 24px;
          background: var(--color-maroon);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--color-parchment);
          border: 2px solid var(--color-gold);
        }

        .citation-title {
          font-family: var(--font-serif);
          font-size: var(--t-body);
          font-weight: 600;
          color: var(--color-parchment);
          margin-bottom: var(--space-xs);
          padding-right: 40px;
          line-height: 1.4;
        }

        .citation-meta {
          font-family: var(--font-body);
          font-size: var(--t-caption);
          color: var(--color-parchment-2);
          margin-bottom: var(--space-md);
        }

        .contribution-section {
          margin-bottom: var(--space-md);
        }

        .contribution-label {
          font-family: var(--font-body);
          font-size: var(--t-caption);
          color: var(--color-parchment-2);
          margin-bottom: var(--space-xs);
        }

        .contribution-track {
          width: 100%;
          height: 4px;
          background: var(--glass-border);
          border-radius: 2px;
          overflow: hidden;
        }

        .contribution-fill {
          height: 100%;
          width: 100%;
          background: var(--color-parchment-3);
          border-radius: 2px;
          transform: scaleX(0);
          transform-origin: left center;
          transition: transform var(--transition-slow);
        }

        .apa-block {
          background: var(--glass-bg);
          border-radius: var(--radius-sm);
          padding: var(--space-sm) var(--space-md);
          margin-bottom: var(--space-md);
        }

        .apa-block code {
          font-family: 'Courier New', monospace;
          font-size: var(--t-caption);
          color: var(--color-parchment-3);
          line-height: 1.5;
          word-break: break-word;
        }

        .citation-links {
          display: flex;
          flex-wrap: wrap;
          gap: var(--space-md);
        }

        .citation-link {
          display: inline-flex;
          align-items: center;
          gap: var(--space-xs);
          font-family: var(--font-serif);
          font-size: var(--t-caption);
          color: var(--color-parchment-2);
          transition: color var(--transition-normal);
        }

        .citation-link:hover {
          color: var(--color-gold);
        }
      `}</style>
    </div>
  );
}

export default CitationCard;
