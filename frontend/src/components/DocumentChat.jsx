import React, { useEffect, useRef, useState } from 'react';
import { Send } from 'lucide-react';
import glassStyles from '../styles/glass.module.css';
import StreamingText from './StreamingText';
import TermTooltip from './TermTooltip';

/**
 * Document-mode chat: compact answers with inline term tooltips.
 */
function DocumentChat({
  messages,
  loading,
  onFollowUp,
  followUpLoading,
  conversationReady,
}) {
  const endRef = useRef(null);
  const [question, setQuestion] = useState('');

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const q = question.trim();
    if (!q || followUpLoading || !conversationReady) return;
    onFollowUp?.(q);
    setQuestion('');
  };

  return (
    <aside className="doc-chat">
      <header className="doc-chat-header">
        <h2>Chat</h2>
      </header>

      <div className="doc-chat-messages">
        {messages.length === 0 && !loading && (
          <p className="doc-chat-empty">
            Highlight text, then <em>Dumb it down</em> — or simplify the whole paper up top.
          </p>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`doc-msg ${msg.role === 'user' ? 'user' : 'assistant'}`}
          >
            {msg.role === 'user' && (
              <>
                {msg.label && (
                  <span className={`doc-msg-chip ${msg.kind || ''} ${msg.role === 'assistant' ? 'muted' : ''}`}>
                    {msg.label}
                  </span>
                )}
                <p className="doc-msg-text user-bubble">{msg.content}</p>
              </>
            )}
            {msg.role === 'assistant' && (
              <>
                {msg.label && (
                  <span className={`doc-msg-chip ${msg.kind || ''} muted`}>{msg.label}</span>
                )}
                {msg.loading && !msg.content ? (
                  <div className="doc-msg-loading">
                    <div className={glassStyles.spinner} />
                    <span>Dumbing it down…</span>
                  </div>
                ) : (
                  <div className="doc-msg-text">
                    {!msg.loading && msg.technical_terms?.length > 0 ? (
                      <StreamingText
                        text={msg.content || ''}
                        technicalTerms={msg.technical_terms}
                        renderWithTooltips
                        TermTooltipComponent={TermTooltip}
                      />
                    ) : (
                      (msg.content || '').split('\n').map((line, i) => (
                        <p key={i}>{line || '\u00A0'}</p>
                      ))
                    )}
                    {msg.loading && <span className="cursor-blink">▍</span>}
                  </div>
                )}
                {msg.warning && <p className="doc-msg-warn">{msg.warning}</p>}
                {msg.error && <p className="doc-msg-error">{msg.error}</p>}
              </>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <form className="doc-chat-composer" onSubmit={handleSubmit}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={
            conversationReady ? 'Ask a follow-up…' : 'Dumb something down to start chatting'
          }
          disabled={!conversationReady || followUpLoading}
          aria-label="Follow-up question"
        />
        <button
          type="submit"
          disabled={!conversationReady || followUpLoading || !question.trim()}
          aria-label="Send"
        >
          <Send size={14} />
        </button>
      </form>

      <style>{`
        .doc-chat {
          display: flex;
          flex-direction: column;
          height: 100%;
          min-height: 0;
        }
        .doc-chat-header {
          padding: 10px 12px 6px;
          border-bottom: 1px solid var(--glass-border);
          flex-shrink: 0;
        }
        .doc-chat-header h2 {
          margin: 0;
          font-family: var(--font-serif);
          font-size: 16px;
          font-weight: 500;
          color: var(--color-parchment);
        }
        .doc-chat-header h2::after {
          content: '';
          display: block;
          width: 24px;
          height: 2px;
          margin-top: 5px;
          background: var(--color-gold);
          border-radius: 1px;
        }
        .doc-chat-messages {
          flex: 1;
          overflow-y: auto;
          padding: 10px 12px;
          min-height: 0;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .doc-chat-empty {
          margin: 20px 0;
          font-family: var(--font-serif);
          font-size: 15px;
          line-height: 1.5;
          color: var(--color-parchment-3);
        }
        .doc-chat-empty em {
          font-style: italic;
          color: var(--color-gold);
        }
        .doc-msg.user .user-bubble {
          background: var(--glass-bg);
          border: 1px solid var(--glass-border);
          border-radius: 8px;
          padding: 8px 10px;
          font-family: var(--font-serif);
          font-size: 13px;
          color: var(--color-parchment-2);
          margin: 4px 0 0;
          white-space: pre-wrap;
        }
        .doc-msg.assistant .doc-msg-text {
          font-family: var(--font-serif);
          font-size: 15px;
          line-height: 1.55;
          color: var(--color-parchment);
          white-space: pre-wrap;
        }
        .doc-msg.assistant .doc-msg-text p { margin: 0 0 0.45em; }
        .doc-msg-chip {
          display: inline-block;
          font-family: var(--font-body);
          font-size: 10px;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          color: var(--color-parchment-3);
          border: 1px solid rgba(212, 168, 83, 0.3);
          padding: 2px 7px;
          border-radius: 999px;
          margin-bottom: 4px;
          max-width: 100%;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          background: transparent;
        }
        .doc-msg-chip.whole {
          color: var(--color-gold);
          border-color: rgba(212, 168, 83, 0.5);
        }
        .doc-msg-chip.text,
        .doc-msg-chip.table,
        .doc-msg-chip.figure {
          color: var(--color-parchment-2);
        }
        .doc-msg-chip.muted { opacity: 0.85; }
        .doc-msg-loading {
          display: flex;
          align-items: center;
          gap: 8px;
          font-family: var(--font-serif);
          font-size: 13px;
          color: var(--color-parchment-2);
        }
        .cursor-blink {
          animation: blink 1s step-end infinite;
          color: var(--color-parchment-3);
        }
        @keyframes blink { 50% { opacity: 0; } }
        .doc-msg-warn {
          margin: 6px 0 0;
          font-size: 12px;
          color: var(--color-parchment-3);
        }
        .doc-msg-error {
          margin: 6px 0 0;
          font-size: 13px;
          color: var(--color-error);
        }
        .doc-chat-composer {
          display: flex;
          gap: 8px;
          padding: 6px 10px 10px;
          border-top: 1px solid var(--glass-border);
          flex-shrink: 0;
        }
        .doc-chat-composer input {
          flex: 1;
          min-width: 0;
          height: 32px;
          padding: 0 10px;
          font-family: var(--font-serif);
          font-size: 14px;
          color: var(--color-parchment);
          background: var(--glass-bg);
          border: 1px solid var(--glass-border);
          border-radius: 7px;
        }
        .doc-chat-composer input:disabled { opacity: 0.5; }
        .doc-chat-composer button {
          width: 32px;
          height: 32px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          background: transparent;
          color: var(--color-parchment-2);
          border: 1px solid var(--glass-border);
          border-radius: 7px;
          cursor: pointer;
          flex-shrink: 0;
        }
        .doc-chat-composer button:hover:not(:disabled) {
          color: var(--color-gold);
          border-color: rgba(212, 168, 83, 0.5);
        }
        .doc-chat-composer button:disabled {
          opacity: 0.35;
          cursor: default;
        }
      `}</style>
    </aside>
  );
}

export default DocumentChat;
