import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.middleware.identity_router import get_request_context, RequestContext
from app.models.user import User, UserRole
from app.models.doctor import DoctorProfile
from app.models.care_plan import CarePlan
from app.models.medical_record import PatientCase, PatientVisit, PatientPrescription
from app.models.registration import Registration, RegistrationStatus
from app.core.mcp.patient_record import PatientRecordModule
from app.schemas.patient import CarePlanItem, CarePlanResponse, CarePlanEpisode, CarePlanEpisodeResponse
from app.schemas.doctor import (
    PatientRecordResponse, EpisodeRecordData,
    DoctorProfileResponse, DoctorProfileUpdate,
    CarePlanCreate, CarePlanUpdate,
)
from app.schemas.medical_record import (
    CaseData, CaseCreate, CaseUpdate,
    VisitData, VisitCreate, VisitUpdate,
    PrescriptionData, PrescriptionCreate, PrescriptionUpdate,
    PatientMedicalRecords,
)
from app.schemas.registration import RegistrationStatusUpdate, RegistrationResponse, RegisteredPatientItem
from app.api.registration import get_active_registration

logger = logging.getLogger(__name__)

# -- Valid status transitions (doctor-operated) --
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "registered": {"in_consultation", "need_reregister"},
    "in_consultation": {"recovering"},
    "recovering": {"recovered"},
    "recovered": set(),
    "need_reregister": {"registered"},
}

router = APIRouter(prefix="/api/doctor", tags=["doctor"])
patient_record_module = PatientRecordModule()

_EDITABLE_STATUSES = {RegistrationStatus.IN_CONSULTATION, RegistrationStatus.RECOVERING}


async def _require_editable(patient_id: int, db: AsyncSession):
    """Raise 403 if the patient has no active registration in an editable status."""
    reg = await get_active_registration(patient_id, db)
    if reg is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="患者未挂号，无法编辑病历",
        )
    if reg.status not in _EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅问诊中或康复中的患者可编辑病历",
        )


def _mask_id_number(id_number: str | None) -> str | None:
    """Return last 4 digits of id_number with asterisks for privacy."""
    if not id_number:
        return None
    if len(id_number) <= 4:
        return "****"
    return "*" * (len(id_number) - 4) + id_number[-4:]


async def _build_episodes(patient_id: int, db: AsyncSession) -> list[EpisodeRecordData]:
    """Query all registrations for a patient and build episode records with nested data."""
    regs_result = await db.execute(
        select(Registration)
        .where(Registration.patient_id == patient_id)
        .order_by(Registration.sequence_number.desc())
    )
    all_regs = regs_result.scalars().all()

    episodes: list[EpisodeRecordData] = []
    for reg in all_regs:
        # Cases for this episode
        cases_result = await db.execute(
            select(PatientCase)
            .where(PatientCase.registration_id == reg.id)
            .order_by(PatientCase.created_at.desc())
        )
        cases = cases_result.scalars().all()

        # Visits for this episode
        visits_result = await db.execute(
            select(PatientVisit)
            .where(PatientVisit.registration_id == reg.id)
            .order_by(PatientVisit.created_at.desc())
        )
        visits = visits_result.scalars().all()

        # Prescriptions for this episode
        rx_result = await db.execute(
            select(PatientPrescription)
            .where(PatientPrescription.registration_id == reg.id)
            .order_by(PatientPrescription.created_at.desc())
        )
        prescriptions = rx_result.scalars().all()

        # Care plans for this episode
        plans_result = await db.execute(
            select(CarePlan)
            .where(CarePlan.registration_id == reg.id)
            .order_by(CarePlan.created_at.desc())
        )
        care_plans = plans_result.scalars().all()

        episodes.append(EpisodeRecordData(
            registration_id=reg.id,
            sequence_number=reg.sequence_number,
            department=reg.department,
            registration_date=str(reg.registration_date),
            status=reg.status,
            cases=[
                CaseData(id=c.id, user_id=c.user_id, diagnosis=c.diagnosis,
                         procedures=c.procedures, allergies=c.allergies,
                         discharge_summary=c.discharge_summary,
                         created_at=str(c.created_at), updated_at=str(c.updated_at))
                for c in cases
            ],
            visits=[
                VisitData(id=v.id, user_id=v.user_id, visit_date=v.visit_date,
                          department=v.department, doctor_name=v.doctor_name,
                          chief_complaint=v.chief_complaint, diagnosis=v.diagnosis,
                          created_at=str(v.created_at))
                for v in visits
            ],
            prescriptions=[
                PrescriptionData(id=p.id, user_id=p.user_id, drug_name=p.drug_name,
                                 dosage=p.dosage, frequency=p.frequency,
                                 duration=p.duration, prescribed_date=p.prescribed_date,
                                 notes=p.notes, created_at=str(p.created_at))
                for p in prescriptions
            ],
            care_plans=[
                CarePlanItem(id=cp.id, title=cp.title, description=cp.description,
                             medication_schedule=cp.medication_schedule,
                             follow_up_date=cp.follow_up_date, status=cp.status)
                for cp in care_plans
            ],
        ))

    # Legacy records with no registration_id (include as a synthetic episode)
    legacy_cases = await db.execute(
        select(PatientCase).where(
            PatientCase.user_id == patient_id, PatientCase.registration_id.is_(None)
        ).order_by(PatientCase.created_at.desc())
    )
    legacy_visits = await db.execute(
        select(PatientVisit).where(
            PatientVisit.user_id == patient_id, PatientVisit.registration_id.is_(None)
        ).order_by(PatientVisit.created_at.desc())
    )
    legacy_rx = await db.execute(
        select(PatientPrescription).where(
            PatientPrescription.user_id == patient_id, PatientPrescription.registration_id.is_(None)
        ).order_by(PatientPrescription.created_at.desc())
    )
    legacy_plans = await db.execute(
        select(CarePlan).where(
            CarePlan.user_id == patient_id, CarePlan.registration_id.is_(None)
        ).order_by(CarePlan.created_at.desc())
    )

    lc = legacy_cases.scalars().all()
    lv = legacy_visits.scalars().all()
    lp = legacy_rx.scalars().all()
    lcp = legacy_plans.scalars().all()

    if lc or lv or lp or lcp:
        episodes.append(EpisodeRecordData(
            registration_id=0,
            sequence_number=0,
            department="",
            registration_date="",
            status="legacy",
            cases=[
                CaseData(id=c.id, user_id=c.user_id, diagnosis=c.diagnosis,
                         procedures=c.procedures, allergies=c.allergies,
                         discharge_summary=c.discharge_summary,
                         created_at=str(c.created_at), updated_at=str(c.updated_at))
                for c in lc
            ],
            visits=[
                VisitData(id=v.id, user_id=v.user_id, visit_date=v.visit_date,
                          department=v.department, doctor_name=v.doctor_name,
                          chief_complaint=v.chief_complaint, diagnosis=v.diagnosis,
                          created_at=str(v.created_at))
                for v in lv
            ],
            prescriptions=[
                PrescriptionData(id=p.id, user_id=p.user_id, drug_name=p.drug_name,
                                 dosage=p.dosage, frequency=p.frequency,
                                 duration=p.duration, prescribed_date=p.prescribed_date,
                                 notes=p.notes, created_at=str(p.created_at))
                for p in lp
            ],
            care_plans=[
                CarePlanItem(id=cp.id, title=cp.title, description=cp.description,
                             medication_schedule=cp.medication_schedule,
                             follow_up_date=cp.follow_up_date, status=cp.status)
                for cp in lcp
            ],
        ))

    return episodes


@router.get("/patients", response_model=list[RegisteredPatientItem])
async def list_patients(
    q: str = "",
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """List patients registered to the doctor's department. Optionally search by name/phone."""
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can search patients")

    # Get doctor's department
    dept_result = await db.execute(
        select(DoctorProfile.department).where(DoctorProfile.user_id == ctx.user_id)
    )
    doctor_dept = dept_result.scalar_one_or_none()

    if not doctor_dept:
        return []

    # Subquery: latest sequence_number per patient in this department (to avoid duplicates)
    latest_seq = (
        select(
            Registration.patient_id,
            func.max(Registration.sequence_number).label("max_seq"),
        )
        .where(Registration.department == doctor_dept)
        .group_by(Registration.patient_id)
    ).subquery()

    stmt = (
        select(User, Registration)
        .join(Registration, User.id == Registration.patient_id)
        .join(
            latest_seq,
            (Registration.patient_id == latest_seq.c.patient_id)
            & (Registration.sequence_number == latest_seq.c.max_seq),
        )
        .where(
            Registration.department == doctor_dept,
            Registration.status != RegistrationStatus.NEED_REREGISTER,
        )
    )

    if q and q.strip():
        q_like = f"%{q.strip()}%"
        stmt = stmt.where(
            (User.name.ilike(q_like)) | (User.phone.ilike(q_like))
        )

    stmt = stmt.order_by(Registration.registration_date.desc()).limit(50)
    result = await db.execute(stmt)
    rows = result.all()

    return [
        RegisteredPatientItem(
            id=user.id,
            name=user.name,
            phone=user.phone,
            registration_status=reg.status,
            registration_date=str(reg.registration_date),
            deleted_at=str(user.deleted_at) if user.deleted_at else None,
        )
        for user, reg in rows
    ]


@router.delete("/patient/{patient_id}/dismiss")
async def dismiss_deleted_patient(
    patient_id: int,
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """Clear all registration records for a deleted patient. Doctor-only, department-scoped."""
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can dismiss patients")

    user_result = await db.execute(select(User).where(User.id == patient_id))
    user = user_result.scalar_one_or_none()
    if not user or user.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户未注销，无法清除")

    await db.execute(delete(Registration).where(Registration.patient_id == patient_id))
    await db.commit()
    return {"message": "已清除"}


@router.put("/patient/{patient_id}/registration-status", response_model=RegistrationResponse)
async def update_registration_status(
    patient_id: int,
    req: RegistrationStatusUpdate,
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """Update a patient's registration status (department-scoped)."""
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can update registration status")

    # Get the active registration (latest by sequence_number among active statuses)
    reg = await get_active_registration(patient_id, db)
    if reg is None:
        # If no active registration, fall back to the latest registration overall
        reg_result = await db.execute(
            select(Registration)
            .where(Registration.patient_id == patient_id)
            .order_by(Registration.sequence_number.desc())
            .limit(1)
        )
        reg = reg_result.scalars().first()
    if reg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    # Department check
    dept_result = await db.execute(
        select(DoctorProfile.department).where(DoctorProfile.user_id == ctx.user_id)
    )
    doctor_dept = dept_result.scalar_one_or_none()
    if not doctor_dept or reg.department != doctor_dept:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update patients in your department")

    # Validate transition
    current = reg.status
    allowed = _VALID_TRANSITIONS.get(current, set())
    if req.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition: {current} -> {req.status}",
        )

    reg.status = req.status
    if req.notes is not None:
        reg.status_notes = req.notes

    # Auto-sync care plan statuses with registration status
    if req.status == RegistrationStatus.RECOVERED:
        # All care plans for this episode → completed
        plans_result = await db.execute(
            select(CarePlan).where(CarePlan.registration_id == reg.id)
        )
        for plan in plans_result.scalars().all():
            plan.status = "completed"
    elif req.status == RegistrationStatus.RECOVERING:
        # All care plans for this episode → active
        plans_result = await db.execute(
            select(CarePlan).where(CarePlan.registration_id == reg.id)
        )
        for plan in plans_result.scalars().all():
            plan.status = "active"

    await db.commit()
    await db.refresh(reg)

    user_result = await db.execute(select(User.name).where(User.id == reg.patient_id))
    patient_name = user_result.scalar_one_or_none()

    return RegistrationResponse(
        id=reg.id,
        patient_id=reg.patient_id,
        patient_name=patient_name or "",
        department=reg.department,
        status=reg.status,
        status_notes=reg.status_notes,
        registration_date=str(reg.registration_date),
        sequence_number=reg.sequence_number,
    )


@router.get("/patient/{patient_id}")
async def get_patient_record(
    patient_id: int,
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.role != UserRole.doctor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can access patient records",
        )

    result = await db.execute(select(User).where(User.id == patient_id))
    patient = result.scalar_one_or_none()

    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient not found: {patient_id}")
    if patient.role != UserRole.patient:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User {patient_id} is not a patient")

    # Department-scoped access: check against the latest registration
    latest_reg_result = await db.execute(
        select(Registration)
        .where(Registration.patient_id == patient_id)
        .order_by(Registration.sequence_number.desc())
        .limit(1)
    )
    latest_reg = latest_reg_result.scalars().first()
    if latest_reg is not None:
        dept_result = await db.execute(
            select(DoctorProfile.department).where(DoctorProfile.user_id == ctx.user_id)
        )
        doctor_dept = dept_result.scalar_one_or_none()
        if not doctor_dept or latest_reg.department != doctor_dept:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view patient records in your department",
            )

    # Get active registration for current status info
    active_reg = await get_active_registration(patient_id, db)

    # Build episode-grouped response
    episodes = await _build_episodes(patient_id, db)

    # If no episodes and no data at all, fall back to MCP mock (plain dicts, bypass Pydantic)
    if not episodes:
        case_result = await patient_record_module.execute("patient_record.query_case", {"patient_name": patient.name})
        visit_result = await patient_record_module.execute("patient_record.query_visit", {"patient_name": patient.name})
        prescription_result = await patient_record_module.execute("patient_record.query_prescription", {"patient_name": patient.name})
        return {
            "patient_id": patient.id,
            "patient_name": patient.name,
            "patient_role": patient.role.value,
            "current_registration_status": None,
            "current_registration_department": None,
            "episodes": [{
                "registration_id": 0, "sequence_number": 0,
                "department": "", "registration_date": "", "status": "mock",
                "cases": case_result.data.get("cases", []) if case_result.data else [],
                "visits": visit_result.data.get("visits", []) if visit_result.data else [],
                "prescriptions": prescription_result.data.get("prescriptions", []) if prescription_result.data else [],
                "care_plans": [],
            }],
        }

    return PatientRecordResponse(
        patient_id=patient.id,
        patient_name=patient.name,
        patient_role=patient.role.value,
        current_registration_status=active_reg.status if active_reg else (latest_reg.status if latest_reg else None),
        current_registration_department=active_reg.department if active_reg else (latest_reg.department if latest_reg else None),
        episodes=episodes,
    )


# --- Case CRUD ---

@router.get("/patient/{patient_id}/cases", response_model=list[CaseData])
async def list_cases(
    patient_id: int,
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can access patient records")
    result = await db.execute(select(PatientCase).where(PatientCase.user_id == patient_id).order_by(PatientCase.created_at.desc()))
    return [CaseData(id=c.id, user_id=c.user_id, diagnosis=c.diagnosis, procedures=c.procedures, allergies=c.allergies, discharge_summary=c.discharge_summary, created_at=str(c.created_at), updated_at=str(c.updated_at)) for c in result.scalars().all()]


@router.post("/patient/{patient_id}/cases", status_code=status.HTTP_201_CREATED, response_model=CaseData)
async def create_case(
    patient_id: int,
    req: CaseCreate,
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can create cases")
    await _require_editable(patient_id, db)
    active_reg = await get_active_registration(patient_id, db)
    case = PatientCase(
        user_id=patient_id,
        registration_id=active_reg.id if active_reg else None,
        diagnosis=req.diagnosis, procedures=req.procedures,
        allergies=req.allergies, discharge_summary=req.discharge_summary,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return CaseData(id=case.id, user_id=case.user_id, diagnosis=case.diagnosis, procedures=case.procedures, allergies=case.allergies, discharge_summary=case.discharge_summary, created_at=str(case.created_at), updated_at=str(case.updated_at))


@router.put("/case/{case_id}", response_model=CaseData)
async def update_case(case_id: int, req: CaseUpdate, ctx: RequestContext = Depends(get_request_context), db: AsyncSession = Depends(get_db)):
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can update cases")
    case = await db.get(PatientCase, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case not found: {case_id}")
    await _require_editable(case.user_id, db)
    if req.diagnosis is not None: case.diagnosis = req.diagnosis
    if req.procedures is not None: case.procedures = req.procedures
    if req.allergies is not None: case.allergies = req.allergies
    if req.discharge_summary is not None: case.discharge_summary = req.discharge_summary
    await db.commit()
    await db.refresh(case)
    return CaseData(id=case.id, user_id=case.user_id, diagnosis=case.diagnosis, procedures=case.procedures, allergies=case.allergies, discharge_summary=case.discharge_summary, created_at=str(case.created_at), updated_at=str(case.updated_at))


@router.delete("/case/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(case_id: int, ctx: RequestContext = Depends(get_request_context), db: AsyncSession = Depends(get_db)):
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can delete cases")
    case = await db.get(PatientCase, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case not found: {case_id}")
    await _require_editable(case.user_id, db)
    await db.delete(case)
    await db.commit()


# --- Visit CRUD ---

@router.get("/patient/{patient_id}/visits", response_model=list[VisitData])
async def list_visits(patient_id: int, ctx: RequestContext = Depends(get_request_context), db: AsyncSession = Depends(get_db)):
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can access patient records")
    result = await db.execute(select(PatientVisit).where(PatientVisit.user_id == patient_id).order_by(PatientVisit.created_at.desc()))
    return [VisitData(id=v.id, user_id=v.user_id, visit_date=v.visit_date, department=v.department, doctor_name=v.doctor_name, chief_complaint=v.chief_complaint, diagnosis=v.diagnosis, created_at=str(v.created_at)) for v in result.scalars().all()]


@router.post("/patient/{patient_id}/visits", status_code=status.HTTP_201_CREATED, response_model=VisitData)
async def create_visit(patient_id: int, req: VisitCreate, ctx: RequestContext = Depends(get_request_context), db: AsyncSession = Depends(get_db)):
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can create visits")
    await _require_editable(patient_id, db)
    active_reg = await get_active_registration(patient_id, db)
    visit = PatientVisit(
        user_id=patient_id,
        registration_id=active_reg.id if active_reg else None,
        visit_date=req.visit_date, department=req.department,
        doctor_name=req.doctor_name, chief_complaint=req.chief_complaint,
        diagnosis=req.diagnosis,
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)
    return VisitData(id=visit.id, user_id=visit.user_id, visit_date=visit.visit_date, department=visit.department, doctor_name=visit.doctor_name, chief_complaint=visit.chief_complaint, diagnosis=visit.diagnosis, created_at=str(visit.created_at))


@router.put("/visit/{visit_id}", response_model=VisitData)
async def update_visit(visit_id: int, req: VisitUpdate, ctx: RequestContext = Depends(get_request_context), db: AsyncSession = Depends(get_db)):
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can update visits")
    visit = await db.get(PatientVisit, visit_id)
    if visit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Visit not found: {visit_id}")
    await _require_editable(visit.user_id, db)
    if req.visit_date is not None: visit.visit_date = req.visit_date
    if req.department is not None: visit.department = req.department
    if req.doctor_name is not None: visit.doctor_name = req.doctor_name
    if req.chief_complaint is not None: visit.chief_complaint = req.chief_complaint
    if req.diagnosis is not None: visit.diagnosis = req.diagnosis
    await db.commit()
    await db.refresh(visit)
    return VisitData(id=visit.id, user_id=visit.user_id, visit_date=visit.visit_date, department=visit.department, doctor_name=visit.doctor_name, chief_complaint=visit.chief_complaint, diagnosis=visit.diagnosis, created_at=str(visit.created_at))


@router.delete("/visit/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_visit(visit_id: int, ctx: RequestContext = Depends(get_request_context), db: AsyncSession = Depends(get_db)):
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can delete visits")
    visit = await db.get(PatientVisit, visit_id)
    if visit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Visit not found: {visit_id}")
    await _require_editable(visit.user_id, db)
    await db.delete(visit)
    await db.commit()


# --- Prescription CRUD ---

@router.get("/patient/{patient_id}/prescriptions", response_model=list[PrescriptionData])
async def list_prescriptions(patient_id: int, ctx: RequestContext = Depends(get_request_context), db: AsyncSession = Depends(get_db)):
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can access patient records")
    result = await db.execute(select(PatientPrescription).where(PatientPrescription.user_id == patient_id).order_by(PatientPrescription.created_at.desc()))
    return [PrescriptionData(id=p.id, user_id=p.user_id, drug_name=p.drug_name, dosage=p.dosage, frequency=p.frequency, duration=p.duration, prescribed_date=p.prescribed_date, notes=p.notes, created_at=str(p.created_at)) for p in result.scalars().all()]


@router.post("/patient/{patient_id}/prescriptions", status_code=status.HTTP_201_CREATED, response_model=PrescriptionData)
async def create_prescription(patient_id: int, req: PrescriptionCreate, ctx: RequestContext = Depends(get_request_context), db: AsyncSession = Depends(get_db)):
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can create prescriptions")
    await _require_editable(patient_id, db)
    active_reg = await get_active_registration(patient_id, db)
    rx = PatientPrescription(
        user_id=patient_id,
        registration_id=active_reg.id if active_reg else None,
        drug_name=req.drug_name, dosage=req.dosage, frequency=req.frequency,
        duration=req.duration, prescribed_date=req.prescribed_date, notes=req.notes,
    )
    db.add(rx)
    await db.commit()
    await db.refresh(rx)
    return PrescriptionData(id=rx.id, user_id=rx.user_id, drug_name=rx.drug_name, dosage=rx.dosage, frequency=rx.frequency, duration=rx.duration, prescribed_date=rx.prescribed_date, notes=rx.notes, created_at=str(rx.created_at))


@router.put("/prescription/{prescription_id}", response_model=PrescriptionData)
async def update_prescription(prescription_id: int, req: PrescriptionUpdate, ctx: RequestContext = Depends(get_request_context), db: AsyncSession = Depends(get_db)):
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can update prescriptions")
    rx = await db.get(PatientPrescription, prescription_id)
    if rx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prescription not found: {prescription_id}")
    await _require_editable(rx.user_id, db)
    if req.drug_name is not None: rx.drug_name = req.drug_name
    if req.dosage is not None: rx.dosage = req.dosage
    if req.frequency is not None: rx.frequency = req.frequency
    if req.duration is not None: rx.duration = req.duration
    if req.prescribed_date is not None: rx.prescribed_date = req.prescribed_date
    if req.notes is not None: rx.notes = req.notes
    await db.commit()
    await db.refresh(rx)
    return PrescriptionData(id=rx.id, user_id=rx.user_id, drug_name=rx.drug_name, dosage=rx.dosage, frequency=rx.frequency, duration=rx.duration, prescribed_date=rx.prescribed_date, notes=rx.notes, created_at=str(rx.created_at))


@router.delete("/prescription/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prescription(prescription_id: int, ctx: RequestContext = Depends(get_request_context), db: AsyncSession = Depends(get_db)):
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can delete prescriptions")
    rx = await db.get(PatientPrescription, prescription_id)
    if rx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prescription not found: {prescription_id}")
    await _require_editable(rx.user_id, db)
    await db.delete(rx)
    await db.commit()


@router.get("/profile", response_model=DoctorProfileResponse)
async def get_profile(
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == ctx.user_id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        return DoctorProfileResponse(user_id=ctx.user_id)

    return DoctorProfileResponse(
        user_id=profile.user_id,
        department=profile.department,
        title=profile.title,
        specialty=profile.specialty,
        license_no=profile.license_no,
    )


@router.put("/profile", response_model=DoctorProfileResponse)
async def update_profile(
    update: DoctorProfileUpdate,
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == ctx.user_id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = DoctorProfile(user_id=ctx.user_id)
        db.add(profile)

    if update.department is not None:
        profile.department = update.department
    if update.title is not None:
        profile.title = update.title
    if update.specialty is not None:
        profile.specialty = update.specialty
    if update.license_no is not None:
        profile.license_no = update.license_no

    await db.commit()
    await db.refresh(profile)

    return DoctorProfileResponse(
        user_id=profile.user_id,
        department=profile.department,
        title=profile.title,
        specialty=profile.specialty,
        license_no=profile.license_no,
    )


@router.get("/patient/{patient_id}/care-plans")
async def get_patient_care_plans(
    patient_id: int,
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.role != UserRole.doctor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can access care plans",
        )

    patient = await db.get(User, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient not found: {patient_id}",
        )

    result = await db.execute(
        select(CarePlan)
        .where(CarePlan.user_id == patient_id)
        .order_by(CarePlan.created_at.desc())
    )
    plans = result.scalars().all()

    return CarePlanResponse(
        plans=[
            CarePlanItem(
                id=p.id, title=p.title, description=p.description,
                medication_schedule=p.medication_schedule,
                follow_up_date=p.follow_up_date, status=p.status,
            )
            for p in plans
        ],
        total=len(plans),
    )


@router.post(
    "/patient/{patient_id}/care-plan",
    status_code=status.HTTP_201_CREATED,
)
async def create_care_plan(
    patient_id: int,
    req: CarePlanCreate,
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.role != UserRole.doctor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can create care plans",
        )

    patient = await db.get(User, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient not found: {patient_id}",
        )
    if patient.role != UserRole.patient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {patient_id} is not a patient",
        )

    await _require_editable(patient_id, db)

    active_reg = await get_active_registration(patient_id, db)
    plan = CarePlan(
        user_id=patient_id,
        registration_id=active_reg.id if active_reg else None,
        title=req.title,
        description=req.description,
        medication_schedule=req.medication_schedule,
        follow_up_date=req.follow_up_date,
        status="active",
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return CarePlanItem(
        id=plan.id,
        title=plan.title,
        description=plan.description,
        medication_schedule=plan.medication_schedule,
        follow_up_date=plan.follow_up_date,
        status=plan.status,
    )


@router.put("/care-plan/{plan_id}")
async def update_care_plan(
    plan_id: int,
    req: CarePlanUpdate,
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.role != UserRole.doctor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can update care plans",
        )

    plan = await db.get(CarePlan, plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Care plan not found: {plan_id}",
        )

    await _require_editable(plan.user_id, db)

    if req.title is not None:
        plan.title = req.title
    if req.description is not None:
        plan.description = req.description
    if req.medication_schedule is not None:
        plan.medication_schedule = req.medication_schedule
    if req.follow_up_date is not None:
        plan.follow_up_date = req.follow_up_date
    if req.status is not None:
        plan.status = req.status

    await db.commit()
    await db.refresh(plan)

    return CarePlanItem(
        id=plan.id,
        title=plan.title,
        description=plan.description,
        medication_schedule=plan.medication_schedule,
        follow_up_date=plan.follow_up_date,
        status=plan.status,
    )


@router.delete("/care-plan/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_care_plan(
    plan_id: int,
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.role != UserRole.doctor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can delete care plans",
        )

    plan = await db.get(CarePlan, plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Care plan not found: {plan_id}",
        )

    await _require_editable(plan.user_id, db)
    await db.delete(plan)
    await db.commit()
