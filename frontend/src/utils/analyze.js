import { consumeSSE } from './sse';

/**
 * Run a document analyze stream (text/table or figure vision).
 */
export async function analyzeDocument(documentId, payload, handlers, signal) {
  const isFigure = payload.content_type === 'figure';
  const url = isFigure
    ? `/api/documents/${documentId}/analyze/vision/stream`
    : `/api/documents/${documentId}/analyze/stream`;

  await consumeSSE(url, payload, handlers, signal);
}

export async function fetchTableMarkdown(documentId, tableId) {
  const res = await fetch(`/api/documents/${documentId}/tables/${tableId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to load table');
  }
  return res.json();
}

export async function simplifyDocument(documentId, conversationId = null) {
  const res = await fetch(`/api/documents/${documentId}/simplify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversation_id: conversationId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Simplify failed');
  }
  return res.json();
}

export function hashKey(...parts) {
  // Simple string hash for client cache keys
  const s = parts.join('|');
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  }
  return String(h);
}
