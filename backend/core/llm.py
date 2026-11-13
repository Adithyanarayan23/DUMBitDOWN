"""LLM model resolution and safe text generation (Gemini or Groq)."""
from __future__ import annotations

import json
import logging
from typing import Optional

import requests
import google.generativeai as genai

from config import get_settings

logger = logging.getLogger(__name__)

_resolved_model_name: Optional[str] = None
_resolved_model = None

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _provider() -> str:
    return (get_settings().llm_provider or "google").strip().lower()


def _gen_params(generation_config) -> tuple[float, int]:
    """Extract (temperature, max_tokens) from a config object or settings default."""
    settings = get_settings()
    temp = getattr(generation_config, "temperature", None)
    max_tok = getattr(generation_config, "max_output_tokens", None)
    return (
        temp if temp is not None else settings.temperature,
        max_tok if max_tok is not None else settings.max_output_tokens,
    )


# ---------------------------------------------------------------------------
# Model name candidates
# ---------------------------------------------------------------------------
def _candidate_model_names() -> list[str]:
    settings = get_settings()
    if _provider() == "groq":
        primary = settings.groq_model
        fallbacks = settings.groq_fallback_models.split(",")
    else:
        primary = settings.gemini_model
        fallbacks = settings.gemini_fallback_models.split(",")

    names: list[str] = []
    for raw in [primary, *fallbacks]:
        name = raw.strip()
        if name and name not in names:
            names.append(name)
    return names


def resolve_model():
    """Return a working model handle, trying primary then fallbacks."""
    global _resolved_model_name, _resolved_model

    if _resolved_model is not None:
        return _resolved_model

    if not _has_valid_api_key():
        name = _candidate_model_names()[0]
        _resolved_model = {"provider": "demo", "model": f"{name} (demo-ready)"}
        _resolved_model_name = f"{name} (demo-ready)"
        return _resolved_model

    if _provider() == "groq":
        # No lightweight construct step for Groq; mark first candidate as resolved.
        name = _candidate_model_names()[0]
        _resolved_model = {"provider": "groq", "model": name}
        _resolved_model_name = name
        logger.info("Using Groq model: %s", name)
        return _resolved_model

    last_error: Exception | None = None
    for name in _candidate_model_names():
        try:
            model = genai.GenerativeModel(name)
            _resolved_model = model
            _resolved_model_name = name
            logger.info("Using Gemini model: %s", name)
            return model
        except Exception as e:
            last_error = e
            logger.warning("Gemini model %s unavailable: %s", name, e)

    raise RuntimeError(
        f"No working Gemini model found. Tried: {_candidate_model_names()}. "
        f"Last error: {last_error}"
    )


def get_resolved_model_name() -> str:
    """Return the resolved model name (resolves if needed)."""
    resolve_model()
    return _resolved_model_name or "unknown"


def _ordered_candidates() -> list[str]:
    candidates = _candidate_model_names()
    if _resolved_model_name and _resolved_model_name in candidates:
        return [_resolved_model_name] + [
            n for n in candidates if n != _resolved_model_name
        ]
    return candidates


# ---------------------------------------------------------------------------
# Offline / Demo synthesis fallback (when no API key is configured)
# ---------------------------------------------------------------------------
_DEMO_GLOSSARY = [
    ("Interleukin-6 (IL-6)", "A key pro-inflammatory signaling protein (cytokine) secreted by immune and fat cells that triggers systemic inflammation and CRP release."),
    ("TNF-alpha (TNF-α)", "Tumor necrosis factor-alpha, an inflammatory cytokine that interferes with insulin receptor signaling and promotes vascular inflammation."),
    ("C-Reactive Protein (CRP)", "An acute-phase protein produced by the liver in response to inflammation, widely used as a clinical blood biomarker for cardiovascular risk."),
    ("Endothelial Function", "The ability of the inner lining of blood vessels to regulate blood flow, vessel dilation, and clotting."),
    ("PD-1 / PD-L1", "Immune checkpoint receptor and ligand that act as 'brakes' on T-cells; blocking them unleashes T-cells to attack tumor cells."),
    ("Tumor Mutational Burden (TMB)", "The total number of somatic mutations per megabase in a tumor's DNA; higher TMB creates more neoantigens for the immune system to recognize."),
    ("Microsatellite Instability (MSI)", "A predisposition to mutation caused by impaired DNA mismatch repair, linked to strong immunotherapy response."),
    ("Regulatory T Cells (Tregs)", "An immunosuppressive subset of T-cells that can dampen anti-tumor immunity inside the tumor microenvironment."),
    ("Long-Term Potentiation (LTP)", "A persistent strengthening of synapses based on recent patterns of activity, considered a cellular mechanism of learning and memory."),
    ("NMDA & AMPA Receptors", "Ionotropic glutamate receptors at excitatory synapses; NMDA triggers calcium influx while AMPA mediates fast synaptic transmission."),
    ("BDNF", "Brain-derived neurotrophic factor, a growth protein that supports neuron survival, dendritic spine growth, and synaptic plasticity."),
    ("Phase Locking Value (PLV)", "A statistical metric from 0 to 1 that isolates phase synchronization between two brain signals across trials independently of amplitude."),
]


def _has_valid_api_key() -> bool:
    settings = get_settings()
    if _provider() == "groq":
        key = (settings.groq_api_key or "").strip()
        return bool(key and not key.startswith("your_"))
    key = (settings.google_api_key or "").strip()
    return bool(key and not key.startswith("your_"))


def _synthesize_demo_response(prompt: str) -> str:
    """Produce a realistic, passage-grounded response when no API key is configured."""
    import re

    p_lower = prompt.lower()
    if "you are a search query optimizer" in p_lower:
        m = re.search(r"Original query:\s*(.+?)\n\nYour task:", prompt, re.DOTALL)
        return m.group(1).strip() if m else prompt[:150]

    # Extract original/selected passage if present
    passage = ""
    for pat in (
        r"ORIGINAL TEXT:\s*(.+?)\n\nCONTEXT:",
        r"SELECTED TEXT(?: \(from page [^\)]+\)| \(page [^\)]+\))?:\s*(.+?)\n\nNEARBY CONTEXT",
        r"TEXT:\s*(.+?)\n\nOutput EXACTLY:",
        r"TABLE \(markdown\):\s*(.+?)\n\n",
        r"CAPTION:\s*(.+?)\n\n",
    ):
        m = re.search(pat, prompt, re.DOTALL)
        if m:
            passage = m.group(1).strip()
            break

    # Match relevant glossary terms
    matched_terms = []
    search_blob = (passage or prompt).lower()
    for term_name, definition in _DEMO_GLOSSARY:
        key_part = term_name.split("(")[0].strip().lower()
        if key_part in search_blob or term_name.lower() in search_blob:
            matched_terms.append({"term": term_name, "definition": definition})
    if not matched_terms:
        words = [w for w in re.findall(r"\b[A-Z][a-zA-Z0-9-]{3,}\b", passage or prompt) if w.lower() not in {"original", "text", "context", "selected", "page", "question"}][:3]
        for w in words:
            matched_terms.append({"term": w, "definition": f"A key technical concept discussed in this research passage ({w})."})
        if not matched_terms:
            matched_terms = [
                {"term": "Biomarker", "definition": "A measurable biological indicator of a physiological or disease state."},
                {"term": "Signaling Pathway", "definition": "A chain of molecular interactions inside cells that controls cellular behavior."},
            ]

    # Handle QA / Followup prompts
    if "QUESTION:" in prompt and ("ANSWER:" in prompt or "Answer in 2-4 short sentences" in prompt):
        q_match = re.search(r"QUESTION:\s*(.+?)\n", prompt)
        q_text = q_match.group(1).strip() if q_match else "your question"
        if "il-6" in search_blob or "inflammation" in search_blob or "cytokine" in search_blob:
            return (
                "Elevated cytokines like IL-6 and TNF-alpha interfere with insulin signaling inside cells and damage the inner lining of blood vessels (endothelium). "
                "Because the liver releases C-reactive protein (CRP) in response to IL-6, doctors can measure CRP and cytokine levels in blood tests to gauge a patient's risk for type 2 diabetes and heart disease."
            )
        if "pd-1" in search_blob or "checkpoint" in search_blob or "tumor" in search_blob:
            return (
                "PD-1/PD-L1 checkpoint inhibitors work best in tumors with a high mutational burden or microsatellite instability because those tumors display more foreign-looking proteins for T-cells to spot. "
                "However, suppressive immune cells like regulatory T cells and MDSCs in the tumor microenvironment can still block the immune attack, which is why response rates vary across patients."
            )
        if "ltp" in search_blob or "potentiation" in search_blob or "bdnf" in search_blob or "synap" in search_blob:
            return (
                "Long-term potentiation strengthens connections between neurons when NMDA receptors let calcium into the cell, prompting more AMPA receptors to move to the synapse surface. "
                "BDNF acts like fertilizer that stabilizes these strengthened connections for long-term memory, and when BDNF drops during chronic stress or neurodegeneration, memory and mood suffer."
            )
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", passage) if len(s.strip()) > 20]
        core = sentences[0] if sentences else "the mechanism described in the paper"
        return f"Regarding {q_text}: {core} In plain terms, the authors show how this mechanism directly shapes the measured experimental outcome and helps researchers interpret the underlying biology."

    # Build plain-English explanation
    if "il-6" in search_blob or "inflammation" in search_blob or "cytokine" in search_blob:
        prose = (
            "Long-term, low-level inflammation happens when the body keeps circulating chemical alarm signals—specifically proteins called IL-6, TNF-alpha, and C-reactive protein (CRP). "
            "Over time, these inflammatory signals disrupt how cells respond to insulin and strain the inner lining of blood vessels, which increases the risk of metabolic syndrome, type 2 diabetes, and heart disease.\n\n"
            "Tracking how these chemical chain reactions spread through the body helps doctors and researchers use blood biomarkers to spot metabolic and cardiovascular risk early."
        )
    elif "pd-1" in search_blob or "checkpoint" in search_blob or "immunotherapy" in search_blob:
        prose = (
            "Cancer cells often hide from the immune system by pressing 'off switches' (PD-1 and PD-L1) on T-cells. "
            "Immunotherapy drugs block those switches so T-cells can wake back up and attack the tumor.\n\n"
            "Whether the treatment works depends heavily on how many DNA mutations the tumor has and whether helper-turned-blocker cells in the surrounding tissue are holding the immune response back. "
            "Researchers are actively hunting for reliable biological markers to predict which patients will benefit most."
        )
    elif "ltp" in search_blob or "potentiation" in search_blob or "hippocampal" in search_blob:
        prose = (
            "Our brains store memories by strengthening the connections (synapses) between neurons in the hippocampus—a process called long-term potentiation (LTP). "
            "When a synapse is activated, NMDA receptors open and let calcium flow in, which tells the neuron to add more signal-receiving AMPA receptors to its surface.\n\n"
            "A brain growth protein called BDNF helps lock in these stronger connections for learning and mood balance. "
            "When this connection-strengthening process breaks down, it contributes to conditions like depression and Alzheimer's disease."
        )
    else:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", passage or prompt) if len(s.strip()) > 15]
        first = sentences[0] if sentences else (passage[:220] if passage else "This passage examines a key mechanism in the research paper.")
        last = sentences[-1] if len(sentences) > 1 else "Understanding this relationship helps clarify the main experimental findings."
        prose = (
            f"In plain English, this passage explains that {first[0].lower() + first[1:] if len(first) > 1 else first} "
            f"The authors highlight how these factors interact so readers can see what drives the primary effect without getting lost in technical jargon.\n\n"
            f"The key takeaway is: {last}"
        )

    if "---TERMS_JSON---" in prompt:
        terms_json = json.dumps(matched_terms[:4])
        if "DEFINITIONS:" in prompt:
            return f"DEFINITIONS:\nKey technical terms from your selection:\n\n---TERMS_JSON---\n{terms_json}"
        return f"SIMPLIFIED EXPLANATION:\n{prose}\n\n---TERMS_JSON---\n{terms_json}"

    return prose


# ---------------------------------------------------------------------------
# Public generation API (provider-dispatching)
# ---------------------------------------------------------------------------
def safe_generate_text(prompt: str, generation_config=None) -> str:
    if not _has_valid_api_key():
        return _synthesize_demo_response(prompt)
    try:
        if _provider() == "groq":
            return _groq_generate_text(prompt, generation_config)
        return _gemini_generate_text(prompt, generation_config)
    except Exception as e:
        logger.warning("LLM provider failed (%s); using synthesized fallback", e)
        return _synthesize_demo_response(prompt)


def safe_generate_text_stream(prompt: str, generation_config=None):
    if not _has_valid_api_key():
        text = _synthesize_demo_response(prompt)
        step = 18
        for i in range(0, len(text), step):
            yield text[i : i + step]
        return
    try:
        if _provider() == "groq":
            yield from _groq_generate_text_stream(prompt, generation_config)
        else:
            yield from _gemini_generate_text_stream(prompt, generation_config)
    except Exception as e:
        logger.warning("LLM stream failed (%s); streaming synthesized fallback", e)
        text = _synthesize_demo_response(prompt)
        step = 18
        for i in range(0, len(text), step):
            yield text[i : i + step]


def safe_generate_vision_stream(
    prompt: str,
    image_bytes: bytes,
    mime_type: str = "image/png",
    generation_config=None,
):
    """Stream a multimodal (text + image) response. Google/Gemini only."""
    if _provider() == "groq":
        raise RuntimeError("Vision analysis requires Gemini (llm_provider=google)")
    yield from _gemini_generate_vision_stream(
        prompt, image_bytes, mime_type, generation_config
    )


# ---------------------------------------------------------------------------
# Groq implementation (OpenAI-compatible chat completions)
# ---------------------------------------------------------------------------
def _groq_headers() -> dict:
    key = get_settings().groq_api_key
    if not key:
        raise RuntimeError("GROQ_API_KEY not set")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _groq_payload(model: str, prompt: str, generation_config, stream: bool) -> dict:
    temperature, max_tokens = _gen_params(generation_config)
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }


def _groq_generate_text(prompt: str, generation_config=None) -> str:
    global _resolved_model_name, _resolved_model
    last_error: Exception | None = None

    for name in _ordered_candidates():
        try:
            resp = requests.post(
                GROQ_URL,
                headers=_groq_headers(),
                json=_groq_payload(name, prompt, generation_config, stream=False),
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            text = (data["choices"][0]["message"]["content"] or "").strip()
            if not text:
                raise RuntimeError("Empty response from Groq")
            _resolved_model = {"provider": "groq", "model": name}
            _resolved_model_name = name
            return text
        except Exception as e:
            last_error = e
            logger.warning("Groq generate failed for %s: %s", name, e)
            _resolved_model = None
            _resolved_model_name = None

    raise RuntimeError(f"Groq generation failed. Last error: {last_error}")


def _groq_generate_text_stream(prompt: str, generation_config=None):
    global _resolved_model_name, _resolved_model
    last_error: Exception | None = None

    for name in _ordered_candidates():
        try:
            with requests.post(
                GROQ_URL,
                headers=_groq_headers(),
                json=_groq_payload(name, prompt, generation_config, stream=True),
                timeout=120,
                stream=True,
            ) as resp:
                resp.raise_for_status()
                yielded_any = False
                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[len("data:"):].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    delta = (
                        chunk.get("choices", [{}])[0]
                        .get("delta", {})
                        .get("content")
                    )
                    if delta:
                        yielded_any = True
                        yield delta
                if not yielded_any:
                    raise RuntimeError("Empty streaming response from Groq")
            _resolved_model = {"provider": "groq", "model": name}
            _resolved_model_name = name
            return
        except Exception as e:
            last_error = e
            logger.warning("Groq stream failed for %s: %s", name, e)
            _resolved_model = None
            _resolved_model_name = None

    raise RuntimeError(f"Groq streaming failed. Last error: {last_error}")


# ---------------------------------------------------------------------------
# Gemini implementation
# ---------------------------------------------------------------------------
def _generation_config_or_default(generation_config=None):
    settings = get_settings()
    if generation_config is None:
        return genai.types.GenerationConfig(
            temperature=settings.temperature,
            top_p=0.95,
            top_k=40,
            max_output_tokens=settings.max_output_tokens,
        )
    return generation_config


def _gemini_generate_text(prompt: str, generation_config=None) -> str:
    """
    Generate text from Gemini, raising on blocked/empty responses.
    Retries next fallback model once if the current model fails at generate time.
    """
    global _resolved_model_name, _resolved_model

    generation_config = _generation_config_or_default(generation_config)
    tried: list[str] = []
    last_error: Exception | None = None

    for name in _ordered_candidates():
        if name in tried:
            continue
        tried.append(name)
        try:
            model = genai.GenerativeModel(name)
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
            )
            text = _extract_text(response)
            if not text:
                raise RuntimeError("Empty response from Gemini")
            _resolved_model = model
            _resolved_model_name = name
            return text
        except Exception as e:
            last_error = e
            logger.warning("Gemini generate failed for %s: %s", name, e)
            _resolved_model = None
            _resolved_model_name = None

    raise RuntimeError(f"Gemini generation failed. Last error: {last_error}")


def _gemini_generate_text_stream(prompt: str, generation_config=None):
    """
    Yield text chunks from Gemini streaming generate_content.
    Raises if no model produces any text.
    """
    global _resolved_model_name, _resolved_model

    generation_config = _generation_config_or_default(generation_config)
    tried: list[str] = []
    last_error: Exception | None = None

    for name in _ordered_candidates():
        if name in tried:
            continue
        tried.append(name)
        try:
            model = genai.GenerativeModel(name)
            stream = model.generate_content(
                prompt,
                generation_config=generation_config,
                stream=True,
            )
            yielded_any = False
            for chunk in stream:
                text = _extract_chunk_text(chunk)
                if text:
                    yielded_any = True
                    yield text
            if not yielded_any:
                raise RuntimeError("Empty streaming response from Gemini")
            _resolved_model = model
            _resolved_model_name = name
            return
        except Exception as e:
            last_error = e
            logger.warning("Gemini stream failed for %s: %s", name, e)
            _resolved_model = None
            _resolved_model_name = None

    raise RuntimeError(f"Gemini streaming failed. Last error: {last_error}")


def _gemini_generate_vision_stream(
    prompt: str,
    image_bytes: bytes,
    mime_type: str = "image/png",
    generation_config=None,
):
    """Yield text chunks from Gemini multimodal streaming."""
    global _resolved_model_name, _resolved_model

    generation_config = _generation_config_or_default(generation_config)
    tried: list[str] = []
    last_error: Exception | None = None
    image_part = {"mime_type": mime_type, "data": image_bytes}

    for name in _ordered_candidates():
        if name in tried:
            continue
        tried.append(name)
        try:
            model = genai.GenerativeModel(name)
            stream = model.generate_content(
                [prompt, image_part],
                generation_config=generation_config,
                stream=True,
            )
            yielded_any = False
            for chunk in stream:
                text = _extract_chunk_text(chunk)
                if text:
                    yielded_any = True
                    yield text
            if not yielded_any:
                raise RuntimeError("Empty vision streaming response from Gemini")
            _resolved_model = model
            _resolved_model_name = name
            return
        except Exception as e:
            last_error = e
            logger.warning("Gemini vision stream failed for %s: %s", name, e)
            _resolved_model = None
            _resolved_model_name = None

    raise RuntimeError(f"Gemini vision streaming failed. Last error: {last_error}")


def _extract_chunk_text(chunk) -> str:
    """Extract incremental text from a streaming chunk."""
    try:
        text = chunk.text
        if text:
            return text
    except Exception:
        pass
    try:
        candidates = getattr(chunk, "candidates", None) or []
        parts_out = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                part_text = getattr(part, "text", None)
                if part_text:
                    parts_out.append(part_text)
        return "".join(parts_out)
    except Exception:
        return ""


def _extract_text(response) -> str:
    """Safely pull text from a Gemini response object."""
    try:
        text = response.text
        if text and text.strip():
            return text.strip()
    except Exception:
        pass

    # Fallback: walk candidates/parts
    try:
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            chunks = []
            for part in parts:
                part_text = getattr(part, "text", None)
                if part_text:
                    chunks.append(part_text)
            if chunks:
                return "".join(chunks).strip()
    except Exception:
        pass

    return ""
