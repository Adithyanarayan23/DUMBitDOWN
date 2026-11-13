# DumbItDown — Full Code Audit Notes (Demo Video Level)

**Date:** 2026-07-12 (updated after fix pass)  
**Scope:** Backend + frontend code only (no Docker / deploy).  
**Bar:** Ready enough to film a demo video of Flow 1 (paste → simplify → stream → follow-up).

**Verdict (post-fix):** Core demo path should be filmable via `python start.py` or `main.py` + `npm run dev`. Embeddings aligned to MiniLM; citations mapped; PDF hang fixed; Gemini try-list added. PubMed links may still be empty (corpus metadata limitation).

---

## Status legend

- **Fixed** — addressed in the demo-readiness pass
- **Known limit** — cannot fully fix without re-ingest
- **Open** — intentionally deferred

---

## P0

| ID | Status | Notes |
|----|--------|-------|
| P0-1 start.py | **Fixed** | Spawns uvicorn + Vite :3000 |
| P0-2 FAISS missing | Ops | Present on this machine; health reports error if missing |
| P0-3 Eager init | **Fixed** | Lazy getters in `api/routes.py` |
| P0-4 Embedding mismatch | **Fixed** | Default MiniLM; set in `backend/.env` |
| P0-5 normalize mismatch | **Fixed** | `normalize_embeddings=False` |
| P0-6 Gemini preview ID | **Fixed** | `core/llm.py` try-list + cache |
| P0-7 .env cwd | **Fixed** | Absolute paths from `config.py` |
| P0-8 Cold start | Ops | Warm once before recording; start.py waits 90s |
| P0-9 PDF hang | **Fixed** | `setState('success')` after simplify |

## P1

| ID | Status | Notes |
|----|--------|-------|
| P1-1 Citation field mismatch | **Fixed** | Backend aliases + `utils/citations.js` |
| P1-2 Authors array | **Fixed** | Normalized to string |
| P1-3 Double retrieve | **Fixed** | Single retrieve per search |
| P1-4 Query rewrite on paste | **Fixed** | Skip if len >= 200 |
| P1-5 L2 rerank inverted | **Fixed** | `sim = 1/(1+d)` |
| P1-6 PDF no citations | **Fixed** | Returns citations + terms |
| P1-7 Follow-up no citations | **Fixed** | Returns citations |
| P1-8 technical_terms | **Fixed** | Same-call `---TERMS_JSON---` trailer |
| P1-9 No loading exchange | **Fixed** | Optimistic loading card |
| P1-10 Soft-fail strings | **Fixed** | Raises → HTTP error |
| P1-11 response.text unguarded | **Fixed** | `safe_generate_text` |
| P1-12 Ingest path | **Fixed** | `OUTPUT_DIR = vector_store` |

## P2

| ID | Status | Notes |
|----|--------|-------|
| P2-1 Session click | **Fixed** | Grouped + scroll |
| P2-2 Server conversation list | **Open** | In-memory enough for demo |
| P2-3 Follow-up only first | **Fixed** | Last exchange gets follow-up |
| P2-4 Citation detail drawer | **Open** | Flat list OK for demo |
| P2-5 Favicon | **Fixed** | `frontend/public/vite.svg` |
| P2-6 GitHub URL | **Open** | Low priority |
| P2-7 Dead vanilla JS | **Open** | Left in tree |
| P2-8/9 Legacy modules | **Fixed** | LEGACY banners |
| P2-10 Cascade delete | **Fixed** | |
| P2-11 Shallow health | **Fixed** | vector + gemini checks |
| P2-12 Error leakage | **Fixed** | Short client detail |
| P2-13 .env.example drift | **Fixed** | |
| P2-14 DEPLOY docs | **Fixed** | Local Vite path documented first |
| P2-15 Hardcoded key in test | **Fixed** | Uses env |
| P2-16 Live .env secrets | Ops | Keep gitignored; rotate if leaked |
| P2-17 ST pin fragility | **Open** | Verify install on demo machine |
| P2-18 TermTooltip unused | **Fixed** | Wired when terms present |
| P2-19 Grand Archive art | **Open** | CSS hero OK |
| P2-20 CORS * | Noted | Comment in `main.py` |

## Known limit

Corpus metadata is mostly `title` / `source` / `section` — **PubMed/arXiv buttons often empty**. Demo sell: titles + contribution %.

## Run

```powershell
cd backend; python main.py
cd frontend; npm run dev
# or: python start.py
```
