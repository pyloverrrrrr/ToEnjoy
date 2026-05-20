from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt

from app.config import settings
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.patient import PatientProfile
from app.models.doctor import DoctorProfile
from app.models.conversation import Conversation
from app.models.care_plan import CarePlan
from app.models.medical_record import PatientCase, PatientVisit, PatientPrescription
from app.models.registration import Registration
from app.schemas.auth import (
    LoginRequest, RegisterRequest, TokenResponse,
    UserUpdateRequest, PasswordChangeRequest, UserMeResponse,
    DeleteAccountRequest,
)
from app.middleware.auth import create_access_token, get_current_user
from app.core.multimodal.file_storage import upload_to_minio, get_from_minio

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(User).where(User.username == req.username, User.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")

    if req.id_number:
        existing_id = await db.execute(
            select(User).where(User.id_number == req.id_number, User.deleted_at.is_(None))
        )
        if existing_id.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该身份证号已被注册")

    hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    user = User(
        username=req.username, password_hash=hashed, role=UserRole(req.role),
        name=req.name, id_number=req.id_number, phone=req.phone,
    )
    db.add(user)
    await db.flush()

    if req.role == "doctor":
        db.add(DoctorProfile(user_id=user.id))
    else:
        db.add(PatientProfile(user_id=user.id))

    await db.commit()
    return {"message": "Registration successful"}


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名不存在")
    if not bcrypt.checkpw(req.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="密码错误")
    if user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账户已注销")

    token = create_access_token(user.id, user.username, user.role.value)
    return TokenResponse(
        token=token,
        user={
            "id": user.id, "username": user.username, "role": user.role.value,
            "name": user.name, "avatar_url": user.avatar_url,
        },
    )


@router.get("/me", response_model=UserMeResponse)
async def me(user: User = Depends(get_current_user)):
    return UserMeResponse(
        id=user.id,
        username=user.username,
        role=user.role.value,
        name=user.name,
        phone=user.phone,
        email=user.email,
        id_number=user.id_number,
        avatar_url=user.avatar_url,
    )


@router.put("/me", response_model=UserMeResponse)
async def update_me(
    req: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.phone is not None:
        user.phone = req.phone
    if req.email is not None:
        user.email = req.email
    if req.id_number is not None:
        user.id_number = req.id_number
    await db.commit()
    await db.refresh(user)
    return UserMeResponse(
        id=user.id,
        username=user.username,
        role=user.role.value,
        name=user.name,
        phone=user.phone,
        email=user.email,
        id_number=user.id_number,
        avatar_url=user.avatar_url,
    )


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    file_bytes = await file.read()
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="头像文件不能超过 5MB")

    object_path = await upload_to_minio(file_bytes, file.filename or "avatar.png")
    user.avatar_url = object_path
    await db.commit()
    return {"avatar_url": object_path}


@router.get("/avatar/{path:path}")
async def serve_avatar(path: str):
    try:
        file_bytes = await get_from_minio(path)
    except Exception:
        raise HTTPException(status_code=404, detail="头像不存在")
    return Response(content=file_bytes, media_type="image/png")


@router.put("/password")
async def change_password(
    req: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not bcrypt.checkpw(req.old_password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=400, detail="原密码错误")

    if len(req.new_password) < 6:
        raise HTTPException(status_code=422, detail="新密码至少需要6个字符")

    user.password_hash = bcrypt.hashpw(req.new_password.encode(), bcrypt.gensalt()).decode()
    await db.commit()
    return {"message": "密码修改成功"}


@router.post("/delete-account")
async def delete_account(
    req: DeleteAccountRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="两次输入的密码不一致")
    if not bcrypt.checkpw(req.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=400, detail="密码错误")

    # 1. Soft-delete user and free unique fields for re-registration
    user.deleted_at = datetime.now(timezone.utc)
    user.username = f"deleted_{user.id}_{int(user.deleted_at.timestamp())}"
    user.id_number = None
    user.phone = None
    user.email = None

    # 2. Delete profiles
    if user.role == UserRole.patient:
        await db.execute(delete(PatientProfile).where(PatientProfile.user_id == user.id))
    else:
        await db.execute(delete(DoctorProfile).where(DoctorProfile.user_id == user.id))

    # 3. Delete conversations
    await db.execute(delete(Conversation).where(Conversation.user_id == user.id))

    # 4. Delete care plans + medical records linked to registrations
    regs_result = await db.execute(select(Registration.id).where(Registration.patient_id == user.id))
    reg_ids = [row[0] for row in regs_result.fetchall()]
    if reg_ids:
        await db.execute(delete(CarePlan).where(CarePlan.registration_id.in_(reg_ids)))
        await db.execute(delete(PatientCase).where(PatientCase.registration_id.in_(reg_ids)))
        await db.execute(delete(PatientVisit).where(PatientVisit.registration_id.in_(reg_ids)))
        await db.execute(delete(PatientPrescription).where(PatientPrescription.registration_id.in_(reg_ids)))

    # 5. Delete legacy records (registration_id IS NULL)
    await db.execute(delete(PatientCase).where(PatientCase.user_id == user.id, PatientCase.registration_id.is_(None)))
    await db.execute(delete(PatientVisit).where(PatientVisit.user_id == user.id, PatientVisit.registration_id.is_(None)))
    await db.execute(delete(PatientPrescription).where(PatientPrescription.user_id == user.id, PatientPrescription.registration_id.is_(None)))
    await db.execute(delete(CarePlan).where(CarePlan.user_id == user.id, CarePlan.registration_id.is_(None)))

    await db.commit()

    # 6. Clean Redis short-term memory (best-effort)
    try:
        import app.db.redis as redis_mod
        r = await redis_mod.get_redis()
        if r:
            keys = await r.keys(f"session:*:{user.id}:*")
            for key in keys:
                await r.delete(key)
    except Exception:
        pass

    # 7. Clean ChromaDB long-term memory (best-effort)
    try:
        import app.db.chroma as chroma_mod
        chroma = await chroma_mod.get_chroma()
        if chroma:
            coll = await chroma.get_collection("user_memory")
            coll.delete(where={"user_id": str(user.id)})
    except Exception:
        pass

    return {"message": "账户已注销"}
