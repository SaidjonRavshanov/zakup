"""UUIDv7 — vaqt bo'yicha tartiblangan ID (ADR-10).

Python 3.14 dan `uuid.uuid7()` bor; 3.12/3.13 uchun RFC 9562 bo'yicha o'zimiz.
"""

import os
import time
import uuid
from typing import NewType

EntityId = NewType("EntityId", uuid.UUID)


def uuid7() -> uuid.UUID:
    unix_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")
    value = (unix_ms & 0xFFFF_FFFF_FFFF) << 80  # 48 bit vaqt
    value |= 0x7 << 76  # versiya 7
    value |= ((rand >> 62) & 0x0FFF) << 64  # 12 bit rand_a
    value |= 0b10 << 62  # RFC 4122 variant
    value |= rand & 0x3FFF_FFFF_FFFF_FFFF  # 62 bit rand_b
    return uuid.UUID(int=value)


def new_id() -> EntityId:
    return EntityId(uuid7())
