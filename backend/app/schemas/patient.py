from pydantic import BaseModel


class PatientProfileResponse(BaseModel):
    user_id: int
    gender: str | None = None
    birthday: str | None = None
    blood_type: str | None = None
    allergies: str | None = None
    medical_history: dict | None = None
    personalization_config: dict | None = None


class PatientProfileUpdate(BaseModel):
    gender: str | None = None
    birthday: str | None = None
    blood_type: str | None = None
    allergies: str | None = None
    medical_history: dict | None = None
    personalization_config: dict | None = None


class CarePlanItem(BaseModel):
    id: int
    title: str
    description: str | None = None
    medication_schedule: str | None = None
    follow_up_date: str | None = None
    status: str


class CarePlanEpisode(BaseModel):
    registration_id: int
    sequence_number: int
    department: str
    registration_date: str
    status: str
    plans: list[CarePlanItem] = []


class CarePlanEpisodeResponse(BaseModel):
    episodes: list[CarePlanEpisode] = []
    total: int = 0


class CarePlanResponse(BaseModel):
    plans: list[CarePlanItem]
    total: int = 0
