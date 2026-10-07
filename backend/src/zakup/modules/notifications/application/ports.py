"""notifications portlari. Modul boshqa modullar kodini bilmaydi: ma'lumotni read-only SQL orqali o'qiydi
(infrastructure), eventlarni — outbox payload'idan oladi."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Recipient:
    user_id: UUID
    telegram_id: int
    locale: str


@dataclass(frozen=True, slots=True)
class RequestInfo:
    number: str
    store_id: UUID
    store: str
    amount: Decimal
    needed_by: date
    initiator_id: UUID
    lines: int
    last_comment: str | None


@dataclass(frozen=True, slots=True)
class OrderInfo:
    number: str
    store_id: UUID
    store: str
    supplier: str
    delivery_date: date
    amount: Decimal
    sent_by: UUID | None


@dataclass(frozen=True, slots=True)
class ReceiptInfo:
    number: str
    store_id: UUID
    store: str
    supplier: str
    amount: Decimal
    received_by: UUID


@dataclass(frozen=True, slots=True)
class PaymentInfo:
    number: str
    supplier: str
    amount: Decimal
    requested_by: UUID
    approved_by: UUID | None
    comment: str | None


@dataclass(frozen=True, slots=True)
class UserInfo:
    full_name: str
    telegram_id: int
    is_active: bool


@dataclass(frozen=True, slots=True)
class StoreDeliveries:
    store_id: UUID
    store: str
    suppliers: list[str]


class Directory(Protocol):
    """Kim, nima: foydalanuvchilar va hujjatlar (read-only)."""

    async def with_roles(self, roles: frozenset[str], store_id: UUID | None) -> list[Recipient]:
        """Faol xodimlar: shu rollardan biri bor va (store_id berilsa) shu omborga yoki barcha omborlarga."""
        ...

    async def user(self, user_id: UUID) -> Recipient | None: ...
    async def user_info(self, user_id: UUID) -> UserInfo | None: ...
    async def request(self, request_id: UUID) -> RequestInfo | None: ...
    async def order(self, order_id: UUID) -> OrderInfo | None: ...
    async def receipt(self, receipt_id: UUID) -> ReceiptInfo | None: ...
    async def payment(self, payment_id: UUID) -> PaymentInfo | None: ...
    async def deliveries(self, day: date) -> list[StoreDeliveries]: ...


@dataclass(frozen=True, slots=True)
class OutgoingMessage:
    key: UUID  # idempotentlik: (key, user_id) — event bir necha marta qayta ishlansa ham xabar bitta
    recipient: Recipient
    text: str
    path: str | None  # Mini App ichidagi yo'l: /requests/{id}


@dataclass(frozen=True, slots=True)
class PendingMessage:
    id: UUID
    chat_id: int
    text: str
    path: str | None
    locale: str
    attempts: int


class MessageQueue(Protocol):
    async def enqueue(self, messages: list[OutgoingMessage]) -> None: ...
    async def next_pending(self, now: datetime) -> PendingMessage | None:
        """Navbatdagi xabar (FOR UPDATE SKIP LOCKED) — shu tranzaksiyada belgilanadi."""
        ...

    async def mark_sent(self, message_id: UUID, at: datetime) -> None: ...
    async def mark_retry(self, message_id: UUID, error: str, next_attempt_at: datetime) -> None: ...
    async def mark_failed(self, message_id: UUID, error: str) -> None: ...


class DeliveryRefusedError(Exception):
    """Telegram qat'iy rad etdi (foydalanuvchi botni bloklagan / /start bosmagan) — qayta urinilmaydi."""


class Sender(Protocol):
    async def send(self, chat_id: int, text: str, button: tuple[str, str] | None) -> None:
        """button: (matn, to'liq https URL) — Mini App tugmasi."""
        ...
