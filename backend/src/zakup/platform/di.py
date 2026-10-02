"""Stub dependency: router abstraksiyaga (use case / port) bog'lanadi,
haqiqiy implementatsiya faqat composition root'da (bootstrap.py) ulanadi.

    async def handler(uc: Annotated[ListSuppliers, Depends(Stub(ListSuppliers))]): ...
    app.dependency_overrides[ListSuppliers] = provide_list_suppliers
"""

from typing import Any, NoReturn


class Stub:
    def __init__(self, dependency: Any) -> None:
        self._dependency = dependency

    def __call__(self) -> NoReturn:
        raise RuntimeError(f"Dependency ulanmagan: {self._dependency!r} (bootstrap.py ni tekshiring)")

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Stub):
            return bool(self._dependency == other._dependency)
        return bool(self._dependency == other)

    def __hash__(self) -> int:
        return hash(self._dependency)
