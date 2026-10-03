from pathlib import Path
from uuid import uuid4

import pytest

from zakup.modules.integration_iiko.domain.mapping import (
    PaymentMethod,
    parse_supplier_name,
    payment_method_from_comment,
    unit_code,
)
from zakup.modules.integration_iiko.domain.models import IikoUnit
from zakup.modules.integration_iiko.infrastructure import parsers
from zakup.modules.integration_iiko.infrastructure.parsers import IikoResponseError

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "iiko"
CASH, TRANSFER = PaymentMethod.CASH, PaymentMethod.TRANSFER


# Haqiqiy Tarnov nomlari (Sebzar, 2026-10)
@pytest.mark.parametrize(
    ("raw", "display", "method"),
    [
        ("(ПЕР) Азиз ака (Алайский)", "Азиз ака (Алайский)", TRANSFER),
        ("НАЛ Азиз ака (Алайский)", "Азиз ака (Алайский)", CASH),
        ('(OOO "HORECA Partners ")(ПЕР)', 'OOO "HORECA Partners "', TRANSFER),
        ("(НАЛ) Чорсу От гушти", "Чорсу От гушти", CASH),
        ("Анвар ака НАЛ (от гошти)", "Анвар ака (от гошти)", CASH),
        ("ИМПИРЕ (пер) товук", "ИМПИРЕ товук", TRANSFER),
        ("Safe touch перчатка", "Safe touch перчатка", None),  # "пер" — so'z ichida
        ("Tarnov Sebzar: Склад Персанал", "Tarnov Sebzar: Склад Персанал", None),
        ("пакет (кг пер)", "пакет (кг пер)", None),
        ("Жиззах тухум", "Жиззах тухум", None),
    ],
)
def test_parse_supplier_name(raw: str, display: str, method: PaymentMethod | None) -> None:
    parsed = parse_supplier_name(raw)
    assert (parsed.display, parsed.payment_method) == (display, method)


def test_cash_and_transfer_cards_share_key() -> None:
    assert parse_supplier_name("(ПЕР) Азиз ака (Алайский)").key == parse_supplier_name("НАЛ Азиз ака (Алайский)").key
    assert (
        parse_supplier_name('"GOLDEN BEEF AND LAMB MEAT" Контур').key
        == parse_supplier_name("GOLDEN BEEF AND LAMB MEAT Контур").key
    )


@pytest.mark.parametrize(("comment", "method"), [("нал", CASH), ("пер", TRANSFER), ("Пер.", TRANSFER), (None, None)])
def test_payment_method_from_comment(comment: str | None, method: PaymentMethod | None) -> None:
    assert payment_method_from_comment(comment) == method


@pytest.mark.parametrize(
    ("code", "name", "expected"),
    [("166", "кг", "kg"), ("112", "л", "l"), ("796", "шт", "pcs"), (None, "кг", "kg"), (None, "порц", None)],
)
def test_unit_code(code: str | None, name: str, expected: str | None) -> None:
    assert unit_code(IikoUnit(id=uuid4(), name=name, code=code)) == expected


def test_parsers_read_fixtures() -> None:
    assert len(parsers.parse_departments((FIXTURES / "departments.xml").read_bytes())) == 4
    stores = parsers.parse_stores((FIXTURES / "stores.xml").read_bytes())
    assert {s.name for s in stores} == {"Главный Склад", "Бар склад", "Главный склад"}
    products = parsers.parse_products((FIXTURES / "products.json").read_bytes())
    cola = next(p for p in products if p.article == "147200")
    assert [(c.name, c.count) for c in cola.containers] == [("Блок", 12)]
    suppliers = parsers.parse_suppliers((FIXTURES / "suppliers.xml").read_bytes())
    assert sum(s.represents_store for s in suppliers) == 1
    invoices = parsers.parse_incoming_invoices((FIXTURES / "incoming_invoices.xml").read_bytes())
    assert [i.is_processed for i in invoices] == [True, True, True, False]
    assert invoices[1].items[1].container_id is not None


def test_broken_xml_is_reported() -> None:
    with pytest.raises(IikoResponseError):
        parsers.parse_stores(b"<html>502 Bad Gateway")


def test_xml_entities_are_not_expanded() -> None:
    """XXE / "billion laughs" — defusedxml rad etadi."""
    bomb = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;">]><r>&b;</r>'
    with pytest.raises(IikoResponseError):
        parsers.parse_stores(bomb)
