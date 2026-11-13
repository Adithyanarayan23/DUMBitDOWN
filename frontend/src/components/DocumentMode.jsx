import React, { useCallback, useEffect, useRef, useState } from 'react';
import '../utils/pdfSetup';
import { ArrowLeft, BookOpen } from 'lucide-react';
import PDFReader from './PDFReader';
import DocumentChat from './DocumentChat';
import glassStyles from '../styles/glass.module.css';
import { analyzeDocument, simplifyDocument } from '../utils/analyze';
import { consumeSSE } from '../utils/sse';

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Document mode: PDF left, chat right.
 * One action — Dumb it down — and Simplify entire PDF, both into the same thread.
 */
function DocumentMode({
  manifest,
  file,
  onBack,
  onCitations,
  onManifestUpdate,
  conversationId,
  setConversationId,
  hasSources = false,
  sourcesOpen = false,
  onToggleSources,
}) {
  const docId = manifest?.document_id;
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const [localConvId, setLocalConvId] = useState(conversationId || null);
  const abortRef = useRef(null);

  const enrichStatus = manifest?.quality?.enrichment_status || 'ready';
  const indexStatus = manifest?.quality?.index_status || 'ready';
  const visionAvailable = manifest?.capabilities?.vision === true;
  const stillEnriching =
    enrichStatus === 'pending' ||
    enrichStatus === 'enriching' ||
    indexStatus === 'pending' ||
    indexStatus === 'indexing';

  // Poll until tables/figures/index finish in the background
  useEffect(() => {
    if (!docId || !stillEnriching) return undefined;
    let cancelled = false;
    const tick = async () => {
      try {
        const res = await fetch(`/api/documents/${docId}`);
        if (!res.ok || cancelled) return;
        const next = await res.json();
        onManifestUpdate?.(next);
      } catch {
        /* ignore transient poll errors */
      }
    };
    tick();
    const id = setInterval(tick, 1400);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [docId, stillEnriching, onManifestUpdate]);

  useEffect(() => {
    if (conversationId && conversationId !== localConvId) {
      setLocalConvId(conversationId);
    }
  }, [conversationId]); // eslint-disable-line react-hooks/exhaustive-deps

  const syncConv = useCallback(
    (id) => {
      if (!id) return;
      setLocalConvId(id);
      setConversationId?.(id);
    },
    [setConversationId]
  );

  const updateMsg = (id, patch) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  };

  const handleDumbDown = async (payload) => {
    if (!docId || busy) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const userId = uid();
    const asstId = uid();
    let label = 'Selection';
    let userContent = '';
    let contentType = 'text';
    let action = 'simplify';
    let apiPayload = {};

    if (payload.type === 'text') {
      label = `Page ${payload.page}`;
      userContent =
        payload.text.length > 280 ? `${payload.text.slice(0, 280)}…` : payload.text;
      contentType = 'text';
      action = 'simplify';
      apiPayload = { text: payload.text, page: payload.page };
    } else if (payload.type === 'table') {
      label = `Table · p${payload.page}`;
      userContent = payload.label
        ? `Dumb down: ${payload.label}`
        : 'Dumb down this table';
      contentType = 'table';
      action = 'simplify';
      apiPayload = { table_id: payload.id };
    } else if (payload.type === 'figure') {
      label = visionAvailable
        ? `Figure · p${payload.page}`
        : `Figure · caption · p${payload.page}`;
      userContent = payload.label
        ? `Dumb down: ${payload.label}`
        : 'Dumb down this figure';
      contentType = 'figure';
      action = 'explain';
      apiPayload = { figure_id: payload.id };
    }

    setMessages((prev) => [
      ...prev,
      { id: userId, role: 'user', label, kind: payload.type, content: userContent },
      {
        id: asstId,
        role: 'assistant',
        label: 'Dumb it down',
        kind: 'answer',
        content: '',
        loading: true,
      },
    ]);
    setBusy(true);

    let streamed = '';
    let terms = [];
    try {
      await analyzeDocument(
        docId,
        {
          content_type: contentType,
          action,
          conversation_id: localConvId,
          ...apiPayload,
        },
        {
          meta: (msg) => {
            if (msg.conversation_id) syncConv(msg.conversation_id);
            if (msg.warnings?.length) {
              updateMsg(asstId, { warning: msg.warnings.join(' ') });
            }
          },
          token: (msg) => {
            streamed += msg.text || '';
            updateMsg(asstId, { content: streamed, loading: true });
          },
          terms: (msg) => {
            terms = msg.technical_terms || [];
          },
          done: (msg) => {
            const text = msg.text || msg.simplified_text || streamed;
            if (msg.conversation_id) syncConv(msg.conversation_id);
            updateMsg(asstId, {
              content: text,
              loading: false,
              technical_terms: msg.technical_terms || terms,
              warning:
                msg.used_vision === false
                  ? visionAvailable
                    ? 'Caption-only analysis (could not read the figure image).'
                    : 'Caption-only — figure vision needs Gemini.'
                  : undefined,
            });
          },
        },
        controller.signal
      );
    } catch (err) {
      if (err.name !== 'AbortError') {
        updateMsg(asstId, {
          loading: false,
          error: err.message || 'Failed to dumb it down',
          content: streamed || '',
        });
      }
    } finally {
      setBusy(false);
    }
  };

  const handleSimplifyAll = async () => {
    if (!docId || busy) return;
    setBusy(true);

    const userId = uid();
    const asstId = uid();
    setMessages((prev) => [
      ...prev,
      {
        id: userId,
        role: 'user',
        label: 'Whole document',
        kind: 'whole',
        content: 'Simplify entire PDF',
      },
      {
        id: asstId,
        role: 'assistant',
        label: 'Paper summary',
        kind: 'answer',
        content: '',
        loading: true,
      },
    ]);

    try {
      const data = await simplifyDocument(docId, localConvId);
      if (data.conversation_id) syncConv(data.conversation_id);
      updateMsg(asstId, {
        content: data.simplified_text || '',
        loading: false,
        technical_terms: data.technical_terms || [],
      });
      onCitations?.(data);
    } catch (err) {
      updateMsg(asstId, {
        loading: false,
        error: err.message || 'Failed to simplify PDF',
      });
    } finally {
      setBusy(false);
    }
  };

  const onFollowUp = async (question) => {
    const convId = localConvId;
    if (!convId || followUpLoading) return;

    const userId = uid();
    const asstId = uid();
    setMessages((prev) => [
      ...prev,
      { id: userId, role: 'user', content: question },
      { id: asstId, role: 'assistant', content: '', loading: true },
    ]);
    setFollowUpLoading(true);

    let streamed = '';
    try {
      await consumeSSE(
        '/api/followup/stream',
        { conversation_id: convId, question, k: 5 },
        {
          token: (msg) => {
            streamed += msg.text || '';
            updateMsg(asstId, { content: streamed, loading: true });
          },
          done: (msg) => {
            const answer = msg.answer || msg.text || streamed;
            updateMsg(asstId, { content: answer, loading: false });
            if (msg.citations) onCitations?.(msg);
          },
        }
      );
    } catch (err) {
      updateMsg(asstId, {
        loading: false,
        error: err.message || 'Follow-up failed',
        content: streamed || '',
      });
    } finally {
      setFollowUpLoading(false);
    }
  };

  const progressLabel = (() => {
    if (enrichStatus === 'pending' || enrichStatus === 'enriching') {
      return 'Detecting tables & figures…';
    }
    if (indexStatus === 'pending' || indexStatus === 'indexing') {
      return 'Indexing for follow-ups…';
    }
    if (enrichStatus === 'error' || indexStatus === 'error') {
      return 'Background setup had an issue — text simplify still works.';
    }
    return null;
  })();

  const title = manifest?.metadata?.title || manifest?.filename || 'Uploaded PDF';

  return (
    <div className="document-mode">
      <header className="document-header">
        <button type="button" className={glassStyles.textButton} onClick={onBack}>
          <ArrowLeft size={16} />
          Back
        </button>
        <div className="document-title-block">
          <h2 className="document-title">{title}</h2>
          <span className="document-meta">
            {manifest?.metadata?.pages || 0} pages
            {manifest?.quality?.table_count
              ? ` · ${manifest.quality.table_count} tables`
              : ''}
            {manifest?.quality?.figure_count
              ? ` · ${manifest.quality.figure_count} figures`
              : ''}
            {!visionAvailable ? ' · caption-only figures' : ''}
          </span>
        </div>
        <div className="document-header-actions">
          {hasSources && (
            <button
              type="button"
              className={`doc-quiet-btn ${sourcesOpen ? 'active' : ''}`}
              onClick={onToggleSources}
              aria-pressed={sourcesOpen}
            >
              <BookOpen size={13} />
              {sourcesOpen ? 'Hide sources' : 'Sources'}
            </button>
          )}
          <button
            type="button"
            className="doc-quiet-btn"
            onClick={handleSimplifyAll}
            disabled={busy}
          >
            {busy ? 'Working…' : 'Simplify entire PDF'}
          </button>
        </div>
      </header>

      {progressLabel && (
        <div className={`doc-progress ${enrichStatus === 'error' ? 'error' : ''}`}>
          {progressLabel}
        </div>
      )}

      <div className="document-split">
        <div className="document-reader-pane">
          <PDFReader
            file={file}
            manifest={manifest}
            onDumbDown={handleDumbDown}
            visionAvailable={visionAvailable}
          />
        </div>
        <div className="document-chat-pane">
          <DocumentChat
            messages={messages}
            loading={busy}
            onFollowUp={onFollowUp}
            followUpLoading={followUpLoading}
            conversationReady={Boolean(localConvId)}
          />
        </div>
      </div>

      <style>{`
        .document-mode {
          display: flex;
          flex-direction: column;
          height: 100%;
          min-height: 0;
        }
        .document-header {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 20px 12px 14px;
          border-bottom: 1px solid var(--glass-border);
          flex-shrink: 0;
        }
        .document-title-block {
          flex: 1;
          min-width: 0;
          padding-top: 6px;
        }
        .document-title {
          margin: 0;
          font-family: var(--font-display);
          font-size: 15px;
          color: var(--color-parchment);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .document-meta {
          font-family: var(--font-body);
          font-size: 11px;
          color: var(--color-parchment-3);
        }
        .document-header-actions {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-shrink: 0;
        }
        .doc-quiet-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          height: 30px;
          padding: 0 10px;
          font-family: var(--font-body);
          font-size: 12px;
          font-weight: 500;
          letter-spacing: 0.01em;
          color: var(--color-parchment-2);
          background: transparent;
          border: 1px solid var(--glass-border);
          border-radius: 6px;
          cursor: pointer;
          white-space: nowrap;
        }
        .doc-quiet-btn:hover:not(:disabled) {
          color: var(--color-gold);
          border-color: rgba(212, 168, 83, 0.5);
        }
        .doc-quiet-btn.active {
          color: var(--color-gold);
          border-color: rgba(212, 168, 83, 0.55);
          background: var(--color-amber-tint);
        }
        .doc-quiet-btn:disabled {
          opacity: 0.45;
          cursor: default;
        }
        .doc-progress {
          flex-shrink: 0;
          padding: 6px 12px;
          font-family: var(--font-body);
          font-size: 12px;
          color: var(--color-gold);
          background: var(--color-amber-tint);
          border-bottom: 1px solid var(--glass-border);
        }
        .doc-progress.error {
          color: var(--color-parchment-2);
        }
        .document-split {
          display: flex;
          flex: 1;
          min-height: 0;
        }
        .document-reader-pane {
          flex: 1.45;
          min-width: 0;
          border-right: 1px solid var(--glass-border);
          overflow: hidden;
        }
        .document-chat-pane {
          flex: 0.95;
          min-width: 260px;
          max-width: 380px;
          overflow: hidden;
        }
        @media (max-width: 900px) {
          .document-split { flex-direction: column; }
          .document-reader-pane {
            flex: 1;
            border-right: none;
            border-bottom: 1px solid var(--glass-border);
            min-height: 45vh;
          }
          .document-chat-pane {
            max-width: none;
            min-height: 35vh;
          }
          .document-header { flex-wrap: wrap; }
        }
      `}</style>
    </div>
  );
}

export default DocumentMode;
