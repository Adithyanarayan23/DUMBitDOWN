import React, { useMemo, useState } from 'react';
import { Plus, MessageSquare, Clock, Trash2 } from 'lucide-react';
import glassStyles from '../styles/glass.module.css';

/**
 * SessionHistory - Left sidebar: server sessions + in-session optimistic items
 */
function SessionHistory({
  exchanges,
  serverSessions = [],
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
}) {
  const conversations = useMemo(() => {
    const byId = new Map();

    for (const s of serverSessions) {
      byId.set(s.id, {
        id: s.id,
        title: s.title || 'Conversation',
        timestamp: s.updated_at || s.created_at || new Date(),
        isActive: s.id === activeConversationId,
        fromServer: true,
      });
    }

    for (const exchange of exchanges) {
      const id = exchange.conversation_id;
      if (!id || String(id).startsWith('temp-')) continue;
      if (!byId.has(id)) {
        byId.set(id, {
          id,
          title:
            exchange.query.slice(0, 50) +
            (exchange.query.length > 50 ? '…' : ''),
          timestamp: exchange.timestamp || new Date(),
          isActive: id === activeConversationId,
          fromServer: false,
        });
      } else {
        const existing = byId.get(id);
        existing.isActive = id === activeConversationId;
      }
    }

    return Array.from(byId.values()).map((c) => ({
      ...c,
      isActive: c.id === activeConversationId,
    }));
  }, [exchanges, serverSessions, activeConversationId]);

  const [pendingDeleteId, setPendingDeleteId] = useState(null);

  const state =
    conversations.length === 0 ? 'empty' : 'list';

  const getRelativeTime = (timestamp) => {
    const now = new Date();
    const past = new Date(timestamp);
    const diffMs = now - past;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (Number.isNaN(diffMins) || diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hr ago`;
    if (diffDays < 7) return `${diffDays} day ago`;
    return past.toLocaleDateString();
  };

  return (
    <div className={`session-history ${glassStyles.stitchedGlass}`}>
      <div className="session-header">
        <h2 className="session-title">Session</h2>
        {conversations.length > 0 && (
          <span className="session-count">{conversations.length}</span>
        )}
      </div>

      <button
        className={`${glassStyles.glassButton} new-chat-button`}
        onClick={onNewChat}
        type="button"
      >
        <Plus size={16} aria-hidden="true" />
        New Chat
      </button>

      <div className="session-content">
        {state === 'empty' && (
          <div className="empty-state">
            <MessageSquare size={32} className="empty-icon" aria-hidden="true" />
            <p className="empty-text">
              <em>Paste a passage or upload a PDF to start.</em>
            </p>
          </div>
        )}

        {state === 'list' && (
          <ul className="conversation-list">
            {conversations.map((conv) => (
              <li
                key={conv.id}
                className={`conversation-item ${conv.isActive ? 'active' : ''}`}
              >
                {pendingDeleteId === conv.id ? (
                  <div className="conversation-confirm" role="group" aria-label="Confirm delete">
                    <p className="conversation-confirm-text">Delete this chat?</p>
                    <div className="conversation-confirm-actions">
                      <button
                        type="button"
                        className="confirm-delete"
                        onClick={() => {
                          onDeleteConversation?.(conv.id);
                          setPendingDeleteId(null);
                        }}
                      >
                        Delete
                      </button>
                      <button
                        type="button"
                        className="confirm-cancel"
                        onClick={() => setPendingDeleteId(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <button
                      type="button"
                      className="conversation-select"
                      onClick={() => onSelectConversation?.(conv.id)}
                    >
                      <p className="conversation-title">{conv.title}</p>
                      <div className="conversation-meta">
                        <Clock size={12} aria-hidden="true" />
                        <span>{getRelativeTime(conv.timestamp)}</span>
                      </div>
                    </button>
                    {onDeleteConversation && (
                      <button
                        type="button"
                        className="conversation-delete"
                        aria-label="Delete conversation"
                        onClick={(e) => {
                          e.stopPropagation();
                          setPendingDeleteId(conv.id);
                        }}
                      >
                        <Trash2 size={14} aria-hidden="true" />
                      </button>
                    )}
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <style>{`
        .session-history {
          width: 240px;
          height: 100%;
          padding: var(--space-lg);
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .session-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: var(--space-md);
        }
        .session-title {
          font-family: var(--font-serif);
          font-size: var(--t-card-title);
          font-weight: 600;
          color: var(--color-parchment);
        }
        .session-count {
          font-family: var(--font-body);
          font-size: var(--t-caption);
          color: var(--color-parchment-2);
          background: var(--glass-bg);
          padding: var(--space-xs) var(--space-sm);
          border-radius: var(--radius-sm);
        }
        .new-chat-button {
          width: 100%;
          margin-bottom: var(--space-md);
          padding: var(--space-sm);
          font-size: var(--t-caption);
        }
        .session-content {
          flex: 1;
          overflow-y: auto;
          min-height: 0;
        }
        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: var(--space-2xl) var(--space-md);
          text-align: center;
        }
        .empty-icon {
          color: var(--color-parchment-3);
          margin-bottom: var(--space-md);
          opacity: 0.5;
        }
        .empty-text {
          font-family: var(--font-serif);
          font-size: var(--t-body);
          font-style: italic;
          color: var(--color-parchment-3);
        }
        .conversation-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }
        .conversation-item {
          display: flex;
          align-items: flex-start;
          gap: var(--space-xs);
          padding: var(--space-sm);
          border: 1px solid transparent;
          border-radius: var(--radius-md);
          margin-bottom: var(--space-xs);
        }
        .conversation-item:hover { background: var(--glass-bg); }
        .conversation-item.active {
          background: var(--glass-bg-heavy);
          border-color: var(--glass-border-heavy);
        }
        .conversation-select {
          flex: 1;
          text-align: left;
          background: none;
          border: none;
          cursor: pointer;
          padding: var(--space-xs);
          color: inherit;
        }
        .conversation-title {
          font-family: var(--font-body);
          font-size: var(--t-body);
          color: var(--color-parchment);
          margin: 0 0 var(--space-xs);
          line-height: 1.4;
          overflow: hidden;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
        }
        .conversation-meta {
          display: flex;
          align-items: center;
          gap: var(--space-xs);
          font-family: var(--font-body);
          font-size: var(--t-caption);
          color: var(--color-parchment-3);
        }
        .conversation-delete {
          background: none;
          border: none;
          color: var(--color-parchment-3);
          cursor: pointer;
          padding: var(--space-xs);
          flex-shrink: 0;
        }
        .conversation-delete:hover { color: var(--color-error); }
        .conversation-confirm {
          flex: 1;
          padding: var(--space-xs);
        }
        .conversation-confirm-text {
          font-family: var(--font-body);
          font-size: var(--t-caption);
          color: var(--color-parchment);
          margin: 0 0 var(--space-sm);
        }
        .conversation-confirm-actions {
          display: flex;
          gap: var(--space-sm);
        }
        .confirm-delete,
        .confirm-cancel {
          font-family: var(--font-body);
          font-size: var(--t-caption);
          padding: 6px 10px;
          border-radius: var(--radius-sm);
          cursor: pointer;
          border: 1px solid var(--glass-border);
          background: var(--glass-bg);
          color: var(--color-parchment);
        }
        .confirm-delete {
          border-color: var(--color-error);
          color: var(--color-error);
        }
        .confirm-delete:hover {
          background: var(--color-maroon-tint-heavy);
        }
        .confirm-cancel:hover {
          border-color: var(--color-parchment-3);
        }
        @media (pointer: coarse) {
          .conversation-delete,
          .confirm-delete,
          .confirm-cancel {
            min-width: 44px;
            min-height: 44px;
          }
        }
        @media (max-width: 1024px) {
          .session-history {
            width: 100%;
            height: auto;
            max-height: 200px;
          }
        }
      `}</style>
    </div>
  );
}

export default SessionHistory;
