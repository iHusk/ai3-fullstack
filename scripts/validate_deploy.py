"""Validate that all 5 Session 4.1 deploy patches are applied.

Run from the repo root after applying the patches and BEFORE pushing
to Community Cloud:

    uv run python scripts/validate_deploy.py

Exits 0 if every patch is present and the modules import cleanly
without API keys (the real test of the lazy-client fix).
Exits 1 with a clear message at the first failure.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    full = REPO_ROOT / rel_path
    if not full.exists():
        print(f"  FAIL — file not found: {rel_path}")
        sys.exit(1)
    return full.read_text()


def expect_in_file(rel_path: str, needle: str, label: str) -> None:
    if needle in _read(rel_path):
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}")
        print(f"        anchor not found in {rel_path}: {needle!r}")
        sys.exit(1)


def expect_not_in_file(rel_path: str, needle: str, label: str) -> None:
    if needle not in _read(rel_path):
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}")
        print(f"        leftover string in {rel_path}: {needle!r}")
        sys.exit(1)


def main() -> None:
    print("Validating Session 4.1 deploy patches...\n")

    print("Patch 1 - app/main.py pysqlite3 shim:")
    expect_in_file("app/main.py", "__import__('pysqlite3')", "pysqlite3 import shim")

    print("\nPatch 2 - app/main.py sidebar API keys:")
    expect_in_file("app/main.py", "=== DEPLOYMENT: API KEYS ===", "sidebar block anchor")
    expect_in_file("app/main.py", 'os.environ["ANTHROPIC_API_KEY"] = anthropic_key', "ANTHROPIC env write")
    expect_in_file("app/main.py", 'os.environ["VOYAGE_API_KEY"] = voyage_key', "VOYAGE env write")

    print("\nPatch 3 - pipeline/retrieval/hyde.py lazy client:")
    expect_in_file("pipeline/retrieval/hyde.py", "def _get_client():", "lazy _get_client function")
    expect_in_file("pipeline/retrieval/hyde.py", "client = _get_client()", "in-function client = _get_client() call")
    expect_not_in_file("pipeline/retrieval/hyde.py", "\nclient = anthropic.Anthropic()", "no module-level client construction")

    print("\nPatch 4 - pipeline/retrieval/enriched.py lazy client:")
    expect_in_file("pipeline/retrieval/enriched.py", "def _get_client():", "lazy _get_client function")
    expect_in_file("pipeline/retrieval/enriched.py", "client = _get_client()", "in-function client = _get_client() call")
    expect_not_in_file("pipeline/retrieval/enriched.py", "\nclient = anthropic.Anthropic()", "no module-level client construction")

    print("\nPatch 5 - app/feedback.py (no change required, just confirming the existing pattern):")
    expect_in_file("app/feedback.py", "try:", "try/except wrapping present")

    print("\nImport check (the real test — patched modules load WITHOUT API keys):")
    saved_anthro = os.environ.pop("ANTHROPIC_API_KEY", None)
    saved_voyage = os.environ.pop("VOYAGE_API_KEY", None)
    sys.path.insert(0, str(REPO_ROOT))
    try:
        import importlib

        for mod in (
            "pipeline.retrieval.hyde",
            "pipeline.retrieval.enriched",
            "app.rag",
        ):
            if mod in sys.modules:
                importlib.reload(sys.modules[mod])
            else:
                importlib.import_module(mod)
            print(f"  PASS  {mod} imports without API key")
    except Exception as e:
        print(f"  FAIL  import error: {e}")
        print("        most likely cause: a module still constructs anthropic.Anthropic() at import time")
        sys.exit(1)
    finally:
        if saved_anthro is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved_anthro
        if saved_voyage is not None:
            os.environ["VOYAGE_API_KEY"] = saved_voyage

    print("\nAll 5 patches applied. You're ready to deploy to Community Cloud.")


if __name__ == "__main__":
    main()
