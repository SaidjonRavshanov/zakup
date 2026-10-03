from uuid import UUID

import pytest

from tests.application.fakes import FakeUoW
from zakup.modules.identity.application.dto import TelegramIdentity
from zakup.modules.identity.application.use_cases import SignIn
from zakup.modules.identity.domain.user import AccountPendingError, User
from zakup.shared_kernel.auth import Principal, Role


class InMemoryUsers:
    def __init__(self) -> None:
        self.items: dict[UUID, User] = {}

    async def get(self, user_id: UUID) -> User | None:
        return self.items.get(user_id)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return next((u for u in self.items.values() if u.telegram_id == telegram_id), None)

    async def add(self, user: User) -> None:
        self.items[user.id] = user

    async def save(self, user: User) -> None:
        self.items[user.id] = user


class FakeAccess:
    def issue(self, principal: Principal) -> tuple[str, int]:
        return f"access:{principal.user_id}", 900


class FakeRefresh:
    def __init__(self) -> None:
        self.issued: list[UUID] = []

    async def issue(self, user_id: UUID) -> str:
        self.issued.append(user_id)
        return f"refresh:{len(self.issued)}"

    async def consume(self, raw_token: str) -> UUID:
        raise NotImplementedError

    async def revoke(self, raw_token: str) -> None: ...

    async def revoke_all(self, user_id: UUID) -> None: ...


ALICE = TelegramIdentity(telegram_id=10, first_name="Alisher", last_name="Navoiy", language_code="ru")


def _sign_in(users: InMemoryUsers, refresh: FakeRefresh, uow: FakeUoW, admins: frozenset[int] = frozenset()) -> SignIn:
    return SignIn(uow, users, access=FakeAccess(), refresh=refresh, bootstrap_admin_ids=admins)


async def test_new_user_is_saved_as_pending_without_session() -> None:
    users, refresh, uow = InMemoryUsers(), FakeRefresh(), FakeUoW()
    with pytest.raises(AccountPendingError):
        await _sign_in(users, refresh, uow)(ALICE)

    (user,) = users.items.values()
    assert (user.full_name, user.locale, user.is_active) == ("Alisher Navoiy", "ru", False)
    assert uow.committed  # admin ko'rishi uchun saqlangan
    assert not refresh.issued


async def test_bootstrap_admin_gets_session_on_first_sign_in() -> None:
    users, refresh, uow = InMemoryUsers(), FakeRefresh(), FakeUoW()
    tokens = await _sign_in(users, refresh, uow, admins=frozenset({ALICE.telegram_id}))(ALICE)

    (user,) = users.items.values()
    assert user.principal().has_role(Role.ADMIN)
    assert tokens.access_token == f"access:{user.id}"
    assert [e.event_type for e in uow.published] == ["identity.user_signed_up", "identity.user_activated"]


async def test_existing_user_profile_is_refreshed() -> None:
    users, refresh, uow = InMemoryUsers(), FakeRefresh(), FakeUoW()
    sign_in = _sign_in(users, refresh, uow, admins=frozenset({ALICE.telegram_id}))
    await sign_in(ALICE)
    await sign_in(TelegramIdentity(telegram_id=ALICE.telegram_id, first_name="Alisher", username="navoiy"))

    (user,) = users.items.values()
    assert (user.full_name, user.username) == ("Alisher", "navoiy")
    assert len(refresh.issued) == 2
