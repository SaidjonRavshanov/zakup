from collections import defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy import Select, delete, func, insert, select, update
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.modules.identity.application.dto import UserProfile, UserStatus
from zakup.modules.identity.domain.user import InvalidUserError, User
from zakup.modules.identity.infrastructure.tables import user_roles, users
from zakup.shared_kernel.auth import SYSTEM_USER_ID, Role, RoleGrant
from zakup.shared_kernel.errors import ConflictError


def _to_row(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "full_name": user.full_name,
        "username": user.username,
        "locale": user.locale,
        "is_active": user.is_active,
        "activated_at": user.activated_at,
    }


async def _load_grants(session: AsyncSession, user_ids: list[UUID]) -> dict[UUID, frozenset[RoleGrant]]:
    if not user_ids:
        return {}
    rows = await session.execute(
        select(user_roles.c.user_id, user_roles.c.role, user_roles.c.store_id).where(user_roles.c.user_id.in_(user_ids))
    )
    grouped: dict[UUID, set[RoleGrant]] = defaultdict(set)
    for row in rows:
        grouped[row.user_id].add(RoleGrant(Role(row.role), row.store_id))
    return {user_id: frozenset(grants) for user_id, grants in grouped.items()}


def _sorted_grants(grants: frozenset[RoleGrant]) -> tuple[RoleGrant, ...]:
    order = list(Role)
    return tuple(sorted(grants, key=lambda g: (order.index(g.role), str(g.store_id or ""))))


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> User | None:
        return await self._one(select(users).where(users.c.id == user_id))

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self._one(select(users).where(users.c.telegram_id == telegram_id))

    async def add(self, user: User) -> None:
        await self._session.execute(insert(users).values(**_to_row(user), version=user.version))
        await self._write_grants(user)

    async def save(self, user: User) -> None:
        result = await self._session.execute(
            update(users)
            .where(users.c.id == user.id, users.c.version == user.version)
            .values(**_to_row(user), version=user.version + 1, updated_at=func.now())
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ConflictError("user.modified")
        user.version += 1
        await self._session.execute(delete(user_roles).where(user_roles.c.user_id == user.id))
        await self._write_grants(user)

    async def _one(self, query: Select[Any]) -> User | None:
        row = (await self._session.execute(query)).mappings().first()
        if row is None:
            return None
        grants = (await _load_grants(self._session, [row["id"]])).get(row["id"], frozenset())
        return _to_domain(row, grants)

    async def _write_grants(self, user: User) -> None:
        if not user.grants:
            return
        try:
            async with self._session.begin_nested():
                await self._session.execute(
                    insert(user_roles),
                    [{"user_id": user.id, "role": g.role.value, "store_id": g.store_id} for g in user.grants],
                )
        except IntegrityError as exc:  # store_id → catalog.stores FK
            raise InvalidUserError("user.unknown_store") from exc


def _to_domain(row: RowMapping, grants: frozenset[RoleGrant]) -> User:
    return User(
        id=row["id"],
        telegram_id=row["telegram_id"],
        full_name=row["full_name"],
        username=row["username"],
        locale=row["locale"],
        is_active=row["is_active"],
        grants=grants,
        activated_at=row["activated_at"],
        version=row["version"],
    )


_PROFILE_COLUMNS = (
    users.c.id,
    users.c.telegram_id,
    users.c.full_name,
    users.c.username,
    users.c.locale,
    users.c.is_active,
)


async def _fetch_profiles(session: AsyncSession, query: Select[Any]) -> list[UserProfile]:
    rows = (await session.execute(query)).all()
    grants = await _load_grants(session, [row.id for row in rows])
    return [
        UserProfile(
            id=row.id,
            telegram_id=row.telegram_id,
            full_name=row.full_name,
            username=row.username,
            locale=row.locale,
            is_active=row.is_active,
            grants=_sorted_grants(grants.get(row.id, frozenset())),
        )
        for row in rows
    ]


class SqlUserReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> UserProfile | None:
        profiles = await _fetch_profiles(self._session, select(*_PROFILE_COLUMNS).where(users.c.id == user_id))
        return profiles[0] if profiles else None

    async def list(self, *, status: UserStatus | None, search: str | None, limit: int) -> list[UserProfile]:
        # Faollashtirishni kutayotganlar birinchi — admin ularni darhol ko'rsin
        query = (
            select(*_PROFILE_COLUMNS)
            .where(users.c.id != SYSTEM_USER_ID)  # avtomatik hujjatlar muallifi — xodim emas
            .order_by(users.c.is_active, users.c.full_name, users.c.id)
        )
        if status is not None:
            query = query.where(users.c.is_active.is_(status == "active"))
        if search:
            pattern = search.lstrip("@")
            query = query.where(
                users.c.full_name.icontains(pattern, autoescape=True)
                | users.c.username.icontains(pattern, autoescape=True)
            )
        return await _fetch_profiles(self._session, query.limit(limit))
