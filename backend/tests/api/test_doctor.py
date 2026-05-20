import pytest


class TestPatientRecord:
    async def test_patient_record_requires_auth(self, async_client):
        resp = await async_client.get("/api/doctor/patient/1")
        assert resp.status_code == 403

    async def test_patient_role_cannot_access(self, async_client, auth_token):
        resp = await async_client.get(
            "/api/doctor/patient/1",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 403
        assert "Only doctors" in resp.json()["detail"]

    async def test_patient_not_found(self, async_client):
        """Register as doctor, then query nonexistent patient."""
        await async_client.post("/api/auth/register", json={
            "username": "testdoctor", "password": "testpass", "name": "Doctor", "role": "doctor",
        })
        login_resp = await async_client.post("/api/auth/login", json={
            "username": "testdoctor", "password": "testpass",
        })
        token = login_resp.json()["token"]

        resp = await async_client.get(
            "/api/doctor/patient/9999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_patient_record_returns_mock_data(self, async_client):
        """Register as doctor, register a patient, query that patient."""
        # Register a patient first
        await async_client.post("/api/auth/register", json={
            "username": "somepatient", "password": "testpass", "name": "张三", "role": "patient",
        })
        patient_resp = await async_client.post("/api/auth/login", json={
            "username": "somepatient", "password": "testpass",
        })
        patient_id = patient_resp.json()["user"]["id"]

        # Register and login as doctor
        await async_client.post("/api/auth/register", json={
            "username": "dr_wang", "password": "testpass", "name": "王医生", "role": "doctor",
        })
        doctor_resp = await async_client.post("/api/auth/login", json={
            "username": "dr_wang", "password": "testpass",
        })
        doctor_token = doctor_resp.json()["token"]

        resp = await async_client.get(
            f"/api/doctor/patient/{patient_id}",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["patient_id"] == patient_id
        assert data["patient_name"] == "张三"
        assert isinstance(data["episodes"], list)
        assert len(data["episodes"]) >= 1
        ep = data["episodes"][0]
        assert isinstance(ep["cases"], list)
        assert isinstance(ep["visits"], list)
        assert isinstance(ep["prescriptions"], list)


class TestDoctorProfile:
    async def test_get_profile_empty(self, async_client, doctor_token):
        resp = await async_client.get(
            "/api/doctor/profile",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] is not None
        assert data["department"] == "内科"  # set by doctor_token fixture

    async def test_update_and_get_profile(self, async_client, doctor_token):
        resp = await async_client.put(
            "/api/doctor/profile",
            json={"department": "心内科", "title": "主任医师", "specialty": "冠心病介入", "license_no": "20240001"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["department"] == "心内科"
        assert data["title"] == "主任医师"
        assert data["specialty"] == "冠心病介入"
        assert data["license_no"] == "20240001"

        # GET should return updated values
        get_resp = await async_client.get(
            "/api/doctor/profile",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["department"] == "心内科"

    async def test_partial_update(self, async_client, doctor_token):
        await async_client.put(
            "/api/doctor/profile",
            json={"department": "神经内科", "title": "副主任医师"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        resp = await async_client.put(
            "/api/doctor/profile",
            json={"specialty": "脑血管病"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["department"] == "神经内科"
        assert data["title"] == "副主任医师"
        assert data["specialty"] == "脑血管病"

    async def test_profile_requires_auth(self, async_client):
        resp = await async_client.get("/api/doctor/profile")
        assert resp.status_code == 403


@pytest.fixture
async def doctor_token(async_client):
    await async_client.post("/api/auth/register", json={
        "username": "careplan_doctor", "password": "test", "name": "CarePlan Doctor", "role": "doctor",
    })
    resp = await async_client.post("/api/auth/login", json={"username": "careplan_doctor", "password": "test"})
    token = resp.json()["token"]
    # Set doctor department so registration checks pass
    await async_client.put("/api/doctor/profile", json={"department": "内科"}, headers={"Authorization": f"Bearer {token}"})
    return token


async def _register_and_enroll(async_client, username: str, name: str) -> int:
    """Register a patient, create a registration with department 内科, transition to in_consultation. Returns patient_id."""
    # Register patient
    await async_client.post("/api/auth/register", json={
        "username": username, "password": "test", "name": name, "role": "patient",
    })
    patient_login = await async_client.post("/api/auth/login", json={"username": username, "password": "test"})
    patient_token = patient_login.json()["token"]
    patient_id = patient_login.json()["user"]["id"]

    # Create registration (as patient)
    await async_client.post("/api/patient/registration", json={"department": "内科"},
                            headers={"Authorization": f"Bearer {patient_token}"})

    # Transition to in_consultation (as doctor)
    doctor_login = await async_client.post("/api/auth/login", json={"username": "careplan_doctor", "password": "test"})
    doctor_tok = doctor_login.json()["token"]
    await async_client.put(f"/api/doctor/patient/{patient_id}/registration-status",
                           json={"status": "in_consultation"},
                           headers={"Authorization": f"Bearer {doctor_tok}"})
    return patient_id


class TestCarePlan:
    async def test_create_care_plan(self, async_client, doctor_token):
        patient_id = await _register_and_enroll(async_client, "cp_patient", "计划患者")

        resp = await async_client.post(
            f"/api/doctor/patient/{patient_id}/care-plan",
            json={
                "title": "高血压管理",
                "description": "每日监测血压",
                "medication_schedule": "氨氯地平 5mg qd",
                "follow_up_date": "2026-06-01",
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "高血压管理"
        assert data["description"] == "每日监测血压"
        assert data["medication_schedule"] == "氨氯地平 5mg qd"
        assert data["status"] == "active"

    async def test_list_care_plans(self, async_client, doctor_token):
        patient_id = await _register_and_enroll(async_client, "cp_patient2", "列表患者")

        await async_client.post(
            f"/api/doctor/patient/{patient_id}/care-plan",
            json={"title": "糖尿病饮食管理"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )

        resp = await async_client.get(
            f"/api/doctor/patient/{patient_id}/care-plans",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["plans"]) >= 1
        assert data["plans"][0]["title"] == "糖尿病饮食管理"

    async def test_update_care_plan(self, async_client, doctor_token):
        patient_id = await _register_and_enroll(async_client, "cp_patient3", "更新患者")

        create_resp = await async_client.post(
            f"/api/doctor/patient/{patient_id}/care-plan",
            json={"title": "术后康复"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        plan_id = create_resp.json()["id"]

        resp = await async_client.put(
            f"/api/doctor/care-plan/{plan_id}",
            json={"status": "completed", "follow_up_date": "2026-07-01"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["follow_up_date"] == "2026-07-01"

    async def test_patient_role_cannot_create(self, async_client, auth_token):
        resp = await async_client.post(
            "/api/doctor/patient/1/care-plan",
            json={"title": "test"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 403
        assert "Only doctors" in resp.json()["detail"]

    async def test_patient_not_found(self, async_client, doctor_token):
        resp = await async_client.post(
            "/api/doctor/patient/9999/care-plan",
            json={"title": "test"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert resp.status_code == 404
