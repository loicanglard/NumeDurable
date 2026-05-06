"""
Shared fixtures for the T.R.A.I.L test suite.

Each test gets a temporary SQLite file so the database persists across
per-request connections (unlike :memory: which spawns a new DB per connection).
CSRF is disabled to keep form submissions straightforward.
"""
import os
import tempfile
import pytest
import bcrypt
from datetime import datetime

from backend import create_app
from backend.db import get_db


def _make_testing_config(db_path):
    class TestingConfig:
        TESTING = True
        DEBUG = True
        SECRET_KEY = "test-secret-key-not-for-production"
        WTF_CSRF_ENABLED = False
        DB_TYPE = "sqlite"
        DATABASE = db_path
        SESSION_COOKIE_HTTPONLY = True
        SESSION_COOKIE_SAMESITE = "Lax"
        SESSION_COOKIE_SECURE = False
        PERMANENT_SESSION_LIFETIME = 3600
        REMEMBER_COOKIE_DURATION = 3600 * 24 * 7
        RATELIMIT_ENABLED = False

    return TestingConfig


@pytest.fixture()
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    cfg = _make_testing_config(db_path)
    application = create_app()
    application.config.from_object(cfg)

    with application.app_context():
        db = get_db()
        with application.open_resource("database/schema.sql") as f:
            db.executescript(f.read().decode("utf8"))

        now = datetime.utcnow()
        pw_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode("utf-8")
        admin_hash = bcrypt.hashpw(b"adminpass1", bcrypt.gensalt()).decode("utf-8")

        db.execute(
            'INSERT INTO "user" (nom, email, mdp_hash, niveau, localisation, is_admin, date_inscription, created_at, updated_at) '
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("Alice Test", "alice@test.fr", pw_hash, "débutant", "Paris", 0, now, now, now),
        )
        db.execute(
            'INSERT INTO "user" (nom, email, mdp_hash, niveau, localisation, is_admin, date_inscription, created_at, updated_at) '
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("Admin Test", "admin@test.fr", admin_hash, "expert", "Lyon", 1, now, now, now),
        )
        db.commit()

    yield application

    os.unlink(db_path)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_client(app):
    """A test client already logged in as the regular user (alice@test.fr)."""
    client = app.test_client()
    with client.session_transaction():
        pass
    client.post(
        "/auth/connexion",
        data={"email": "alice@test.fr", "mdp": "password123"},
        follow_redirects=True,
    )
    return client


@pytest.fixture()
def admin_client(app):
    """A test client already logged in as the admin user (admin@test.fr)."""
    client = app.test_client()
    client.post(
        "/auth/connexion",
        data={"email": "admin@test.fr", "mdp": "adminpass1"},
        follow_redirects=True,
    )
    return client


@pytest.fixture()
def sentier_id(app, auth_client):
    """Creates a sample sentier and returns its id."""
    resp = auth_client.post(
        "/sentiers/nouveau",
        data={
            "nom": "Sentier Test",
            "region": "Isère",
            "distance_km": "12.5",
            "denivele_pos": "400",
            "difficulte": "moyen",
            "types_pratique": ["trail"],
        },
        follow_redirects=False,
    )
    with app.app_context():
        row = get_db().execute("SELECT id FROM sentier ORDER BY id DESC LIMIT 1").fetchone()
        return row["id"] if row else None