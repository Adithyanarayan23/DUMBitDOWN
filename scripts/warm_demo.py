#!/usr/bin/env python3
"""Warm the DumbItDown backend before filming a demo.

Hits /api/health then /api/search with Sample 1 so MiniLM + FAISS + Gemini
are loaded before you hit record.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:5000"

SAMPLE_1 = (
    "Chronic low-grade inflammation is characterized by elevated circulating "
    "levels of pro-inflammatory cytokines such as interleukin-6 (IL-6), tumor "
    "necrosis factor-alpha (TNF-α), and C-reactive protein (CRP). These "
    "mediators interact with insulin signaling pathways and endothelial "
    "function, contributing to metabolic syndrome and cardiovascular risk. "
    "Understanding how cytokine cascades propagate systemic effects is "
    "essential for interpreting clinical biomarkers in obesity and type 2 "
    "diabetes research."
)


def _request(method: str, path: str, body: dict | None = None) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    print(f"Warming {BASE} ...")
    try:
        health = _request("GET", "/api/health")
        print("Health:", json.dumps(health, indent=2)[:500])
        if health.get("status") not in ("ok", "healthy", "degraded"):
            # Accept any successful JSON health payload
            print("Health responded; continuing warm search.")
    except urllib.error.URLError as e:
        print(
            f"Backend not reachable at {BASE}. Start it with: python start.py\n({e})",
            file=sys.stderr,
        )
        return 1

    print("Running warm /api/search (Sample 1) — may take 30–90s on cold start...")
    try:
        result = _request(
            "POST",
            "/api/search",
            {"query": SAMPLE_1, "k": 5},
        )
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        print(f"Search failed ({e.code}): {detail}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"Search failed: {e}", file=sys.stderr)
        return 1

    sources = (result.get("citations") or {}).get("sources") or []
    preview = (result.get("simplified_text") or "")[:160]
    print(f"OK — {len(sources)} citation(s); preview: {preview!r}...")
    print("Backend is warm. Record your demo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
