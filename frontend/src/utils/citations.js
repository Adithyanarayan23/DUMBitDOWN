/**
 * Normalize citation objects from the backend for UI display.
 * Backend may send contribution_percentage / formatted_citation / urls.*;
 * UI expects contribution / apa_citation / authors string / link URLs.
 */
export function normalizeCitation(c = {}) {
  const authors = Array.isArray(c.authors)
    ? c.authors.join(', ')
    : (c.authors_display || c.authors || '—');

  const contribution = Number(
    c.contribution ?? c.contribution_percentage ?? 0
  ) || 0;

  let title = (c.title || '').trim();
  const badTitles = new Set([
    '',
    'Untitled',
    'Unknown Title',
    'Untitled Source',
    'Unknown',
  ]);
  if (badTitles.has(title)) {
    const snippet =
      c.snippet ?? c.abstract_preview ?? c.chunk_preview ?? '';
    const cleaned = String(snippet).replace(/\s+/g, ' ').trim();
    title = cleaned
      ? cleaned.slice(0, 90) + (cleaned.length > 90 ? '…' : '')
      : c.id || c.source || 'Related source';
  }

  let apa = c.apa_citation ?? c.formatted_citation ?? '';
  if (/^Unknown\.?/i.test(apa) || /Unknown Title/i.test(apa)) {
    apa = title ? `${title}.` : '';
  }

  const pmid = c.pmid ?? null;
  const arxiv_id = c.arxiv_id ?? null;
  const doi = c.doi ?? null;

  const pubmedUrl =
    c.urls?.pubmed ??
    (pmid ? `https://pubmed.ncbi.nlm.nih.gov/${pmid}/` : null);
  const arxivUrl =
    c.urls?.arxiv ??
    (arxiv_id ? `https://arxiv.org/abs/${arxiv_id}` : null);
  const doiUrl =
    c.urls?.doi ?? (doi ? `https://doi.org/${doi}` : null);

  const scholarUrl =
    c.urls?.scholar ??
    c.scholarUrl ??
    (title
      ? `https://scholar.google.com/scholar?q=${encodeURIComponent(title)}`
      : null);

  const snippet =
    c.snippet ?? c.abstract_preview ?? c.chunk_preview ?? null;

  return {
    ...c,
    title,
    authors: authors === 'Unknown' ? '—' : authors,
    year: c.year || null,
    contribution,
    apa_citation: apa,
    pmid,
    arxiv_id,
    doi,
    pubmedUrl,
    arxivUrl,
    doiUrl,
    scholarUrl,
    snippet,
  };
}

export function normalizeCitations(sources = []) {
  return sources.map(normalizeCitation);
}
