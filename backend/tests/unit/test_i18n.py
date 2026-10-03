"""Tarjima katalogi to'liqligi: kodda ishlatilgan har bir kalit ikkala tilda ham bo'lishi shart."""

import ast
import inspect
from pathlib import Path

import pytest

import zakup
from zakup.platform.i18n import LOCALES, MESSAGES, negotiate_locale, translate
from zakup.shared_kernel.errors import DomainError

SRC = Path(zakup.__file__).parent


def _is_key(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and "." in node.value


def _keys_used_in_source() -> set[str]:
    """`raise SomeError("kalit", ...)`, `load(repo, id, "kalit")` va `conflict_key = "kalit"`."""
    keys: set[str] = set()
    for path in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "load":
                keys.update(arg.value for arg in node.args[2:3] if _is_key(arg))  # type: ignore[attr-defined]
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "conflict_key" for t in node.targets
            ):
                keys.update([node.value.value] if _is_key(node.value) else [])  # type: ignore[attr-defined]
            if (
                isinstance(node, ast.Raise)
                and isinstance(node.exc, ast.Call)
                and isinstance(node.exc.func, ast.Name)
                and node.exc.func.id.endswith("Error")
                and node.exc.args
                and isinstance(node.exc.args[0], ast.Constant)
                and isinstance(node.exc.args[0].value, str)
                and node.exc.func.id not in {"RuntimeError", "ValueError", "TypeError"}
            ):
                keys.add(node.exc.args[0].value)
    return keys


def _domain_error_codes() -> set[str]:
    """Kalitsiz chiqarilgan xatolar `code` ni kalit sifatida ishlatadi."""
    codes: set[str] = set()
    for module_path in SRC.rglob("*.py"):
        module_name = "zakup." + ".".join(module_path.relative_to(SRC).with_suffix("").parts)
        module_name = module_name.removesuffix(".__init__")
        module = __import__(module_name, fromlist=["_"])
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, DomainError):
                codes.add(obj.code)
    return codes


@pytest.mark.parametrize("key", sorted(_keys_used_in_source() | _domain_error_codes()))
def test_every_key_is_translated(key: str) -> None:
    assert key in MESSAGES, f"'{key}' platform/i18n.py katalogida yo'q"
    for locale in LOCALES:
        assert MESSAGES[key][locale].strip(), f"'{key}' uchun '{locale}' tarjimasi bo'sh"


def test_params_are_interpolated() -> None:
    assert translate("supplier.duplicate_inn", "ru", {"inn": "305123456"}) == "Поставщик с ИНН 305123456 уже существует"


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, "uz"),
        ("ru-RU,ru;q=0.9,en;q=0.8", "ru"),
        ("en-US,ru;q=0.5", "ru"),
        ("uz", "uz"),
        ("en", "uz"),
        ("de;q=1,uz;q=0.4,ru;q=0.7", "ru"),
    ],
)
def test_negotiate_locale(header: str | None, expected: str) -> None:
    assert negotiate_locale(header) == expected
