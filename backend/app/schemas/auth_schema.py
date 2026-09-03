from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.common import StrictRequestModel


class RegisterRequest(StrictRequestModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(StrictRequestModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class RegisterResponse(StrictRequestModel):
    id: UUID
    email: str


class RefreshRequest(StrictRequestModel):
    refresh_token: str = Field(min_length=1, max_length=512)


class TokenResponse(StrictRequestModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
