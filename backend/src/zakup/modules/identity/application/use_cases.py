"""Identity use case'lari: kirish (Telegram), sessiya, profil, admin — foydalanuvchilarni boshqarish."""

from uuid import UUID

from zakup.modules.identity.application.dto import SessionTokens, TelegramIdentity, UserProfile, UserStatus
from zakup.modules.identity.application.ports import (
    AccessTokenIssuer,
    InitDataVerifier,
    RefreshTokenStore,
    UserReader,
    UserRepository,
)
from zakup.modules.identity.domain.user import AccountPendingError, Locale, User, normalize_locale
from zakup.shared_kernel.auth import Principal, Role, RoleGrant
from zakup.shared_kernel.clock import Clock, utc_now
from zakup.shared_kernel.errors import NotFoundError
from zakup.shared_kernel.uow import UnitOfWork

MAX_PAGE_SIZE = 200


class _SessionIssuer:
    """Access (qisqa, JWT) + refresh (uzun, bir martalik) juftligi."""

    def __init__(self, access: AccessTokenIssuer, refresh: RefreshTokenStore) -> None:
        self._access = access
        self._refresh = refresh

    async def __call__(self, user: User) -> SessionTokens:
        access_token, expires_in = self._access.issue(user.principal())
        refresh_token = await self._refresh.issue(user.id)
        return SessionTokens(access_token=access_token, expires_in=expires_in, refresh_token=refresh_token)


class SignIn:
    """Tekshirilgan Telegram foydalanuvchisi → sessiya. Yangi foydalanuvchi — faollashtirishni kutadi."""

    def __init__(
        self,
        uow: UnitOfWork,
        users: UserRepository,
        *,
        access: AccessTokenIssuer,
        refresh: RefreshTokenStore,
        bootstrap_admin_ids: frozenset[int] = frozenset(),
        clock: Clock = utc_now,
    ) -> None:
        self._uow = uow
        self._users = users
        self._session = _SessionIssuer(access, refresh)
        self._bootstrap_admin_ids = bootstrap_admin_ids
        self._clock = clock

    async def __call__(self, identity: TelegramIdentity) -> SessionTokens:
        async with self._uow:
            user = await self._users.get_by_telegram_id(identity.telegram_id)
            is_new = user is None
            if user is None:
                user = User.sign_up(
                    telegram_id=identity.telegram_id,
                    full_name=identity.full_name,
                    username=identity.username,
                    locale=normalize_locale(identity.language_code),
                )
            else:
                user.refresh_profile(full_name=identity.full_name, username=identity.username)
            if identity.telegram_id in self._bootstrap_admin_ids:
                user.bootstrap_admin(self._clock())

            await (self._users.add(user) if is_new else self._users.save(user))
            self._uow.track(user)
            if not user.is_active:
                await self._uow.commit()  # ro'yxatga tushsin — admin ko'rib faollashtiradi
                raise AccountPendingError("auth.account_pending")
            tokens = await self._session(user)
            await self._uow.commit()
            return tokens


class SignInWithTelegram:
    def __init__(self, verifier: InitDataVerifier, sign_in: SignIn) -> None:
        self._verifier = verifier
        self._sign_in = sign_in

    async def __call__(self, init_data: str) -> SessionTokens:
        return await self._sign_in(self._verifier.verify(init_data))


class RefreshSession:
    def __init__(
        self, uow: UnitOfWork, users: UserRepository, access: AccessTokenIssuer, refresh: RefreshTokenStore
    ) -> None:
        self._uow = uow
        self._users = users
        self._refresh = refresh
        self._session = _SessionIssuer(access, refresh)

    async def __call__(self, refresh_token: str) -> SessionTokens:
        async with self._uow:
            user_id = await self._refresh.consume(refresh_token)
            user = await self._users.get(user_id)
            if user is None or not user.is_active:
                await self._refresh.revoke_all(user_id)
                await self._uow.commit()
                raise AccountPendingError("auth.account_pending")
            tokens = await self._session(user)
            await self._uow.commit()
            return tokens


class SignOut:
    def __init__(self, uow: UnitOfWork, refresh: RefreshTokenStore) -> None:
        self._uow = uow
        self._refresh = refresh

    async def __call__(self, refresh_token: str) -> None:
        async with self._uow:
            await self._refresh.revoke(refresh_token)
            await self._uow.commit()


class GetMyProfile:
    def __init__(self, reader: UserReader) -> None:
        self._reader = reader

    async def __call__(self, actor: Principal) -> UserProfile:
        profile = await self._reader.get(actor.user_id)
        if profile is None:
            raise NotFoundError("user.not_found")
        return profile


class ChangeMyLocale:
    def __init__(self, uow: UnitOfWork, users: UserRepository) -> None:
        self._uow = uow
        self._users = users

    async def __call__(self, actor: Principal, locale: Locale) -> None:
        async with self._uow:
            user = await _load(self._users, actor.user_id)
            user.change_locale(locale)
            await self._users.save(user)
            await self._uow.commit()


class ListUsers:
    def __init__(self, reader: UserReader) -> None:
        self._reader = reader

    async def __call__(
        self, actor: Principal, *, status: UserStatus | None = None, search: str | None = None, limit: int = 100
    ) -> list[UserProfile]:
        actor.require(Role.ADMIN)
        return await self._reader.list(
            status=status,
            search=search.strip() if search else None,
            limit=max(1, min(limit, MAX_PAGE_SIZE)),
        )


class ActivateUser:
    def __init__(self, uow: UnitOfWork, users: UserRepository, clock: Clock = utc_now) -> None:
        self._uow = uow
        self._users = users
        self._clock = clock

    async def __call__(self, actor: Principal, user_id: UUID) -> None:
        actor.require(Role.ADMIN)
        async with self._uow:
            user = await _load(self._users, user_id)
            user.activate(actor, self._clock())
            await self._users.save(user)
            self._uow.track(user)
            await self._uow.commit()


class DeactivateUser:
    def __init__(self, uow: UnitOfWork, users: UserRepository, refresh: RefreshTokenStore) -> None:
        self._uow = uow
        self._users = users
        self._refresh = refresh

    async def __call__(self, actor: Principal, user_id: UUID) -> None:
        actor.require(Role.ADMIN)
        async with self._uow:
            user = await _load(self._users, user_id)
            user.deactivate(actor)
            await self._users.save(user)
            await self._refresh.revoke_all(user.id)  # ochiq sessiyalar access muddati tugashi bilan yopiladi
            self._uow.track(user)
            await self._uow.commit()


class SetUserRoles:
    def __init__(self, uow: UnitOfWork, users: UserRepository) -> None:
        self._uow = uow
        self._users = users

    async def __call__(self, actor: Principal, user_id: UUID, grants: frozenset[RoleGrant]) -> None:
        actor.require(Role.ADMIN)
        async with self._uow:
            user = await _load(self._users, user_id)
            user.set_grants(grants, actor)
            await self._users.save(user)
            self._uow.track(user)
            await self._uow.commit()


async def _load(users: UserRepository, user_id: UUID) -> User:
    user = await users.get(user_id)
    if user is None:
        raise NotFoundError("user.not_found")
    return user
