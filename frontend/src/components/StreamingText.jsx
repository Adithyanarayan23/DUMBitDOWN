import React from 'react';

/**
 * StreamingText - Renders live token stream (or final text).
 * No fake RAF reveal; text grows as tokens arrive from SSE.
 */
function StreamingText({
  text = '',
  technicalTerms = [],
  renderWithTooltips = false,
  TermTooltipComponent = null,
}) {
  if (!text) {
    return <span className="streaming-text streaming-text--empty" />;
  }

  if (renderWithTooltips && technicalTerms?.length > 0 && TermTooltipComponent) {
    const escapedTerms = technicalTerms.map((t) =>
      t.term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    );
    const pattern = new RegExp(`\\b(${escapedTerms.join('|')})\\b`, 'gi');
    const parts = text.split(pattern);

    return (
      <span className="streaming-text">
        {parts.map((part, index) => {
          const matchingTerm = technicalTerms.find(
            (t) => t.term.toLowerCase() === part.toLowerCase()
          );
          if (matchingTerm) {
            return (
              <TermTooltipComponent
                key={index}
                term={matchingTerm.term}
                definition={matchingTerm.definition}
              />
            );
          }
          return <span key={index}>{part}</span>;
        })}
      </span>
    );
  }

  return <span className="streaming-text">{text}</span>;
}

export default StreamingText;
