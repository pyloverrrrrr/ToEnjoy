import logging

from sqlalchemy import select
import app.db.session
from app.models.user import User, UserRole
from app.models.doctor import DoctorProfile
from app.models.patient import PatientProfile
from app.schemas.mcp import ToolDefinition, ToolCallResponse, ToolStatus
from app.core.mcp.base import BaseMCPModule

logger = logging.getLogger(__name__)

ROLE_PERMISSIONS = {
    "patient": ["chat", "search_patient_kb", "view_own_profile", "upload_report", "view_care_plan"],
    "doctor": ["chat", "search_professional_kb", "query_patient_record", "decision_support",
               "view_own_profile", "view_reasoning_chain"],
    "admin": ["chat", "search_professional_kb", "query_patient_record", "decision_support",
              "manage_users", "manage_kb", "view_analytics"],
}


class IdentityModule(BaseMCPModule):

    @property
    def module_name(self) -> str:
        return "identity"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="identity.verify_patient",
                description="验证患者身份，确认用户存在且角色为patient",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {"type": "string", "description": "用户名"},
                    },
                    "required": ["username"],
                },
            ),
            ToolDefinition(
                name="identity.verify_doctor",
                description="验证医生身份，确认用户存在且角色为doctor，返回执业信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {"type": "string", "description": "用户名"},
                    },
                    "required": ["username"],
                },
            ),
            ToolDefinition(
                name="identity.get_permissions",
                description="获取指定用户的权限列表",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {"type": "string", "description": "用户名"},
                    },
                    "required": ["username"],
                },
            ),
        ]

    async def execute(self, tool_name: str, params: dict) -> ToolCallResponse:
        username = params.get("username", "")
        if not username:
            return ToolCallResponse(
                tool=tool_name, status=ToolStatus.ERROR,
                error="参数错误: username 不能为空",
            )

        async with app.db.session.async_session() as db:
            result = await db.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()

        if user is None:
            return ToolCallResponse(
                tool=tool_name, status=ToolStatus.ERROR,
                error=f"用户不存在: {username}",
            )

        handlers = {
            "identity.verify_patient": self._verify_patient,
            "identity.verify_doctor": self._verify_doctor,
            "identity.get_permissions": self._get_permissions,
        }

        handler = handlers.get(tool_name)
        if handler is None:
            return ToolCallResponse(
                tool=tool_name, status=ToolStatus.ERROR,
                error=f"模块 {self.module_name} 不支持工具: {tool_name}",
            )

        try:
            data = await handler(user)
            return ToolCallResponse(tool=tool_name, status=ToolStatus.SUCCESS, data=data)
        except Exception as e:
            logger.error(f"MCP tool '{tool_name}' failed: {e}", exc_info=True)
            return ToolCallResponse(tool=tool_name, status=ToolStatus.ERROR, error=str(e))

    async def _verify_patient(self, user: User) -> dict:
        if user.role != UserRole.patient:
            return {"verified": False, "reason": f"用户 {user.username} 不是患者角色"}
        async with app.db.session.async_session() as db:
            result = await db.execute(
                select(PatientProfile).where(PatientProfile.user_id == user.id)
            )
            profile = result.scalar_one_or_none()
        return {
            "verified": True,
            "user_id": user.id,
            "username": user.username,
            "name": user.name,
            "role": user.role.value,
            "has_profile": profile is not None,
        }

    async def _verify_doctor(self, user: User) -> dict:
        if user.role != UserRole.doctor:
            return {"verified": False, "reason": f"用户 {user.username} 不是医生角色"}
        async with app.db.session.async_session() as db:
            result = await db.execute(
                select(DoctorProfile).where(DoctorProfile.user_id == user.id)
            )
            profile = result.scalar_one_or_none()
        return {
            "verified": True,
            "user_id": user.id,
            "username": user.username,
            "name": user.name,
            "role": user.role.value,
            "department": profile.department if profile else None,
            "title": profile.title if profile else None,
            "specialty": profile.specialty if profile else None,
            "license_no": profile.license_no if profile else None,
        }

    async def _get_permissions(self, user: User) -> dict:
        perms = ROLE_PERMISSIONS.get(user.role.value, [])
        return {
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value,
            "permissions": perms,
        }
