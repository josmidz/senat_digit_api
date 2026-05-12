"""Pytest fixtures for the characterization harness.

Adapts the spec in `_planning/05_characterization_harness.md` to the actual
project layout (Beanie/MongoDB + unqualified `app.*` imports).
"""
import os

import pytest


CHAR_DB_NAME = os.environ.get("CHAR_DB_NAME", "senat_digit_char")
CHAR_DB_URL = os.environ.get("CHAR_DB_URL", "mongodb://localhost:27017")


@pytest.fixture(scope="session")
def app():
    """Import the FastAPI app. Triggers all startup-time imports."""
    from app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture(scope="session")
def tokens(client):
    """Pre-authenticate one user per role used in scenarios.

    Token *bodies* are pinned via redaction in snapshot.py, not by value.
    Login endpoint and credentials are placeholder until §3.5 seed creates
    deterministic char-* test users — populate after first restructure pass
    or via a dedicated `tests/characterization/fixtures_seed.py`.
    """
    creds = {
        "senateur":   ("char.senateur@senat.local",   "char-pass"),
        "greffier":   ("char.greffier@senat.local",   "char-pass"),
        "admin_it":   ("char.adminit@senat.local",    "char-pass"),
        "archiviste": ("char.archiviste@senat.local", "char-pass"),
        "anon":       (None, None),
    }
    out = {}
    for role, (username, pwd) in creds.items():
        if username is None:
            out[role] = None
            continue
        try:
            r = client.post("/api/v1/login", json={"username": username, "password": pwd})
            out[role] = r.json().get("access_token") if r.status_code == 200 else None
        except Exception:
            out[role] = None
    return out


def pytest_addoption(parser):
    parser.addoption(
        "--snapshot-update",
        action="store_true",
        default=False,
        help="Capture/refresh baseline snapshots instead of comparing.",
    )


@pytest.fixture(scope="session")
def snapshot_update(request):
    return request.config.getoption("--snapshot-update")
