import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.chat import ChatRequest
from app.schemas.search import SearchRequest


class TestLoginRequest:
    def test_valid(self):
        req = LoginRequest(username="test", password="secret")
        assert req.username == "test"

    def test_missing_username(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="secret")

    def test_missing_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="test")


class TestRegisterRequest:
    def test_default_role_is_patient(self):
        req = RegisterRequest(username="test", password="secret", name="Test User")
        assert req.role == "patient"

    def test_explicit_role(self):
        req = RegisterRequest(username="doc", password="s", name="Doctor", role="doctor")
        assert req.role == "doctor"

    def test_missing_name(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="test", password="secret")


class TestChatRequest:
    def test_default_session_id(self):
        req = ChatRequest(message="hello")
        assert req.session_id == "default"

    def test_custom_session_id(self):
        req = ChatRequest(message="hello", session_id="sess-123")
        assert req.session_id == "sess-123"


class TestSearchRequest:
    def test_filters_is_optional(self):
        req = SearchRequest(query="test")
        assert req.filters is None

    def test_with_filters(self):
        req = SearchRequest(query="test", filters={"type": "guideline"})
        assert req.filters == {"type": "guideline"}


from app.schemas.chat import ChatHistoryItem, ChatHistoryResponse, ChatDetailMessage, ChatDetailResponse
from app.schemas.patient import PatientProfileResponse, PatientProfileUpdate, CarePlanItem, CarePlanResponse
from app.schemas.doctor import PatientRecordResponse


class TestChatHistoryItem:
    def test_valid(self):
        item = ChatHistoryItem(session_id="s1", first_message="hello", message_count=5, last_message_at="2025-01-01T00:00:00")
        assert item.session_id == "s1"
        assert item.message_count == 5

    def test_defaults(self):
        item = ChatHistoryItem(session_id="s1", first_message="", message_count=0, last_message_at="")
        assert item.message_count == 0


class TestChatHistoryResponse:
    def test_empty(self):
        resp = ChatHistoryResponse(items=[], total=0)
        assert resp.page == 1
        assert resp.items == []


class TestPatientProfileResponse:
    def test_minimal(self):
        resp = PatientProfileResponse(user_id=1)
        assert resp.user_id == 1
        assert resp.gender is None

    def test_full(self):
        resp = PatientProfileResponse(
            user_id=1, gender="male", birthday="1990-01-01", blood_type="A",
            allergies="penicillin", medical_history={"asthma": True},
        )
        assert resp.blood_type == "A"


class TestPatientProfileUpdate:
    def test_all_fields_optional(self):
        update = PatientProfileUpdate()
        assert update.gender is None

    def test_partial_update(self):
        update = PatientProfileUpdate(gender="female")
        assert update.gender == "female"
        assert update.blood_type is None


class TestPatientRecordResponse:
    def test_empty(self):
        resp = PatientRecordResponse(patient_id=1)
        assert resp.patient_id == 1
        assert resp.episodes == []

    def test_full(self):
        from app.schemas.doctor import EpisodeRecordData
        from app.schemas.medical_record import CaseData, VisitData, PrescriptionData
        from app.schemas.patient import CarePlanItem
        ep = EpisodeRecordData(
            registration_id=1, sequence_number=1, department="内科",
            registration_date="2026-01-01", status="registered",
            cases=[CaseData(id=1, user_id=1, diagnosis="test")],
            visits=[VisitData(id=1, user_id=1, visit_date="2026-01-01")],
            prescriptions=[PrescriptionData(id=1, user_id=1, drug_name="aspirin")],
            care_plans=[CarePlanItem(id=1, title="plan", status="active")],
        )
        resp = PatientRecordResponse(
            patient_id=1, patient_name="张三", patient_role="patient",
            current_registration_status="registered",
            current_registration_department="内科",
            episodes=[ep],
        )
        assert resp.patient_name == "张三"
        assert len(resp.episodes) == 1
        assert len(resp.episodes[0].cases) == 1


from app.schemas.auth import UserUpdateRequest, PasswordChangeRequest, UserMeResponse


class TestUserUpdateRequest:
    def test_all_fields_optional(self):
        req = UserUpdateRequest()
        assert req.phone is None
        assert req.email is None
        assert req.id_number is None

    def test_partial_update(self):
        req = UserUpdateRequest(phone="13800138000")
        assert req.phone == "13800138000"
        assert req.email is None


class TestPasswordChangeRequest:
    def test_valid(self):
        req = PasswordChangeRequest(old_password="old", new_password="new123")
        assert req.old_password == "old"
        assert req.new_password == "new123"

    def test_missing_old_password(self):
        with pytest.raises(ValidationError):
            PasswordChangeRequest(new_password="new123")

    def test_missing_new_password(self):
        with pytest.raises(ValidationError):
            PasswordChangeRequest(old_password="old")


class TestUserMeResponse:
    def test_minimal(self):
        resp = UserMeResponse(id=1, username="test", role="patient", name="Test")
        assert resp.avatar_url is None
        assert resp.phone is None

    def test_full(self):
        resp = UserMeResponse(
            id=1, username="test", role="patient", name="Test",
            phone="13800138000", email="test@test.com", avatar_url="avatars/abc.png",
        )
        assert resp.phone == "13800138000"
        assert resp.avatar_url == "avatars/abc.png"
