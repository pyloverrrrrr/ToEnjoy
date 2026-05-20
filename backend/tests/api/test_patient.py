import pytest


class TestPatientProfile:
    async def test_get_profile_requires_auth(self, async_client):
        resp = await async_client.get("/api/patient/profile")
        assert resp.status_code == 403

    async def test_get_profile_empty_for_new_user(self, async_client, auth_token):
        resp = await async_client.get(
            "/api/patient/profile",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] is not None
        assert data["gender"] is None

    async def test_update_profile_and_get(self, async_client, auth_token):
        headers = {"Authorization": f"Bearer {auth_token}"}
        update_resp = await async_client.put(
            "/api/patient/profile",
            headers=headers,
            json={"gender": "male", "blood_type": "O", "allergies": "penicillin"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["gender"] == "male"
        assert update_resp.json()["blood_type"] == "O"

        get_resp = await async_client.get("/api/patient/profile", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["gender"] == "male"

    async def test_update_profile_bad_birthday(self, async_client, auth_token):
        resp = await async_client.put(
            "/api/patient/profile",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"birthday": "not-a-date"},
        )
        assert resp.status_code == 422

    async def test_update_profile_requires_auth(self, async_client):
        resp = await async_client.put(
            "/api/patient/profile",
            json={"gender": "male"},
        )
        assert resp.status_code == 403


class TestCarePlan:
    async def test_care_plan_requires_auth(self, async_client):
        resp = await async_client.get("/api/patient/care-plan")
        assert resp.status_code == 403

    async def test_care_plan_empty(self, async_client, auth_token):
        resp = await async_client.get(
            "/api/patient/care-plan",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["episodes"] == []
        assert data["total"] == 0
