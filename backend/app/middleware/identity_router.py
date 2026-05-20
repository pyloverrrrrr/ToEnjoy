from dataclasses import dataclass
from fastapi import Depends
from app.models.user import User, UserRole
from app.middleware.auth import get_current_user


@dataclass
class RequestContext:
    user_id: int
    username: str
    role: UserRole
    kb_collection: str
    response_template: str


async def get_request_context(user: User = Depends(get_current_user)) -> RequestContext:
    if user.role == UserRole.doctor:
        kb = "kb_professional"
        template = "professional"
    else:
        kb = "kb_patient"
        template = "patient"
    return RequestContext(
        user_id=user.id,
        username=user.username,
        role=user.role,
        kb_collection=kb,
        response_template=template,
    )
