import logging

from sqlalchemy import select
import app.db.session
from app.models.user import User
from app.models.medical_record import PatientCase, PatientVisit, PatientPrescription
from app.schemas.mcp import ToolDefinition, ToolCallResponse, ToolStatus
from app.core.mcp.base import BaseMCPModule

logger = logging.getLogger(__name__)

# Legacy mock data kept as fallback
MOCK_CASES: dict[int, list[dict]] = {
    1: [
        {"case_id": "C2025001", "admission_date": "2025-03-15", "discharge_date": "2025-03-22",
         "chief_complaint": "反复头痛伴恶心3天", "diagnosis": "偏头痛", "department": "神经内科",
         "attending_doctor": "李医生", "allergies": ["青霉素"], "procedures": ["头颅CT平扫"],
         "discharge_summary": "患者经治疗后症状明显缓解，嘱定期复查。"},
        {"case_id": "C2024020", "admission_date": "2024-11-05", "discharge_date": "2024-11-12",
         "chief_complaint": "血压升高1月", "diagnosis": "原发性高血压", "department": "心内科",
         "attending_doctor": "王医生", "allergies": [], "procedures": ["24h动态血压监测"],
         "discharge_summary": "血压控制达标后出院，嘱按时服药。"},
    ],
}

MOCK_VISITS: dict[int, list[dict]] = {
    1: [
        {"visit_id": "V2025120", "date": "2025-05-01", "department": "神经内科", "doctor": "李医生",
         "chief_complaint": "头痛复发", "diagnosis": "偏头痛(复诊)"},
        {"visit_id": "V2024100", "date": "2024-10-20", "department": "心内科", "doctor": "王医生",
         "chief_complaint": "头晕、血压偏高", "diagnosis": "待查"},
    ],
}

MOCK_PRESCRIPTIONS: dict[int, list[dict]] = {
    1: [
        {"rx_id": "RX2025080", "date": "2025-05-01", "drug_name": "布洛芬", "dosage": "200mg",
         "frequency": "bid", "duration": "7天", "doctor": "李医生"},
        {"rx_id": "RX2024500", "date": "2024-11-12", "drug_name": "硝苯地平缓释片", "dosage": "30mg",
         "frequency": "qd", "duration": "30天", "doctor": "王医生"},
    ],
}


class PatientRecordModule(BaseMCPModule):

    @property
    def module_name(self) -> str:
        return "patient_record"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="patient_record.query_case",
                description="查询患者的病例记录，包括诊断、手术、过敏史、出院小结等",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_name": {"type": "string", "description": "患者姓名（支持模糊匹配）"},
                    },
                    "required": ["patient_name"],
                },
            ),
            ToolDefinition(
                name="patient_record.query_visit",
                description="查询患者的就诊记录，可按日期范围筛选",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_name": {"type": "string", "description": "患者姓名"},
                        "start_date": {"type": "string", "description": "开始日期（YYYY-MM-DD），可选"},
                        "end_date": {"type": "string", "description": "结束日期（YYYY-MM-DD），可选"},
                    },
                    "required": ["patient_name"],
                },
            ),
            ToolDefinition(
                name="patient_record.query_prescription",
                description="查询患者的处方和用药记录",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_name": {"type": "string", "description": "患者姓名"},
                    },
                    "required": ["patient_name"],
                },
            ),
        ]

    async def execute(self, tool_name: str, params: dict) -> ToolCallResponse:
        patient_name = params.get("patient_name", "")
        if not patient_name:
            return ToolCallResponse(
                tool=tool_name, status=ToolStatus.ERROR,
                error="参数错误: patient_name 不能为空",
            )

        user_id = await self._resolve_patient(patient_name)
        if user_id is None:
            return ToolCallResponse(
                tool=tool_name, status=ToolStatus.ERROR,
                error=f"未找到患者: {patient_name}",
            )

        handlers = {
            "patient_record.query_case": self._query_case,
            "patient_record.query_visit": self._query_visit,
            "patient_record.query_prescription": self._query_prescription,
        }

        handler = handlers.get(tool_name)
        if handler is None:
            return ToolCallResponse(
                tool=tool_name, status=ToolStatus.ERROR,
                error=f"模块 {self.module_name} 不支持工具: {tool_name}",
            )

        try:
            data = await handler(user_id, params)
            return ToolCallResponse(tool=tool_name, status=ToolStatus.SUCCESS, data=data)
        except Exception as e:
            logger.error(f"MCP tool '{tool_name}' failed: {e}", exc_info=True)
            return ToolCallResponse(tool=tool_name, status=ToolStatus.ERROR, error=str(e))

    async def _resolve_patient(self, patient_name: str) -> int | None:
        async with app.db.session.async_session() as db:
            result = await db.execute(
                select(User.id).where(User.name.contains(patient_name))
            )
            return result.scalar()

    async def _query_case(self, user_id: int, _params: dict) -> dict:
        try:
            async with app.db.session.async_session() as db:
                result = await db.execute(
                    select(PatientCase).where(PatientCase.user_id == user_id).order_by(PatientCase.created_at.desc())
                )
                cases = result.scalars().all()
            if cases:
                return {
                    "patient_id": user_id,
                    "cases": [{"case_id": f"C{c.id}", "diagnosis": c.diagnosis, "allergies": c.allergies, "procedures": c.procedures, "discharge_summary": c.discharge_summary} for c in cases],
                    "total": len(cases),
                }
        except Exception:
            logger.debug("DB query for cases failed, falling back to mock", exc_info=True)
        mock = MOCK_CASES.get(user_id, [])
        return {"patient_id": user_id, "cases": mock, "total": len(mock)}

    async def _query_visit(self, user_id: int, params: dict) -> dict:
        try:
            async with app.db.session.async_session() as db:
                result = await db.execute(
                    select(PatientVisit).where(PatientVisit.user_id == user_id).order_by(PatientVisit.created_at.desc())
                )
                visits = result.scalars().all()
            if visits:
                data = [{"visit_id": f"V{v.id}", "date": v.visit_date, "department": v.department, "doctor": v.doctor_name, "chief_complaint": v.chief_complaint, "diagnosis": v.diagnosis} for v in visits]
                return {"patient_id": user_id, "visits": data, "total": len(data)}
        except Exception:
            logger.debug("DB query for visits failed, falling back to mock", exc_info=True)
        mock = MOCK_VISITS.get(user_id, [])
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        if start_date:
            mock = [v for v in mock if v["date"] >= start_date]
        if end_date:
            mock = [v for v in mock if v["date"] <= end_date]
        return {"patient_id": user_id, "visits": mock, "total": len(mock)}

    async def _query_prescription(self, user_id: int, _params: dict) -> dict:
        try:
            async with app.db.session.async_session() as db:
                result = await db.execute(
                    select(PatientPrescription).where(PatientPrescription.user_id == user_id).order_by(PatientPrescription.created_at.desc())
                )
                prescriptions = result.scalars().all()
            if prescriptions:
                data = [{"rx_id": f"RX{p.id}", "date": p.prescribed_date, "drug_name": p.drug_name, "dosage": p.dosage, "frequency": p.frequency, "duration": p.duration, "doctor": ""} for p in prescriptions]
                return {"patient_id": user_id, "prescriptions": data, "total": len(data)}
        except Exception:
            logger.debug("DB query for prescriptions failed, falling back to mock", exc_info=True)
        mock = MOCK_PRESCRIPTIONS.get(user_id, [])
        return {"patient_id": user_id, "prescriptions": mock, "total": len(mock)}
