from datetime import UTC, datetime

import pytest

from zakup.modules.identity.domain.user import (
    AccountPendingError,
    SelfLockoutError,
    User,
    normalize_locale,
)
from zakup.shared_kernel.auth import Principal, Role, RoleGrant
from zakup.shared_kernel.ids import new_id

NOW = datetime(2026, 10, 3, tzinfo=UTC)


def _user() -> User:
    return User.sign_up(telegram_id=42, full_name="  Aziz   Karimov ", username="aziz", locale="uz")


def _admin() -> Principal:
    return Principal(user_id=new_id(), grants=frozenset({RoleGrant(Role.ADMIN)}))


def test_sign_up_creates_pending_user() -> None:
    user = _user()
    assert not user.is_active
    assert user.full_name == "Aziz Karimov"
    assert [e.event_type for e in user.pull_events()] == ["identity.user_signed_up"]
    with pytest.raises(AccountPendingError):
        user.ensure_can_sign_in()


def test_empty_name_falls_back_to_telegram_id() -> None:
    assert User.sign_up(telegram_id=7, full_name=" ", username=None, locale="ru").full_name == "tg:7"


def test_bootstrap_admin_activates_with_admin_role() -> None:
    user = _user()
    user.bootstrap_admin(NOW)
    assert user.is_active
    assert user.principal().has_role(Role.ADMIN)


def test_activate_is_idempotent() -> None:
    user, admin = _user(), _admin()
    user.pull_events()
    user.activate(admin, NOW)
    user.activate(admin, NOW)
    assert [e.event_type for e in user.pull_events()] == ["identity.user_activated"]


def test_admin_cannot_deactivate_self() -> None:
    user = _user()
    with pytest.raises(SelfLockoutError):
        user.deactivate(user.principal())


def test_admin_cannot_remove_own_admin_role() -> None:
    user = _user()
    user.bootstrap_admin(NOW)
    with pytest.raises(SelfLockoutError):
        user.set_grants(frozenset({RoleGrant(Role.BUYER)}), user.principal())


def test_set_grants_records_event_only_on_change() -> None:
    user, admin = _user(), _admin()
    user.pull_events()
    grants = frozenset({RoleGrant(Role.BUYER), RoleGrant(Role.STOREKEEPER, new_id())})
    user.set_grants(grants, admin)
    user.set_grants(grants, admin)
    assert [e.event_type for e in user.pull_events()] == ["identity.user_roles_changed"]


@pytest.mark.parametrize(
    ("code", "expected"), [("ru", "ru"), ("ru-RU", "ru"), ("uz", "uz"), ("en", "uz"), (None, "uz")]
)
def test_normalize_locale(code: str | None, expected: str) -> None:
    assert normalize_locale(code) == expected


def test_principal_store_scope() -> None:
    kitchen, bar = new_id(), new_id()
    principal = Principal(user_id=new_id(), grants=frozenset({RoleGrant(Role.STOREKEEPER, kitchen)}))
    assert principal.has_role(Role.STOREKEEPER, store_id=kitchen)
    assert not principal.has_role(Role.STOREKEEPER, store_id=bar)
    assert principal.has_role(Role.STOREKEEPER)  # "qaysidir omborda"
    assert not principal.has_role(Role.BUYER)

    everywhere = Principal(user_id=new_id(), grants=frozenset({RoleGrant(Role.BUYER)}))
    assert everywhere.has_role(Role.BUYER, store_id=bar)
