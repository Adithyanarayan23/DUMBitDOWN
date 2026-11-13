import React, { useState, useEffect, useCallback } from 'react';
import { ChevronDown, ChevronUp, BookOpen, AlertCircle, Layers } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import StreamingText from './StreamingText';
import TermTooltip from './TermTooltip';
import glassStyles from '../styles/glass.module.css';

/**
 * Exchange - Conversation thread with before/after + live SSE text
 * States: idle → loading → streaming → complete → error
 */
function Exchange({
  query,
  responseData,
  onFollowUp,
  isFollowUp = false,
  conversationId,
  showFollowUp = false,
  loading = false,
  exchangeId,
  onOpenSources,
}) {
  const [state, setState] = useState('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [showPipeline, setShowPipeline] = useState(false);
  const [expandOriginal, setExpandOriginal] = useState(false);
  const [followUpText, setFollowUpText] = useState('');
  const [responseText, setResponseText] = useState('');
  const [citations, setCitations] = useState({ sources: [], total: 0 });
  const [technicalTerms, setTechnicalTerms] = useState([]);
  const [pipeline, setPipeline] = useState(null);

  const getResponseText = (data) =>
    data?.simplified_text ?? data?.answer ?? data?.streamText ?? '';

  useEffect(() => {
    if (loading && !responseData) {
      setState('loading');
      return;
    }

    if (!responseData) {
      setState('idle');
      return;
    }

    if (responseData.error) {
      setState('error');
      setErrorMessage(responseData.error.detail || 'An error occurred');
      return;
    }

    const text = getResponseText(responseData);
    const terms = responseData.technical_terms || [];
    const cites = responseData.citations || { sources: [], total: 0 };

    setResponseText(text);
    setTechnicalTerms(terms);
    setCitations(cites);
    setPipeline(responseData.pipeline || null);

    if (responseData.streaming) {
      setState('streaming');
    } else if (text) {
      setState('complete');
    } else if (loading) {
      setState('loading');
    }
  }, [responseData, loading]);

  const handleFollowUpSubmit = (e) => {
    e.preventDefault();
    if (!followUpText.trim() || !conversationId) return;
    onFollowUp?.(followUpText);
    setFollowUpText('');
  };

  const renderTextWithTooltips = useCallback((text, terms) => {
    if (!terms || terms.length === 0) {
      return <span>{text}</span>;
    }
    const escapedTerms = terms.map((t) =>
      t.term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    );
    const pattern = new RegExp(`\\b(${escapedTerms.join('|')})\\b`, 'gi');
    const parts = text.split(pattern);

    return parts.map((part, index) => {
      const matchingTerm = terms.find(
        (t) => t.term.toLowerCase() === part.toLowerCase()
      );
      if (matchingTerm) {
        return (
          <TermTooltip
            key={index}
            term={matchingTerm.term}
            definition={matchingTerm.definition}
          />
        );
      }
      return <span key={index}>{part}</span>;
    });
  }, []);

  const originalPreview =
    query && query.length > 220 && !expandOriginal
      ? `${query.slice(0, 220)}…`
      : query;

  return (
    <motion.div
      id={exchangeId ? `exchange-${exchangeId}` : undefined}
      className={`exchange ${isFollowUp ? 'exchange-followup' : ''}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, ease: [0.23, 1, 0.32, 1] }}
    >
      <div className="query-bubble">
        <div className="query-content">{query}</div>
      </div>

      <div className={`response-block ${glassStyles.stitchedGlass}`}>
        {state === 'error' && (
          <div className={glassStyles.error}>
            <AlertCircle size={20} />
            <span>{errorMessage}</span>
          </div>
        )}

        {state === 'loading' && (
          <div className="loading-state">
            <div className={glassStyles.spinner} />
            <span>Retrieving & simplifying…</span>
          </div>
        )}

        {(state === 'streaming' || state === 'complete') && (
          <>
            {!isFollowUp && query?.startsWith('PDF:') ? (
              <div className="pdf-result">
                <div className="ba-label">Simplified from {query.replace(/^PDF:\s*/, '')}</div>
                <div
                  className="response-text"
                  aria-live={state === 'streaming' ? 'polite' : 'off'}
                  aria-atomic="false"
                >
                  {state === 'streaming' ? (
                    <StreamingText
                      text={responseText}
                      technicalTerms={technicalTerms}
                      renderWithTooltips={technicalTerms.length > 0}
                      TermTooltipComponent={TermTooltip}
                    />
                  ) : (
                    renderTextWithTooltips(responseText, technicalTerms)
                  )}
                </div>
              </div>
            ) : !isFollowUp ? (
              <div className="before-after">
                <div className="ba-col ba-original">
                  <div className="ba-label">Original</div>
                  <p className="ba-body">{originalPreview}</p>
                  {query && query.length > 220 && (
                    <button
                      type="button"
                      className="ba-expand"
                      onClick={() => setExpandOriginal((v) => !v)}
                    >
                      {expandOriginal ? 'Show less' : 'Show more'}
                    </button>
                  )}
                </div>
                <div className="ba-col ba-simplified">
                  <div className="ba-label">Simplified</div>
                  <div
                    className="response-text"
                    aria-live={state === 'streaming' ? 'polite' : 'off'}
                    aria-atomic="false"
                  >
                    {state === 'streaming' ? (
                      <StreamingText
                        text={responseText}
                        technicalTerms={technicalTerms}
                        renderWithTooltips={technicalTerms.length > 0}
                        TermTooltipComponent={TermTooltip}
                      />
                    ) : (
                      renderTextWithTooltips(responseText, technicalTerms)
                    )}
                  </div>
                </div>
              </div>
            ) : null}

            {isFollowUp && (
              <div
                className="response-text"
                aria-live={state === 'streaming' ? 'polite' : 'off'}
                aria-atomic="false"
              >
                {state === 'streaming' ? (
                  <StreamingText text={responseText} />
                ) : (
                  renderTextWithTooltips(responseText, technicalTerms)
                )}
              </div>
            )}

            {state === 'complete' && citations.sources?.length > 0 && (
              <div className="sources-section">
                <button
                  type="button"
                  className="sources-toggle sources-toggle-primary"
                  onClick={() => onOpenSources?.()}
                >
                  <BookOpen size={16} aria-hidden="true" />
                  <span>View sources ({citations.total || citations.sources.length})</span>
                </button>
              </div>
            )}

            {state === 'complete' && pipeline && (
              <div className="pipeline-section">
                <button
                  type="button"
                  className="sources-toggle"
                  onClick={() => setShowPipeline(!showPipeline)}
                >
                  <Layers size={16} />
                  <span>How this answer was built</span>
                  {showPipeline ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
                <AnimatePresence>
                  {showPipeline && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="pipeline-body"
                    >
                      <p>
                        <strong>Model:</strong> {pipeline.model || '—'}
                      </p>
                      <p>
                        <strong>Query rewrite:</strong>{' '}
                        {pipeline.rewritten_query || 'skipped (paste / short query)'}
                      </p>
                      {pipeline.top_scores?.length > 0 && (
                        <p>
                          <strong>Top scores:</strong>{' '}
                          {pipeline.top_scores.join(', ')}
                        </p>
                      )}
                      {pipeline.contributions?.length > 0 && (
                        <ul className="pipeline-contrib">
                          {pipeline.contributions.map((c, i) => (
                            <li key={i}>
                              {c.title} — {c.contribution}%
                            </li>
                          ))}
                        </ul>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}

            {state === 'complete' && showFollowUp && (
              <form onSubmit={handleFollowUpSubmit} className="followup-form">
                <input
                  type="text"
                  value={followUpText}
                  onChange={(e) => setFollowUpText(e.target.value)}
                  aria-label="Ask a follow-up question"
                  placeholder="Ask about this response..."
                  className="followup-input"
                  disabled={state === 'loading'}
                />
                <button
                  type="submit"
                  className={glassStyles.glassButton}
                  disabled={!followUpText.trim()}
                >
                  Ask
                </button>
              </form>
            )}
          </>
        )}
      </div>

      <style>{`
        .exchange { margin-bottom: var(--space-xl); }
        .exchange-followup { margin-left: var(--space-2xl); }
        .query-bubble {
          display: flex;
          justify-content: flex-end;
          margin-bottom: var(--space-md);
        }
        .query-content {
          background: var(--color-parchment);
          color: var(--color-void);
          font-family: var(--font-body);
          font-size: var(--t-body);
          padding: var(--space-md) var(--space-lg);
          border-radius: var(--radius-xl);
          max-width: 80%;
          word-wrap: break-word;
        }
        .response-block {
          padding: var(--space-xl);
          min-height: 100px;
        }
        .loading-state {
          display: flex;
          align-items: center;
          gap: var(--space-md);
          color: var(--color-parchment-2);
          font-family: var(--font-body);
        }
        .before-after {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: var(--space-lg);
          margin-bottom: var(--space-lg);
        }
        .pdf-result {
          margin-bottom: var(--space-lg);
        }
        .pdf-result .response-text {
          margin-top: var(--space-sm);
        }
        @media (max-width: 768px) {
          .before-after { grid-template-columns: 1fr; }
          .exchange-followup { margin-left: 0; }
        }
        .ba-label {
          font-family: var(--font-serif);
          font-size: var(--t-caption);
          color: var(--color-parchment-3);
          text-transform: uppercase;
          letter-spacing: 0.06em;
          margin-bottom: var(--space-sm);
        }
        .ba-original .ba-body {
          font-family: var(--font-serif);
          font-size: var(--t-caption);
          color: var(--color-parchment);
          line-height: 1.6;
          opacity: 0.85;
        }
        .ba-expand {
          background: none;
          border: none;
          color: var(--color-parchment-2);
          font-family: var(--font-serif);
          font-size: var(--t-caption);
          cursor: pointer;
          padding: var(--space-xs) 0;
        }
        @media (pointer: coarse) {
          .ba-expand,
          .sources-toggle {
            min-height: 44px;
          }
        }
        .response-text {
          font-family: var(--font-serif);
          font-size: 16px;
          font-weight: 400;
          color: var(--color-parchment);
          line-height: 1.6;
          white-space: pre-wrap;
        }
        .sources-section, .pipeline-section {
          margin-top: var(--space-lg);
          border-top: 1px solid var(--glass-border);
          padding-top: var(--space-md);
        }
        .sources-toggle {
          display: flex;
          align-items: center;
          gap: var(--space-sm);
          color: var(--color-parchment-2);
          font-family: var(--font-body);
          font-size: var(--t-caption);
          background: none;
          border: none;
          cursor: pointer;
          padding: var(--space-sm) 0;
        }
        .sources-toggle:hover { color: var(--color-parchment); }
        .sources-toggle-primary {
          color: var(--color-gold);
          border: 1px solid var(--glass-border-heavy);
          border-radius: var(--radius-md);
          padding: var(--space-sm) var(--space-md);
        }
        .sources-toggle-primary:hover {
          border-color: var(--color-gold);
          color: var(--color-parchment);
        }
        .source-item {
          padding: var(--space-md);
          border-bottom: 1px solid var(--glass-border);
        }
        .source-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: var(--space-md);
          margin-bottom: var(--space-xs);
        }
        .source-title {
          font-family: var(--font-serif);
          font-size: var(--t-body);
          font-weight: 600;
          color: var(--color-parchment);
        }
        .contribution-bar {
          height: 4px;
          background: var(--color-parchment-3);
          border-radius: 2px;
          max-width: 100px;
          flex-shrink: 0;
        }
        .source-meta {
          font-family: var(--font-body);
          font-size: var(--t-caption);
          color: var(--color-parchment-2);
        }
        .pipeline-body {
          font-family: var(--font-body);
          font-size: var(--t-caption);
          color: var(--color-parchment-2);
          line-height: 1.6;
          padding: var(--space-sm) 0;
        }
        .pipeline-body strong { color: var(--color-parchment); }
        .pipeline-contrib {
          margin: var(--space-sm) 0 0;
          padding-left: var(--space-lg);
        }
        .followup-form {
          display: flex;
          gap: var(--space-md);
          margin-top: var(--space-lg);
          padding-top: var(--space-md);
          border-top: 1px solid var(--glass-border);
        }
        .followup-input {
          flex: 1;
          padding: var(--space-sm) var(--space-md);
          background: var(--glass-bg);
          border: 1px solid var(--glass-border);
          border-radius: var(--radius-md);
          color: var(--color-parchment);
          font-family: var(--font-body);
          font-size: var(--t-body);
        }
        .followup-input::placeholder { color: var(--color-parchment-3); }
        .followup-input:focus {
          outline: none;
          border-color: var(--color-gold);
        }
        .followup-input:focus-visible {
          outline: 2px solid var(--color-gold);
          outline-offset: 2px;
        }
        .followup-form button { padding: var(--space-sm) var(--space-lg); }
      `}</style>
    </motion.div>
  );
}

export default Exchange;
