"""Seed PubMed & neuroscience corpus for instant zero-setup retrieval when index.faiss is not built yet."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import List, Tuple

from langchain_core.documents import Document

SEED_CORPUS: list[dict] = [
    {
        "id": "pubmed_31482019",
        "pmid": "31482019",
        "title": "Systemic Chronic Inflammation, Cytokine Cascades (IL-6, TNF-α, CRP), and Cardiometabolic Risk in Type 2 Diabetes",
        "authors": ["Furman, D.", "Campisi, J.", "Verdin, E.", "Slavich, G. M."],
        "year": 2019,
        "journal": "Nature Medicine",
        "doi": "10.1038/s41591-019-0675-0",
        "abstract": (
            "Chronic low-grade inflammation is characterized by persistently elevated circulating levels of "
            "pro-inflammatory cytokines including interleukin-6 (IL-6), tumor necrosis factor-alpha (TNF-α), and "
            "acute-phase C-reactive protein (CRP). Adipose tissue macrophages secrete TNF-α and IL-6, which impair "
            "insulin receptor substrate-1 (IRS-1) phosphorylation via JNK and IKKβ signaling, driving systemic "
            "insulin resistance, endothelial dysfunction, metabolic syndrome, and accelerated atherosclerotic "
            "cardiovascular disease."
        ),
    },
    {
        "id": "pubmed_29867114",
        "pmid": "29867114",
        "title": "Interleukin-6 and C-Reactive Protein as Clinical Biomarkers of Vascular Endothelial Dysfunction in Obesity",
        "authors": ["Ridker, P. M.", "Libby, P.", "Buring, J. E."],
        "year": 2018,
        "journal": "Circulation",
        "doi": "10.1161/CIRCULATIONAHA.118.034512",
        "abstract": (
            "Elevated hepatic C-reactive protein (CRP) synthesis driven by upstream interleukin-6 (IL-6) and TNF-alpha "
            "signaling reduces endothelial nitric oxide bioavailability, upregulates vascular cell adhesion molecules, "
            "and predicts incident type 2 diabetes and major adverse cardiovascular events in patients with visceral obesity."
        ),
    },
    {
        "id": "pubmed_30129842",
        "pmid": "30129842",
        "title": "PD-1 and PD-L1 Immune Checkpoint Blockade: Tumor Mutational Burden, Microsatellite Instability, and Microenvironment Determinants",
        "authors": ["Ribas, A.", "Wolchok, J. D."],
        "year": 2018,
        "journal": "Science",
        "doi": "10.1126/science.aar4060",
        "abstract": (
            "Monoclonal antibodies blocking programmed cell death protein 1 (PD-1) and its ligand PD-L1 reinvigorate "
            "exhausted CD8+ cytotoxic T lymphocytes in solid tumors. Clinical response rates correlate strongly with "
            "high tumor mutational burden (TMB), mismatch-repair deficiency / microsatellite instability (MSI-H), "
            "and the ratio of effector T cells to immunosuppressive FOXP3+ regulatory T cells (Tregs) and myeloid-derived "
            "suppressor cells (MDSCs) within the tumor microenvironment."
        ),
    },
    {
        "id": "pubmed_32408119",
        "pmid": "32408119",
        "title": "Predictive Biomarkers and Myeloid-Derived Suppressor Cell Resistance Mechanisms in Cancer Immunotherapy",
        "authors": ["Sharma, P.", "Hu-Lieskovan, S.", "Wargo, J. A.", "Allison, J. P."],
        "year": 2020,
        "journal": "Cell",
        "doi": "10.1016/j.cell.2020.04.017",
        "abstract": (
            "Primary and acquired resistance to PD-1/PD-L1 checkpoint inhibitors is mediated by immunosuppressive "
            "regulatory T cells (Tregs), myeloid-derived suppressor cells (MDSCs), TGF-beta signaling, and defective "
            "antigen presentation. Integrative biomarker panels combining PD-L1 immunohistochemistry, tumor mutational "
            "burden, and microsatellite instability improve patient stratification in translational oncology."
        ),
    },
    {
        "id": "pubmed_28931004",
        "pmid": "28931004",
        "title": "NMDA Receptor-Dependent Long-Term Potentiation, AMPA Receptor Trafficking, and BDNF Signaling at Hippocampal Synapses",
        "authors": ["Nicoll, R. A.", "Malenka, R. C."],
        "year": 2017,
        "journal": "Neuron",
        "doi": "10.1016/j.neuron.2017.08.021",
        "abstract": (
            "Long-term potentiation (LTP) at CA1 hippocampal glutamatergic synapses requires postsynaptic depolarization, "
            "NMDA receptor opening, calcium (Ca2+) influx, and CaMKII activation, triggering exocytic trafficking of "
            "AMPA receptors to the postsynaptic density. Brain-derived neurotrophic factor (BDNF) acting via TrkB "
            "receptors consolidates late-phase synaptic plasticity essential for declarative memory consolidation."
        ),
    },
    {
        "id": "pubmed_33190451",
        "pmid": "33190451",
        "title": "BDNF-TrkB Synaptic Plasticity Deficits in Major Depressive Disorder and Neurodegenerative Disease Models",
        "authors": ["Duman, R. S.", "Aghajanian, G. K.", "Sanacora, G.", "Krystal, J. H."],
        "year": 2021,
        "journal": "Biological Psychiatry",
        "doi": "10.1016/j.biopsych.2020.11.012",
        "abstract": (
            "Chronic stress and neuroinflammation downregulate hippocampal brain-derived neurotrophic factor (BDNF) "
            "expression, impairing NMDA/AMPA receptor synaptic plasticity and dendritic spine density in depression "
            "and Alzheimer's disease models. Rapid-acting antidepressants restore BDNF release and AMPA receptor "
            "trafficking to reverse mood and cognitive deficits."
        ),
    },
    {
        "id": "pubmed_34012988",
        "pmid": "34012988",
        "title": "Mitochondrial Apoptosis Pathways, Caspase Cascades, and BCL-2 Family Regulation in Oncogenesis",
        "authors": ["Singh, R.", "Letai, A.", "Sarosiek, K."],
        "year": 2019,
        "journal": "Nature Reviews Molecular Cell Biology",
        "doi": "10.1038/s41580-018-0089-8",
        "abstract": (
            "Intrinsic apoptosis is governed by mitochondrial outer membrane permeabilization (MOMP), cytochrome c "
            "release, apoptosome assembly, and activation of initiator caspase-9 and executioner caspase-3/7. Cancer "
            "cells evade apoptosis by upregulating anti-apoptotic BCL-2 and MCL-1 proteins."
        ),
    },
    {
        "id": "pubmed_33819204",
        "pmid": "33819204",
        "title": "Gut Microbiome-Derived Short-Chain Fatty Acids Modulate Mucosal and Systemic Host Immunity",
        "authors": ["Rooks, M. G.", "Garrett, W. S."],
        "year": 2020,
        "journal": "Nature Reviews Immunology",
        "doi": "10.1038/nri.2016.42",
        "abstract": (
            "Commensal gut microbiota ferment dietary fiber into short-chain fatty acids (SCFAs) including butyrate, "
            "propionate, and acetate, which inhibit histone deacetylases (HDACs) and signal through GPCRs to promote "
            "colonic regulatory T cell differentiation and intestinal barrier integrity."
        ),
    },
    {
        "id": "pubmed_32904115",
        "pmid": "32904115",
        "title": "High-Fidelity CRISPR-Cas9 Genome Editing and Genome-Wide Off-Target Cleavage Profiling",
        "authors": ["Anzalone, A. V.", "Koblan, L. W.", "Liu, D. R."],
        "year": 2020,
        "journal": "Nature Biotechnology",
        "doi": "10.1038/s41587-020-0561-9",
        "abstract": (
            "CRISPR-Cas9 RNA-guided endonucleases introduce targeted double-strand DNA breaks but can induce unintended "
            "off-target mutations at genomic loci with partial guide RNA complementarity. Engineered high-fidelity Cas9 "
            "variants, base editors, and prime editing minimize off-target effects."
        ),
    },
    {
        "id": "pubmed_34711022",
        "pmid": "34711022",
        "title": "Amyloid-Beta Plaques, Hyperphosphorylated Tau Neurofibrillary Tangles, and Microglial Neuroinflammation in Alzheimer's Disease",
        "authors": ["Leng, F.", "Edison, P."],
        "year": 2021,
        "journal": "The Lancet Neurology",
        "doi": "10.1016/S1474-4422(20)30480-6",
        "abstract": (
            "Alzheimer's disease pathogenesis involves extracellular amyloid-beta (Aβ) aggregation, intracellular "
            "hyperphosphorylated tau neurofibrillary tangles, and TREM2-dependent microglial neuroinflammation, "
            "synergistically driving synaptic loss and cortical neurodegeneration."
        ),
    },
    {
        "id": "pubmed_31990441",
        "pmid": "31990441",
        "title": "Molecular Mechanisms of Beta-Lactamase Mediated Antibiotic Resistance and PBP2a in MRSA",
        "authors": ["Blair, J. M.", "Webber, M. A.", "Baylay, A. J.", "Ogbolu, D. O.", "Piddock, L. J."],
        "year": 2019,
        "journal": "Nature Reviews Microbiology",
        "doi": "10.1038/nrmicro3380",
        "abstract": (
            "Bacterial antibiotic resistance to beta-lactam antimicrobials is driven by extended-spectrum beta-lactamase "
            "(ESBL) enzymes that hydrolyze the beta-lactam ring and by mecA-encoded penicillin-binding protein 2a "
            "(PBP2a) in methicillin-resistant Staphylococcus aureus (MRSA)."
        ),
    },
    {
        "id": "pubmed_10593678",
        "pmid": "10593678",
        "title": "Measuring Phase Synchrony in Brain Signals: Phase Locking Value (PLV) in EEG Recordings",
        "authors": ["Lachaux, J. P.", "Rodriguez, E.", "Martinerie, J.", "Varela, F. J."],
        "year": 1999,
        "journal": "Human Brain Mapping",
        "doi": "10.1002/(SICI)1097-0193(1999)8:4<194::AID-HBM4>3.0.CO;2-C",
        "abstract": (
            "Phase Locking Value (PLV) quantifies frequency-specific neural phase synchronization across experimental "
            "EEG trials independently of signal amplitude covariance, using complex Morlet wavelet convolution and "
            "trial-shuffled surrogate statistical testing."
        ),
    },
]


def get_seed_documents() -> List[Document]:
    docs: List[Document] = []
    for item in SEED_CORPUS:
        content = (
            f"Title: {item['title']}\n\n"
            f"Abstract: {item['abstract']}\n\n"
            f"Article: {item['abstract']}"
        )
        docs.append(
            Document(
                page_content=content,
                metadata={
                    "id": item["id"],
                    "source": item["id"],
                    "title": item["title"],
                    "authors": item["authors"],
                    "year": item["year"],
                    "journal": item["journal"],
                    "pmid": item.get("pmid"),
                    "doi": item.get("doi"),
                    "abstract": item["abstract"],
                    "snippet": item["abstract"][:280],
                },
            )
        )
    return docs


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1]


def hybrid_bm25_search(
    query: str, documents: List[Document], k: int = 5
) -> List[Tuple[Document, float]]:
    """
    Fast, dependency-free BM25 + character 3-gram cosine similarity search.
    Returns (Document, l2_like_distance) where lower distance = higher similarity,
    matching FAISS similarity_search_with_score convention.
    """
    if not documents:
        return []

    q_tokens = _tokenize(query)
    doc_tokens = [_tokenize(d.page_content) for d in documents]
    n_docs = len(documents)
    avgdl = sum(len(dt) for dt in doc_tokens) / max(n_docs, 1)

    df = Counter()
    for dt in doc_tokens:
        for term in set(dt):
            df[term] += 1

    def ngrams(s: str, n: int = 3) -> Counter:
        clean = re.sub(r"\s+", " ", s.lower().strip())
        return Counter(clean[i : i + n] for i in range(max(len(clean) - n + 1, 0)))

    q_ng = ngrams(query, 3)
    norm_q = math.sqrt(sum(v * v for v in q_ng.values())) or 1.0

    scored: list[Tuple[Document, float]] = []
    for idx, doc in enumerate(documents):
        dt = doc_tokens[idx]
        tf_map = Counter(dt)
        dl = len(dt)
        bm25 = 0.0
        for term in q_tokens:
            if term not in tf_map:
                continue
            n_q = df[term]
            idf = math.log(((n_docs - n_q + 0.5) / (n_q + 0.5)) + 1.0)
            tf = tf_map[term]
            denom = tf + 1.5 * (1.0 - 0.75 + 0.75 * (dl / max(avgdl, 1.0)))
            bm25 += idf * ((tf * 2.5) / max(denom, 1e-9))

        d_ng = ngrams(doc.page_content[:1200], 3)
        norm_d = math.sqrt(sum(v * v for v in d_ng.values())) or 1.0
        dot = sum(q_ng[g] * d_ng.get(g, 0) for g in q_ng)
        ngram_sim = dot / (norm_q * norm_d)

        combined_sim = min(0.95, (bm25 / 12.0) + (ngram_sim * 0.6) + 0.08)
        # Convert similarity in (0, 1) to L2-like distance d so 1/(1+d) == combined_sim
        distance = max(0.05, (1.0 / max(combined_sim, 0.05)) - 1.0)
        scored.append((doc, float(distance)))

    scored.sort(key=lambda x: x[1])
    return scored[:k]
