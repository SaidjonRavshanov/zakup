from datetime import date, time
from decimal import Decimal

import pytest

from zakup.modules.catalog.domain.offer import (
    InvalidOfferError,
    Packaging,
    PriceSource,
    SupplierOffer,
)
from zakup.modules.catalog.domain.product import InvalidProductError, Product, Unit
from zakup.modules.catalog.domain.purchase_card import (
    InvalidPurchaseCardError,
    Norms,
    PurchaseCard,
    PurchaseMode,
    SupplierChoice,
)
from zakup.modules.catalog.domain.supplier import Contacts, InvalidSupplierError, OrderSchedule
from zakup.shared_kernel.ids import new_id

TODAY = date(2026, 10, 3)


def _offer(factor: str = "25", multiple: str = "1", price: str = "250000") -> SupplierOffer:
    offer, _ = SupplierOffer.create(
        supplier_id=new_id(),
        product_id=new_id(),
        packaging=Packaging(Unit.BAG, Decimal(factor), Decimal(multiple)),
        price=Decimal(price),
        valid_from=TODAY,
    )
    return offer


@pytest.mark.parametrize(
    ("need", "factor", "multiple", "packs", "base"),
    [
        ("30", "25", "1", "2", "50"),  # 30 kg → 2 qop (1.2 qop bo'lmaydi)
        ("50", "25", "1", "2", "50"),  # aniq karrali
        ("13", "12", "2", "2", "24"),  # 12 donali quti, 2 qutidan karrali
        ("0", "25", "1", "0", "0"),
        ("-5", "25", "1", "0", "0"),  # ortiqcha qoldiq — buyurtma yo'q
        ("0.3", "0.5", "1", "1", "0.5"),
    ],
)
def test_order_quantity_rounds_up_to_pack_multiple(
    need: str, factor: str, multiple: str, packs: str, base: str
) -> None:
    quantity = _offer(factor, multiple).order_quantity(Decimal(need))
    assert (quantity.packs, quantity.base_qty) == (Decimal(packs), Decimal(base))


def test_base_unit_price_compares_different_packs() -> None:
    assert _offer("25", price="250000").base_unit_price == Decimal("10000.0000")
    assert _offer("10", price="105000").base_unit_price == Decimal("10500.0000")


def test_create_returns_initial_price_record() -> None:
    _, record = SupplierOffer.create(
        supplier_id=new_id(),
        product_id=new_id(),
        packaging=Packaging(Unit.KG, Decimal(1)),
        price=Decimal("12.34567"),
        valid_from=TODAY,
    )
    assert (record.price, record.source) == (Decimal("12.3457"), PriceSource.MANUAL)


def test_price_change_is_recorded_once() -> None:
    offer = _offer()
    record = offer.change_price(Decimal(260000), date(2026, 10, 5), PriceSource.SUPPLIER_RESPONSE)
    assert record is not None
    assert record.price == Decimal(260000)
    assert offer.change_price(Decimal(260000), date(2026, 10, 5), PriceSource.MANUAL) is None
    assert [e.event_type for e in offer.pull_events()] == ["catalog.offer_price_changed"]


def test_price_cannot_be_backdated() -> None:
    with pytest.raises(InvalidOfferError):
        _offer().change_price(Decimal(1), date(2026, 9, 1), PriceSource.MANUAL)


@pytest.mark.parametrize(("factor", "multiple"), [("0", "1"), ("-1", "1"), ("25", "0")])
def test_packaging_must_be_positive(factor: str, multiple: str) -> None:
    with pytest.raises(InvalidOfferError):
        Packaging(Unit.BAG, Decimal(factor), Decimal(multiple))


def test_product_base_unit_cannot_be_a_pack() -> None:
    with pytest.raises(InvalidProductError):
        Product.register(name="Un", base_unit=Unit.BAG)


def test_auto_mode_requires_primary_supplier() -> None:
    card = PurchaseCard.open(product_id=new_id(), store_id=new_id())
    assert card.mode is PurchaseMode.MANUAL  # yangi tovar — faqat qo'lda (WORKFLOW B1)
    with pytest.raises(InvalidPurchaseCardError):
        card.configure(mode=PurchaseMode.AUTO, norms=Norms(), suppliers=SupplierChoice())


def test_suppliers_must_differ() -> None:
    supplier = new_id()
    with pytest.raises(InvalidPurchaseCardError):
        SupplierChoice(supplier, supplier)


@pytest.mark.parametrize(
    ("coverage", "shelf_life", "lead_time", "expected"),
    [(7, None, 2, 7), (7, 5, 2, 3), (7, 2, 2, 0), (3, 30, 1, 3)],
)
def test_effective_coverage_for_perishables(
    coverage: int, shelf_life: int | None, lead_time: int, expected: int
) -> None:
    card = PurchaseCard.open(product_id=new_id(), store_id=new_id())
    card.configure(
        mode=PurchaseMode.MANUAL,
        norms=Norms(coverage_days=coverage, shelf_life_days=shelf_life),
        suppliers=SupplierChoice(),
    )
    assert card.effective_coverage_days(lead_time) == expected


@pytest.mark.parametrize(
    "kwargs",
    [{"lead_time_days": 61}, {"order_weekdays": frozenset()}, {"delivery_weekdays": frozenset({0})}],
)
def test_schedule_validation(kwargs: dict[str, object]) -> None:
    with pytest.raises(InvalidSupplierError):
        OrderSchedule(**kwargs)  # type: ignore[arg-type]


def test_schedule_accepts_cutoff() -> None:
    assert OrderSchedule(order_cutoff=time(16, 0), order_weekdays=frozenset({1, 4})).order_cutoff == time(16, 0)


@pytest.mark.parametrize("kwargs", [{"phone": "12"}, {"email": "no-at-sign"}])
def test_contacts_validation(kwargs: dict[str, str]) -> None:
    with pytest.raises(InvalidSupplierError):
        Contacts(**kwargs)
