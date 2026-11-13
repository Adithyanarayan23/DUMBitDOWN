import React, { useState, useRef, useEffect, useCallback, lazy, Suspense } from 'react';
import { Send, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Exchange from '../components/Exchange';
import SessionHistory from '../components/SessionHistory';
import PDFDropzone from '../components/PDFDropzone';
import CitationCard from '../components/CitationCard';
import CitationDrawer from '../components/CitationDrawer';
import GlassCard from '../components/GlassCard';
import glassStyles from '../styles/glass.module.css';
import { normalizeCitations } from '../utils/citations';
import { consumeSSE } from '../utils/sse';
import { DEMO_SAMPLES } from '../data/samples';

const DocumentMode = lazy(() => import('../components/DocumentMode'));
const panelEase = [0.32, 0.72, 0, 1];

/**
 * AppPage - Three-column layout: Session History | Input/Response | Citations
 */
function AppPage() {
  const [inputText, setInputText] = useState('');
  const [charCount, setCharCount] = useState(0);
  const [isInputValid, setIsInputValid] = useState(false);
  const [exchanges, setExchanges] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showCitations, setShowCitations] = useState(false);
  const [currentCitations, setCurrentCitations] = useState([]);
  const [pipeline, setPipeline] = useState(null);
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [serverSessions, setServerSessions] = useState([]);
  const [viewMode, setViewMode] = useState('compose'); // 'compose' | 'document'
  const [activeDocument, setActiveDocument] = useState(null);
  const [pdfFile, setPdfFile] = useState(null);
  const threadEndRef = useRef(null);
  const abortRef = useRef(null);

  const hasConversation = exchanges.length > 0;
  const inDocumentMode = viewMode === 'document' && activeDocument && pdfFile;

  useEffect(() => {
    setCharCount(inputText.length);
    setIsInputValid(inputText.length >= 10 && inputText.length <= 10000);
  }, [inputText]);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [exchanges]);

  const refreshSessions = useCallback(async () => {
    try {
      const res = await fetch('/api/conversations');
      if (!res.ok) return;
      const data = await res.json();
      setServerSessions(data.conversations || []);
    } catch {
      /* offline / cold start */
    }
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  const applyCitations = (data) => {
    if (data.citations?.sources?.length > 0) {
      setCurrentCitations(normalizeCitations(data.citations.sources));
      setShowCitations(true);
    }
    if (data.pipeline) setPipeline(data.pipeline);
  };

  const updateExchange = (exchangeId, patch) => {
    setExchanges((prev) =>
      prev.map((ex) => (ex.id === exchangeId ? { ...ex, ...patch } : ex))
    );
  };

  const handleSimplifyFallback = async (query, exchangeId) => {
    const response = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        k: 5,
        conversation_id: conversationId,
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Request failed');
    }
    const data = await response.json();
    if (data.conversation_id) {
      setConversationId(data.conversation_id);
      setActiveConversationId(data.conversation_id);
    }
    updateExchange(exchangeId, {
      responseData: data,
      loading: false,
      conversation_id: data.conversation_id,
    });
    applyCitations(data);
    refreshSessions();
  };

  const handleSimplify = async () => {
    if (!isInputValid || isLoading) return;

    setIsLoading(true);
    const query = inputText.trim();
    const exchangeId = Date.now();
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setExchanges((prev) => [
      ...prev,
      {
        id: exchangeId,
        query,
        responseData: null,
        loading: true,
        conversation_id: conversationId,
        timestamp: new Date(),
      },
    ]);
    setInputText('');

    let streamedText = '';
    let metaCitations = null;
    let metaPipeline = null;
    let convId = conversationId;

    try {
      await consumeSSE(
        '/api/search/stream',
        { query, k: 5, conversation_id: conversationId },
        {
          meta: (msg) => {
            if (msg.conversation_id) {
              convId = msg.conversation_id;
              setConversationId(msg.conversation_id);
              setActiveConversationId(msg.conversation_id);
            }
            metaCitations = msg.citations;
            metaPipeline = msg.pipeline;
            applyCitations({ citations: msg.citations, pipeline: msg.pipeline });
            updateExchange(exchangeId, {
              loading: false,
              conversation_id: msg.conversation_id,
              responseData: {
                streaming: true,
                streamText: '',
                citations: msg.citations,
                pipeline: msg.pipeline,
                technical_terms: [],
              },
            });
          },
          token: (msg) => {
            streamedText += msg.text || '';
            updateExchange(exchangeId, {
              loading: false,
              responseData: {
                streaming: true,
                streamText: streamedText,
                simplified_text: streamedText,
                citations: metaCitations,
                pipeline: metaPipeline,
                technical_terms: [],
              },
            });
          },
          terms: (msg) => {
            updateExchange(exchangeId, {
              responseData: {
                streaming: true,
                streamText: streamedText,
                simplified_text: streamedText,
                citations: metaCitations,
                pipeline: metaPipeline,
                technical_terms: msg.technical_terms || [],
              },
            });
          },
          done: (msg) => {
            const data = {
              simplified_text: msg.simplified_text || streamedText,
              citations: msg.citations || metaCitations,
              technical_terms: msg.technical_terms || [],
              pipeline: msg.pipeline || metaPipeline,
              conversation_id: msg.conversation_id || convId,
              streaming: false,
            };
            if (data.conversation_id) {
              setConversationId(data.conversation_id);
              setActiveConversationId(data.conversation_id);
            }
            updateExchange(exchangeId, {
              responseData: data,
              loading: false,
              conversation_id: data.conversation_id,
            });
            applyCitations(data);
            refreshSessions();
          },
        },
        controller.signal
      );
    } catch (error) {
      if (error.name === 'AbortError') return;
      console.warn('Stream failed, falling back to /api/search', error);
      try {
        await handleSimplifyFallback(query, exchangeId);
      } catch (fallbackErr) {
        updateExchange(exchangeId, {
          responseData: { error: { detail: fallbackErr.message } },
          loading: false,
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleFollowUp = async (question) => {
    if (!conversationId || isLoading) return;

    setIsLoading(true);
    const exchangeId = Date.now();
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setExchanges((prev) => [
      ...prev,
      {
        id: exchangeId,
        query: question,
        responseData: null,
        loading: true,
        conversation_id: conversationId,
        timestamp: new Date(),
        isFollowUp: true,
      },
    ]);

    let streamedText = '';
    let metaCitations = null;
    let metaPipeline = null;

    try {
      await consumeSSE(
        '/api/followup/stream',
        { conversation_id: conversationId, question, k: 5 },
        {
          meta: (msg) => {
            metaCitations = msg.citations;
            metaPipeline = msg.pipeline;
            applyCitations({ citations: msg.citations, pipeline: msg.pipeline });
            updateExchange(exchangeId, {
              loading: false,
              responseData: {
                streaming: true,
                answer: '',
                citations: msg.citations,
                pipeline: msg.pipeline,
              },
            });
          },
          token: (msg) => {
            streamedText += msg.text || '';
            updateExchange(exchangeId, {
              loading: false,
              responseData: {
                streaming: true,
                answer: streamedText,
                citations: metaCitations,
                pipeline: metaPipeline,
              },
            });
          },
          done: (msg) => {
            const data = {
              answer: msg.answer || streamedText,
              citations: msg.citations || metaCitations,
              pipeline: msg.pipeline || metaPipeline,
              streaming: false,
            };
            updateExchange(exchangeId, {
              responseData: data,
              loading: false,
            });
            applyCitations(data);
            refreshSessions();
          },
        },
        controller.signal
      );
    } catch (error) {
      if (error.name === 'AbortError') return;
      try {
        const response = await fetch('/api/followup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            conversation_id: conversationId,
            question,
            k: 5,
          }),
        });
        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail || 'Request failed');
        }
        const data = await response.json();
        updateExchange(exchangeId, { responseData: data, loading: false });
        applyCitations(data);
        refreshSessions();
      } catch (fallbackErr) {
        updateExchange(exchangeId, {
          responseData: { error: { detail: fallbackErr.message } },
          loading: false,
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleDocumentCitations = (data) => {
    if (data?.conversation_id) {
      setConversationId(data.conversation_id);
      setActiveConversationId(data.conversation_id);
    }
    applyCitations(data);
    refreshSessions();
  };

  const handleDocumentReady = ({ manifest, file }) => {
    setActiveDocument(manifest);
    setPdfFile(file);
    setViewMode('document');
  };

  const handleExitDocument = () => {
    setViewMode('compose');
  };

  const handleClear = async () => {
    abortRef.current?.abort();
    setInputText('');
    setExchanges([]);
    setConversationId(null);
    setActiveConversationId(null);
    setCurrentCitations([]);
    setShowCitations(false);
    setPipeline(null);
    setSelectedCitation(null);
    setViewMode('compose');
    setActiveDocument(null);
    setPdfFile(null);
  };

  const handleSelectConversation = async (id) => {
    setActiveConversationId(id);
    // Prefer server hydrate
    try {
      const res = await fetch(`/api/conversations/${id}`);
      if (res.ok) {
        const data = await res.json();
        const msgs = data.messages || [];
        const hydrated = [];
        let pendingUser = null;
        for (const msg of msgs) {
          if (msg.role === 'user') {
            pendingUser = msg;
          } else if (msg.role === 'assistant' && pendingUser) {
            const isFollowUp = pendingUser.metadata?.type === 'question';
            hydrated.push({
              id: `${id}-${hydrated.length}`,
              query: pendingUser.content,
              responseData: {
                simplified_text: isFollowUp ? undefined : msg.content,
                answer: isFollowUp ? msg.content : undefined,
                streaming: false,
              },
              loading: false,
              conversation_id: id,
              timestamp: new Date(msg.timestamp || Date.now()),
              isFollowUp,
            });
            pendingUser = null;
          }
        }
        setExchanges(hydrated);
        setConversationId(id);
        setCurrentCitations([]);
        setShowCitations(false);
        setPipeline(null);
        return;
      }
    } catch {
      /* fall through to local scroll */
    }

    const first = exchanges.find((ex) => ex.conversation_id === id);
    if (first) {
      document
        .getElementById(`exchange-${first.id}`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const handleDeleteConversation = async (id) => {
    try {
      await fetch(`/api/conversations/${id}`, { method: 'DELETE' });
    } catch {
      /* ignore */
    }
    if (conversationId === id) handleClear();
    refreshSessions();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSimplify();
    }
  };

  return (
    <div className="app-page">
      <aside className="sidebar-left">
        <SessionHistory
          exchanges={exchanges}
          serverSessions={serverSessions}
          activeConversationId={activeConversationId}
          onNewChat={handleClear}
          onSelectConversation={handleSelectConversation}
          onDeleteConversation={handleDeleteConversation}
        />
      </aside>

      <main id="main-content" className="main-panel" tabIndex={-1}>
        <h1 className="sr-only">DumbItDown - Simplify research text</h1>
        <GlassCard stitched className="main-panel-card">
          <AnimatePresence mode="wait">
          {inDocumentMode ? (
            <motion.div
              key="document"
              className="mode-pane"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.22, ease: panelEase }}
            >
            <Suspense
              fallback={
                <div className="doc-loading-fallback" role="status" aria-live="polite">
                  Opening document…
                </div>
              }
            >
              <DocumentMode
                manifest={activeDocument}
                file={pdfFile}
                onBack={handleExitDocument}
                onCitations={handleDocumentCitations}
                onManifestUpdate={setActiveDocument}
                conversationId={conversationId}
                setConversationId={(id) => {
                  setConversationId(id);
                  setActiveConversationId(id);
                }}
                hasSources={currentCitations.length > 0}
                sourcesOpen={showCitations}
                onToggleSources={() => setShowCitations((v) => !v)}
              />
            </Suspense>
            </motion.div>
          ) : (
            <motion.div
              key="compose"
              className="mode-pane"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.22, ease: panelEase }}
            >
          {!hasConversation && (
            <div className="input-section">
              <div className="sample-chips">
                <span className="sample-label">Try a sample:</span>
                {DEMO_SAMPLES.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    className="sample-chip"
                    disabled={isLoading}
                    onClick={() => setInputText(s.text)}
                  >
                    {s.label}
                  </button>
                ))}
              </div>

              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                aria-label="Research text to simplify"
                placeholder="Paste a passage, upload a PDF, or ask about the paper..."
                className={glassStyles.glassInput}
                disabled={isLoading}
                rows={4}
              />
              <div className="input-meta">
                <span className={`char-count ${charCount > 10000 ? 'invalid' : ''}`}>
                  {charCount}/10000
                </span>
              </div>

              <PDFDropzone onDocumentReady={handleDocumentReady} />

              {activeDocument && pdfFile && (
                <div className="reopen-doc" style={{ marginTop: '12px' }}>
                  <button
                    type="button"
                    className={glassStyles.textButton}
                    onClick={() => setViewMode('document')}
                  >
                    Continue with {activeDocument.filename || 'uploaded PDF'}
                  </button>
                </div>
              )}

              <div className="action-bar">
                <button
                  className={glassStyles.textButton}
                  onClick={handleClear}
                  disabled={isLoading}
                >
                  <Trash2 size={16} aria-hidden="true" />
                  Clear
                </button>
                <button
                  className={glassStyles.glassButton}
                  onClick={handleSimplify}
                  disabled={!isInputValid || isLoading}
                >
                  {isLoading ? (
                    <>
                      <div className={glassStyles.spinner} aria-hidden="true" />
                      Simplifying…
                    </>
                  ) : (
                    <>
                      <Send size={16} aria-hidden="true" />
                      Simplify
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {exchanges.length > 0 && (
            <div className="conversation-thread" aria-live="polite" aria-relevant="additions text">
              {hasConversation && activeDocument && (
                <div className="reopen-doc">
                  <button
                    type="button"
                    className={glassStyles.textButton}
                    onClick={() => setViewMode('document')}
                    disabled={!pdfFile}
                  >
                    Reopen PDF reader
                  </button>
                </div>
              )}
              {exchanges.map((exchange, index) => (
                <Exchange
                  key={exchange.id}
                  exchangeId={exchange.id}
                  query={exchange.query}
                  responseData={exchange.responseData}
                  loading={exchange.loading}
                  onFollowUp={handleFollowUp}
                  isFollowUp={exchange.isFollowUp}
                  showFollowUp={index === exchanges.length - 1 && !exchange.loading}
                  conversationId={exchange.conversation_id || conversationId}
                  onOpenSources={() => setShowCitations(true)}
                />
              ))}
              <div ref={threadEndRef} />
            </div>
          )}
            </motion.div>
          )}
          </AnimatePresence>
        </GlassCard>
      </main>

      <aside className={`sidebar-right ${showCitations && currentCitations.length > 0 ? 'visible' : ''}`}>
        <AnimatePresence>
        {showCitations && currentCitations.length > 0 && (
          <motion.div
            key="sources-panel"
            className="sources-panel-motion"
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 12 }}
            transition={{ duration: 0.22, ease: panelEase }}
            style={{ height: '100%' }}
          >
          <GlassCard stitched className="citations-panel">
            <div className="panel-title-row">
              <h2 className="panel-title">Sources</h2>
              <button
                type="button"
                className="sources-close"
                onClick={() => setShowCitations(false)}
                aria-label="Hide sources"
              >
                Hide
              </button>
            </div>
            {pipeline && (
              <div className="pipeline-aside">
                <div className="pipeline-aside-title">How this was retrieved</div>
                <p>{pipeline.model || 'LLM'}</p>
                {pipeline.rewritten_query && (
                  <p className="pipeline-aside-muted">
                    Rewrote query for retrieval
                  </p>
                )}
              </div>
            )}
            <div className="citations-list">
              {currentCitations.map((citation, index) => (
                <CitationCard
                  key={index}
                  citation={citation}
                  onSelect={setSelectedCitation}
                />
              ))}
            </div>
          </GlassCard>
          </motion.div>
        )}
        </AnimatePresence>
      </aside>

      <CitationDrawer
        citation={selectedCitation}
        onClose={() => setSelectedCitation(null)}
      />

      <style>{`
        .app-page {
          display: flex;
          height: calc(100dvh - 60px);
          min-height: calc(100vh - 60px);
          padding: var(--space-lg);
          gap: var(--space-lg);
          background: linear-gradient(
            180deg,
            var(--color-void) 0%,
            var(--color-maroon-deep) 50%,
            var(--color-void) 100%
          );
          padding-top: 80px;
        }
        .doc-loading-fallback {
          padding: var(--space-2xl);
          font-family: var(--font-body);
          color: var(--color-parchment-2);
        }
        .sidebar-left {
          flex-shrink: 0;
          height: 100%;
          overflow: hidden;
        }
        .main-panel {
          flex: 1;
          height: 100%;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          min-width: 0;
        }
        .main-panel-card {
          height: 100%;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .mode-pane {
          height: 100%;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          min-height: 0;
        }
        .input-section {
          padding: var(--space-lg);
          border-bottom: 1px solid var(--glass-border);
          flex-shrink: 0;
        }
        .conversation-thread {
          flex: 1;
          overflow-y: auto;
          padding: var(--space-lg);
          min-height: 0;
          scroll-padding-top: var(--space-md);
        }
        .reopen-doc {
          margin-bottom: var(--space-md);
        }
        .sample-chips {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: var(--space-sm);
          margin-bottom: var(--space-md);
        }
        .sample-label {
          font-family: var(--font-body);
          font-size: var(--t-caption);
          color: var(--color-parchment-3);
        }
        .sample-chip {
          font-family: var(--font-body);
          font-size: var(--t-caption);
          color: var(--color-parchment);
          background: var(--glass-bg);
          border: 1px solid var(--glass-border);
          border-radius: var(--radius-md);
          padding: 6px 12px;
          cursor: pointer;
        }
        .sample-chip:hover:not(:disabled) {
          border-color: var(--color-gold);
          color: var(--color-gold);
        }
        .sample-chip:disabled { opacity: 0.5; cursor: not-allowed; }
        @media (pointer: coarse) {
          .sample-chip {
            min-height: 44px;
            padding: 10px 14px;
          }
        }
        .input-meta {
          display: flex;
          justify-content: flex-end;
          margin-top: var(--space-xs);
          margin-bottom: var(--space-md);
        }
        .char-count {
          font-family: var(--font-body);
          font-size: var(--t-caption);
          color: var(--color-parchment-3);
        }
        .char-count.invalid { color: var(--color-error); }
        .action-bar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: var(--space-md);
        }
        .sidebar-right {
          width: 320px;
          flex-shrink: 0;
          height: 100%;
          overflow: hidden;
          display: none;
        }
        .sidebar-right.visible { display: block; }
        .citations-panel {
          height: 100%;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .panel-title-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          padding: var(--space-lg);
          border-bottom: 1px solid var(--glass-border);
          flex-shrink: 0;
        }
        .panel-title {
          font-family: var(--font-serif);
          font-size: var(--t-card-title);
          font-weight: 600;
          color: var(--color-parchment);
          margin: 0;
        }
        .sources-close {
          font-family: var(--font-serif);
          font-size: 13px;
          color: var(--color-parchment-3);
          background: transparent;
          border: 1px solid var(--glass-border);
          border-radius: 6px;
          padding: 4px 10px;
          cursor: pointer;
        }
        .sources-close:hover {
          color: var(--color-parchment);
          border-color: var(--color-parchment-3);
        }
        .pipeline-aside {
          padding: var(--space-md) var(--space-lg);
          border-bottom: 1px solid var(--glass-border);
          font-family: var(--font-body);
          font-size: var(--t-caption);
          color: var(--color-parchment-2);
        }
        .pipeline-aside-title {
          color: var(--color-parchment-3);
          margin-bottom: 4px;
        }
        .pipeline-aside-muted { opacity: 0.8; margin-top: 4px; }
        .citations-list {
          flex: 1;
          overflow-y: auto;
          padding: var(--space-md);
          min-height: 0;
        }
        @media (max-width: 1024px) {
          .app-page {
            flex-direction: column;
            height: auto;
            min-height: calc(100dvh - 60px);
            min-height: calc(100vh - 60px);
          }
          .sidebar-left {
            width: 100%;
            height: auto;
            max-height: 200px;
            order: 2;
          }
          .main-panel { order: 1; }
          .sidebar-right {
            width: 100%;
            height: auto;
            max-height: 360px;
            order: 3;
          }
          .sidebar-right.visible { display: block; }
        }
      `}</style>
    </div>
  );
}

export default AppPage;
