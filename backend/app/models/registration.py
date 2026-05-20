import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RegistrationStatus(str, enum.Enum):
    REGISTERED = "registered"
    IN_CONSULTATION = "in_consultation"
    RECOVERING = "recovering"
    RECOVERED = "recovered"
    NEED_REREGISTER = "need_reregister"


class Registration(Base):
    __tablename__ = "registrations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(nullable=False, default=1, index=True)
    department: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=RegistrationStatus.REGISTERED
    )
    status_notes: Mapped[str | None] = mapped_column(String(256), nullable=True)
    registration_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
