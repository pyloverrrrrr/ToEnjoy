from pydantic import BaseModel


class CaseData(BaseModel):
    id: int
    user_id: int
    diagnosis: str | None = None
    procedures: str | None = None
    allergies: str | None = None
    discharge_summary: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CaseCreate(BaseModel):
    diagnosis: str | None = None
    procedures: str | None = None
    allergies: str | None = None
    discharge_summary: str | None = None


class CaseUpdate(BaseModel):
    diagnosis: str | None = None
    procedures: str | None = None
    allergies: str | None = None
    discharge_summary: str | None = None


class VisitData(BaseModel):
    id: int
    user_id: int
    visit_date: str | None = None
    department: str | None = None
    doctor_name: str | None = None
    chief_complaint: str | None = None
    diagnosis: str | None = None
    created_at: str | None = None


class VisitCreate(BaseModel):
    visit_date: str | None = None
    department: str | None = None
    doctor_name: str | None = None
    chief_complaint: str | None = None
    diagnosis: str | None = None


class VisitUpdate(BaseModel):
    visit_date: str | None = None
    department: str | None = None
    doctor_name: str | None = None
    chief_complaint: str | None = None
    diagnosis: str | None = None


class PrescriptionData(BaseModel):
    id: int
    user_id: int
    drug_name: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None
    prescribed_date: str | None = None
    notes: str | None = None
    created_at: str | None = None


class PrescriptionCreate(BaseModel):
    drug_name: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None
    prescribed_date: str | None = None
    notes: str | None = None


class PrescriptionUpdate(BaseModel):
    drug_name: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None
    prescribed_date: str | None = None
    notes: str | None = None


class MedicalRecordsEpisode(BaseModel):
    registration_id: int
    sequence_number: int
    department: str
    registration_date: str
    status: str
    cases: list[CaseData] = []
    visits: list[VisitData] = []
    prescriptions: list[PrescriptionData] = []


class EpisodeGroupedMedicalRecords(BaseModel):
    patient_id: int
    patient_name: str
    episodes: list[MedicalRecordsEpisode] = []


class PatientMedicalRecords(BaseModel):
    patient_id: int
    patient_name: str
    cases: list[CaseData] = []
    visits: list[VisitData] = []
    prescriptions: list[PrescriptionData] = []
