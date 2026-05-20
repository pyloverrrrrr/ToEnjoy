from pydantic import BaseModel, field_validator

VALID_STATUSES = {"registered", "in_consultation", "recovering", "recovered", "need_reregister"}


class RegistrationCreate(BaseModel):
    department: str


class RegistrationStatusUpdate(BaseModel):
    status: str
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"Invalid status, must be one of: {', '.join(sorted(VALID_STATUSES))}")
        return v


class RegistrationResponse(BaseModel):
    id: int
    patient_id: int
    patient_name: str
    department: str
    status: str
    status_notes: str | None = None
    registration_date: str
    sequence_number: int = 1


class DepartmentInfo(BaseModel):
    name: str
    doctor_count: int


class RegisteredPatientItem(BaseModel):
    id: int
    name: str
    phone: str | None = None
    registration_status: str
    registration_date: str
    deleted_at: str | None = None
