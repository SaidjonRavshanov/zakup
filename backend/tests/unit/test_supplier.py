from datetime import UTC, datetime

import pytest

from zakup.modules.catalog.domain.supplier import (
    InvalidSupplierError,
    PaymentTerms,
    Supplier,
    SupplierArchived,
    SupplierRegistered,
)


def test_register_records_event_and_normalizes() -> None:
    supplier = Supplier.register(name="  Sutli Vodiy  ", inn="305123456", payment_terms=PaymentTerms.ON_DELIVERY)
    assert supplier.name == "Sutli Vodiy"
    [event] = supplier.pull_events()
    assert isinstance(event, SupplierRegistered)
    assert event.aggregate_id == supplier.id
    assert supplier.pull_events() == []


@pytest.mark.parametrize(
    ("kwargs", "key"),
    [
        ({"name": " ", "inn": None, "payment_terms": PaymentTerms.PREPAY}, "supplier.name_empty"),
        ({"name": "A", "inn": "12345", "payment_terms": PaymentTerms.PREPAY}, "supplier.inn_format"),
        (
            {"name": "A", "inn": None, "payment_terms": PaymentTerms.DEFERRED, "deferral_days": 0},
            "supplier.deferral_range",
        ),
        (
            {"name": "A", "inn": None, "payment_terms": PaymentTerms.PREPAY, "deferral_days": 7},
            "supplier.deferral_only_deferred",
        ),
    ],
)
def test_register_rejects_invalid(kwargs: dict[str, object], key: str) -> None:
    with pytest.raises(InvalidSupplierError) as exc_info:
        Supplier.register(**kwargs)  # type: ignore[arg-type]
    assert exc_info.value.key == key


def test_archive_is_idempotent() -> None:
    supplier = Supplier.register(name="A", inn=None, payment_terms=PaymentTerms.PREPAY)
    supplier.pull_events()
    now = datetime.now(UTC)
    supplier.archive(now)
    supplier.archive(now)
    assert supplier.is_archived
    assert [type(e) for e in supplier.pull_events()] == [SupplierArchived]
