import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.middleware.identity_router import get_request_context, RequestContext
from app.models.user import User, UserRole
from app.models.doctor import DoctorProfile
from app.models.registration import Registration, RegistrationStatus
from app.schemas.registration import (
    DepartmentInfo,
    RegistrationCreate,
    RegistrationResponse,
    VALID_STATUSES,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["registration"])

FALLBACK_DEPARTMENTS = [
    "内科", "外科", "妇产科", "儿科", "眼科", "耳鼻喉科", "口腔科", "皮肤科",
    "神经内科", "心内科", "骨科", "泌尿外科", "内分泌科", "呼吸内科", "消化内科",
    "中医科", "急诊科",
]

_VALID_TRANSITIONS: dict[str, set[str]] = {
    "registered": {"in_consultation", "need_reregister"},
    "in_consultation": {"recovering", "need_reregister"},
    "recovering": {"recovered"},
    "recovered": set(),                         # terminal
    "need_reregister": {"registered"},           # re-register creates new record
}


# -- Active statuses that block re-registration --
_ACTIVE_STATUSES = {RegistrationStatus.REGISTERED, RegistrationStatus.IN_CONSULTATION, RegistrationStatus.RECOVERING}


async def get_active_registration(patient_id: int, db: AsyncSession) -> Registration | None:
    """Return the patient's active registration (registered/in_consultation/recovering), or None."""
    result = await db.execute(
        select(Registration)
        .where(Registration.patient_id == patient_id, Registration.status.in_(_ACTIVE_STATUSES))
        .order_by(Registration.sequence_number.desc())
    )
    return result.scalars().first()


# ========================
#  Department listing
# ========================

@router.get("/api/departments", response_model=list[DepartmentInfo])
async def list_departments(
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """List all available departments (dynamic from doctor profiles + fallback)."""
    result = await db.execute(
        select(DoctorProfile.department, func.count(DoctorProfile.user_id))
        .where(DoctorProfile.department.isnot(None), DoctorProfile.department != "")
        .group_by(DoctorProfile.department)
    )
    dynamic = {row[0]: row[1] for row in result.all()}

    departments: dict[str, int] = {}
    for dept in FALLBACK_DEPARTMENTS:
        departments[dept] = dynamic.get(dept, 0)
    for dept, count in dynamic.items():
        if dept not in departments:
            departments[dept] = count

    return [
        DepartmentInfo(name=name, doctor_count=count)
        for name, count in sorted(departments.items())
    ]


# ========================
#  Patient registration
# ========================

@router.get("/api/patient/registration")
async def get_my_registration(
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """Get the current patient's registration status."""
    if ctx.role != UserRole.patient:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only patients can view registration")

    result = await db.execute(
        select(Registration)
        .where(Registration.patient_id == ctx.user_id)
        .order_by(Registration.sequence_number.desc())
        .limit(1)
    )
    reg = result.scalars().first()

    if reg is None:
        return {"registered": False}

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


@router.post("/api/patient/registration", status_code=status.HTTP_201_CREATED, response_model=RegistrationResponse)
async def create_registration(
    req: RegistrationCreate,
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """Register with a department. One active registration per patient."""
    if ctx.role != UserRole.patient:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only patients can register")

    # Block if already has an active registration
    active_reg = await get_active_registration(ctx.user_id, db)
    if active_reg is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="您已有进行中的挂号，请勿重复挂号",
        )

    # Validate department
    dept_names = {d.name for d in (await list_departments(ctx=ctx, db=db))}
    if req.department not in dept_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的科室: {req.department}",
        )

    # Calculate next sequence_number (keep old registrations for history)
    max_seq_result = await db.execute(
        select(func.max(Registration.sequence_number))
        .where(Registration.patient_id == ctx.user_id)
    )
    next_seq = (max_seq_result.scalar() or 0) + 1

    reg = Registration(
        patient_id=ctx.user_id,
        department=req.department,
        status=RegistrationStatus.REGISTERED,
        sequence_number=next_seq,
    )
    db.add(reg)
    await db.commit()
    await db.refresh(reg)

    user_result = await db.execute(select(User.name).where(User.id == ctx.user_id))
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
