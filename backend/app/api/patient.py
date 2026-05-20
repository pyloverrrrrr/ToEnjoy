import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.middleware.identity_router import get_request_context, RequestContext
from app.models.patient import PatientProfile
from app.models.care_plan import CarePlan
from app.models.medical_record import PatientCase, PatientVisit, PatientPrescription
from app.models.registration import Registration, RegistrationStatus
from app.models.user import User
from app.schemas.patient import (
    PatientProfileResponse,
    PatientProfileUpdate,
    CarePlanItem,
    CarePlanResponse,
    CarePlanEpisode,
)
from app.schemas.medical_record import PatientMedicalRecords, CaseData, VisitData, PrescriptionData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/patient", tags=["patient"])


@router.get("/profile", response_model=PatientProfileResponse)
async def get_profile(
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == ctx.user_id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        return PatientProfileResponse(user_id=ctx.user_id)

    return PatientProfileResponse(
        user_id=profile.user_id,
        gender=profile.gender,
        birthday=profile.birthday.isoformat() if profile.birthday else None,
        blood_type=profile.blood_type,
        allergies=profile.allergies,
        medical_history=profile.medical_history,
        personalization_config=profile.personalization_config,
    )


@router.put("/profile", response_model=PatientProfileResponse)
async def update_profile(
    update: PatientProfileUpdate,
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == ctx.user_id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = PatientProfile(user_id=ctx.user_id)
        db.add(profile)

    if update.gender is not None:
        profile.gender = update.gender
    if update.birthday is not None:
        try:
            profile.birthday = date.fromisoformat(update.birthday)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid birthday format, use YYYY-MM-DD",
            )
    if update.blood_type is not None:
        profile.blood_type = update.blood_type
    if update.allergies is not None:
        profile.allergies = update.allergies
    if update.medical_history is not None:
        profile.medical_history = update.medical_history
    if update.personalization_config is not None:
        profile.personalization_config = update.personalization_config

    await db.commit()
    await db.refresh(profile)

    return PatientProfileResponse(
        user_id=profile.user_id,
        gender=profile.gender,
        birthday=profile.birthday.isoformat() if profile.birthday else None,
        blood_type=profile.blood_type,
        allergies=profile.allergies,
        medical_history=profile.medical_history,
        personalization_config=profile.personalization_config,
    )


@router.get("/care-plan")
async def get_care_plan(
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    # Fetch all registrations for this patient, grouped by episode
    regs_result = await db.execute(
        select(Registration)
        .where(Registration.patient_id == ctx.user_id)
        .order_by(Registration.sequence_number.desc())
    )
    all_regs = regs_result.scalars().all()

    episodes: list[CarePlanEpisode] = []
    seen_legacy = False
    for reg in all_regs:
        plans_result = await db.execute(
            select(CarePlan)
            .where(CarePlan.registration_id == reg.id)
            .order_by(CarePlan.created_at.desc())
        )
        plans = plans_result.scalars().all()
        if plans:
            episodes.append(CarePlanEpisode(
                registration_id=reg.id,
                sequence_number=reg.sequence_number,
                department=reg.department,
                registration_date=str(reg.registration_date),
                status=reg.status,
                plans=[
                    CarePlanItem(
                        id=p.id, title=p.title, description=p.description,
                        medication_schedule=p.medication_schedule,
                        follow_up_date=p.follow_up_date, status=p.status,
                    )
                    for p in plans
                ],
            ))

    # Legacy care plans (no registration_id)
    legacy_result = await db.execute(
        select(CarePlan)
        .where(CarePlan.user_id == ctx.user_id, CarePlan.registration_id.is_(None))
        .order_by(CarePlan.created_at.desc())
    )
    legacy_plans = legacy_result.scalars().all()
    if legacy_plans:
        episodes.append(CarePlanEpisode(
            registration_id=0, sequence_number=0,
            department="", registration_date="", status="legacy",
            plans=[
                CarePlanItem(
                    id=p.id, title=p.title, description=p.description,
                    medication_schedule=p.medication_schedule,
                    follow_up_date=p.follow_up_date, status=p.status,
                )
                for p in legacy_plans
            ],
        ))

    total = sum(len(ep.plans) for ep in episodes)
    return {"episodes": [ep.model_dump() for ep in episodes], "total": total}


@router.get("/medical-records")
async def get_medical_records(
    ctx: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """Patient views their own medical records (read-only), grouped by episode."""
    user_result = await db.execute(select(User).where(User.id == ctx.user_id))
    user = user_result.scalar_one_or_none()

    # Build episodes from registrations
    regs_result = await db.execute(
        select(Registration)
        .where(Registration.patient_id == ctx.user_id)
        .order_by(Registration.sequence_number.desc())
    )
    all_regs = regs_result.scalars().all()

    episodes = []
    for reg in all_regs:
        is_finalized = reg.status in (RegistrationStatus.RECOVERED,)

        plans_result = await db.execute(
            select(CarePlan).where(CarePlan.registration_id == reg.id).order_by(CarePlan.created_at.desc()))
        plans = plans_result.scalars().all()

        # Only show cases/visits/prescriptions after recovery (finalized)
        if is_finalized:
            cases_result = await db.execute(
                select(PatientCase).where(PatientCase.registration_id == reg.id).order_by(PatientCase.created_at.desc()))
            visits_result = await db.execute(
                select(PatientVisit).where(PatientVisit.registration_id == reg.id).order_by(PatientVisit.created_at.desc()))
            rx_result = await db.execute(
                select(PatientPrescription).where(PatientPrescription.registration_id == reg.id).order_by(PatientPrescription.created_at.desc()))
            cases = cases_result.scalars().all()
            visits = visits_result.scalars().all()
            prescriptions = rx_result.scalars().all()
        else:
            cases, visits, prescriptions = [], [], []

        episodes.append({
            "registration_id": reg.id,
            "sequence_number": reg.sequence_number,
            "department": reg.department,
            "registration_date": str(reg.registration_date),
            "status": reg.status,
            "cases": [
                {"id": c.id, "user_id": c.user_id, "diagnosis": c.diagnosis,
                 "procedures": c.procedures, "allergies": c.allergies,
                 "discharge_summary": c.discharge_summary,
                 "created_at": str(c.created_at), "updated_at": str(c.updated_at)}
                for c in cases
            ],
            "visits": [
                {"id": v.id, "user_id": v.user_id, "visit_date": v.visit_date,
                 "department": v.department, "doctor_name": v.doctor_name,
                 "chief_complaint": v.chief_complaint, "diagnosis": v.diagnosis,
                 "created_at": str(v.created_at)}
                for v in visits
            ],
            "prescriptions": [
                {"id": p.id, "user_id": p.user_id, "drug_name": p.drug_name,
                 "dosage": p.dosage, "frequency": p.frequency,
                 "duration": p.duration, "prescribed_date": p.prescribed_date,
                 "notes": p.notes, "created_at": str(p.created_at)}
                for p in prescriptions
            ],
            "care_plans": [
                {"id": cp.id, "title": cp.title, "description": cp.description,
                 "medication_schedule": cp.medication_schedule,
                 "follow_up_date": cp.follow_up_date, "status": cp.status}
                for cp in plans
            ],
        })

    # Legacy records (no registration_id)
    lc_result = await db.execute(
        select(PatientCase).where(PatientCase.user_id == ctx.user_id, PatientCase.registration_id.is_(None)).order_by(PatientCase.created_at.desc()))
    lv_result = await db.execute(
        select(PatientVisit).where(PatientVisit.user_id == ctx.user_id, PatientVisit.registration_id.is_(None)).order_by(PatientVisit.created_at.desc()))
    lr_result = await db.execute(
        select(PatientPrescription).where(PatientPrescription.user_id == ctx.user_id, PatientPrescription.registration_id.is_(None)).order_by(PatientPrescription.created_at.desc()))
    lp_result = await db.execute(
        select(CarePlan).where(CarePlan.user_id == ctx.user_id, CarePlan.registration_id.is_(None)).order_by(CarePlan.created_at.desc()))

    lc = lc_result.scalars().all()
    lv = lv_result.scalars().all()
    lr = lr_result.scalars().all()
    lp = lp_result.scalars().all()

    if lc or lv or lr or lp:
        episodes.append({
            "registration_id": 0,
            "sequence_number": 0,
            "department": "",
            "registration_date": "",
            "status": "legacy",
            "cases": [
                {"id": c.id, "user_id": c.user_id, "diagnosis": c.diagnosis,
                 "procedures": c.procedures, "allergies": c.allergies,
                 "discharge_summary": c.discharge_summary,
                 "created_at": str(c.created_at), "updated_at": str(c.updated_at)}
                for c in lc
            ],
            "visits": [
                {"id": v.id, "user_id": v.user_id, "visit_date": v.visit_date,
                 "department": v.department, "doctor_name": v.doctor_name,
                 "chief_complaint": v.chief_complaint, "diagnosis": v.diagnosis,
                 "created_at": str(v.created_at)}
                for v in lv
            ],
            "prescriptions": [
                {"id": p.id, "user_id": p.user_id, "drug_name": p.drug_name,
                 "dosage": p.dosage, "frequency": p.frequency,
                 "duration": p.duration, "prescribed_date": p.prescribed_date,
                 "notes": p.notes, "created_at": str(p.created_at)}
                for p in lr
            ],
            "care_plans": [
                {"id": cp.id, "title": cp.title, "description": cp.description,
                 "medication_schedule": cp.medication_schedule,
                 "follow_up_date": cp.follow_up_date, "status": cp.status}
                for cp in lp
            ],
        })

    return {
        "patient_id": ctx.user_id,
        "patient_name": user.name if user else "",
        "episodes": episodes,
    }
