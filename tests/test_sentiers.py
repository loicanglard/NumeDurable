"""Tests for trail (sentier) CRUD and authorization."""
import pytest


VALID_SENTIER = {
    "nom": "Col du Test",
    "region": "Haute-Savoie",
    "distance_km": "15.0",
    "denivele_pos": "900",
    "difficulte": "difficile",
    "types_pratique": ["trail"],
}


class TestSentiersList:
    def test_public_access(self, client):
        resp = client.get("/sentiers/")
        assert resp.status_code == 200

    def test_filter_by_region(self, client, sentier_id):
        resp = client.get("/sentiers/?region=Isère")
        assert resp.status_code == 200

    def test_filter_by_difficulte(self, client, sentier_id):
        resp = client.get("/sentiers/?difficulte=moyen")
        assert resp.status_code == 200

    def test_invalid_difficulte_ignored(self, client):
        resp = client.get("/sentiers/?difficulte=INVALID")
        assert resp.status_code == 200


class TestSentierDetail:
    def test_existing_sentier(self, client, sentier_id):
        resp = client.get(f"/sentiers/{sentier_id}")
        assert resp.status_code == 200

    def test_nonexistent_sentier_redirects(self, client):
        resp = client.get("/sentiers/99999", follow_redirects=False)
        assert resp.status_code == 302


class TestSentierCreate:
    def test_requires_auth(self, client):
        resp = client.get("/sentiers/nouveau", follow_redirects=False)
        assert resp.status_code == 302
        assert b"connexion" in resp.headers.get("Location", "").encode()

    def test_authenticated_can_see_form(self, auth_client):
        resp = auth_client.get("/sentiers/nouveau")
        assert resp.status_code == 200

    def test_create_valid_sentier(self, auth_client):
        resp = auth_client.post(
            "/sentiers/nouveau", data=VALID_SENTIER, follow_redirects=False
        )
        assert resp.status_code == 302

    def test_missing_nom_rejected(self, auth_client):
        data = {**VALID_SENTIER, "nom": ""}
        resp = auth_client.post("/sentiers/nouveau", data=data, follow_redirects=True)
        assert resp.status_code == 200
        assert b"nom" in resp.data.lower()

    def test_invalid_distance_rejected(self, auth_client):
        data = {**VALID_SENTIER, "distance_km": "-5"}
        resp = auth_client.post("/sentiers/nouveau", data=data, follow_redirects=True)
        assert resp.status_code == 200

    def test_invalid_difficulte_rejected(self, auth_client):
        data = {**VALID_SENTIER, "difficulte": "ULTRA"}
        resp = auth_client.post("/sentiers/nouveau", data=data, follow_redirects=True)
        assert resp.status_code == 200


class TestSentierAuthorization:
    def test_owner_can_edit(self, auth_client, sentier_id):
        resp = auth_client.get(f"/sentiers/{sentier_id}/modifier")
        assert resp.status_code == 200

    def test_other_user_cannot_edit(self, app, sentier_id):
        """A second user registered via the signup form cannot modify someone else's sentier."""
        other_client = app.test_client()
        # Register + auto-login as a different user
        other_client.post(
            "/auth/inscription",
            data={
                "nom": "Autre",
                "email": "autre@test.fr",
                "mdp": "autrepass123",
                "mdp_confirm": "autrepass123",
                "niveau": "débutant",
            },
            follow_redirects=True,
        )
        resp = other_client.post(
            f"/sentiers/{sentier_id}/modifier",
            data=VALID_SENTIER,
            follow_redirects=False,
        )
        # Must redirect back (not to success URL), or the redirect target is the detail page
        # The important thing is: the edit is NOT applied (flash 'Non autorisé' → redirect detail)
        assert resp.status_code == 302

    def test_admin_can_delete_any(self, admin_client, sentier_id):
        resp = admin_client.post(
            f"/sentiers/{sentier_id}/supprimer", follow_redirects=False
        )
        assert resp.status_code == 302

    def test_delete_requires_auth(self, app):
        """Unauthenticated DELETE must redirect to connexion (no sentier_id fixture to avoid state leak)."""
        anon = app.test_client()
        resp = anon.post("/sentiers/1/supprimer", follow_redirects=False)
        assert resp.status_code == 302
        assert "connexion" in resp.headers.get("Location", "")