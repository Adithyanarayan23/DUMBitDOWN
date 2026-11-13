"""Step 2 of index.pkl migration: run with the venv (langchain 0.1.0 pins).

Rebuilds index.pkl from _docstore_export.json using the OLD pydantic-v1
Document class so FAISS.load_local works under the pinned requirements.
Backs up the original pickle to index.pkl.bak first.
"""
import json
import pickle
import shutil
from pathlib import Path

from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_core.documents import Document

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "backend" / "vector_store"
PKL = STORE / "index.pkl"
BAK = STORE / "index.pkl.bak"
EXPORT = STORE / "_docstore_export.json"

payload = json.loads(EXPORT.read_text(encoding="utf-8"))

docs = {
    doc_id: Document(page_content=d["page_content"], metadata=d["metadata"])
    for doc_id, d in payload["docs"].items()
}
index_to_docstore_id = {int(k): v for k, v in payload["index_to_docstore_id"].items()}

if not BAK.exists():
    shutil.copy2(PKL, BAK)
    print(f"Backed up original to {BAK}")

with open(PKL, "wb") as f:
    pickle.dump((InMemoryDocstore(docs), index_to_docstore_id), f)

print(f"Rebuilt {PKL} with {len(docs)} docs (old-langchain compatible)")
