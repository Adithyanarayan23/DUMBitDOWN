"""
Local demo launcher: starts FastAPI backend + Vite frontend, opens the browser.

Requires: Python deps installed, Node/npm on PATH, GOOGLE_API_KEY in backend/.env
"""
from __future__ import annotations

import os
import sys
import subprocess
import threading
import time
import webbrowser
from urllib.request import urlopen
from urllib.error import URLError

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "backend")
FRONTEND_DIR = os.path.join(SCRIPT_DIR, "frontend")


def _python_executable() -> str:
    """Prefer the project venv interpreter so pinned deps are always used."""
    venv_python = os.path.join(
        SCRIPT_DIR,
        ".venv",
        "Scripts" if os.name == "nt" else "bin",
        "python.exe" if os.name == "nt" else "python",
    )
    return venv_python if os.path.exists(venv_python) else sys.executable

BACKEND_HEALTH = "http://localhost:5000/api/health"
FRONTEND_URL = "http://localhost:3000"
POLL_SECONDS = 90


def _pipe_output(prefix: str, stream):
    for line in iter(stream.readline, ""):
        if line:
            print(f"[{prefix}] {line.rstrip()}")
    stream.close()


def _start_process(cmd, cwd, prefix, shell=False):
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=shell,
    )
    thread = threading.Thread(
        target=_pipe_output, args=(prefix, process.stdout), daemon=True
    )
    thread.start()
    return process


def _wait_for(url: str, timeout: int) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as resp:
                if resp.status < 500:
                    return True
        except (URLError, OSError, TimeoutError):
            pass
        time.sleep(1)
    return False


def main():
    print("Starting DumbItDown (backend :5000 + frontend :3000)...")

    backend = _start_process(
        [_python_executable(), "main.py"],
        BACKEND_DIR,
        "BACKEND",
    )

    npm_cmd = ["npm", "run", "dev"]
    # Windows needs shell so npm.cmd resolves
    frontend = _start_process(
        npm_cmd if os.name != "nt" else " ".join(npm_cmd),
        FRONTEND_DIR,
        "FRONTEND",
        shell=(os.name == "nt"),
    )

    print(f"Waiting up to {POLL_SECONDS}s for services (FAISS cold start can be slow)...")
    backend_ok = _wait_for(BACKEND_HEALTH, POLL_SECONDS)
    frontend_ok = _wait_for(FRONTEND_URL, POLL_SECONDS)

    if not backend_ok:
        print("WARNING: Backend health check did not pass. Check [BACKEND] logs.")
    if not frontend_ok:
        print("WARNING: Frontend did not respond on :3000. Is Node/npm installed?")

    if frontend_ok:
        print(f"Opening {FRONTEND_URL}")
        webbrowser.open(FRONTEND_URL)
    elif backend_ok:
        webbrowser.open("http://localhost:5000/docs")

    try:
        print("App is running. Press Ctrl+C to quit.")
        while True:
            if backend.poll() is not None:
                print("Backend exited unexpectedly.")
                break
            if frontend.poll() is not None:
                print("Frontend exited unexpectedly.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        for proc in (frontend, backend):
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        print("Done.")


if __name__ == "__main__":
    main()
