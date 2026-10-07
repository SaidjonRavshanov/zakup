from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zakup.modules.identity.application.dto import UserProfile
from zakup.modules.identity.domain.user import Locale
from zakup.shared_kernel.auth import Role, RoleGrant


class TelegramSignInIn(BaseModel):
    init_data: str = Field(min_length=1, max_length=4096)


class DevSignInIn(BaseModel):
    telegram_id: int = Field(gt=0)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    username: str | None = Field(default=None, max_length=64)
    language_code: str | None = Field(default=None, max_length=10)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=200)


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    expires_in: int
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 — OAuth2 atamasi, sir emas


class GrantSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: Role
    store_id: UUID | None = None

    def to_domain(self) -> RoleGrant:
        return RoleGrant(self.role, self.store_id)


class UserOut(BaseModel):
    id: UUID
    telegram_id: int
    full_name: str
    username: str | None
    locale: Locale
    is_active: bool
    grants: list[GrantSchema]

    @classmethod
    def from_profile(cls, profile: UserProfile) -> "UserOut":
        return cls(
            id=profile.id,
            telegram_id=profile.telegram_id,
            full_name=profile.full_name,
            username=profile.username,
            locale=profile.locale,
            is_active=profile.is_active,
            grants=[GrantSchema.model_validate(grant) for grant in profile.grants],
        )


class ChangeLocaleIn(BaseModel):
    locale: Locale


class SetRolesIn(BaseModel):
    grants: list[GrantSchema] = Field(max_length=1000)
