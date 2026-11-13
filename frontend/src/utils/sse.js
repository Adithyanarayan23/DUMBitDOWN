/**
 * Consume a POST SSE (text/event-stream) endpoint.
 * Each data line is JSON: { event, ...payload }
 */
export async function consumeSSE(url, body, handlers = {}, signal) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    let detail = 'Request failed';
    try {
      const err = await response.json();
      detail = err.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  if (!response.body) {
    throw new Error('No response body for stream');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split('\n\n');
    buffer = parts.pop() || '';

    for (const part of parts) {
      const lines = part.split('\n');
      for (const line of lines) {
        if (!line.startsWith('data:')) continue;
        const raw = line.slice(5).trim();
        if (!raw || raw === '[DONE]') continue;
        let msg;
        try {
          msg = JSON.parse(raw);
        } catch {
          continue;
        }
        const event = msg.event || 'message';
        const fn = handlers[event];
        if (typeof fn === 'function') {
          fn(msg);
        }
        if (event === 'error') {
          throw new Error(msg.detail || 'Stream error');
        }
      }
    }
  }
}
