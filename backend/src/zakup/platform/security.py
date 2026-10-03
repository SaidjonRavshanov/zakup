"""Router'lar uchun "kim so'rov yubordi" dependency'si.

    async def handler(actor: CurrentPrincipal): ...

Implementatsiya (Bearer JWT → Principal) bootstrap.py da ulanadi.
"""

from typing import Annotated

from fastapi import Depends

from zakup.platform.di import Stub
from zakup.shared_kernel.auth import Principal

CurrentPrincipal = Annotated[Principal, Depends(Stub(Principal))]
