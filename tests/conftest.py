"""Shared fixtures for all tests.

Uses an in-memory mock Supabase client so tests run without a live database.
"""
import copy
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# In-memory mock Supabase client
# ---------------------------------------------------------------------------

class _Result:
    """Mimics the Supabase execute() return value."""
    def __init__(self, data):
        self.data = data


class _QueryBuilder:
    """Mimics the Supabase chained query API."""

    def __init__(self, store, table_name):
        self._store = store            # reference to the dict-of-lists
        self._table = table_name
        self._filters = []             # list of (field, value)
        self._order_field = None
        self._order_desc = False
        self._single = False
        self._op = None                # "select" | "insert" | "update" | "delete"
        self._payload = None

    # -- operation starters --------------------------------------------------

    def select(self, _cols="*"):
        self._op = "select"
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def delete(self):
        self._op = "delete"
        return self

    # -- modifiers -----------------------------------------------------------

    def eq(self, field, value):
        self._filters.append((field, value))
        return self

    def order(self, field, desc=False):
        self._order_field = field
        self._order_desc = desc
        return self

    def maybe_single(self):
        self._single = True
        return self

    # -- execution -----------------------------------------------------------

    def _rows(self):
        """Return rows from the in-memory store that match all filters."""
        rows = self._store.setdefault(self._table, [])
        for field, value in self._filters:
            rows = [r for r in rows if r.get(field) == value]
        return rows

    def execute(self):
        now = datetime.now(timezone.utc)

        if self._op == "select":
            rows = self._rows()
            if self._order_field:
                rows = sorted(rows, key=lambda r: r.get(self._order_field, ""),
                              reverse=self._order_desc)
            if self._single:
                return _Result(copy.deepcopy(rows[0]) if rows else None)
            return _Result([copy.deepcopy(r) for r in rows])

        elif self._op == "insert":
            record = dict(self._payload)
            record.setdefault("id", str(uuid.uuid4()))
            record.setdefault("created_at", now)
            record.setdefault("updated_at", now)
            self._store.setdefault(self._table, []).append(record)
            return _Result([copy.deepcopy(record)])

        elif self._op == "update":
            rows = self._rows()
            updated = []
            for row in rows:
                row.update(self._payload)
                row["updated_at"] = now
                updated.append(copy.deepcopy(row))
            return _Result(updated)

        elif self._op == "delete":
            matching = self._rows()
            ids_to_remove = {r["id"] for r in matching}
            self._store[self._table] = [
                r for r in self._store.get(self._table, [])
                if r["id"] not in ids_to_remove
            ]
            return _Result([])

        return _Result([])


class MockSupabase:
    """Lightweight in-memory replacement for the Supabase client."""

    def __init__(self):
        self._store = {}  # table_name -> list of dicts

    def table(self, name):
        return _QueryBuilder(self._store, name)

    def reset(self):
        self._store.clear()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _mock_supabase():
    """Session-scoped mock — shared across all tests."""
    return MockSupabase()


@pytest.fixture(scope="session")
def app(_mock_supabase):
    """Create the Flask app with the mock Supabase client patched in."""
    import app as app_module
    # Patch before create_app tries to connect
    app_module.supabase = _mock_supabase

    from app.config import config

    class _TestConfig(config["testing"]):
        TESTING = True
        SUPABASE_URL = "http://mock"
        SUPABASE_SERVICE_KEY = "mock-key"
        SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiJ9.signature"
        SCREEN_MATERIALS_DIR = tempfile.mkdtemp(prefix="screen-materials-tests-")

    config["testing"] = _TestConfig

    flask_app = app_module.create_app("testing")
    # Re-patch after create_app (it may overwrite the global)
    app_module.supabase = _mock_supabase
    return flask_app


@pytest.fixture(autouse=True)
def _clean_store(_mock_supabase, app):
    """Reset all in-memory data between tests (also ensures app is created)."""
    _mock_supabase.reset()
    materials_dir = app.config.get("SCREEN_MATERIALS_DIR")
    if materials_dir:
        shutil.rmtree(materials_dir, ignore_errors=True)


@pytest.fixture
def user(app):
    from app.services.auth_service import AuthService
    return AuthService.create_user("test@example.com", "password123", name="Test User")


@pytest.fixture
def client(app, user):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email
        sess["user_name"] = user.name
    return client


@pytest.fixture
def anonymous_client(app):
    return app.test_client()


@pytest.fixture
def project(app, user):
    """Isolated test project."""
    from app.services.project_service import ProjectService
    p = ProjectService.create(name="Test Project", user_id=user.id)
    return p


@pytest.fixture
def project_id(project):
    return project.id
