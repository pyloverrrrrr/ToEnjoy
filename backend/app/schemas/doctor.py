from pydantic import BaseModel

from app.schemas.medical_record import CaseData, VisitData, PrescriptionData
from app.schemas.patient import CarePlanItem


class PatientSearchItem(BaseModel):
    id: int
    name: str
    phone: str | None = None
    id_number_suffix: str | None = None


class EpisodeRecordData(BaseModel):
    registration_id: int
    sequence_number: int
    department: str
    registration_date: str
    status: str
    cases: list[CaseData] = []
    visits: list[VisitData] = []
    prescriptions: list[PrescriptionData] = []
    care_plans: list[CarePlanItem] = []


class PatientRecordResponse(BaseModel):
    patient_id: int
    patient_name: str | None = None
    patient_role: str | None = None
    current_registration_status: str | None = None
    current_registration_department: str | None = None
    episodes: list[EpisodeRecordData] = []


class DoctorProfileResponse(BaseModel):
    user_id: int
    department: str | None = None
    title: str | None = None
    specialty: str | None = None
    license_no: str | None = None


class DoctorProfileUpdate(BaseModel):
    department: str | None = None
    title: str | None = None
    specialty: str | None = None
    license_no: str | None = None


class CarePlanCreate(BaseModel):
    title: str
    description: str | None = None
    medication_schedule: str | None = None
    follow_up_date: str | None = None


class CarePlanUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    medication_schedule: str | None = None
    follow_up_date: str | None = None
    status: str | None = None
