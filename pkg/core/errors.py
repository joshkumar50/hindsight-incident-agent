import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger("errors")


class ErrorResponse(BaseModel):
    """Standardized API Error Response for all Hindsight Incident Agent â€” Autonomous SRE Platform services."""

    error_code: str
    message: str
    details: dict | None = None


class HindsightIncidentAgentException(Exception):
    """Base exception class for all custom domain errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: dict = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


def register_error_handlers(app: FastAPI):
    """Registers global exception handlers to enforce standard error responses."""

    @app.exception_handler(HindsightIncidentAgentException)
    async def hindsight_agent_exception_handler(request: Request, exc: HindsightIncidentAgentException):
        logger.error(
            "hindsight_agent_exception",
            error_code=exc.error_code,
            message=exc.message,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=exc.error_code, message=exc.message, details=exc.details
            ).model_dump(),
        )

    # FIX: Catch FastAPI Validation Errors (422) and coerce to our schema
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        logger.warn("validation_error", errors=exc.errors(), path=request.url.path)
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error_code="VALIDATION_ERROR",
                message="Request payload validation failed.",
                details={"errors": exc.errors()},
            ).model_dump(),
        )

    # FIX: Catch standard HTTP Exceptions (e.g. 404, 401) and coerce to our schema
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warn(
            "http_exception",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=f"HTTP_{exc.status_code}", message=str(exc.detail)
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            exception=str(exc),
            path=request.url.path,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred processing the request.",
            ).model_dump(),
        )
