"""iikoServer javoblari → domen modellari. XML — defusedxml (tashqi ma'lumot, XXE himoyasi).

Formatlar Tarnov Sebzar serveridan (iikoRMS 9.2.7014.0) olingan namunalar bo'yicha; contract testlari —
tests/contract/iiko/.
"""

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID
from xml.etree.ElementTree import Element, SubElement, tostring

from defusedxml.ElementTree import fromstring

from zakup.modules.integration_iiko.domain.models import (
    DepartmentType,
    IikoContainer,
    IikoDepartment,
    IikoIncomingInvoice,
    IikoInvoiceItem,
    IikoProduct,
    IikoProductGroup,
    IikoStore,
    IikoSupplier,
    IikoUnit,
    ImportResult,
    IncomingInvoiceDraft,
)
from zakup.shared_kernel.errors import DomainError


class IikoResponseError(DomainError):
    code = "iiko_response"


def _uuid(value: str | None) -> UUID | None:
    if not value or value == "null":
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _required_uuid(value: str | None, what: str) -> UUID:
    parsed = _uuid(value)
    if parsed is None:
        raise IikoResponseError("iiko.bad_id", what=what, value=value)
    return parsed


def _decimal(value: str | float | int | None) -> Decimal:
    if value is None or value == "":
        return Decimal(0)
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise IikoResponseError("iiko.bad_number", value=value) from exc


def _text(element: Element, tag: str) -> str | None:
    value = element.findtext(tag)
    return value.strip() or None if value is not None else None


def _xml(payload: bytes) -> Element:
    try:
        root: Element = fromstring(payload)
    except Exception as exc:  # defusedxml / ParseError
        raise IikoResponseError("iiko.bad_xml") from exc
    return root


def _json(payload: bytes) -> list[dict[str, Any]]:
    try:
        data = json.loads(payload)
    except ValueError as exc:
        raise IikoResponseError("iiko.bad_json") from exc
    if not isinstance(data, list):
        raise IikoResponseError("iiko.bad_json")
    return data


def parse_departments(payload: bytes) -> list[IikoDepartment]:
    result = []
    for item in _xml(payload):
        kind = _text(item, "type")
        if kind is None or kind not in DepartmentType.__members__:
            continue
        result.append(
            IikoDepartment(
                id=_required_uuid(_text(item, "id"), "department"),
                name=_text(item, "name") or "",
                code=_text(item, "code"),
                type=DepartmentType(kind),
            )
        )
    return result


def parse_stores(payload: bytes) -> list[IikoStore]:
    return [
        IikoStore(
            id=_required_uuid(_text(item, "id"), "store"),
            name=_text(item, "name") or "",
            department_id=_uuid(_text(item, "parentId")),
        )
        for item in _xml(payload)
        if _text(item, "type") == "STORE"
    ]


def parse_units(payload: bytes) -> list[IikoUnit]:
    return [
        IikoUnit(id=_required_uuid(row["id"], "unit"), name=str(row.get("name") or ""), code=row.get("code"))
        for row in _json(payload)
        if not row.get("deleted")
    ]


def parse_product_groups(payload: bytes) -> list[IikoProductGroup]:
    return [
        IikoProductGroup(
            id=_required_uuid(row["id"], "group"),
            name=str(row.get("name") or "").strip(),
            parent_id=_uuid(row.get("parent")),
            deleted=bool(row.get("deleted")),
        )
        for row in _json(payload)
    ]


def parse_products(payload: bytes) -> list[IikoProduct]:
    return [
        IikoProduct(
            id=_required_uuid(row["id"], "product"),
            name=str(row.get("name") or "").strip(),
            article=(str(row["num"]).strip() or None) if row.get("num") else None,
            type=str(row.get("type") or ""),
            unit_id=_uuid(row.get("mainUnit")),
            group_id=_uuid(row.get("parent")),
            deleted=bool(row.get("deleted")),
            containers=tuple(
                IikoContainer(
                    id=_required_uuid(c["id"], "container"),
                    name=str(c.get("name") or ""),
                    count=_decimal(c.get("count")),
                )
                for c in row.get("containers") or []
                if not c.get("deleted")
            ),
        )
        for row in _json(payload)
    ]


def parse_suppliers(payload: bytes) -> list[IikoSupplier]:
    return [
        IikoSupplier(
            id=_required_uuid(_text(item, "id"), "supplier"),
            name=_text(item, "name") or "",
            code=_text(item, "code"),
            phone=_text(item, "phone") or _text(item, "cellPhone"),
            inn=_text(item, "taxpayerIdNumber"),
            deleted=_text(item, "deleted") == "true",
            represents_store=_text(item, "representsStore") == "true",
        )
        for item in _xml(payload)
        if _text(item, "supplier") == "true"
    ]


def parse_incoming_invoices(payload: bytes) -> list[IikoIncomingInvoice]:
    invoices = []
    for doc in _xml(payload):
        default_store = _uuid(_text(doc, "defaultStore"))
        items = tuple(
            IikoInvoiceItem(
                product_id=_required_uuid(_text(item, "product"), "invoice product"),
                store_id=_uuid(_text(item, "store")) or default_store,
                amount=_decimal(_text(item, "amount")),
                price=_decimal(_text(item, "price")),
                total=_decimal(_text(item, "sum")),
                container_id=_uuid(_text(item, "containerId")),
            )
            for item in doc.findall("items/item")
            if _text(item, "isAdditionalExpense") != "true"
        )
        raw_date = _text(doc, "incomingDate") or (_text(doc, "dateIncoming") or "")[:10]
        invoices.append(
            IikoIncomingInvoice(
                id=_required_uuid(_text(doc, "id"), "invoice"),
                number=_text(doc, "documentNumber"),
                incoming_date=date.fromisoformat(raw_date),
                supplier_id=_uuid(_text(doc, "supplier")),
                store_id=default_store,
                status=_text(doc, "status") or "",
                comment=_text(doc, "comment"),
                items=items,
            )
        )
    return invoices


def render_incoming_invoice(draft: IncomingInvoiceDraft) -> bytes:
    """iikoRMS incomingInvoice import DTO (iiko API hujjati bo'yicha; Tarnov serverida hali sinovdan o'tmagan)."""
    doc = Element("document")
    items = SubElement(doc, "items")
    for num, item in enumerate(draft.items, start=1):
        node = SubElement(items, "item")
        for tag, value in (
            ("amount", item.amount),
            ("product", item.product_id),
            ("num", num),
            ("price", item.price),
            ("sum", item.total),
            ("store", item.store_id),
        ):
            SubElement(node, tag).text = str(value)
    header: tuple[tuple[str, object], ...] = (
        ("dateIncoming", draft.incoming_at),
        ("useDefaultDocumentTime", "false"),
        ("documentNumber", draft.document_number),
        ("supplier", draft.supplier_id),
        ("defaultStore", draft.store_id),
        ("invoice", draft.supplier_invoice_no or ""),
        ("comment", draft.comment),
        ("status", "PROCESSED" if draft.processed else "NEW"),
    )
    for tag, header_value in header:
        SubElement(doc, tag).text = str(header_value)
    body: bytes = tostring(doc, encoding="unicode").encode()
    return b'<?xml version="1.0" encoding="UTF-8"?>' + body


def parse_import_result(payload: bytes) -> ImportResult:
    root = _xml(payload)
    valid = (root.findtext("valid") or "").strip().lower() == "true"
    error = (root.findtext("errorMessage") or "").strip() or None
    return ImportResult(valid=valid, document_number=_text(root, "documentNumber"), error=error)
