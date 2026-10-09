"""HTTP ↔ use case moslashtirish. Biznes mantiq va ruxsat tekshiruvi yo'q — ular use case'da (ARCHITECTURE §4, §7)."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from zakup.modules.identity.api.schemas import (
    ChangeLocaleIn,
    DevSignInIn,
    HandoffOut,
    RefreshIn,
    SessionOut,
    SetRolesIn,
    TelegramSignInIn,
    UserOut,
)
from zakup.modules.identity.application.dto import TelegramIdentity
from zakup.modules.identity.application.use_cases import (
    ActivateUser,
    ChangeMyLocale,
    DeactivateUser,
    GetMyProfile,
    IssueBrowserHandoff,
    ListUsers,
    RefreshSession,
    SetUserRoles,
    SignIn,
    SignInWithTelegram,
    SignOut,
)
from zakup.platform.di import Stub
from zakup.platform.security import CurrentPrincipal

auth_router = APIRouter(prefix="/auth", tags=["auth"])
me_router = APIRouter(prefix="/me", tags=["auth"])
users_router = APIRouter(prefix="/identity/users", tags=["identity"])
# Faqat ZAKUP_DEV_AUTH_BYPASS=true bo'lganda ulanadi (bootstrap.py): brauzerda Telegram'siz kirish
dev_auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/telegram")
async def sign_in_with_telegram(
    body: TelegramSignInIn, use_case: Annotated[SignInWithTelegram, Depends(Stub(SignInWithTelegram))]
) -> SessionOut:
    return SessionOut.model_validate(await use_case(body.init_data))


@auth_router.post("/refresh")
async def refresh_session(
    body: RefreshIn, use_case: Annotated[RefreshSession, Depends(Stub(RefreshSession))]
) -> SessionOut:
    return SessionOut.model_validate(await use_case(body.refresh_token))


@auth_router.post("/handoff")
async def browser_handoff(
    actor: CurrentPrincipal, use_case: Annotated[IssueBrowserHandoff, Depends(Stub(IssueBrowserHandoff))]
) -> HandoffOut:
    return HandoffOut(code=await use_case(actor))


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def sign_out(body: RefreshIn, use_case: Annotated[SignOut, Depends(Stub(SignOut))]) -> None:
    await use_case(body.refresh_token)


@dev_auth_router.post("/dev")
async def dev_sign_in(body: DevSignInIn, use_case: Annotated[SignIn, Depends(Stub(SignIn))]) -> SessionOut:
    return SessionOut.model_validate(await use_case(TelegramIdentity(**body.model_dump())))


@me_router.get("")
async def get_me(actor: CurrentPrincipal, use_case: Annotated[GetMyProfile, Depends(Stub(GetMyProfile))]) -> UserOut:
    return UserOut.from_profile(await use_case(actor))


@me_router.patch("", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_locale(
    body: ChangeLocaleIn, actor: CurrentPrincipal, use_case: Annotated[ChangeMyLocale, Depends(Stub(ChangeMyLocale))]
) -> None:
    await use_case(actor, body.locale)


@users_router.get("")
async def list_users(
    actor: CurrentPrincipal,
    use_case: Annotated[ListUsers, Depends(Stub(ListUsers))],
    user_status: Annotated[Literal["active", "pending"] | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[UserOut]:
    profiles = await use_case(actor, status=user_status, search=search, limit=limit)
    return [UserOut.from_profile(profile) for profile in profiles]


@users_router.post("/{user_id}/activate", status_code=status.HTTP_204_NO_CONTENT)
async def activate_user(
    user_id: UUID, actor: CurrentPrincipal, use_case: Annotated[ActivateUser, Depends(Stub(ActivateUser))]
) -> None:
    await use_case(actor, user_id)


@users_router.post("/{user_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: UUID, actor: CurrentPrincipal, use_case: Annotated[DeactivateUser, Depends(Stub(DeactivateUser))]
) -> None:
    await use_case(actor, user_id)


@users_router.put("/{user_id}/roles", status_code=status.HTTP_204_NO_CONTENT)
async def set_user_roles(
    user_id: UUID,
    body: SetRolesIn,
    actor: CurrentPrincipal,
    use_case: Annotated[SetUserRoles, Depends(Stub(SetUserRoles))],
) -> None:
    await use_case(actor, user_id, frozenset(grant.to_domain() for grant in body.grants))
