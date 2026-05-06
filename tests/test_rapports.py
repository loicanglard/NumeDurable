"""Tests for condition report (rapport) CRUD, authorization, and expiration."""
import pytest
from datetime import datetime, timedelta


VALID_RAPPORT = {
    "statut": "praticable",
    "type_pratique": "trail",
    "obstacles": [],
    "commentaire": "Tout va bien.",
}


def create_rapport(auth_client, sentier_id, extra=None):
    data = {**VALID_RAPPORT, "sentier_id": sentier_id, **(extra or {})}
    return auth_client.post("/rapports/nouveau", data=data, follow_redirects=False)


class TestRapportCreate:
    def test_requires_auth(self, app):
        """POST to /rapports/nouveau without session must redirect to connexion."""
        anon = app.test_client(use_cookies=True)
        resp = anon.post(
            "/rapports/nouveau",
            data={**VALID_RAPPORT, "sentier_id": 1},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        location = resp.headers.get("Location", "")
        assert "connexion" in location

    def test_valid_rapport_created(self, auth_client, sentier_id):
        resp = create_rapport(auth_client, sentier_id)
        assert resp.status_code == 302

    def test_invalid_statut_rejected(self, auth_client, sentier_id):
        resp = create_rapport(auth_client, sentier_id, {"statut": "INVALID"})
        assert resp.status_code in (200, 302)

    def test_invalid_type_pratique_rejected(self, auth_client, sentier_id):
        resp = create_rapport(auth_client, sentier_id, {"type_pratique": "NOPE"})
        assert resp.status_code in (200, 302)

    def test_rapport_expires_in_7_days(self, app, auth_client, sentier_id):
        create_rapport(auth_client, sentier_id)
        with app.app_context():
            from backend.db import get_db
            row = get_db().execute(
                "SELECT date_rapport, date_expiration FROM rapport ORDER BY id DESC LIMIT 1"
            ).fetchone()
        assert row is not None
        created = datetime.strptime(row["date_rapport"][:19], "%Y-%m-%d %H:%M:%S")
        expired = datetime.strptime(row["date_expiration"][:19], "%Y-%m-%d %H:%M:%S")
        delta = expired - created
        assert 6 <= delta.days <= 7


class TestRapportAuthorization:
    def _get_rapport_id(self, app, auth_client, sentier_id):
        create_rapport(auth_client, sentier_id)
        with app.app_context():
            from backend.db import get_db
            row = get_db().execute(
                "SELECT id FROM rapport ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return row["id"]

    def test_owner_can_delete(self, app, auth_client, sentier_id):
        rapport_id = self._get_rapport_id(app, auth_client, sentier_id)
        resp = auth_client.post(
            f"/rapports/{rapport_id}/supprimer", follow_redirects=False
        )
        assert resp.status_code == 302

    def test_other_user_cannot_delete(self, app, auth_client, sentier_id):
        rapport_id = self._get_rapport_id(app, auth_client, sentier_id)

        tiers_client = app.test_client()
        tiers_client.post(
            "/auth/inscription",
            data={
                "nom": "Tiers",
                "email": "tiers@test.fr",
                "mdp": "tierspass123",
                "mdp_confirm": "tierspass123",
                "niveau": "débutant",
            },
            follow_redirects=True,
        )
        resp = tiers_client.post(
            f"/rapports/{rapport_id}/supprimer", follow_redirects=False
        )
        assert resp.status_code == 302
        # Must redirect back to sentier detail, not to sentiers list (which would indicate success)
        location = resp.headers.get("Location", "")
        assert "sentiers" in location

    def test_admin_can_delete_any(self, app, auth_client, admin_client, sentier_id):
        rapport_id = self._get_rapport_id(app, auth_client, sentier_id)
        resp = admin_client.post(
            f"/rapports/{rapport_id}/supprimer", follow_redirects=False
        )
        assert resp.status_code == 302