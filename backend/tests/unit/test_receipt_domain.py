from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from zakup.modules.integration_iiko.domain.models import IncomingInvoiceDraft, InvoiceDraftItem
from zakup.modules.integration_iiko.infrastructure.parsers import (
    parse_import_result,
    parse_incoming_invoices,
    render_incoming_invoice,
)
from zakup.modules.receiving.domain.receipt import (
    DiscrepancyKind,
    ExpectedLine,
    FactLine,
    InvalidReceiptError,
    PaymentMethod,
    Receipt,
    ReceiptHeader,
    ReceiptStatus,
    ReceivingTolerance,
    Resolution,
)
from zakup.shared_kernel.errors import InvalidTransitionError

NOW = datetime(2026, 10, 5, 8, tzinfo=UTC)
FLOUR, COLA = uuid4(), uuid4()


def _expected() -> list[ExpectedLine]:
    return [
        ExpectedLine(order_line_id=FLOUR, product_id=uuid4(), base_unit="kg", qty=Decimal(50), price=Decimal(10500)),
        ExpectedLine(order_line_id=COLA, product_id=uuid4(), base_unit="pcs", qty=Decimal(24), price=Decimal(6000)),
    ]


def _receipt(*facts: FactLine) -> Receipt:
    return Receipt.submit(
        id=uuid4(),
        number="R-000001",
        header=ReceiptHeader(
            order_id=uuid4(),
            store_id=uuid4(),
            supplier_id=uuid4(),
            received_by=uuid4(),
            received_at=NOW,
            supplier_invoice_no=" 1234 ",
            payment_method=PaymentMethod.CASH,
            invoice_photo_id=uuid4(),
        ),
        expected=_expected(),
        facts=list(facts),
        line_ids=[uuid4(), uuid4()],
        tolerance=ReceivingTolerance(),
    )


def _kinds(receipt: Receipt) -> set[tuple[DiscrepancyKind, bool]]:
    return {(d.kind, d.within_tolerance) for d in receipt.discrepancies}


def test_exact_delivery_is_accepted() -> None:
    receipt = _receipt(FactLine(FLOUR, Decimal(50), Decimal(10500)), FactLine(COLA, Decimal(24), Decimal(6000)))
    assert receipt.status is ReceiptStatus.ACCEPTED
    assert receipt.discrepancies == []
    assert receipt.total == Decimal(669000)
    assert receipt.header.supplier_invoice_no == "1234"
    assert [e.event_type for e in receipt.pull_events()] == ["receiving.receipt_accepted"]


def test_weight_within_tolerance_accepted_piece_must_match() -> None:
    receipt = _receipt(FactLine(FLOUR, Decimal("51.2"), Decimal(10500)), FactLine(COLA, Decimal(24), Decimal(6000)))
    assert receipt.status is ReceiptStatus.ACCEPTED  # +2.4% vazn — dopuskda
    assert _kinds(receipt) == {(DiscrepancyKind.QTY_OVER, True)}

    short_cola = _receipt(FactLine(FLOUR, Decimal(50), Decimal(10500)), FactLine(COLA, Decimal(23), Decimal(6000)))
    assert short_cola.status is ReceiptStatus.DISPUTED  # donali — aniq
    assert _kinds(short_cola) == {(DiscrepancyKind.QTY_UNDER, False)}
    assert not short_cola.is_complete


def test_missing_line_is_short_and_blocks() -> None:
    receipt = _receipt(FactLine(FLOUR, Decimal(50), Decimal(10500)))
    assert receipt.status is ReceiptStatus.DISPUTED
    assert _kinds(receipt) == {(DiscrepancyKind.SHORT, False)}
    assert [e.event_type for e in receipt.pull_events()] == ["receiving.receipt_disputed"]


def test_price_down_is_saving_price_up_blocks_over_tolerance() -> None:
    cheaper = _receipt(FactLine(FLOUR, Decimal(50), Decimal(10000)), FactLine(COLA, Decimal(24), Decimal(6000)))
    assert cheaper.status is ReceiptStatus.ACCEPTED
    assert _kinds(cheaper) == {(DiscrepancyKind.PRICE_DOWN, True)}

    slightly = _receipt(FactLine(FLOUR, Decimal(50), Decimal(10700)), FactLine(COLA, Decimal(24), Decimal(6000)))
    assert slightly.status is ReceiptStatus.ACCEPTED  # +1.9% — "с пометкой"

    pricier = _receipt(FactLine(FLOUR, Decimal(50), Decimal(11500)), FactLine(COLA, Decimal(24), Decimal(6000)))
    assert pricier.status is ReceiptStatus.DISPUTED
    assert _kinds(pricier) == {(DiscrepancyKind.PRICE_UP, False)}


def test_defect_is_not_accepted_and_needs_reason() -> None:
    with pytest.raises(InvalidReceiptError):
        _receipt(
            FactLine(FLOUR, Decimal(50), Decimal(10500), qty_defect=Decimal(5)),
            FactLine(COLA, Decimal(24), Decimal(6000)),
        )
    receipt = _receipt(
        FactLine(FLOUR, Decimal(50), Decimal(10500), qty_defect=Decimal(5), defect_reason="Ho'l qop"),
        FactLine(COLA, Decimal(24), Decimal(6000)),
    )
    assert receipt.status is ReceiptStatus.DISPUTED
    assert receipt.lines[0].qty_accepted == Decimal(45)
    assert receipt.total == Decimal(45 * 10500 + 24 * 6000)


def test_resolve_dispute_accepts_once() -> None:
    receipt = _receipt(FactLine(FLOUR, Decimal(50), Decimal(11500)), FactLine(COLA, Decimal(24), Decimal(6000)))
    receipt.pull_events()
    with pytest.raises(InvalidReceiptError):
        receipt.resolve_dispute(by=uuid4(), resolution=Resolution.ACCEPTED, comment=" ", at=NOW)
    receipt.resolve_dispute(by=uuid4(), resolution=Resolution.DISCOUNT, comment="Chegirma kelishildi", at=NOW)
    assert receipt.status is ReceiptStatus.ACCEPTED
    assert [e.event_type for e in receipt.pull_events()] == ["receiving.receipt_accepted"]
    with pytest.raises(InvalidTransitionError):
        receipt.resolve_dispute(by=uuid4(), resolution=Resolution.ACCEPTED, comment="x", at=NOW)


def test_unknown_order_line_is_rejected() -> None:
    with pytest.raises(InvalidReceiptError):
        _receipt(FactLine(uuid4(), Decimal(1), Decimal(1)))


def test_invoice_xml_roundtrip() -> None:
    product, store, supplier = uuid4(), uuid4(), uuid4()
    draft = IncomingInvoiceDraft(
        document_number="R-000007",
        incoming_at="2026-10-05T13:00:00",
        supplier_id=supplier,
        store_id=store,
        supplier_invoice_no="Н-55",
        comment="Zakup R-000007 нал",
        processed=True,
        items=(InvoiceDraftItem(product, store, Decimal("51.2"), Decimal(10500), Decimal(537600)),),
    )
    xml = render_incoming_invoice(draft)
    # O'zimiz yozgan XML iiko eksport formati bilan bir xil o'qiladi
    (parsed,) = parse_incoming_invoices(
        b"<incomingInvoiceDtoes>"
        + xml.split(b"?>", 1)[1].replace(b"<document>", b"<document><id>" + str(uuid4()).encode() + b"</id>")
        + b"</incomingInvoiceDtoes>"
    )
    assert (parsed.number, parsed.supplier_id, parsed.status) == ("R-000007", supplier, "PROCESSED")
    assert [(i.product_id, i.amount, i.price) for i in parsed.items] == [(product, Decimal("51.2"), Decimal(10500))]

    ok = parse_import_result(
        b"<documentValidationResult><valid>true</valid><documentNumber>R-000007</documentNumber></documentValidationResult>"
    )
    assert (ok.valid, ok.document_number) == (True, "R-000007")
    bad = parse_import_result(
        b"<documentValidationResult><valid>false</valid>"
        b"<errorMessage>No product</errorMessage></documentValidationResult>"
    )
    assert (bad.valid, bad.error) == (False, "No product")
