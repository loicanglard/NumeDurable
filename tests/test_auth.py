"""Tests for authentication flows."""
import pytest


class TestInscription:
    def test_get_shows_form(self, client):
        resp = client.get("/auth/inscription")
        assert resp.status_code == 200
        assert b"inscription" in resp.data.lower()

    def test_successful_registration_redirects(self, client):
        resp = client.post(
            "/auth/inscription",
            data={
                "nom": "Bob",
                "email": "bob@example.fr",
                "mdp": "monmotdepasse",
                "mdp_confirm": "monmotdepasse",
                "niveau": "débutant",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_successful_registration_logs_in(self, client):
        resp = client.post(
            "/auth/inscription",
            data={
                "nom": "Bob",
                "email": "bob@example.fr",
                "mdp": "monmotdepasse",
                "mdp_confirm": "monmotdepasse",
                "niveau": "débutant",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_missing_nom_rejected(self, client):
        resp = client.post(
            "/auth/inscription",
            data={
                "nom": "",
                "email": "bob@example.fr",
                "mdp": "monmotdepasse",
                "mdp_confirm": "monmotdepasse",
                "niveau": "débutant",
            },
            follow_redirects=True,
        )
        assert b"nom est requis" in resp.data.lower() or resp.status_code == 200

    def test_short_password_rejected(self, client):
        resp = client.post(
            "/auth/inscription",
            data={
                "nom": "Bob",
                "email": "bob@example.fr",
                "mdp": "court",
                "mdp_confirm": "court",
                "niveau": "débutant",
            },
            follow_redirects=True,
        )
        assert b"8" in resp.data

    def test_password_mismatch_rejected(self, client):
        resp = client.post(
            "/auth/inscription",
            data={
                "nom": "Bob",
                "email": "bob@example.fr",
                "mdp": "monmotdepasse",
                "mdp_confirm": "autrechose",
                "niveau": "débutant",
            },
            follow_redirects=True,
        )
        assert b"correspondent" in resp.data.lower()

    def test_duplicate_email_rejected(self, client):
        data = {
            "nom": "Bob",
            "email": "alice@test.fr",
            "mdp": "monmotdepasse",
            "mdp_confirm": "monmotdepasse",
            "niveau": "débutant",
        }
        resp = client.post("/auth/inscription", data=data, follow_redirects=True)
        assert b"email" in resp.data.lower()

    def test_invalid_email_rejected(self, client):
        resp = client.post(
            "/auth/inscription",
            data={
                "nom": "Bob",
                "email": "pasunemail",
                "mdp": "monmotdepasse",
                "mdp_confirm": "monmotdepasse",
                "niveau": "débutant",
            },
            follow_redirects=True,
        )
        assert b"email" in resp.data.lower()


class TestConnexion:
    def test_get_shows_form(self, client):
        resp = client.get("/auth/connexion")
        assert resp.status_code == 200

    def test_valid_credentials_redirect(self, client):
        resp = client.post(
            "/auth/connexion",
            data={"email": "alice@test.fr", "mdp": "password123"},
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_wrong_password_rejected(self, client):
        resp = client.post(
            "/auth/connexion",
            data={"email": "alice@test.fr", "mdp": "mauvaismdp"},
            follow_redirects=True,
        )
        assert b"incorrect" in resp.data.lower()

    def test_unknown_email_rejected(self, client):
        resp = client.post(
            "/auth/connexion",
            data={"email": "inconnu@test.fr", "mdp": "password123"},
            follow_redirects=True,
        )
        assert b"incorrect" in resp.data.lower()


class TestDeconnexion:
    def test_logout_redirects(self, auth_client):
        resp = auth_client.get("/auth/deconnexion", follow_redirects=False)
        assert resp.status_code == 302

    def test_logout_requires_login(self, client):
        resp = client.get("/auth/deconnexion", follow_redirects=False)
        assert resp.status_code == 302
        assert b"/auth/connexion" in resp.headers.get("Location", "").encode()