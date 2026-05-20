from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str
    role: str = "patient"
    id_number: str | None = None
    phone: str | None = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("patient", "doctor"):
            raise ValueError("role must be 'patient' or 'doctor'")
        return v


class TokenResponse(BaseModel):
    token: str
    user: dict


class UserUpdateRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    id_number: str | None = None


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


class UserMeResponse(BaseModel):
    id: int
    username: str
    role: str
    name: str
    phone: str | None = None
    email: str | None = None
    id_number: str | None = None
    avatar_url: str | None = None


class DeleteAccountRequest(BaseModel):
    password: str
    confirm_password: str
