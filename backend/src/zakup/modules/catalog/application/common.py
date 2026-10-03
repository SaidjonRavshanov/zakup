from uuid import UUID

from zakup.modules.catalog.application.ports import Repository
from zakup.shared_kernel.errors import NotFoundError

MAX_PAGE_SIZE = 200


async def load[A](repository: Repository[A], entity_id: UUID, not_found_key: str) -> A:
    entity = await repository.get(entity_id)
    if entity is None:
        raise NotFoundError(not_found_key)
    return entity


def page_size(limit: int) -> int:
    return max(1, min(limit, MAX_PAGE_SIZE))
