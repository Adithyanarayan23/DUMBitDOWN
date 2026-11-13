"""Text simplification and Q&A using Gemini (unified native API)."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from typing import List, Optional

import google.generativeai as genai

from config import get_settings
from core.llm import safe_generate_text, safe_generate_text_stream

logger = logging.getLogger(__name__)


SIMPLIFICATION_PROMPT = """You are an AI assistant that simplifies complex research text for college students.

ORIGINAL TEXT:
{query}

CONTEXT:
{context}

Your task:
- Rephrase the original text so a college student can understand it
- Use the context only as silent background knowledge if needed
- Write a single standalone explanation. NEVER mention "the context", "the documents", "Document 1/2/3", "sources", or "as provided"
- If the context is not relevant, ignore it and explain only the original text
- Be brief: 1-2 short paragraphs maximum (about 80-120 words total)
- Do NOT use markdown formatting (no ** or * characters)
- After the explanation, list up to 4 technical terms you used with short definitions

Output EXACTLY in this format (no extra commentary after the JSON):

SIMPLIFIED EXPLANATION:
<plain text explanation here>

---TERMS_JSON---
[{{"term":"example","definition":"short definition"}}]
"""


QA_PROMPT = """You are an AI assistant answering questions about research topics.

QUESTION: {question}

ORIGINAL TEXT: {original_text}

CONTEXT: {context}

SIMPLIFIED TEXT: {simplified_text}

Provide a short, accurate answer (2-3 sentences). Answer directly without preambles.
Write a standalone answer. NEVER mention "the context", "the documents", "Document 1/2/3", or "sources".
If the information is insufficient, say so politely.

ANSWER:"""


TERMS_SPLIT = "---TERMS_JSON---"


@dataclass
class SimplifyResult:
    text: str
    technical_terms: List[dict]


def _parse_terms_json(raw: str) -> List[dict]:
    """Parse technical terms JSON; return [] on failure."""
    if not raw or not raw.strip():
        return []
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []

    if not isinstance(data, list):
        return []

    terms = []
    for item in data[:8]:
        if not isinstance(item, dict):
            continue
        term = str(item.get("term", "")).strip()
        definition = str(item.get("definition", "")).strip()
        if term and definition:
            terms.append({"term": term, "definition": definition})
    return terms


def parse_simplify_response(raw: str) -> SimplifyResult:
    """Split prose and TERMS_JSON trailer from model output."""
    if TERMS_SPLIT in raw:
        prose, _, trailer = raw.partition(TERMS_SPLIT)
    else:
        prose, trailer = raw, ""

    prose = prose.replace("SIMPLIFIED EXPLANATION:", "", 1).strip()
    terms = _parse_terms_json(trailer)
    return SimplifyResult(text=prose, technical_terms=terms)


class Simplifier:
    """Simplifies complex text using Gemini."""

    def __init__(self) -> None:
        settings = get_settings()
        self.generation_config = genai.types.GenerationConfig(
            temperature=settings.temperature,
            top_p=0.95,
            top_k=40,
            max_output_tokens=settings.max_output_tokens,
        )
        self._cache: dict[str, SimplifyResult] = {}

    def simplify(self, query: str, context: str) -> SimplifyResult:
        """
        Simplify complex text using retrieved context.

        Returns:
            SimplifyResult with plain text and technical_terms list
        """
        cache_key = hashlib.md5(f"{query}_{context}".encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt = SIMPLIFICATION_PROMPT.format(query=query, context=context)
        raw = safe_generate_text(prompt, self.generation_config)
        result = parse_simplify_response(raw)
        if not result.text:
            raise RuntimeError("Simplification returned empty text")
        self._cache[cache_key] = result
        return result

    def simplify_stream(self, query: str, context: str):
        """
        Stream simplification tokens. Yields ('token', str) for prose only,
        then ('result', SimplifyResult) when complete.

        Buffers the ---TERMS_JSON--- trailer so it is not shown to the client.
        """
        cache_key = hashlib.md5(f"{query}_{context}".encode()).hexdigest()
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            yield ("token", cached.text)
            yield ("result", cached)
            return

        prompt = SIMPLIFICATION_PROMPT.format(query=query, context=context)
        header = "SIMPLIFIED EXPLANATION:"
        raw = ""
        emitted = 0

        for chunk in safe_generate_text_stream(prompt, self.generation_config):
            raw += chunk
            trailer_seen = TERMS_SPLIT in raw
            prose_raw = raw.split(TERMS_SPLIT, 1)[0] if trailer_seen else raw

            # Strip the header only once it has fully arrived.
            header_seen = header in prose_raw
            if header_seen:
                clean = prose_raw.split(header, 1)[1].lstrip("\n")
            else:
                clean = prose_raw

            # Hold back a suffix so we never leak a partially-formed header or
            # the start of the TERMS_JSON trailer while streaming.
            if trailer_seen:
                visible = clean
            else:
                holdback = len(TERMS_SPLIT)
                if not header_seen:
                    holdback = max(holdback, len(header))
                visible = clean[: max(0, len(clean) - holdback)]

            if len(visible) > emitted:
                yield ("token", visible[emitted:])
                emitted = len(visible)

        result = parse_simplify_response(raw)
        if not result.text:
            raise RuntimeError("Simplification returned empty text")
        # Flush prose the holdback withheld during streaming so the visible
        # text is complete even before the final 'done' payload is applied.
        if len(result.text) > emitted:
            tail = result.text[emitted:]
            if tail:
                yield ("token", tail)
        self._cache[cache_key] = result
        yield ("result", result)


class QAChain:
    """Question answering using Gemini."""

    def __init__(self) -> None:
        settings = get_settings()
        self.generation_config = genai.types.GenerationConfig(
            temperature=settings.temperature,
            top_p=0.95,
            top_k=40,
            max_output_tokens=settings.max_output_tokens,
        )
        self._cache: dict[str, str] = {}

    def answer(
        self,
        question: str,
        original_text: str,
        context: str,
        simplified_text: str,
    ) -> str:
        """Answer a question about the text."""
        cache_key = hashlib.md5(
            f"{question}_{original_text}_{context}_{simplified_text}".encode()
        ).hexdigest()

        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt = QA_PROMPT.format(
            question=question,
            original_text=original_text,
            context=context,
            simplified_text=simplified_text,
        )
        answer = safe_generate_text(prompt, self.generation_config)
        if not answer:
            raise RuntimeError("QA returned empty answer")
        # Strip optional ANSWER: prefix
        cleaned = answer.replace("ANSWER:", "", 1).strip()
        self._cache[cache_key] = cleaned
        return cleaned

    def answer_stream(
        self,
        question: str,
        original_text: str,
        context: str,
        simplified_text: str,
    ):
        """Yield ('token', str) chunks then ('result', full_answer)."""
        cache_key = hashlib.md5(
            f"{question}_{original_text}_{context}_{simplified_text}".encode()
        ).hexdigest()
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            yield ("token", cached)
            yield ("result", cached)
            return

        prompt = QA_PROMPT.format(
            question=question,
            original_text=original_text,
            context=context,
            simplified_text=simplified_text,
        )
        raw = ""
        last_visible = ""
        for chunk in safe_generate_text_stream(prompt, self.generation_config):
            raw += chunk
            visible = raw.replace("ANSWER:", "", 1).lstrip()
            if visible.startswith(last_visible):
                delta = visible[len(last_visible) :]
            else:
                delta = visible
            if delta:
                last_visible = visible
                yield ("token", delta)

        answer = raw.replace("ANSWER:", "", 1).strip()
        if not answer:
            raise RuntimeError("QA returned empty answer")
        self._cache[cache_key] = answer
        yield ("result", answer)
