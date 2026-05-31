"""Pytest configuration.

Ensures the backend package root is importable and documents the dependency
gating used by the suite. Tests that need third-party packages (FastAPI,
SQLAlchemy, bcrypt, PyJWT, httpx) use ``pytest.importorskip`` so they run in CI
(where dependencies are installed) and skip cleanly in minimal environments.
"""
from __future__ import annotations

import os
import sys

# Make ``import app...`` work regardless of the invocation directory.
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)
