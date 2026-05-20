import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.user import User, UserRole
from app.schemas.mcp import ToolStatus


def _make_user(uid, uname, name, role, **extra):
    user = MagicMock()
    user.id = uid
    user.username = uname
    user.name = name
    user.role = role
    for k, v in extra.items():
        setattr(user, k, v)
    return user


def _mock_session(user_return=None):
    """Returns (mock_session, mock_db) where mock_db.execute returns user_return."""
    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock()
    mock_db.execute.return_value.scalar_one_or_none.return_value = user_return
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_db
    mock_session.__aexit__.return_value = None
    return mock_session


class TestIdentityModule:
    @pytest.fixture
    def module(self):
        from app.core.mcp.identity import IdentityModule
        return IdentityModule()

    def test_module_name(self, module):
        assert module.module_name == "identity"

    def test_get_tools_has_three_tools(self, module):
        tools = module.get_tools()
        assert len(tools) == 3
        names = {t.name for t in tools}
        assert names == {
            "identity.verify_patient",
            "identity.verify_doctor",
            "identity.get_permissions",
        }

    def test_tool_schemas_have_required_fields(self, module):
        for tool in module.get_tools():
            assert "username" in tool.inputSchema.get("required", [])

    @pytest.mark.asyncio
    async def test_execute_missing_username(self, module):
        resp = await module.execute("identity.verify_patient", {})
        assert resp.status == ToolStatus.ERROR
        assert "username" in resp.error

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, module):
        user = _make_user(1, "test", "test", UserRole.patient)
        mock_session = _mock_session(user_return=user)
        with patch("app.db.session.async_session", return_value=mock_session):
            resp = await module.execute("identity.unknown", {"username": "test"})
        assert resp.status == ToolStatus.ERROR
        assert "不支持工具" in resp.error

    @pytest.mark.asyncio
    async def test_execute_user_not_found(self, module):
        mock_session = _mock_session(user_return=None)
        with patch("app.db.session.async_session", return_value=mock_session):
            resp = await module.execute("identity.verify_patient", {"username": "ghost"})
        assert resp.status == ToolStatus.ERROR
        assert "用户不存在" in resp.error

    @pytest.mark.asyncio
    async def test_verify_patient_success(self, module):
        user = _make_user(1, "testpatient", "测试患者", UserRole.patient)
        mock_session = _mock_session(user_return=user)
        with patch("app.db.session.async_session", return_value=mock_session):
            resp = await module.execute("identity.verify_patient", {"username": "testpatient"})
        assert resp.status == ToolStatus.SUCCESS
        assert resp.data["verified"] is True
        assert resp.data["username"] == "testpatient"
        assert resp.data["role"] == "patient"

    @pytest.mark.asyncio
    async def test_verify_patient_wrong_role(self, module):
        user = _make_user(2, "testdoctor", "测试医生", UserRole.doctor)
        mock_session = _mock_session(user_return=user)
        with patch("app.db.session.async_session", return_value=mock_session):
            resp = await module.execute("identity.verify_patient", {"username": "testdoctor"})
        assert resp.status == ToolStatus.SUCCESS
        assert resp.data["verified"] is False
        assert "不是患者" in resp.data["reason"]

    @pytest.mark.asyncio
    async def test_verify_doctor_success(self, module):
        user = _make_user(2, "testdoctor", "李医生", UserRole.doctor,
                          department="心内科", title="主任医师",
                          specialty="心血管", license_no="LIC12345")
        mock_session = _mock_session(user_return=user)
        with patch("app.db.session.async_session", return_value=mock_session):
            resp = await module.execute("identity.verify_doctor", {"username": "testdoctor"})
        assert resp.status == ToolStatus.SUCCESS
        assert resp.data["verified"] is True
        assert resp.data["role"] == "doctor"

    @pytest.mark.asyncio
    async def test_verify_doctor_wrong_role(self, module):
        user = _make_user(1, "testpatient", "患者", UserRole.patient)
        mock_session = _mock_session(user_return=user)
        with patch("app.db.session.async_session", return_value=mock_session):
            resp = await module.execute("identity.verify_doctor", {"username": "testpatient"})
        assert resp.status == ToolStatus.SUCCESS
        assert resp.data["verified"] is False
        assert "不是医生" in resp.data["reason"]

    @pytest.mark.asyncio
    async def test_get_permissions_patient(self, module):
        user = _make_user(1, "testpatient", "患者", UserRole.patient)
        mock_session = _mock_session(user_return=user)
        with patch("app.db.session.async_session", return_value=mock_session):
            resp = await module.execute("identity.get_permissions", {"username": "testpatient"})
        assert resp.status == ToolStatus.SUCCESS
        assert resp.data["role"] == "patient"
        assert "chat" in resp.data["permissions"]
        assert "decision_support" not in resp.data["permissions"]

    @pytest.mark.asyncio
    async def test_get_permissions_doctor(self, module):
        user = _make_user(2, "testdoctor", "医生", UserRole.doctor)
        mock_session = _mock_session(user_return=user)
        with patch("app.db.session.async_session", return_value=mock_session):
            resp = await module.execute("identity.get_permissions", {"username": "testdoctor"})
        assert resp.status == ToolStatus.SUCCESS
        assert resp.data["role"] == "doctor"
        assert "decision_support" in resp.data["permissions"]

    @pytest.mark.asyncio
    async def test_execute_catches_handler_exception(self, module):
        user = _make_user(1, "testpatient", "患者", UserRole.patient)
        mock_session = _mock_session(user_return=user)
        with patch("app.db.session.async_session", return_value=mock_session):
            module._verify_patient = AsyncMock(side_effect=RuntimeError("DB gone"))
            resp = await module.execute("identity.verify_patient", {"username": "testpatient"})
        assert resp.status == ToolStatus.ERROR
        assert "DB gone" in resp.error
