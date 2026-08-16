from fastapi import Request
from fastapi.responses import JSONResponse

from .config import get_settings
from .utils.security import redact_secrets


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: object | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    settings = get_settings()
    secrets = [getattr(settings, "nptel_cookie", "")]
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": redact_secrets(exc.message, secrets),
                "details": redact_secrets(exc.details, secrets),
            }
        },
    )
