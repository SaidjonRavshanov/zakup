from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from zakup.modules.notifications.application.ports import (
    DeliveryRefusedError,
    OrderInfo,
    OutgoingMessage,
    PaymentInfo,
    PendingMessage,
    Recipient,
    RequestInfo,
    StoreDeliveries,
    UserInfo,
)
from zakup.modules.notifications.application.use_cases import DeliveriesDigest, NotifyOnEvent, SendNextMessage
from zakup.modules.notifications.domain.messages import Facts, Kind, money, render

STORE = uuid4()
INITIATOR = Recipient(uuid4(), 101, "ru")
BUYER = Recipient(uuid4(), 102, "uz")
APPROVER = Recipient(uuid4(), 103, "ru")
ADMIN = Recipient(uuid4(), 104, "ru")
ACCOUNTANT = Recipient(uuid4(), 105, "ru")
STOREKEEPER = Recipient(uuid4(), 106, "uz")
ROLES = {
    "initiator": [INITIATOR],
    "buyer": [BUYER],
    "approver": [APPROVER],
    "admin": [ADMIN],
    "accountant": [ACCOUNTANT],
    "storekeeper": [STOREKEEPER],
}
EVERYONE = {r.user_id: r for rs in ROLES.values() for r in rs}


class FakeDirectory:
    def __init__(self) -> None:
        self.requests: dict[UUID, RequestInfo] = {}
        self.orders: dict[UUID, OrderInfo] = {}
        self.payments: dict[UUID, PaymentInfo] = {}
        self.users: dict[UUID, UserInfo] = {}
        self.today: list[StoreDeliveries] = []

    async def with_roles(self, roles: frozenset[str], store_id: UUID | None) -> list[Recipient]:
        return [r for role in sorted(roles) for r in ROLES.get(role, [])]

    async def user(self, user_id: UUID) -> Recipient | None:
        return EVERYONE.get(user_id)

    async def user_info(self, user_id: UUID) -> UserInfo | None:
        return self.users.get(user_id)

    async def request(self, request_id: UUID) -> RequestInfo | None:
        return self.requests.get(request_id)

    async def order(self, order_id: UUID) -> OrderInfo | None:
        return self.orders.get(order_id)

    async def receipt(self, receipt_id: UUID) -> None:
        return None

    async def payment(self, payment_id: UUID) -> PaymentInfo | None:
        return self.payments.get(payment_id)

    async def deliveries(self, day: date) -> list[StoreDeliveries]:
        return self.today


class FakeQueue:
    def __init__(self) -> None:
        self.messages: list[OutgoingMessage] = []

    async def enqueue(self, messages: list[OutgoingMessage]) -> None:
        self.messages += messages


LIMITS = {"buyer": Decimal(2_000_000), "approver": Decimal(10_000_000), "admin": None}


def event(aggregate_id: UUID, **extra: object) -> dict[str, object]:
    return {"event_id": str(uuid4()), "aggregate_id": str(aggregate_id), **extra}


def request_info(amount: int) -> RequestInfo:
    return RequestInfo("Z-000007", STORE, "Кухня", Decimal(amount), date(2026, 10, 8), INITIATOR.user_id, 3, None)


@pytest.fixture
def setup() -> tuple[FakeDirectory, FakeQueue, NotifyOnEvent]:
    directory, queue = FakeDirectory(), FakeQueue()
    return directory, queue, NotifyOnEvent(directory, queue, LIMITS)  # type: ignore[arg-type]


async def test_request_pending_goes_to_deciders_within_limit(
    setup: tuple[FakeDirectory, FakeQueue, NotifyOnEvent],
) -> None:
    directory, queue, notify = setup
    small, big = uuid4(), uuid4()
    directory.requests[small] = request_info(1_500_000)
    directory.requests[big] = request_info(5_000_000)

    await notify("procurement.request_submitted", event(small, store_id=str(STORE), amount="1500000"))
    assert {m.recipient for m in queue.messages} == {BUYER, APPROVER, ADMIN}
    assert {m.path for m in queue.messages} == {f"/requests/{small}"}
    buyer_text = next(m.text for m in queue.messages if m.recipient == BUYER)
    assert "Z-000007" in buyer_text
    assert "1 500 000 so'm" in buyer_text

    queue.messages.clear()
    await notify("procurement.request_submitted", event(big, store_id=str(STORE), amount="5000000"))
    assert {m.recipient for m in queue.messages} == {APPROVER, ADMIN}  # zakupshik limiti 2 mln


async def test_author_does_not_notify_himself(setup: tuple[FakeDirectory, FakeQueue, NotifyOnEvent]) -> None:
    directory, queue, notify = setup
    request_id = uuid4()
    directory.requests[request_id] = RequestInfo(
        "Z-1", STORE, "Кухня", Decimal(100), date(2026, 10, 8), ADMIN.user_id, 1, None
    )
    await notify("procurement.request_submitted", event(request_id))
    assert ADMIN not in {m.recipient for m in queue.messages}


async def test_decision_goes_to_initiator_with_comment(setup: tuple[FakeDirectory, FakeQueue, NotifyOnEvent]) -> None:
    directory, queue, notify = setup
    request_id = uuid4()
    directory.requests[request_id] = RequestInfo(
        "Z-2", STORE, "Кухня", Decimal(100), date(2026, 10, 8), INITIATOR.user_id, 1, "Мало позиций"
    )
    await notify(
        "procurement.request_decided", event(request_id, decision="returned", approver_id=str(APPROVER.user_id))
    )
    (message,) = queue.messages
    assert message.recipient == INITIATOR
    assert "возвращена" in message.text
    assert "Мало позиций" in message.text


async def test_order_reapproval_and_confirmation(setup: tuple[FakeDirectory, FakeQueue, NotifyOnEvent]) -> None:
    directory, queue, notify = setup
    order_id = uuid4()
    directory.orders[order_id] = OrderInfo(
        "PO-1", STORE, "Кухня", "Дон Махсулот", date(2026, 10, 8), Decimal(262_500), BUYER.user_id
    )
    await notify("procurement.order_responded", event(order_id, status="REAPPROVAL"))
    assert {m.recipient for m in queue.messages} == {APPROVER, ADMIN}

    queue.messages.clear()
    await notify("procurement.order_responded", event(order_id, status="CONFIRMED"))
    (message,) = queue.messages
    assert message.recipient == BUYER
    assert "Don" not in message.text
    assert "Дон Махсулот" in message.text

    queue.messages.clear()
    await notify("procurement.order_responded", event(order_id, status="SENT"))
    assert queue.messages == []


async def test_payment_flow_recipients(setup: tuple[FakeDirectory, FakeQueue, NotifyOnEvent]) -> None:
    directory, queue, notify = setup
    payment_id = uuid4()
    directory.payments[payment_id] = PaymentInfo("P-1", "Анвар ака", Decimal(2_000_000), ACCOUNTANT.user_id, None, None)

    await notify("finance.payment_submitted", event(payment_id, status="SUBMITTED"))
    assert {m.recipient for m in queue.messages} == {APPROVER, ADMIN}

    queue.messages.clear()
    await notify("finance.payment_submitted", event(payment_id, status="APPROVED"))  # tasdiq shart emas
    assert {m.recipient for m in queue.messages} == {ADMIN}  # muallif (buxgalter) o'ziga yozmaydi

    queue.messages.clear()
    await notify(
        "finance.payment_rejected", event(payment_id, comment="Нет счёта", requested_by=str(ACCOUNTANT.user_id))
    )
    (message,) = queue.messages
    assert message.recipient == ACCOUNTANT
    assert "Нет счёта" in message.text


async def test_pending_user_only_when_not_active(setup: tuple[FakeDirectory, FakeQueue, NotifyOnEvent]) -> None:
    directory, queue, notify = setup
    pending, admin_now = uuid4(), uuid4()
    directory.users[pending] = UserInfo("Ali <b>", 555, is_active=False)
    directory.users[admin_now] = UserInfo("Boss", 1, is_active=True)

    await notify("identity.user_signed_up", event(admin_now))
    assert queue.messages == []
    await notify("identity.user_signed_up", event(pending))
    (message,) = queue.messages
    assert message.recipient == ADMIN
    assert "Ali &lt;b&gt;" in message.text  # HTML ekranlangan


async def test_unknown_event_is_ignored(setup: tuple[FakeDirectory, FakeQueue, NotifyOnEvent]) -> None:
    _, queue, notify = setup
    assert await notify("catalog.product_registered", event(uuid4())) == 0
    assert queue.messages == []


async def test_deliveries_digest_is_idempotent_per_store_and_day() -> None:
    directory, queue = FakeDirectory(), FakeQueue()
    directory.today = [StoreDeliveries(STORE, "Кухня", ["Анвар ака", "Дон Махсулот"])]
    digest = DeliveriesDigest(directory, queue, lambda: datetime(2026, 10, 7, 2, tzinfo=UTC))  # type: ignore[arg-type]
    await digest()
    await digest()
    keys = {m.key for m in queue.messages}
    assert len(keys) == 1  # bir kun + ombor → bitta kalit (navbatda ON CONFLICT)
    assert {m.recipient for m in queue.messages} == {STOREKEEPER}
    assert "Bugun yetkazmalar: 2" in queue.messages[0].text
    assert "• Дон Махсулот" in queue.messages[0].text


def test_render_and_money() -> None:
    assert money("1250000.50", "ru") == "1 250 001 сум"
    assert money("975000", "uz") == "975 000 so'm"
    text = render(Kind.PAYMENT_PAID, "de", Facts(number="P-1", supplier="X", amount="10"))
    assert text.startswith("✅ <b>Оплата P-1 проведена</b>")  # noma'lum til → ruscha


class FakeSendQueue:
    def __init__(self, message: PendingMessage | None) -> None:
        self.message = message
        self.result: tuple[str, object] | None = None

    async def next_pending(self, now: datetime) -> PendingMessage | None:
        return self.message

    async def mark_sent(self, message_id: UUID, at: datetime) -> None:
        self.result = ("sent", at)

    async def mark_retry(self, message_id: UUID, error: str, next_attempt_at: datetime) -> None:
        self.result = ("retry", next_attempt_at)

    async def mark_failed(self, message_id: UUID, error: str) -> None:
        self.result = ("failed", error)


class FakeSender:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.sent: list[tuple[int, str, tuple[str, str] | None]] = []

    async def send(self, chat_id: int, text: str, button: tuple[str, str] | None) -> None:
        if self.error:
            raise self.error
        self.sent.append((chat_id, text, button))


NOW = datetime(2026, 10, 7, 9, tzinfo=UTC)


async def _send(queue: FakeSendQueue, sender: FakeSender, base: str = "https://zakup.example") -> bool:
    async def commit() -> None:
        return None

    return await SendNextMessage(queue, sender, base, commit, clock=lambda: NOW)()  # type: ignore[arg-type]


async def test_send_with_mini_app_button() -> None:
    queue = FakeSendQueue(PendingMessage(uuid4(), 101, "hi", "/requests/1", "uz", 0))
    sender = FakeSender()
    assert await _send(queue, sender) is True
    assert sender.sent == [(101, "hi", ("Ochish", "https://zakup.example/requests/1"))]
    assert queue.result == ("sent", NOW)


async def test_send_without_button_on_http_and_nothing_pending() -> None:
    queue = FakeSendQueue(PendingMessage(uuid4(), 101, "hi", "/", "ru", 0))
    sender = FakeSender()
    await _send(queue, sender, base="http://127.0.0.1:5173")
    assert sender.sent[0][2] is None
    assert await _send(FakeSendQueue(None), sender) is False


async def test_send_retry_then_fail() -> None:
    queue = FakeSendQueue(PendingMessage(uuid4(), 101, "hi", None, "ru", 1))
    await _send(queue, FakeSender(RuntimeError("telegram 502")))
    assert queue.result is not None
    assert queue.result[0] == "retry"
    assert queue.result[1] == datetime(2026, 10, 7, 9, 1, tzinfo=UTC)  # 30 * 2**1 s

    refused = FakeSendQueue(PendingMessage(uuid4(), 101, "hi", None, "ru", 0))
    await _send(refused, FakeSender(DeliveryRefusedError("403: bot was blocked")))
    assert refused.result == ("failed", "403: bot was blocked")

    last = FakeSendQueue(PendingMessage(uuid4(), 101, "hi", None, "ru", 5))
    await _send(last, FakeSender(RuntimeError("timeout")))
    assert last.result == ("failed", "timeout")
