"""Tests for user profile management."""
import pytest


class TestProfil:
    def test_requires_auth(self, client):
        resp = client.get("/utilisateurs/profil", follow_redirects=False)
        assert resp.status_code == 302

    def test_profile_visible_when_logged_in(self, auth_client):
        resp = auth_client.get("/utilisateurs/profil")
        assert resp.status_code == 200
        assert b"Alice" in resp.data

    def test_update_profile_nom(self, auth_client):
        resp = auth_client.post(
            "/utilisateurs/profil",
            data={"nom": "Alice Modifiée", "niveau": "intermédiaire", "localisation": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_update_profile_with_password(self, auth_client):
        """Regression test: datetime import bug — should not raise NameError."""
        resp = auth_client.post(
            "/utilisateurs/profil",
            data={
                "nom": "Alice",
                "niveau": "débutant",
                "localisation": "",
                "mdp": "nouveaumdp1",
                "mdp_confirm": "nouveaumdp1",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_password_too_short_rejected(self, auth_client):
        resp = auth_client.post(
            "/utilisateurs/profil",
            data={
                "nom": "Alice",
                "niveau": "débutant",
                "localisation": "",
                "mdp": "court",
                "mdp_confirm": "court",
            },
            follow_redirects=True,
        )
        assert b"8" in resp.data or b"trop court" in resp.data.lower()

    def test_password_mismatch_rejected(self, auth_client):
        resp = auth_client.post(
            "/utilisateurs/profil",
            data={
                "nom": "Alice",
                "niveau": "débutant",
                "localisation": "",
                "mdp": "nouveaumdp1",
                "mdp_confirm": "autrechose",
            },
            follow_redirects=True,
        )
        assert b"correspondent" in resp.data.lower()


class TestPublicProfile:
    def test_existing_user_profile(self, client, app):
        with app.app_context():
            from backend.db import get_db
            row = get_db().execute(
                'SELECT id FROM "user" WHERE email = ?', ("alice@test.fr",)
            ).fetchone()
        resp = client.get(f"/utilisateurs/{row['id']}")
        assert resp.status_code == 200

    def test_nonexistent_user_redirects(self, client):
        resp = client.get("/utilisateurs/99999", follow_redirects=False)
        assert resp.status_code == 302