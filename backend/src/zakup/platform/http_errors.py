"""Xatolar → HTTP javoblari. Yagona format: {"code": ..., "message": ..., ["fields": ...]}.

`code` — mashina uchun (frontend shunga qarab ishlaydi), `message` — foydalanuvchi tilida (Accept-Language).
"""

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from zakup.platform.i18n import negotiate_locale, translate
from zakup.shared_kernel.errors import ConflictError, DomainError, NotFoundError, PermissionDeniedError

log = structlog.get_logger()

_STATUS: list[tuple[type[DomainError], int]] = [
    (NotFoundError, 404),
    (ConflictError, 409),
    (PermissionDeniedError, 403),
    (DomainError, 422),
]


def _status_for(exc: DomainError) -> int:
    return next(status for cls, status in _STATUS if isinstance(exc, cls))


async def _domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    message = translate(exc.key, negotiate_locale(request.headers.get("accept-language")), exc.params)
    return JSONResponse(status_code=_status_for(exc), content={"code": exc.code, "message": message})


async def _validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    locale = negotiate_locale(request.headers.get("accept-language"))
    # Maydon darajasidagi xatolar: frontend `loc` bo'yicha o'z tilida ko'rsatadi
    fields = [{"loc": [str(part) for part in err["loc"]], "type": err["type"]} for err in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"code": "validation_error", "message": translate("validation_error", locale), "fields": fields},
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_error", path=request.url.path, exc_info=exc)
    locale = negotiate_locale(request.headers.get("accept-language"))
    return JSONResponse(
        status_code=500, content={"code": "internal_error", "message": translate("internal_error", locale)}
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
