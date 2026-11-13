"""Step 1 of index.pkl migration: run with the NEW langchain-core env (global py312).

Loads backend/vector_store/index.pkl (built with pydantic-v2 langchain-core)
and exports it to a neutral JSON file.
"""
import json
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKL = ROOT / "backend" / "vector_store" / "index.pkl"
OUT = ROOT / "backend" / "vector_store" / "_docstore_export.json"

with open(PKL, "rb") as f:
    docstore, index_to_docstore_id = pickle.load(f)

docs = {}
for doc_id, doc in docstore._dict.items():
    docs[doc_id] = {"page_content": doc.page_content, "metadata": doc.metadata or {}}

payload = {
    "index_to_docstore_id": {str(k): v for k, v in index_to_docstore_id.items()},
    "docs": docs,
}
OUT.write_text(json.dumps(payload), encoding="utf-8")
print(f"Exported {len(docs)} docs, {len(index_to_docstore_id)} index mappings -> {OUT}")
sys.exit(0)
