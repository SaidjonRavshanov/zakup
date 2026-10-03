"""Domen xatolari — tilsiz: faqat `code` (HTTP javobida), `key` (tarjima kaliti) va `params`.

Matn domen ichida yozilmaydi; HTTP qatlami `platform/i18n.py` katalogidan
foydalanuvchi tilida (Accept-Language) chiqaradi.
"""


class DomainError(Exception):
    """Biznes qoidasi buzildi (422)."""

    code: str = "domain_error"

    def __init__(self, key: str | None = None, /, **params: object) -> None:
        self.key = key or self.code
        self.params = params
        super().__init__(f"{self.key} {params}" if params else self.key)


class NotFoundError(DomainError):
    code = "not_found"


class ConflictError(DomainError):
    """Parallel tahrir (optimistic lock) yoki dublikat."""

    code = "conflict"


class UnauthenticatedError(DomainError):
    """Token yo'q, muddati o'tgan yoki yaroqsiz (401): klient sessiyani yangilashi kerak."""

    code = "unauthenticated"


class PermissionDeniedError(DomainError):
    code = "permission_denied"


class InvalidTransitionError(DomainError):
    """Status mashinasida ruxsat etilmagan o'tish."""

    code = "invalid_transition"
