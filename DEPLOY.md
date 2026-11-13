# DumbItDown Deployment Guide

**100% FREE TO RUN** — No paid APIs required.

## Local demo (recommended — use this)

Requires Python 3.10+, Node.js/npm, and a Google Gemini API key.

```bash
# 1) Env
cp .env.example backend/.env
# Edit backend/.env — set GOOGLE_API_KEY
# Keep EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
# Keep NORMALIZE_EMBEDDINGS=false (matches existing FAISS index)

# 2a) One-command launcher (opens http://localhost:3000)
python start.py

# 2b) Or two terminals:
cd backend && python main.py          # API :5000
cd frontend && npm install && npm run dev   # UI :3000 (proxies /api)
```

- Frontend (React/Vite): http://localhost:3000  
- Backend API / docs: http://localhost:5000/docs  
- Health: http://localhost:5000/api/health  

FAISS files live in `backend/vector_store/` (`index.faiss` + `index.pkl`). Re-ingest only if missing:

```bash
cd backend
python ingest_data.py
```

Warm before a demo video:

```bash
python scripts/warm_demo.py
```

See root [README.md](README.md) for architecture and [demo/SAMPLES.md](demo/SAMPLES.md) for paste texts.

---

## Docker (secondary / fragile)

Docker Compose exists for experimentation but is **not** the supported demo path.

Known issues:

- Older compose setups mounted frontend **source** into nginx instead of a Vite `dist/` build.
- `docker-compose.prod.yml` is not guaranteed to exist.
- Prefer building a static frontend (`cd frontend && npm run build`) and serving `dist/` if you use containers.

### Backend-only compose (default)

```bash
cp .env.example .env
# set GOOGLE_API_KEY, DEPLOYMENT=local
docker-compose up --build backend
```

### Optional nginx frontend (requires Vite build first)

```bash
cd frontend && npm run build && cd ..
docker-compose --profile with-nginx up --build
```

Nginx serves `frontend/dist/` only (profile `with-nginx`). Do not mount raw `frontend/` source.

---

## Cloud path (Railway / Fly + Qdrant)

Configs: [railway.json](railway.json), [fly.toml](fly.toml).

1. Create a free [Qdrant Cloud](https://qdrant.tech/cloud/) cluster.
2. Set env:

```
GOOGLE_API_KEY=...
DEPLOYMENT=cloud
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_key
QDRANT_COLLECTION=dumbitdown_papers
```

3. Upload / re-ingest vectors into Qdrant (local FAISS files are not used in cloud mode).
4. Deploy the FastAPI backend via Railway or Fly; host the Vite build on the same platform or a static host with `/api` proxied to the backend.

This path is for production-style hosting, not for filming the local demo video.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Backend won't start | Check `GOOGLE_API_KEY` in `backend/.env` |
| Vector store missing | `cd backend && python ingest_data.py` |
| First request very slow | Normal cold start; run `python scripts/warm_demo.py` |
| Embedding mismatch | Keep MiniLM + `NORMALIZE_EMBEDDINGS=false` aligned with ingest |
